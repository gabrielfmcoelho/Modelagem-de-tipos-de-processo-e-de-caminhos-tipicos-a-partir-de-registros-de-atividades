
from __future__ import annotations

import logging
from statistics import median

from ..core._stage_base import RunContext, StageMeta, truthy as _truthy
from ..core.cypher import COHORT_ATIVIDADE_DOC_BANDS_CYPHER, COHORT_DOC_SIMILARITY_CYPHER, COHORT_PROCESSO_DOC_BANDS_CYPHER, LOAD_ATIVIDADE_BAND_CYPHER, LOAD_DOC_BAND_CYPHER, LOAD_PROCESSO_BAND_CYPHER
from ..model.doc_band import activity_band_score, doc_band_score, processo_band_score
from ..core.neo4j_driver import run_query
from ..core.registry import stage

log = logging.getLogger(__name__)

def _flush(writer, name, cypher, rows, cohort_id, chunk=1000):
    for i in range(0, len(rows), chunk):
        writer.execute_template(
            name, cypher, {"rows": rows[i:i + chunk], "cohort_id": cohort_id}, phase="doc-band",
        )


@stage(StageMeta(
    name="doc-band",
    phase="typical-path",
    question="Quao proximos entre si sao os documentos de abertura de uma coorte?",
    deterministic=True,
    description="Métrica de banda de embedding documental (nem muito próximo nem distante), agregada a atividades/processos.",
    type="enrich",
    depends_on=("cohort", "similarity"),
    soft_depends_on=("embed",),
    modes=("neo4j",),
    can_skip_when_done=False,
    estimated_duration="~2-5min",
))
def run(ctx: RunContext) -> None:
    driver = ctx.require_driver()
    writer = ctx.require_writer()
    flags = ctx.flags

    cohort_id = (flags.get("cohort_id") or "").strip()
    if not cohort_id:
        raise ValueError("doc-band stage requires --flag cohort_id=<id>")

    center = float(flags.get("band_center") or 0.60)
    halfwidth = float(flags.get("band_halfwidth") or 0.20)
    agg = (flags.get("band_agg") or "median").strip()
    use_cross = _truthy(flags.get("use_cross_corpus"), default=False)

    writer.open_phase("doc-band")
    try:
        doc_rows_in = run_query(driver, COHORT_DOC_SIMILARITY_CYPHER, {"cohort_id": cohort_id})
        doc_rows = []
        n_with_band = 0
        for r in doc_rows_in:
            scores = list(r.get("intra_scores") or [])
            if not scores and use_cross:
                scores = list(r.get("cross_scores") or [])
            bs = doc_band_score(scores, center=center, halfwidth=halfwidth, agg=agg)
            if bs is not None:
                n_with_band += 1
            doc_rows.append({"numero": r["numero"], "band_score": bs})
        _flush(writer, "load_doc_band", LOAD_DOC_BAND_CYPHER, doc_rows, cohort_id)
        log.info("doc-band %s: %d docs, %d with a band score", cohort_id, len(doc_rows), n_with_band)

        act_rows_in = run_query(driver, COHORT_ATIVIDADE_DOC_BANDS_CYPHER, {"cohort_id": cohort_id})
        act_rows = [
            {"source_id": r["source_id"],
             "activity_band_score": activity_band_score(r.get("bands") or [])}
            for r in act_rows_in
        ]
        _flush(writer, "load_atividade_band", LOAD_ATIVIDADE_BAND_CYPHER, act_rows, cohort_id)

        proc_rows_in = run_query(driver, COHORT_PROCESSO_DOC_BANDS_CYPHER, {"cohort_id": cohort_id})
        raw: list[tuple[str, float | None]] = []
        for r in proc_rows_in:
            docs = [d for d in (r.get("docs") or []) if d.get("ts") is not None]
            docs.sort(key=lambda d: d["ts"])
            score = processo_band_score([d["band"] for d in docs])
            raw.append((r["protocolo"], score))

        known = [s for _, s in raw if s is not None]
        cohort_median = round(median(known), 4) if known else 0.0
        proc_rows = []
        n_imputed = 0
        for pf, score in raw:
            if score is None:
                n_imputed += 1
                proc_rows.append({"protocolo": pf, "processo_band_score": cohort_median, "band_imputed": True})
            else:
                proc_rows.append({"protocolo": pf, "processo_band_score": score, "band_imputed": False})
        _flush(writer, "load_processo_band", LOAD_PROCESSO_BAND_CYPHER, proc_rows, cohort_id)
        log.info("doc-band %s: %d processos (%d imputed, cohort_median=%.4f)",
                 cohort_id, len(proc_rows), n_imputed, cohort_median)
    finally:
        writer.close_phase("doc-band")

    ctx.cache["doc_band_summary"] = {
        "docs": len(doc_rows),
        "docs_with_band": n_with_band,
        "activities": len(act_rows),
        "processos": len(proc_rows),
        "processos_imputed": n_imputed,
        "cohort_median": cohort_median,
    }
