
from __future__ import annotations

import json
import logging
from pathlib import Path

from ..core._stage_base import RunContext, StageMeta
from ..core.cypher import CLEAR_IDEAL_DIRECTLY_FOLLOWS_CYPHER, LOAD_DIRECTLY_FOLLOWS_IDEAL_CYPHER, LOAD_GCN_NODE_IMPORTANCE_CYPHER, LOAD_IDEAL_DIRECTLY_FOLLOWS_CYPHER, READ_DFG_EDGES_CYPHER, READ_DFG_NODES_CYPHER
from ..model.gcn import blend_importance, contract_edges, gcn_importance, pagerank_importance, select_kept, weighted_degree_importance
from ..core.neo4j_driver import run_query
from ..core.registry import stage
from ..core.state import now_iso

log = logging.getLogger(__name__)


def _float(flags, key, default):
    v = flags.get(key)
    return float(v) if v not in (None, "") else default


def _int(flags, key, default):
    v = flags.get(key)
    return int(v) if v not in (None, "") else default


@stage(StageMeta(
    name="gcn-distill",
    phase="typical-path",
    question="Que nos sao estruturalmente importantes no fluxo de uma coorte?",
    deterministic=False,
    nondeterminism="treino em GPU: inicializacao e nao-determinismo de kernels CUDA",
    description="Importância de nós via GCN (com baselines) + grafo 'ideal' podado da coorte.",
    type="op",
    depends_on=("dfg-build",),
    modes=("neo4j", "json-emit"),
    can_skip_when_done=False,
    estimated_duration="~5-20min (GPU) para coorte pequena",
))
def run(ctx: RunContext) -> None:
    driver = ctx.require_driver()
    writer = ctx.require_writer()
    flags = ctx.flags

    cohort_id = (flags.get("cohort_id") or "").strip()
    if not cohort_id:
        raise ValueError("gcn-distill stage requires --flag cohort_id=<id>")

    method = (flags.get("method") or "gcn").strip()
    w_struct = _float(flags, "w_struct", 0.5)
    w_band = _float(flags, "w_band", 0.2)
    w_gcn = _float(flags, "w_gcn", 0.3)
    prune_quantile = _float(flags, "prune_quantile", 0.25)
    freq_floor = _int(flags, "freq_floor", 1)

    nodes = run_query(driver, READ_DFG_NODES_CYPHER, {"cohort_id": cohort_id})
    edges = run_query(driver, READ_DFG_EDGES_CYPHER, {"cohort_id": cohort_id})
    if not nodes:
        raise ValueError(f"gcn-distill: no DFG for cohort {cohort_id!r}; run dfg-build first")
    log.info("gcn-distill %s: DFG %d nodes / %d edges, method=%s",
             cohort_id, len(nodes), len(edges), method)

    learned: dict[str, float]
    if method == "gcn":
        try:
            learned = gcn_importance(
                nodes, edges,
                hidden=_int(flags, "hidden_dim", 32),
                epochs=_int(flags, "epochs", 200),
                lr=_float(flags, "lr", 0.01),
            )
        except Exception as exc:
            log.warning("gcn-distill %s: GCN unavailable (%s); falling back to pagerank baseline",
                        cohort_id, exc)
            method = "pagerank"
            learned = pagerank_importance(nodes, edges)
    elif method == "weighted_degree":
        learned = weighted_degree_importance(nodes, edges)
    else:
        method = "pagerank"
        learned = pagerank_importance(nodes, edges)

    importance = blend_importance(nodes, learned, w_struct=w_struct, w_band=w_band, w_gcn=w_gcn)
    kept = select_kept(nodes, importance, prune_quantile=prune_quantile, freq_floor=freq_floor)
    ideal_pairs = contract_edges(edges, kept)
    log.info("gcn-distill %s: kept %d/%d nodes; ideal graph has %d edges",
             cohort_id, len(kept), len(nodes), len(ideal_pairs))

    def nid(state_key):
        return f"{cohort_id}|{state_key}"

    node_rows = [
        {"id": nid(n["state_key"]),
         "gcn_importance": importance.get(n["state_key"], 0.0),
         "in_ideal_graph": n["state_key"] in kept}
        for n in nodes
    ]
    edge_rows = [
        {"from_id": nid(e["from_key"]), "to_id": nid(e["to_key"]),
         "in_ideal_graph": (e["from_key"] in kept and e["to_key"] in kept),
         "gcn_edge_importance": round(
             (importance.get(e["from_key"], 0.0) + importance.get(e["to_key"], 0.0)) / 2, 4)}
        for e in edges
    ]
    ideal_rows = [{"from_id": nid(a), "to_id": nid(b)} for (a, b) in sorted(ideal_pairs)]

    computed_at = now_iso()
    writer.open_phase("gcn-distill")
    try:
        for i in range(0, len(node_rows), 500):
            writer.execute_template(
                "load_gcn_node_importance", LOAD_GCN_NODE_IMPORTANCE_CYPHER,
                {"rows": node_rows[i:i + 500], "method": method}, phase="gcn-distill",
            )
        for i in range(0, len(edge_rows), 500):
            writer.execute_template(
                "load_directly_follows_ideal", LOAD_DIRECTLY_FOLLOWS_IDEAL_CYPHER,
                {"rows": edge_rows[i:i + 500]}, phase="gcn-distill",
            )
        writer.execute_template(
            "clear_ideal_df", CLEAR_IDEAL_DIRECTLY_FOLLOWS_CYPHER,
            {"cohort_id": cohort_id}, phase="gcn-distill",
        )
        for i in range(0, len(ideal_rows), 500):
            writer.execute_template(
                "load_ideal_directly_follows", LOAD_IDEAL_DIRECTLY_FOLLOWS_CYPHER,
                {"rows": ideal_rows[i:i + 500], "cohort_id": cohort_id}, phase="gcn-distill",
            )
    finally:
        writer.close_phase("gcn-distill")

    metrics = {
        "cohort_id": cohort_id,
        "method": method,
        "dfg_nodes": len(nodes),
        "dfg_edges": len(edges),
        "kept_nodes": len(kept),
        "ideal_edges": len(ideal_rows),
        "weights": {"w_struct": w_struct, "w_band": w_band, "w_gcn": w_gcn},
        "prune_quantile": prune_quantile,
        "freq_floor": freq_floor,
        "computed_at": computed_at,
    }
    emit_dir = flags.get("emit_dir")
    if emit_dir:
        out = Path(emit_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / f"gcn-metrics-{cohort_id}.json").write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
        ideal_nodes = [
            {"id": nid(n["state_key"]), "state_key": n["state_key"],
             "tipo_acao": n["tipo_acao"], "importance": importance.get(n["state_key"], 0.0)}
            for n in nodes if n["state_key"] in kept
        ]
        (out / f"ideal-dfg-{cohort_id}.json").write_text(json.dumps({
            "cohort_id": cohort_id, "method": method,
            "nodes": ideal_nodes,
            "edges": [{"from": a, "to": b} for (a, b) in sorted(ideal_pairs)],
            "computed_at": computed_at,
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    ctx.cache["gcn_distill_summary"] = metrics
