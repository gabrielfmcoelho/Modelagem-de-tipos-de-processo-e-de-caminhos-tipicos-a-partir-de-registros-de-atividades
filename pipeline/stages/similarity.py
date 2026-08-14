
from __future__ import annotations

import logging
import math
from typing import Any

from ..core._stage_base import RunContext, StageMeta
from ..core.cypher import CLEAR_SIMILAR_DOC_FOR_BATCH_CYPHER, LIST_DOCS_PER_PROCESSO_CYPHER, LOAD_SIMILAR_DOC_CYPHER, QUERY_VECTOR_NEIGHBORS_CYPHER
from ..core.registry import stage
from ..core.state import now_iso

log = logging.getLogger(__name__)


def classify_tier(score: float) -> str:
    if score >= 0.90:
        return "very_high"
    if score >= 0.80:
        return "high"
    if score >= 0.40:
        return "medium"
    return "low"


def _cosine(v1: list[float], v2: list[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    n1 = math.sqrt(sum(a * a for a in v1))
    n2 = math.sqrt(sum(b * b for b in v2))
    if n1 == 0.0 or n2 == 0.0:
        return 0.0
    return dot / (n1 * n2)


def _ordered_pair(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a < b else (b, a)


def _pass_cross_corpus(
    ctx: RunContext,
    k: int,
    model: str,
) -> list[dict[str, Any]]:
    driver = ctx.require_driver()
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    ts = now_iso()

    with driver.session() as session:
        result = session.run(
            "MATCH (d:Documento) WHERE d.embedding IS NOT NULL "
            "RETURN d.numero AS numero, d.embedding AS embedding"
        )
        for record in result:
            numero = record["numero"]
            embedding = record["embedding"]
            neighbors = session.run(
                QUERY_VECTOR_NEIGHBORS_CYPHER,
                k=k, k_plus_one=k + 1,
                query_embedding=embedding, exclude=numero,
            )
            for n in neighbors:
                target = n["numero"]
                pair = _ordered_pair(numero, target)
                if pair in seen:
                    continue
                seen.add(pair)
                score = float(n["score"])
                rows.append({
                    "from_doc": pair[0],
                    "to_doc": pair[1],
                    "score": round(score, 4),
                    "tier": classify_tier(score),
                    "intra_processo": False,
                    "modelo": model,
                    "computed_at": ts,
                })

    log.info("similarity pass 1 (cross-corpus): %d unique pairs", len(rows))
    return rows


def _pass_intra_processo(
    ctx: RunContext,
    model: str,
) -> list[dict[str, Any]]:
    driver = ctx.require_driver()
    rows: list[dict[str, Any]] = []
    ts = now_iso()
    processo_count = 0
    pair_count = 0

    with driver.session() as session:
        result = session.run(LIST_DOCS_PER_PROCESSO_CYPHER)
        for record in result:
            processo_count += 1
            docs = record["docs"]
            n = len(docs)
            if n < 2:
                continue
            for i in range(n):
                for j in range(i + 1, n):
                    a = docs[i]
                    b = docs[j]
                    pair = _ordered_pair(a["numero"], b["numero"])
                    score = _cosine(a["embedding"], b["embedding"])
                    rows.append({
                        "from_doc": pair[0],
                        "to_doc": pair[1],
                        "score": round(score, 4),
                        "tier": classify_tier(score),
                        "intra_processo": True,
                        "modelo": model,
                        "computed_at": ts,
                    })
                    pair_count += 1

    log.info(
        "similarity pass 2 (intra-processo): %d processos × %d pairs total",
        processo_count, pair_count,
    )
    return rows


def _flush_rows(ctx: RunContext, rows: list[dict[str, Any]], chunk: int = 500) -> None:
    if not rows:
        return
    writer = ctx.require_writer()
    for i in range(0, len(rows), chunk):
        writer.execute_template(
            "load_similar_doc",
            LOAD_SIMILAR_DOC_CYPHER,
            {"rows": rows[i:i + chunk]},
            phase="similarity",
        )


def _clear_existing(ctx: RunContext, numeros: list[str], chunk: int = 500) -> None:
    if not numeros:
        return
    writer = ctx.require_writer()
    for i in range(0, len(numeros), chunk):
        writer.execute_template(
            "clear_similar_doc",
            CLEAR_SIMILAR_DOC_FOR_BATCH_CYPHER,
            {"numeros": numeros[i:i + chunk]},
            phase="similarity",
        )


@stage(StageMeta(
    name="similarity",
    phase="documents",
    question="Que documentos sao semanticamente proximos entre si?",
    deterministic=True,
    description="Edges SIMILAR_DOC entre documentos (top-K cross-corpus + par-a-par intra-processo).",
    type="enrich",
    depends_on=("embed",),
    modes=("neo4j", "json-emit", "json-replay"),
    estimated_duration="~10-30min para 3k docs (depende do K e do paralelismo intra-processo)",
))
def run(ctx: RunContext) -> None:
    k = int(ctx.flags.get("k") or 20)
    skip_cross = bool(ctx.flags.get("skip_cross", False))
    skip_intra = bool(ctx.flags.get("skip_intra", False))

    driver = ctx.require_driver()
    with driver.session() as session:
        rec = session.run(
            "MATCH (d:Documento) WHERE d.embedding IS NOT NULL "
            "RETURN d.embedding_modelo AS modelo LIMIT 1"
        ).single()
    model = rec["modelo"] if rec and rec["modelo"] else "unknown"
    log.info("similarity: K=%d, model=%s, skip_cross=%s skip_intra=%s",
             k, model, skip_cross, skip_intra)

    with driver.session() as session:
        all_numeros = [
            r["numero"] for r in session.run(
                "MATCH (d:Documento) WHERE d.embedding IS NOT NULL RETURN d.numero AS numero"
            )
        ]
    log.info("similarity: %d documents with embeddings (clearing existing edges)", len(all_numeros))
    writer = ctx.require_writer()
    writer.open_phase("similarity")
    try:
        _clear_existing(ctx, all_numeros)

        cross_rows: list[dict[str, Any]] = []
        intra_rows: list[dict[str, Any]] = []
        if not skip_cross:
            cross_rows = _pass_cross_corpus(ctx, k, model)
            _flush_rows(ctx, cross_rows)
        if not skip_intra:
            intra_rows = _pass_intra_processo(ctx, model)
            _flush_rows(ctx, intra_rows)

    finally:
        writer.close_phase("similarity")

    by_tier_cross: dict[str, int] = {"very_high": 0, "high": 0, "medium": 0, "low": 0}
    by_tier_intra: dict[str, int] = {"very_high": 0, "high": 0, "medium": 0, "low": 0}
    for r in cross_rows:
        by_tier_cross[r["tier"]] += 1
    for r in intra_rows:
        by_tier_intra[r["tier"]] += 1

    summary = {
        "k": k,
        "model": model,
        "documentos_com_embedding": len(all_numeros),
        "cross_corpus_pairs": len(cross_rows),
        "intra_processo_pairs": len(intra_rows),
        "tiers_cross": by_tier_cross,
        "tiers_intra": by_tier_intra,
    }
    ctx.cache["similarity_summary"] = summary
    log.info("similarity complete: cross=%d intra=%d (tiers cross=%s intra=%s)",
             len(cross_rows), len(intra_rows), by_tier_cross, by_tier_intra)
