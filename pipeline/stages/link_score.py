
from __future__ import annotations

import logging

from ..core._stage_base import RunContext, StageMeta
from ..core.cypher import COHORT_DURATIONS_CYPHER, LOAD_ATIVIDADE_SCORE_CYPHER, LOAD_LINK_SCORE_EDGE_CYPHER
from ..model.link_score import score_process, speed_scores_from_durations
from ..core.neo4j_driver import run_query
from ..model.process_state import compute_processo_state
from ..readers import CohortNeo4jReader
from ..core.registry import stage
from ..core.state import now_iso

log = logging.getLogger(__name__)


def _float(flags, key, default):
    v = flags.get(key)
    return float(v) if v not in (None, "") else default


@stage(StageMeta(
    name="link-score",
    phase="typical-path",
    question="Que transicoes contribuem para a conclusao, e quais sao retrabalho?",
    deterministic=True,
    description="Score de contribuição-à-conclusão (avanço-vs-retrabalho + velocidade) em SEGUIDA_POR e Atividade.",
    type="enrich",
    depends_on=("cohort", "timeline", "permanencia", "situacao"),
    modes=("neo4j",),
    can_skip_when_done=False,
    estimated_duration="~3-10min para coorte de centenas",
))
def run(ctx: RunContext) -> None:
    driver = ctx.require_driver()
    writer = ctx.require_writer()
    flags = ctx.flags

    cohort_id = (flags.get("cohort_id") or "").strip()
    if not cohort_id:
        raise ValueError("link-score stage requires --flag cohort_id=<id>")

    kw = dict(
        w_adv=_float(flags, "w_adv", 0.5),
        w_speed=_float(flags, "w_speed", 0.2),
        rework_penalty=_float(flags, "rework_penalty", 0.5),
        idle_penalty=_float(flags, "idle_penalty", 0.4),
        idle_factor=_float(flags, "idle_factor", 3.0),
        idle_floor_h=_float(flags, "idle_floor_h", 24.0),
    )

    dur_rows = run_query(driver, COHORT_DURATIONS_CYPHER, {"cohort_id": cohort_id})
    durations = {
        r["protocolo"]: r["duracao_lifetime_horas"]
        for r in dur_rows
        if r.get("duracao_lifetime_horas") is not None
    }
    speed_map = speed_scores_from_durations(durations)
    log.info("link-score %s: %d processos, %d with lifetime durations",
             cohort_id, len(dur_rows), len(durations))

    reader = CohortNeo4jReader(driver, cohort_id)
    computed_at = now_iso()
    totals = {"processos": 0, "edges": 0, "nodes": 0, "rework_edges": 0, "idle_edges": 0}

    writer.open_phase("link-score")
    try:
        for batch in reader.iter_processo_batches(batch_size=500):
            edge_rows: list[dict] = []
            node_rows: list[dict] = []
            for processo in batch:
                pf = processo.protocolo_formatado
                acts = processo.activities
                if not acts:
                    continue
                state = compute_processo_state(acts, protocolo_formatado=pf)
                speed = speed_map.get(pf, 0.5)
                edges, nodes = score_process(acts, state, speed=speed, **kw)
                edge_rows.extend(edges)
                node_rows.extend(nodes.values())
                totals["processos"] += 1
                totals["rework_edges"] += sum(1 for e in edges if e["rework_flag"])
                totals["idle_edges"] += sum(1 for e in edges if e["idle_flag"])

            for i in range(0, len(edge_rows), 1000):
                writer.execute_template(
                    "load_link_score_edge", LOAD_LINK_SCORE_EDGE_CYPHER,
                    {"rows": edge_rows[i:i + 1000], "cohort_id": cohort_id, "computed_at": computed_at},
                    phase="link-score",
                )
            for i in range(0, len(node_rows), 1000):
                writer.execute_template(
                    "load_atividade_score", LOAD_ATIVIDADE_SCORE_CYPHER,
                    {"rows": node_rows[i:i + 1000], "cohort_id": cohort_id},
                    phase="link-score",
                )
            totals["edges"] += len(edge_rows)
            totals["nodes"] += len(node_rows)
    finally:
        writer.close_phase("link-score")

    log.info("link-score %s complete: %s", cohort_id, totals)
    ctx.cache["link_score_summary"] = totals
