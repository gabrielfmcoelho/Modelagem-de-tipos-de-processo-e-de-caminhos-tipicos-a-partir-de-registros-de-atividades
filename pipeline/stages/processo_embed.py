
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

import numpy as np

from ..core._stage_base import RunContext, StageMeta
from ..core.cypher import CLEAR_PROCESSO_CLUSTER_FEATURES_CYPHER, LIST_PROCESSOS_FOR_CLUSTERING_CYPHER, LOAD_PROCESSO_CLUSTER_FEATURES_CYPHER
from ..model.embedding import build_embedder
from ..model.processo_features import ALGO_VERSION, BlockWeights, FeatureWeights, ProcessoInput, apply_cutoff, build_batch_features, feature_hash, reduce_with_umap
from ..core.registry import stage
from ..core.state import now_iso
from ..core.paths import ARTIFACTS
from ..evidence.artifact import write_sidecar

log = logging.getLogger(__name__)


def _flag_float(ctx, key: str, default: float) -> float:
    v = ctx.flags.get(key)
    return float(v) if v not in (None, "") else default


def feature_digest(pairs) -> str:
    h = hashlib.sha256()
    for pf, fh in sorted(pairs):
        h.update(f"{pf}:{fh}\n".encode("utf-8"))
    return h.hexdigest()[:16]


def resolve_text_variant(explicit: str | None, state_dir: Path | None = None) -> str:
    if explicit:
        return explicit
    base = state_dir or Path(".pipeline-state") / "stages"
    try:
        args = json.loads((base / "embed.json").read_text(encoding="utf-8")).get("args") or {}
    except Exception:
        return "unknown"
    return str(args.get("text_variant") or "unknown")


def _export_features_npz(path: Path, protocolos: list[str], features: np.ndarray,
                         *, digest: str = "", text_variant: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        protocolos=np.asarray(protocolos, dtype=str),
        features=np.asarray(features, dtype=np.float32),
        digest=np.asarray(digest, dtype=str),
        text_variant=np.asarray(text_variant, dtype=str),
    )
    write_sidecar(path, stage="processo-embed",
                  params={"n_processos": len(protocolos),
                          "dim": int(features.shape[1]) if features.ndim == 2 else None,
                          "feature_hash": digest, "text_variant": text_variant})


def load_keywords_by_processo(parsed_dir="./parsed_documents") -> dict[str, list[str]]:
    from ..model.keywords import load_keywords_store
    store = load_keywords_store()
    if store:
        return store
    out: dict[str, tuple[str, list[str]]] = {}
    for meta_path in Path(parsed_dir).glob("*/metadata.json"):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        pf = (meta.get("protocolo") or "").replace("_", "/")
        numero = meta.get("documento_numero") or ""
        if not pf or not numero:
            continue
        prev = out.get(pf)
        if prev is None or numero < prev[0]:
            out[pf] = (numero, list(meta.get("keywords") or []))
    return {pf: kws for pf, (_, kws) in out.items() if kws}


def _embedded_documentos(docs_raw: list[dict]) -> list[dict]:
    ordered = sorted(docs_raw or [], key=lambda d: (d or {}).get("first_seen") or "")
    return [
        {"numero": d["numero"], "embedding": d["embedding"],
         "embedding_hash": d.get("embedding_hash") or "",
         "topic": d.get("topic") or "", "summary": d.get("summary") or ""}
        for d in ordered if d and d.get("embedding")
    ]


TOPIC_CACHE_PATH = ARTIFACTS / "cache" / "topic_embeddings.npz"
TOPIC_BATCH = 32


def topic_key(text: str, model: str) -> str:
    h = hashlib.sha256()
    h.update(model.encode("utf-8"))
    h.update(b"\x00")
    h.update(text.encode("utf-8", errors="ignore"))
    return h.hexdigest()


def load_topic_cache(path: Path = TOPIC_CACHE_PATH) -> dict[str, list[float]]:
    if not Path(path).is_file():
        return {}
    z = np.load(path, allow_pickle=False)
    return {str(k): v.tolist() for k, v in zip(z["keys"], z["vecs"])}


def save_topic_cache(cache: dict[str, list[float]], path: Path = TOPIC_CACHE_PATH) -> None:
    if not cache:
        return
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = sorted(cache)
    np.savez_compressed(
        path,
        keys=np.asarray(keys, dtype=str),
        vecs=np.asarray([cache[k] for k in keys], dtype=np.float32),
    )
    write_sidecar(path, stage="processo-embed",
                  params={"n_vectors": len(keys), "cache": "topic embeddings"})


def _attach_first_doc_topic_embeddings(pending: list[ProcessoInput], settings,
                                       cache_path: Path = TOPIC_CACHE_PATH) -> int:
    items: list[tuple[int, str]] = []
    for i, p in enumerate(pending):
        docs = [d for d in p.documentos if d.get("embedding")]
        if not docs:
            continue
        first = docs[0]
        topic = (first.get("topic") or "").strip()
        summary = (first.get("summary") or "").strip()
        if not topic and not summary:
            continue
        items.append((i, f"{topic}. {summary}".strip()))
    if not items:
        return 0
    try:
        embedder = build_embedder(settings)
    except Exception as e:
        log.warning("processo-embed: topic embedding unavailable (%s) — topic block will be zeros", e)
        return 0
    model = getattr(embedder, "model_name", "unknown")
    cache = load_topic_cache(cache_path)
    keys = [topic_key(t, model) for _, t in items]
    missing = sorted({k: t for k, (_, t) in zip(keys, items) if k not in cache}.items())
    log.info("processo-embed: topic embeddings %d cached, %d to compute (batch=%d)",
             len(items) - len(missing), len(missing), TOPIC_BATCH)
    try:
        for start in range(0, len(missing), TOPIC_BATCH):
            chunk = missing[start:start + TOPIC_BATCH]
            vecs = embedder.embed_batch([t for _, t in chunk])
            for (k, _), v in zip(chunk, vecs):
                cache[k] = list(v)
    except Exception as e:
        log.warning("processo-embed: topic embedding failed (%s) — topic block will be zeros", e)
        return 0
    save_topic_cache(cache, cache_path)
    n = 0
    for (i, _), k in zip(items, keys):
        v = cache.get(k)
        if v is not None:
            pending[i].first_doc_topic_embedding = list(v)
            n += 1
    return n


@stage(StageMeta(
    name="processo-embed",
    phase="features",
    question="Que vetor representa cada processo, fundindo conteudo e forma?",
    deterministic='conditional',
    nondeterminism="UMAP fixado por seed; dois blocos de feature vem de LLM a montante",
    description="Agrega 1º-doc semantic + topic/summary + TF-IDF de unidades + tipo_acao + UMAP → :Processo.cluster_features.",
    type="enrich",
    depends_on=("embed",),
    soft_depends_on=("permanencia", "atividades", "evaluate"),
    modes=("neo4j", "json-emit"),
    estimated_duration="~5-10min para 12k processos com embeddings prontos",
))
def run(ctx: RunContext) -> None:
    driver = ctx.require_driver()
    writer = ctx.require_writer()

    weights = FeatureWeights(
        first_doc_weight=float(ctx.flags.get("first_doc_weight") or 3.0),
        early_doc_weight=float(ctx.flags.get("early_doc_weight") or 1.5),
        early_doc_until_rank=int(ctx.flags.get("early_doc_until_rank") or 3),
        default_doc_weight=float(ctx.flags.get("default_doc_weight") or 1.0),
    )
    first_doc_only = str(ctx.flags.get("first_doc_only", "true")).strip().lower() not in ("false", "0", "no")
    block_weights = BlockWeights(
        semantic=_flag_float(ctx, "semantic_weight", 1.0),
        topic=_flag_float(ctx, "topic_weight", 1.0),
        unigram=_flag_float(ctx, "unigram_weight", 1.0),
        bigram=_flag_float(ctx, "bigram_weight", 1.0),
        tipo_acao=_flag_float(ctx, "tipo_acao_weight", 1.0),
        keyword=_flag_float(ctx, "keyword_weight", 1.0),
    )
    n_components = int(ctx.flags.get("umap_n_components") or 50)
    unigram_max = int(ctx.flags.get("unigram_max_features") or 500)
    bigram_max = int(ctx.flags.get("bigram_max_features") or 1000)
    cutoff_frac = float(ctx.flags.get("cutoff_frac") or 1.0)
    limit = int(ctx.flags.get("limit") or 0)
    force_all = bool(ctx.flags.get("force_all", False))
    only_situacao = (ctx.flags.get("only_situacao") or "").strip()
    export_path = (ctx.flags.get("export_features") or "").strip()

    log.info(
        "processo-embed: first_doc_only=%s, only_situacao=%s, block_weights=%s, weights=%s, umap_n=%d, unigram_max=%d, bigram_max=%d",
        first_doc_only, only_situacao or "(all)", block_weights, weights, n_components, unigram_max, bigram_max,
    )

    keywords_by_pf = load_keywords_by_processo(ctx.flags.get("parsed_dir") or "./parsed_documents")
    log.info("processo-embed: keywords available for %d processos", len(keywords_by_pf))

    processos_input: list[ProcessoInput] = []
    existing_hash: dict[str, str] = {}
    sem_documento: list[str] = []
    fora_situacao: list[str] = []

    with driver.session() as session:
        result = session.run(LIST_PROCESSOS_FOR_CLUSTERING_CYPHER)
        for record in result:
            pf = record["protocolo"]
            existing_hash[pf] = record.get("cluster_features_hash") or ""

            if only_situacao and (record.get("situacao") or "") != only_situacao:
                fora_situacao.append(pf)
                continue

            documentos = _embedded_documentos(list(record.get("documentos_raw") or []))
            if not documentos:
                sem_documento.append(pf)
                continue

            events = list(record.get("unidade_events_raw") or [])
            atividades = list(record.get("atividades_raw") or [])
            if cutoff_frac < 1.0:
                events, atividades = apply_cutoff(events, atividades, cutoff_frac)
            events.sort(key=lambda ev: ev.get("ts") or "")
            cronologia = [ev["u"] for ev in events if ev.get("u")]
            if cutoff_frac < 1.0:
                unidades = [ev["u"] for ev in events if ev.get("u")]
            else:
                unidades = list(record.get("unidades_visitadas") or [])

            tipos = [a["t"] for a in atividades if a.get("t")]
            processos_input.append(ProcessoInput(
                protocolo_formatado=pf,
                documentos=documentos,
                unidades_visitadas=unidades,
                unidades_cronologicas=cronologia,
                atividades_tipo_acao=tipos,
                keywords=keywords_by_pf.get(pf),
            ))
            if limit and len(processos_input) >= limit:
                break

    log.info(
        "processo-embed: clustering corpus = %d processos; discarded %d without a first "
        "document and %d outside situacao=%s",
        len(processos_input), len(sem_documento), len(fora_situacao), only_situacao or "(any)",
    )

    discarded = sem_documento + fora_situacao
    if discarded:
        writer.open_phase("processo-embed-discard")
        try:
            for i in range(0, len(discarded), 500):
                writer.execute_template(
                    "clear_processo_cluster_features",
                    CLEAR_PROCESSO_CLUSTER_FEATURES_CYPHER,
                    {"protocolos": discarded[i:i + 500]},
                    phase="processo-embed-discard",
                )
        finally:
            writer.close_phase("processo-embed-discard")

    if not processos_input:
        ctx.cache["processo_embed_summary"] = {
            "total": 0, "computed": 0, "skipped": 0,
            "discarded_sem_documento": len(sem_documento),
            "discarded_fora_situacao": len(fora_situacao),
        }
        return

    pending: list[ProcessoInput] = []
    skipped = 0
    for p in processos_input:
        h = feature_hash(p, weights, ALGO_VERSION,
                         first_doc_only=first_doc_only, block_weights=block_weights,
                         cutoff_frac=cutoff_frac)
        if not force_all and existing_hash.get(p.protocolo_formatado) == h:
            skipped += 1
            continue
        pending.append(p)

    log.info("processo-embed: %d pending, %d skipped (hash match)", len(pending), skipped)
    if not pending:
        if export_path:
            log.warning("processo-embed: export_features=%s requested but nothing computed — no npz written (use force_all=true)", export_path)
        ctx.cache["processo_embed_summary"] = {
            "total": len(processos_input), "computed": 0, "skipped": skipped,
            "discarded_sem_documento": len(sem_documento),
            "discarded_fora_situacao": len(fora_situacao),
        }
        return

    n_topic = _attach_first_doc_topic_embeddings(pending, ctx.settings)
    log.info("processo-embed: attached %d first-doc topic embeddings", n_topic)
    if pending and n_topic == 0:
        raise RuntimeError(
            f"processo-embed: 0 of {len(pending)} processos carry a first-doc topic — the topic "
            "block would be all zeros. :Documento.topic is empty in Neo4j; run "
            "`pipeline run evaluate --no-deps` to sync the on-disk evaluations back into the graph."
        )

    log.info("processo-embed: composing raw feature matrix...")
    batch = build_batch_features(
        pending, weights=weights, block_weights=block_weights,
        first_doc_only=first_doc_only,
        unigram_max_features=unigram_max,
        bigram_max_features=bigram_max,
        keyword_max_features=int(ctx.flags.get("keyword_max_features") or 1500),
        keyword_min_df=int(ctx.flags.get("keyword_min_df") or 3),
    )
    log.info(
        "processo-embed: raw shape=%s (semantic=%d, topic=%d, unigram=%d, bigram=%d, tipo_acao=%d)",
        batch.raw.shape, batch.semantic_dim, batch.topic_dim, batch.unigram_dim,
        batch.bigram_dim, batch.tipo_acao_dim,
    )

    log.info("processo-embed: running UMAP → %d dims", n_components)
    reduced = reduce_with_umap(
        batch, n_components=n_components,
        random_state=int(ctx.flags.get("umap_random_state") or 42),
    )

    text_variant = resolve_text_variant(ctx.flags.get("text_variant"))
    digest = feature_digest(
        (p.protocolo_formatado,
         feature_hash(p, weights, ALGO_VERSION, first_doc_only=first_doc_only,
                      block_weights=block_weights, cutoff_frac=cutoff_frac))
        for p in pending)
    log.info("processo-embed: feature digest=%s text_variant=%s", digest, text_variant)

    writer.open_phase("processo-embed")
    try:
        ts = now_iso()
        rows = []
        for i, p in enumerate(pending):
            h = feature_hash(p, weights, ALGO_VERSION,
                             first_doc_only=first_doc_only, block_weights=block_weights,
                             cutoff_frac=cutoff_frac)
            rows.append({
                "protocolo_formatado": p.protocolo_formatado,
                "features": reduced[i].tolist(),
                "dim": int(reduced.shape[1]),
                "hash": h,
                "computed_at": ts,
            })
        for i in range(0, len(rows), 200):
            writer.execute_template(
                "load_processo_cluster_features",
                LOAD_PROCESSO_CLUSTER_FEATURES_CYPHER,
                {"rows": rows[i:i + 200]},
                phase="processo-embed",
            )
    finally:
        writer.close_phase("processo-embed")

    if export_path:
        if skipped:
            log.warning("processo-embed: export_features npz covers only the %d computed processos (%d skipped by hash — use force_all=true for full corpus)", len(pending), skipped)
        _export_features_npz(Path(export_path), [p.protocolo_formatado for p in pending], reduced,
                             digest=digest, text_variant=text_variant)
        log.info("processo-embed: exported features npz to %s (shape=%s)", export_path, reduced.shape)

    summary = {
        "digest": digest,
        "text_variant": text_variant,
        "total": len(processos_input),
        "computed": len(pending),
        "skipped": skipped,
        "discarded_sem_documento": len(sem_documento),
        "discarded_fora_situacao": len(fora_situacao),
        "situacao_filter": only_situacao or None,
        "keyword_dim": int(batch.keyword_dim),
        "processos_with_keywords": sum(1 for p in pending if p.keywords),
        "umap_dim": int(reduced.shape[1]),
        "raw_dim": int(batch.raw.shape[1]),
    }
    ctx.cache["processo_embed_summary"] = summary
    log.info("processo-embed complete: %s", summary)
