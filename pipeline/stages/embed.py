
from __future__ import annotations

import hashlib
import logging

from pathlib import Path

import numpy as np

from ..core._stage_base import RunContext, StageMeta
from ..core.cypher import CHECK_EMBEDDING_HASH_CYPHER, LOAD_DOCUMENTO_EMBEDDING_CYPHER
from ..model.embedding import build_embedder
from ..core.parsed_store import iter_parsed_documents
from ..core.registry import stage
from ..core.state import now_iso
from ..core.paths import ARTIFACTS
from ..evidence.artifact import write_sidecar

log = logging.getLogger(__name__)


DOC_CACHE_PATH = ARTIFACTS / "cache" / "doc_embeddings.npz"


def load_doc_cache(path=DOC_CACHE_PATH) -> dict[str, list[float]]:
    path = Path(path)
    if not path.is_file():
        return {}
    z = np.load(path, allow_pickle=False)
    return {str(k): v.tolist() for k, v in zip(z["keys"], z["vecs"])}


def save_doc_cache(cache: dict[str, list[float]], path=DOC_CACHE_PATH) -> None:
    if not cache:
        return
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = sorted(cache)
    np.savez_compressed(path, keys=np.asarray(keys, dtype=str),
                        vecs=np.asarray([cache[k] for k in keys], dtype=np.float32))
    write_sidecar(path, stage="embed",
                  params={"n_vectors": len(keys), "cache": "document embeddings"})


def _hash_for(text: str, model: str) -> str:
    h = hashlib.sha256()
    h.update(model.encode("utf-8"))
    h.update(b"\x00")
    h.update(text.encode("utf-8", errors="ignore"))
    return h.hexdigest()


def _iter_parsed_docs(parsed_dir: Path, variant: str = "raw"):
    for doc in iter_parsed_documents(parsed_dir, variant=variant):
        try:
            text = doc.text_path.read_text(encoding="utf-8", errors="replace").strip()
        except OSError as e:
            log.warning("could not read %s: %s", doc.text_path, e)
            continue
        if not text:
            continue
        yield doc.doc_id, text


@stage(StageMeta(
    name="embed",
    phase="documents",
    question="Que vetor representa o conteudo de cada documento?",
    deterministic='conditional',
    nondeterminism="modelo remoto; fixo enquanto a versao do modelo nao muda, e cacheado por hash de conteudo",
    description="Computa embeddings dos textos parseados e persiste em :Documento (Neo4j vector index).",
    type="enrich",
    depends_on=("parse",),
    soft_depends_on=("ner-load",),
    modes=("neo4j", "json-emit"),
    estimated_duration="~5-15min para ~3k documentos via Mandu API",
))
def run(ctx: RunContext) -> None:
    parsed_dir = Path(ctx.flags.get("input") or ctx.flags.get("parsed_dir") or "./parsed_documents")
    if not parsed_dir.is_dir():
        log.error("parsed-documents dir not found: %s", parsed_dir)
        ctx.cache["embed_summary"] = {"total": 0, "embedded": 0, "skipped": 0, "error": "missing_dir"}
        return

    limit = int(ctx.flags.get("limit") or 0)
    batch_size = int(ctx.flags.get("batch_size") or 32)
    preference = (ctx.flags.get("embedder") or "auto").lower()
    variant = str(ctx.flags.get("text_variant") or "raw").lower()

    embedder = build_embedder(ctx.settings, preference=preference)
    model = embedder.model_name
    dim = embedder.dimension
    log.info("embed: using %s (dim=%d), batch_size=%d, text_variant=%s", model, dim, batch_size, variant)

    docs = list(_iter_parsed_docs(parsed_dir, variant=variant))
    if limit:
        docs = docs[:limit]
    log.info("embed: %d parsed documents (variant=%s) to consider in %s", len(docs), variant, parsed_dir)
    if not docs:
        ctx.cache["embed_summary"] = {"total": 0, "embedded": 0, "skipped": 0}
        return

    existing_hashes: dict[str, str] = {}
    existing_models: dict[str, str] = {}
    if ctx.driver is not None:
        with ctx.driver.session() as session:
            for i in range(0, len(docs), 500):
                batch_ids = [n for n, _ in docs[i:i + 500]]
                result = session.run(CHECK_EMBEDDING_HASH_CYPHER, numeros=batch_ids)
                for rec in result:
                    n = rec["numero"]
                    existing_hashes[n] = rec.get("hash") or ""
                    existing_models[n] = rec.get("modelo") or ""
    else:
        log.info("embed: no Neo4j driver available — assuming all docs are new (json-emit mode).")

    pending: list[tuple[str, str, str]] = []
    skipped = 0
    missing_in_graph = 0
    for numero, text in docs:
        if ctx.driver is not None and numero not in existing_hashes:
            missing_in_graph += 1
            continue
        h = _hash_for(text, model)
        if existing_hashes.get(numero) == h and existing_models.get(numero) == model:
            skipped += 1
            continue
        pending.append((numero, text, h))

    log.info(
        "embed: %d pending, %d skipped (hash match), %d missing :Documento node",
        len(pending), skipped, missing_in_graph,
    )

    doc_cache = load_doc_cache()
    from_cache = sum(1 for _, _, h in pending if h in doc_cache)
    log.info("embed: %d of %d pending served from the disk cache", from_cache, len(pending))

    writer = ctx.require_writer()
    writer.open_phase("embed")
    embedded = 0
    failed = 0
    cache_dirty = False
    try:
        for i in range(0, len(pending), batch_size):
            batch = pending[i:i + batch_size]
            need = [(n, t, h) for n, t, h in batch if h not in doc_cache]
            if need:
                try:
                    fresh = embedder.embed_batch([t for _, t, _ in need])
                except Exception as e:
                    log.exception("embed batch %d-%d failed: %s", i, i + len(batch), e)
                    failed += len(batch)
                    continue
                for (_, _, h), v in zip(need, fresh):
                    doc_cache[h] = list(v)
                cache_dirty = True
            vectors = [doc_cache[h] for _, _, h in batch]

            for v in vectors:
                if len(v) != embedder.dimension:
                    raise RuntimeError(
                        f"Embedder returned dim={len(v)} but expected {embedder.dimension}. "
                        f"Refusing to write inconsistent vectors. Check model + index config."
                    )

            rows = []
            ts = now_iso()
            for (numero, _text, h), v in zip(batch, vectors):
                rows.append({
                    "documento_numero": numero,
                    "embedding": v,
                    "modelo": model,
                    "hash": h,
                    "dim": embedder.dimension,
                    "computed_at": ts,
                })
            writer.execute_template(
                "load_documento_embedding",
                LOAD_DOCUMENTO_EMBEDDING_CYPHER,
                {"rows": rows},
                phase="embed",
            )
            embedded += len(rows)

            if (i + batch_size) % (batch_size * 10) == 0 or (i + len(batch)) >= len(pending):
                log.info("embed: %d/%d embedded", embedded, len(pending))
        if cache_dirty:
            save_doc_cache(doc_cache)
    finally:
        writer.close_phase("embed")

    summary = {
        "total": len(docs),
        "embedded": embedded,
        "skipped": skipped,
        "missing_in_graph": missing_in_graph,
        "failed": failed,
        "model": model,
        "dim": embedder.dimension,
    }
    ctx.cache["embed_summary"] = summary
    log.info(
        "embed complete: embedded=%d skipped=%d missing=%d failed=%d (model=%s, dim=%d)",
        embedded, skipped, missing_in_graph, failed, model, embedder.dimension,
    )
