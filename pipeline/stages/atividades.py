
from __future__ import annotations

import logging
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import perf_counter

from ..core._stage_base import RunContext, StageMeta
from ..model.classifier import transform_row
from ..core.config import Settings
from ..core.cypher import LOAD_ATIVIDADE_NODES_CYPHER, LOAD_DOCUMENTO_EDGES_CYPHER, LOAD_TIPO_ACAO_EDGES_CYPHER, LOAD_UNIDADE_EDGES_CYPHER, LOAD_USUARIO_EDGES_CYPHER
from ..model.discovery import discover
from ..core.registry import stage
from ..core.sql import FETCH_ANDAMENTOS_SQL
from ..core.trino_source import literal_date_filter
from ..core.trino_source import make_trino_conn, sql_quote_list
from ..writers import GraphWriter

log = logging.getLogger(__name__)


_UNIDADE_LOCK = threading.Lock()
_TIPO_LOCK = threading.Lock()
_USUARIO_LOCK = threading.Lock()
_DOC_LOCK = threading.Lock()

_TIMINGS_LOCK = threading.Lock()
_TIMINGS = {
    "fetch": 0.0, "nodes": 0.0, "edge_wait": 0.0,
    "unidade_hold": 0.0, "tipo_hold": 0.0, "usuario_hold": 0.0, "doc_hold": 0.0,
}


def _add_timing(key: str, dt: float) -> None:
    with _TIMINGS_LOCK:
        _TIMINGS[key] += dt


def _reset_timings() -> None:
    with _TIMINGS_LOCK:
        for k in _TIMINGS:
            _TIMINGS[k] = 0.0


def _snapshot_timings() -> dict[str, float]:
    with _TIMINGS_LOCK:
        return dict(_TIMINGS)


def _write_atividade_nodes(writer: GraphWriter, transformed: list[dict]) -> None:
    writer.execute_template(
        "load_atividade_nodes", LOAD_ATIVIDADE_NODES_CYPHER,
        {"rows": transformed}, phase="B",
    )


def _locked_dim_write(writer, lock, name, cypher, rows, dim) -> None:
    if not rows:
        return
    t_req = perf_counter()
    with lock:
        t_acq = perf_counter()
        _add_timing("edge_wait", t_acq - t_req)
        writer.execute_template(name, cypher, {"rows": rows}, phase="B")
        _add_timing(f"{dim}_hold", perf_counter() - t_acq)


def _write_atividade_edges(writer: GraphWriter, transformed: list[dict]) -> None:
    rows = [
        {
            "source_id": t["source_id"],
            "unidade": t["unidade"],
            "tipo_acao": t["tipo_acao"],
            "usuario": t["usuario"],
            "protocolo_formatado": t["protocolo_formatado"],
            "source_unidade": t["source_unidade"],
            "numero": t["doc_info"]["numero"] if t["doc_info"] else None,
            "tipo": t["doc_info"]["tipo"] if t["doc_info"] else None,
            "serie_id": t["doc_info"]["serie_id"] if t["doc_info"] else None,
        }
        for t in transformed
    ]
    doc_rows = [r for r in rows if r["numero"] is not None]

    _locked_dim_write(writer, _UNIDADE_LOCK, "load_unidade_edges", LOAD_UNIDADE_EDGES_CYPHER, rows, "unidade")
    _locked_dim_write(writer, _TIPO_LOCK, "load_tipo_acao_edges", LOAD_TIPO_ACAO_EDGES_CYPHER, rows, "tipo")
    _locked_dim_write(writer, _USUARIO_LOCK, "load_usuario_edges", LOAD_USUARIO_EDGES_CYPHER, rows, "usuario")
    _locked_dim_write(writer, _DOC_LOCK, "load_documento_edges", LOAD_DOCUMENTO_EDGES_CYPHER, doc_rows, "doc")


def load_atividades_batch(writer: GraphWriter, transformed: list[dict]) -> None:
    t0 = perf_counter()
    _write_atividade_nodes(writer, transformed)
    _add_timing("nodes", perf_counter() - t0)
    _write_atividade_edges(writer, transformed)


def process_chunk(
    protocolo_ids: list[str],
    writer: GraphWriter | None,
    dry_run: bool,
    batch_size: int,
    settings: Settings,
    date_filter: str = "",
) -> tuple[int, Counter, list[str], set[str]]:
    _t_fetch = perf_counter()
    conn = make_trino_conn(settings)
    try:
        in_list = sql_quote_list(protocolo_ids)
        cursor = conn.cursor()
        cursor.execute(FETCH_ANDAMENTOS_SQL.format(in_list=in_list, date_filter=date_filter))
        cols = [c[0] for c in cursor.description]
        rows = [dict(zip(cols, r)) for r in cursor.fetchall()]
        cursor.close()
    finally:
        conn.close()
    _add_timing("fetch", perf_counter() - _t_fetch)

    if not rows:
        log.warning("  Chunk has 0 matching rows for %d IDs! Sample: %s",
                    len(protocolo_ids), protocolo_ids[:5])
    else:
        log.info("  Chunk: %d IDs -> %d rows", len(protocolo_ids), len(rows))

    total_rows = 0
    stats: Counter = Counter()
    unclassified: list[str] = []
    unidades: set[str] = set()
    seq_counters: dict[str, int] = {}

    batch: list[dict] = []
    for d in rows:
        pf = d["protocolo_formatado"]
        seq_counters[pf] = seq_counters.get(pf, 0) + 1
        t = transform_row(d, seq_counters[pf])
        batch.append(t)
        stats[t["tipo_acao"]] += 1
        unidades.add(t["unidade"])
        if t["source_unidade"]:
            unidades.add(t["source_unidade"])
        if t["tipo_acao"] == "OUTROS" and len(unclassified) < 20:
            desc = t["descricao"][:100]
            if desc not in unclassified:
                unclassified.append(desc)

        if len(batch) >= batch_size:
            total_rows += len(batch)
            if not dry_run and writer is not None:
                load_atividades_batch(writer, batch)
            batch = []

    if batch:
        total_rows += len(batch)
        if not dry_run and writer is not None:
            load_atividades_batch(writer, batch)

    return total_rows, stats, unclassified, unidades


@stage(StageMeta(
    name="atividades",
    phase="graph",
    question="Quais atividades cada processo registrou, e sob que unidade?",
    deterministic='conditional',
    nondeterminism="o lakehouse esta sob curadoria ativa; o resultado e fixo por snapshot",
    description="Carrega Atividades + arestas (DO_PROCESSO, EXECUTADO_PELA_UNIDADE, …).",
    type="core",
    depends_on=("precreate",),
    modes=("neo4j", "json-emit"),
    estimated_duration="~20-60min para 1M atividades",
))
def run(ctx: RunContext) -> None:
    ctx.settings.require_trino()
    discovery = ctx.cached(
        "discovery",
        lambda: discover(
            ctx.settings,
            ctx.flags.get("from_date"),
            ctx.flags.get("to_date"),
            ctx.flags.get("orgao"),
            ctx.flags.get("limit"),
            status=ctx.flags.get("status"),
            concluded_before=ctx.flags.get("concluded_before"),
        ),
    )
    protocolo_ids = discovery["protocolo_ids"]
    if not protocolo_ids:
        log.info("No processos discovered — skipping atividades.")
        ctx.cache["atividades_summary"] = {"atividades_loaded": 0, "failed_chunks": 0}
        return

    writer = ctx.require_writer()
    workers = int(ctx.flags.get("workers") or ctx.settings.workers or 8)
    chunk_size = int(ctx.flags.get("chunk_size") or 200)
    batch_size = int(ctx.flags.get("batch_size") or ctx.settings.batch_size or 500)

    chunks = [protocolo_ids[i:i + chunk_size] for i in range(0, len(protocolo_ids), chunk_size)]
    log.info(
        "atividades: %d processos in %d chunks, %d workers",
        len(protocolo_ids), len(chunks), workers,
    )
    date_filter = literal_date_filter(ctx.flags.get("from_date"), ctx.flags.get("to_date"))
    log.info("atividades: activity window filter = %s", date_filter or "(none)")
    _reset_timings()
    ctx.progress.set_total(len(chunks))

    grand_total = 0
    grand_stats: Counter = Counter()
    all_unclassified: list[str] = []
    completed_chunks = 0
    failed_chunks = 0

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(process_chunk, chunk, writer, False, batch_size, ctx.settings, date_filter): i
            for i, chunk in enumerate(chunks)
        }
        for future in as_completed(futures):
            chunk_idx = futures[future]
            try:
                count, stats, unclassified, _units = future.result()
                grand_total += count
                grand_stats += stats
                for desc in unclassified:
                    if desc not in all_unclassified and len(all_unclassified) < 50:
                        all_unclassified.append(desc)
                completed_chunks += 1
                if completed_chunks % 10 == 0 or completed_chunks == len(chunks):
                    log.info(
                        "  Progress: %d/%d chunks (%d rows)",
                        completed_chunks, len(chunks), grand_total,
                    )
            except Exception:
                log.exception("Failed chunk %d", chunk_idx)
                failed_chunks += 1
            ctx.progress.advance()

    log.info("atividades complete: %d rows, %d failed chunks", grand_total, failed_chunks)
    _t = _snapshot_timings()
    log.info(
        "atividades timings (summed across %d workers): fetch=%.1fs nodes=%.1fs "
        "edge_wait=%.1fs | holds: unidade=%.1fs tipo=%.1fs usuario=%.1fs doc=%.1fs",
        workers, _t["fetch"], _t["nodes"], _t["edge_wait"],
        _t["unidade_hold"], _t["tipo_hold"], _t["usuario_hold"], _t["doc_hold"],
    )
    if grand_stats:
        log.info("Classification distribution:")
        for tipo, count in grand_stats.most_common():
            log.info("  %-45s %6d", tipo, count)

    ctx.cache["atividades_summary"] = {
        "atividades_loaded": grand_total,
        "failed_chunks": failed_chunks,
        "chunks": len(chunks),
    }
