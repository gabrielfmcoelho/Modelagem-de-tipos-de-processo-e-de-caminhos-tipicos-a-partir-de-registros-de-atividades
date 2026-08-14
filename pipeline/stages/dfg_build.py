
from __future__ import annotations

import json
import logging
from pathlib import Path

from ..core._stage_base import RunContext, StageMeta
from ..core.cypher import CLEAR_DFG_CYPHER, COHORT_ACTIVITIES_FOR_DFG_CYPHER, COHORT_EDGES_FOR_DFG_CYPHER, LOAD_DFG_NODE_CYPHER, LOAD_DIRECTLY_FOLLOWS_CYPHER
from ..model.dfg import NODE_FEATURE_DIM, build_dfg
from ..core.neo4j_driver import run_query
from ..readers import CohortNeo4jReader
from ..core.registry import stage
from ..core.state import now_iso

log = logging.getLogger(__name__)


@stage(StageMeta(
    name="dfg-build",
    phase="typical-path",
    question="Qual o grafo directly-follows agregado da coorte?",
    deterministic=True,
    description="Constrói o directly-follows graph agregado da coorte (nós=tipo de atividade, pesos=freq+scores).",
    type="enrich",
    depends_on=("cohort", "link-score", "doc-band"),
    modes=("neo4j", "json-emit"),
    can_skip_when_done=False,
    estimated_duration="~3-8min",
))
def run(ctx: RunContext) -> None:
    driver = ctx.require_driver()
    writer = ctx.require_writer()
    flags = ctx.flags

    cohort_id = (flags.get("cohort_id") or "").strip()
    if not cohort_id:
        raise ValueError("dfg-build stage requires --flag cohort_id=<id>")
    node_identity = (flags.get("node_identity") or "tipo_acao").strip()
    _lane_depth = flags.get("lane_depth")
    lane_depth = int(_lane_depth) if _lane_depth not in (None, "") else None

    total_processos = CohortNeo4jReader(driver, cohort_id).count_processos()
    activity_rows = run_query(driver, COHORT_ACTIVITIES_FOR_DFG_CYPHER, {"cohort_id": cohort_id})
    edge_rows = run_query(driver, COHORT_EDGES_FOR_DFG_CYPHER, {"cohort_id": cohort_id})
    log.info("dfg-build %s: %d processos, %d activities, %d typed edges",
             cohort_id, total_processos, len(activity_rows), len(edge_rows))

    node_records, edge_records = build_dfg(
        activity_rows, edge_rows,
        total_processos=total_processos, node_identity=node_identity,
        lane_depth=lane_depth,
    )
    log.info("dfg-build %s: DFG has %d nodes, %d directly-follows edges (feature_dim=%d)",
             cohort_id, len(node_records), len(edge_records), NODE_FEATURE_DIM)

    computed_at = now_iso()
    node_rows = [
        {**r, "id": f"{cohort_id}|{r['state_key']}"} for r in node_records
    ]
    df_rows = [
        {
            "from_id": f"{cohort_id}|{r['from_key']}",
            "to_id": f"{cohort_id}|{r['to_key']}",
            "frequency": r["frequency"],
            "n_processos": r["n_processos"],
            "mean_contrib_score": r["mean_contrib_score"],
            "mean_advancement": r["mean_advancement"],
            "mean_speed": r["mean_speed"],
            "mean_intervalo_horas": r["mean_intervalo_horas"],
        }
        for r in edge_records
    ]

    writer.open_phase("dfg-build")
    try:
        writer.execute_template("clear_dfg", CLEAR_DFG_CYPHER, {"cohort_id": cohort_id}, phase="dfg-build")
        for i in range(0, len(node_rows), 500):
            writer.execute_template(
                "load_dfg_node", LOAD_DFG_NODE_CYPHER,
                {"rows": node_rows[i:i + 500], "cohort_id": cohort_id, "computed_at": computed_at},
                phase="dfg-build",
            )
        for i in range(0, len(df_rows), 500):
            writer.execute_template(
                "load_directly_follows", LOAD_DIRECTLY_FOLLOWS_CYPHER,
                {"rows": df_rows[i:i + 500], "cohort_id": cohort_id},
                phase="dfg-build",
            )
    finally:
        writer.close_phase("dfg-build")

    emit_dir = flags.get("emit_dir")
    if emit_dir:
        out = Path(emit_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / f"dfg-{cohort_id}.json").write_text(json.dumps({
            "cohort_id": cohort_id,
            "node_identity": node_identity,
            "lane_depth": lane_depth,
            "feature_dim": NODE_FEATURE_DIM,
            "total_processos": total_processos,
            "nodes": node_rows,
            "edges": df_rows,
            "computed_at": computed_at,
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    ctx.cache["dfg_build_summary"] = {
        "cohort_id": cohort_id,
        "nodes": len(node_rows),
        "edges": len(df_rows),
        "feature_dim": NODE_FEATURE_DIM,
        "total_processos": total_processos,
    }
