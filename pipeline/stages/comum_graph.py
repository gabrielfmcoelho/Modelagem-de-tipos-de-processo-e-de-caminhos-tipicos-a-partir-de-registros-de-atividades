
from __future__ import annotations

import json
import logging
from pathlib import Path

from ..core._stage_base import RunContext, StageMeta
from ..model.comum_graph import build_swimlane
from ..core.cypher import CLEAR_COMUM_CYPHER, LOAD_COMUM_EDGE_CYPHER, LOAD_COMUM_NODE_CYPHER, READ_DFG_EDGES_CYPHER, READ_DFG_NODES_CYPHER
from ..core.neo4j_driver import run_query
from ..readers import CohortNeo4jReader
from ..core.registry import stage
from ..core.state import now_iso

log = logging.getLogger(__name__)


@stage(StageMeta(
    name="comum-graph",
    phase="typical-path",
    question="Qual a linha do tempo representativa de uma coorte, em raias por unidade?",
    deterministic=True,
    description="Grafo 'comum' — linha do tempo representativa da coorte em raias por unidade.",
    type="op",
    depends_on=("dfg-build",),
    modes=("neo4j", "json-emit"),
    can_skip_when_done=False,
    estimated_duration="~1min",
))
def run(ctx: RunContext) -> None:
    driver = ctx.require_driver()
    writer = ctx.require_writer()
    flags = ctx.flags

    cohort_id = (flags.get("cohort_id") or "").strip()
    if not cohort_id:
        raise ValueError("comum-graph stage requires --flag cohort_id=<id>")
    cf = flags.get("coverage_floor")
    coverage_floor = float(cf) if cf not in (None, "") else 0.2

    nodes = run_query(driver, READ_DFG_NODES_CYPHER, {"cohort_id": cohort_id})
    edges = run_query(driver, READ_DFG_EDGES_CYPHER, {"cohort_id": cohort_id})
    if not nodes:
        raise ValueError(
            f"comum-graph: no DFG for cohort {cohort_id!r}; run dfg-build "
            "(with node_identity=tipo_acao_unidade) first"
        )
    total = CohortNeo4jReader(driver, cohort_id).count_processos()

    sw = build_swimlane(nodes, edges, total_processos=total, coverage_floor=coverage_floor)
    log.info(
        "comum-graph %s: %d lanes, %d nodes, %d edges, spine len %d (coverage_floor=%.2f)",
        cohort_id, len(sw["lanes"]), len(sw["nodes"]), len(sw["edges"]),
        len(sw["spine"]), coverage_floor,
    )

    computed_at = now_iso()

    def nid(state_key: str) -> str:
        return f"{cohort_id}|{state_key}"

    node_rows = [
        {
            "id": nid(n["id"]),
            "state_key": n["id"],
            "label": n["label"],
            "lane": n["lane"],
            "x": n["x"],
            "coverage": n["coverage"],
            "frequency": n["frequency"],
            "grupo": n["grupo"],
            "on_spine": n["on_spine"],
            "is_start": n["is_start"],
            "is_end": n["is_end"],
            "gcn_kept": n.get("gcn_kept"),
        }
        for n in sw["nodes"]
    ]
    edge_rows = [
        {
            "from_id": nid(e["from"]),
            "to_id": nid(e["to"]),
            "coverage": e["coverage"],
            "frequency": e["frequency"],
            "mean_interval_h": e["mean_interval_h"],
            "kind": e["kind"],
            "on_spine": e["on_spine"],
            "back_edge": e["back_edge"],
        }
        for e in sw["edges"]
    ]

    writer.open_phase("comum-graph")
    try:
        writer.execute_template(
            "clear_comum", CLEAR_COMUM_CYPHER, {"cohort_id": cohort_id}, phase="comum-graph")
        for i in range(0, len(node_rows), 500):
            writer.execute_template(
                "load_comum_node", LOAD_COMUM_NODE_CYPHER,
                {"rows": node_rows[i:i + 500], "cohort_id": cohort_id, "computed_at": computed_at},
                phase="comum-graph",
            )
        for i in range(0, len(edge_rows), 500):
            writer.execute_template(
                "load_comum_edge", LOAD_COMUM_EDGE_CYPHER,
                {"rows": edge_rows[i:i + 500], "cohort_id": cohort_id}, phase="comum-graph",
            )
    finally:
        writer.close_phase("comum-graph")

    emit_dir = flags.get("emit_dir")
    if emit_dir:
        out = Path(emit_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / f"comum-graph-{cohort_id}.json").write_text(
            json.dumps(
                {
                    "cohort_id": cohort_id,
                    "coverage_floor": coverage_floor,
                    "total_processos": total,
                    **sw,
                    "computed_at": computed_at,
                },
                ensure_ascii=False, indent=2,
            ),
            encoding="utf-8",
        )

    ctx.cache["comum_graph_summary"] = {
        "cohort_id": cohort_id,
        "lanes": len(sw["lanes"]),
        "nodes": len(sw["nodes"]),
        "edges": len(sw["edges"]),
        "spine": sw["spine"],
        "coverage_floor": coverage_floor,
    }
