
import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx

_HERE = Path(__file__).resolve()
_ROOT = next((p.parent for p in _HERE.parents if p.name == "pipeline"), _HERE.parents[2])
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from pipeline.cli import add_standard_args, resolve_settings
from ..core.config import ConfigError, Settings
from ..core.sei_client import (
    DEFAULT_SEI_BASE_URL,
    resolve_token,
    try_download_with_unidades,
)
from ..core.doc_store import DocumentStore, FsDocumentStore, OutcomeLedger
from ..core.logging_setup import configure_logging
from ..core.neo4j_driver import build_driver





log = configure_logging(__name__)


QUERY_PROCESSOS_BY_ORGAO = """
MATCH (p:Processo)-[:CRIADO_NO_ORGAO]->(o:Orgao {sigla: $orgao})
OPTIONAL MATCH (p)-[:PASSOU_PELA_UNIDADE]->(u:Unidade)
WITH p, collect(DISTINCT {sigla: u.sigla, id_unidade: u.id_unidade}) AS unidades_raw
OPTIONAL MATCH (p)-[:CONTEM_DOCUMENTO]->(d:Documento)
OPTIONAL MATCH (a:Atividade)-[:REFERENCIA_DOCUMENTO]->(d)
WITH p, unidades_raw, d, toString(min(a.data_hora)) AS ordem
WITH p, unidades_raw,
     collect(CASE WHEN d IS NULL THEN null
                  ELSE {numero: d.numero, tipo: d.tipo, ordem: ordem} END) AS documentos_raw
RETURN p.protocolo_formatado AS protocolo,
       [x IN documentos_raw WHERE x IS NOT NULL] AS documentos,
       [x IN unidades_raw WHERE x.sigla IS NOT NULL] AS unidades
"""

QUERY_PROCESSOS_BY_PROTOCOLO = """
MATCH (p:Processo)
WHERE p.protocolo_formatado IN $protocolos
OPTIONAL MATCH (p)-[:PASSOU_PELA_UNIDADE]->(u:Unidade)
WITH p, collect(DISTINCT {sigla: u.sigla, id_unidade: u.id_unidade}) AS unidades_raw
OPTIONAL MATCH (p)-[:CONTEM_DOCUMENTO]->(d:Documento)
OPTIONAL MATCH (a:Atividade)-[:REFERENCIA_DOCUMENTO]->(d)
WITH p, unidades_raw, d, toString(min(a.data_hora)) AS ordem
WITH p, unidades_raw,
     collect(CASE WHEN d IS NULL THEN null
                  ELSE {numero: d.numero, tipo: d.tipo, ordem: ordem} END) AS documentos_raw
RETURN p.protocolo_formatado AS protocolo,
       [x IN documentos_raw WHERE x IS NOT NULL] AS documentos,
       [x IN unidades_raw WHERE x.sigla IS NOT NULL] AS unidades
"""

QUERY_DOC_CREATORS = """
MATCH (p:Processo {protocolo_formatado: $protocolo})-[:CONTEM_DOCUMENTO]->(d:Documento)
OPTIONAL MATCH (a:Atividade)-[:REFERENCIA_DOCUMENTO]->(d)
WHERE a.tipo_acao IN ['GERACAO-DOCUMENTO', 'ARQUIVO-ANEXADO', 'RECEBIMENTO-DOCUMENTO']
OPTIONAL MATCH (a)-[:EXECUTADO_PELA_UNIDADE]->(u:Unidade)
RETURN d.numero AS doc_numero, u.sigla AS unidade_sigla, u.id_unidade AS id_unidade
"""





















def _order_and_limit_docs(documentos: list[dict], only_first_doc: bool) -> list[dict]:
    ordered = sorted(documentos, key=lambda d: (d.get("ordem") is None, d.get("ordem") or ""))
    return ordered[:1] if only_first_doc else ordered


def fetch_processos_from_neo4j(
    settings: Settings,
    orgao: str,
    protocolos: list[str] | None = None,
) -> list[dict]:
    log.info("Connecting to Neo4j: %s", settings.neo4j_uri)
    driver = build_driver(settings)
    log.info("Neo4j connected")

    processos: list[dict] = []
    try:
        with driver.session() as session:
            if protocolos:
                log.info("Querying %d specific processos", len(protocolos))
                result = session.run(QUERY_PROCESSOS_BY_PROTOCOLO, protocolos=protocolos)
            else:
                log.info("Querying processos for orgão: %s", orgao)
                result = session.run(QUERY_PROCESSOS_BY_ORGAO, orgao=orgao)
            for record in result:
                protocolo = record["protocolo"]
                documentos = record["documentos"]
                unidades = record["unidades"]
                documentos = [d for d in documentos if d.get("numero")]
                unidades = [u for u in unidades if u.get("id_unidade")]
                if documentos:
                    processos.append({
                        "protocolo": protocolo,
                        "documentos": documentos,
                        "unidades": unidades,
                    })

            log.info("Fetching document creator unidades for %d processos...", len(processos))
            for p in processos:
                doc_creators: dict = {}
                result = session.run(QUERY_DOC_CREATORS, protocolo=p["protocolo"])
                for rec in result:
                    doc_num = rec["doc_numero"]
                    if doc_num and rec["id_unidade"]:
                        doc_creators[doc_num] = {
                            "sigla": rec["unidade_sigla"],
                            "id_unidade": rec["id_unidade"],
                        }
                p["doc_creators"] = doc_creators
    finally:
        driver.close()

    return processos


def download_processo_docs(
    processo: dict,
    token: str,
    store: DocumentStore,
    ledger: OutcomeLedger,
    login_orgao: str = "",
    success_stats: dict | None = None,
    dry_run: bool = False,
    sei_base_url: str = DEFAULT_SEI_BASE_URL,
) -> dict:
    protocolo = processo["protocolo"]
    documentos = processo["documentos"]
    unidades = processo["unidades"]
    doc_creators = processo.get("doc_creators", {})

    stats = {"total": len(documentos), "downloaded": 0, "failed": 0, "skipped": 0, "cancelled": 0}

    if not unidades:
        log.warning("Processo %s has no unidades — skipping %d docs", protocolo, len(documentos))
        stats["skipped"] = len(documentos)
        return stats

    if dry_run:
        log.info(
            "[DRY-RUN] Processo %s: %d documentos, %d unidades to try",
            protocolo, len(documentos), len(unidades),
        )
        return stats

    with httpx.Client(verify=False) as client:
        for doc in documentos:
            numero = doc["numero"]

            if store.exists(protocolo, numero):
                log.info("  Already stored, skipping: %s/%s", protocolo, numero)
                stats["skipped"] += 1
                continue
            if ledger.seen_terminal(protocolo, numero) == "cancelled":
                log.info("  Known-cancelled, skipping: %s/%s", protocolo, numero)
                stats["skipped"] += 1
                continue

            creator = doc_creators.get(numero)

            result, used_unidade, status = try_download_with_unidades(
                client, token, numero, unidades,
                login_orgao=login_orgao,
                doc_creator_unidade=creator,
                success_stats=success_stats,
                sei_base_url=sei_base_url,
            )

            if result is None:
                ledger.record(protocolo, numero, status,
                              unidades_tried=[u.get("sigla") for u in unidades])
                if status == "cancelled":
                    stats["cancelled"] += 1
                else:
                    log.warning("FAILED doc %s in processo %s (tried %d unidades)", numero, protocolo, len(unidades))
                    stats["failed"] += 1
                continue

            location = store.put(protocolo, numero, result["filename"], result["content"])
            ledger.record(protocolo, numero, "ok",
                          unidades_tried=[used_unidade] if used_unidade else [])
            stats["downloaded"] += 1
            log.debug(
                "Downloaded %s → %s (unidade=%s, %d bytes)",
                numero, location, used_unidade, len(result["content"]),
            )

    return stats


def _execute(args, settings, progress=None) -> dict:
    sei_base_url = getattr(settings, "sei_base_url", None) or DEFAULT_SEI_BASE_URL

    token = resolve_token(args, settings)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        processos = fetch_processos_from_neo4j(settings, args.orgao, args.processo)
    except ConfigError as e:
        log.error("%s", e)
        sys.exit(2)
    if args.limit > 0:
        processos = processos[:args.limit]

    for p in processos:
        p["documentos"] = _order_and_limit_docs(p["documentos"], args.only_first_doc)

    total_docs = sum(len(p["documentos"]) for p in processos)
    filter_desc = f"protocolos {args.processo}" if args.processo else f"orgão {args.orgao}"
    log.info(
        "Found %d processos with %d documents (%s)",
        len(processos), total_docs, filter_desc,
    )

    if not processos:
        log.info("Nothing to download.")
        return {"total": 0, "downloaded": 0, "failed": 0, "skipped": 0, "cancelled": 0,
                "processos": 0}

    if args.dry_run:
        for p in processos:
            log.info(
                "  %s: %d docs, unidades: %s",
                p["protocolo"],
                len(p["documentos"]),
                ", ".join(u["sigla"] for u in p["unidades"]),
            )
        log.info("DRY-RUN complete. Use without --dry-run to download.")
        return {"total": 0, "downloaded": 0, "failed": 0, "skipped": 0, "cancelled": 0,
                "processos": len(processos), "dry_run": True}

    store = FsDocumentStore(output_dir)
    ledger = OutcomeLedger(output_dir / "_download_log.ndjson")
    if progress is not None:
        progress.set_total(len(processos))
    success_stats: dict[str, int] = {}
    totals = {"total": 0, "downloaded": 0, "failed": 0, "skipped": 0, "cancelled": 0}
    completed = 0

    log.info("Unidade priority: 1) doc creator, 2) %s unidades, 3) others", args.orgao)

    def _do_download(processo):
        return download_processo_docs(
            processo, token, store, ledger,
            login_orgao=args.orgao,
            success_stats=success_stats,
            sei_base_url=sei_base_url,
        )

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(_do_download, p): p["protocolo"] for p in processos}
        for future in as_completed(futures):
            protocolo = futures[future]
            completed += 1
            try:
                stats = future.result()
                for k in totals:
                    totals[k] += stats[k]
                log.info(
                    "[%d/%d] Processo %s: %d downloaded, %d failed, %d cancelled, %d skipped",
                    completed, len(processos), protocolo,
                    stats["downloaded"], stats["failed"], stats["cancelled"], stats["skipped"],
                )
            except Exception as e:
                log.error("[%d/%d] Processo %s ERROR: %s", completed, len(processos), protocolo, e)
            if progress is not None:
                progress.advance()

    log.info(
        "DONE. Total: %d docs | Downloaded: %d | Failed: %d | Cancelled: %d | Skipped: %d",
        totals["total"], totals["downloaded"], totals["failed"], totals["cancelled"], totals["skipped"],
    )
    totals["processos"] = len(processos)
    return totals


def main():
    parser = argparse.ArgumentParser(description=f"Download {ORGAO_SIGLA} processo documents from SEI")

    auth = parser.add_argument_group("authentication (pick one)")
    auth.add_argument("--token", help="SEI API token")
    auth.add_argument("--usuario", help="SEI username for direct login")
    auth.add_argument("--senha", help="SEI password for direct login")

    parser.add_argument("--output", default="./documentos_sead", help="Output directory (default: ./documentos_sead)")
    parser.add_argument("--orgao", default=ORGAO_SIGLA,
                        help=f"Orgão sigla to filter (default: {ORGAO_SIGLA})")
    parser.add_argument("--processo", nargs="+", default=None, help="Specific protocolo(s) to download (overrides --orgao)")
    parser.add_argument("--dry-run", action="store_true", help="Only list what would be downloaded")
    parser.add_argument("--only-first-doc", action="store_true",
                        help="Download only the chronologically-first (initiating) document of each processo")
    parser.add_argument("--workers", type=int, default=3, help="Parallel processo workers (default: 3)")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of processos (0=all)")
    add_standard_args(parser, skip={"--read-json", "--workers"})
    args = parser.parse_args()

    settings = resolve_settings(args)
    configure_logging(__name__, settings.log_level)
    _execute(args, settings)


from argparse import Namespace as _Namespace

from ..core.deployment import ORGAO_SIGLA
from ..core._stage_base import RunContext, StageMeta
from ..core.registry import stage


@stage(StageMeta(
    name="download",
    phase="ingest",
    question="Qual o documento de abertura de cada processo?",
    deterministic='conditional',
    nondeterminism="depende da disponibilidade do documento no SEI no momento da chamada",
    description="Baixa documentos do SEI listados no grafo (ou via --processo).",
    type="enrich",
    depends_on=(),
    soft_depends_on=("atividades",),
    modes=("fs",),
    estimated_duration="depende do volume; ~1-3 docs/s",
))
def run(ctx: RunContext) -> None:
    args = _Namespace(
        token=ctx.flags.get("token"),
        usuario=ctx.flags.get("usuario"),
        senha=ctx.flags.get("senha"),
        output=ctx.flags.get("output", "./documentos_sead"),
        orgao=ctx.flags.get("orgao", ORGAO_SIGLA),
        processo=ctx.flags.get("processo"),
        dry_run=bool(ctx.flags.get("dry_run", False)),
        only_first_doc=str(ctx.flags.get("only_first_doc", "")).lower() in {"1", "true", "yes", "on"},
        workers=int(ctx.flags.get("workers") or 3),
        limit=int(ctx.flags.get("limit") or 0),
    )
    totals = _execute(args, ctx.settings, progress=ctx.progress) or {}
    ctx.cache["download_summary"] = totals


if __name__ == "__main__":
    main()
