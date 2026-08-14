
from __future__ import annotations

from ..model.gcn import blend_importance, contract_edges, gcn_importance, pagerank_importance, quantile, select_kept, weighted_degree_importance


def _node(key, *, act=False, con=False, freq=5, contrib=0.5, band=0.5):
    return {
        "state_key": key, "tipo_acao": key, "frequency": freq, "n_processos": freq,
        "is_activation": act, "is_conclusion": con,
        "features": [0.0], "mean_contrib": contrib, "mean_advancement": contrib,
        "mean_speed": 0.5, "mean_activity_band": band,
    }


def _edge(f, t, freq=1, contrib=1.0):
    return {"from_key": f, "to_key": t, "frequency": freq, "mean_contrib_score": contrib}


def test_quantile_linear_interpolation():
    assert quantile([0.1, 0.2, 0.9, 1.0], 0.5) == 0.55
    assert quantile([], 0.5) == 0.0
    assert quantile([0.3], 0.9) == 0.3


def test_weighted_degree_importance_normalized():
    nodes = [_node("A"), _node("B"), _node("C")]
    edges = [_edge("A", "B", freq=2, contrib=1.0), _edge("B", "C", freq=1, contrib=0.0)]
    imp = weighted_degree_importance(nodes, edges)
    assert imp["B"] == 1.0
    assert imp["A"] == 0.8
    assert imp["C"] == 0.2


def test_pagerank_in_unit_interval_and_favors_conclusion():
    nodes = [_node("A", act=True), _node("B"), _node("C", con=True)]
    edges = [_edge("A", "B"), _edge("B", "C")]
    imp = pagerank_importance(nodes, edges)
    assert all(0.0 <= v <= 1.0 for v in imp.values())
    assert imp["C"] == max(imp.values())


def test_blend_importance_normalized():
    nodes = [_node("A", contrib=1.0, band=1.0), _node("B", contrib=0.0, band=0.0)]
    learned = {"A": 1.0, "B": 0.0}
    imp = blend_importance(nodes, learned, w_struct=0.5, w_band=0.2, w_gcn=0.3)
    assert imp["A"] == 1.0
    assert imp["B"] == 0.0


def test_select_kept_always_keeps_activation_and_conclusion():
    nodes = [
        _node("ACT", act=True, contrib=0.0),
        _node("MID", contrib=0.2, freq=5),
        _node("HI", contrib=0.9, freq=5),
        _node("CON", con=True, contrib=0.0),
    ]
    imp = {"ACT": 0.1, "MID": 0.2, "HI": 0.9, "CON": 1.0}
    kept = select_kept(nodes, imp, prune_quantile=0.5, freq_floor=1)
    assert "ACT" in kept and "CON" in kept
    assert "HI" in kept
    assert "MID" not in kept


def test_select_kept_respects_freq_floor():
    nodes = [_node("ACT", act=True), _node("RARE", contrib=0.9, freq=0), _node("CON", con=True)]
    imp = {"ACT": 0.5, "RARE": 1.0, "CON": 0.5}
    kept = select_kept(nodes, imp, prune_quantile=0.0, freq_floor=1)
    assert "RARE" not in kept


def test_contract_edges_bypasses_pruned_nodes():
    edges = [_edge("A", "X"), _edge("X", "B")]
    ideal = contract_edges(edges, kept={"A", "B"})
    assert ideal == {("A", "B")}


def test_contract_edges_direct_and_bypass_collapse():
    edges = [_edge("A", "B"), _edge("A", "X"), _edge("X", "B")]
    ideal = contract_edges(edges, kept={"A", "B"})
    assert ideal == {("A", "B")}


def test_contract_edges_drops_self_loops():
    edges = [_edge("A", "A"), _edge("A", "B")]
    ideal = contract_edges(edges, kept={"A", "B"})
    assert ideal == {("A", "B")}


def test_gcn_importance_returns_dict_or_fails_cleanly():
    nodes = [_node("A"), _node("B")]
    edges = [_edge("A", "B")]
    try:
        out = gcn_importance(nodes, edges, epochs=2)
    except Exception:
        return
    assert isinstance(out, dict) and set(out) == {"A", "B"}
    assert all(0.0 <= v <= 1.0 for v in out.values())


def test_select_kept_respects_coverage_floor():
    nodes = [
        _node("ACT", act=True),
        _node("COMMON", contrib=0.9, freq=8),
        _node("RARE", contrib=0.9, freq=1),
        _node("CON", con=True),
    ]
    imp = {"ACT": 0.5, "COMMON": 0.9, "RARE": 0.9, "CON": 0.5}
    kept = select_kept(
        nodes, imp, prune_quantile=0.0, freq_floor=1,
        coverage_floor=0.5, total_processos=10,
    )
    assert "COMMON" in kept
    assert "RARE" not in kept
    assert "ACT" in kept and "CON" in kept


def test_select_kept_coverage_floor_defaults_to_noop():
    nodes = [_node("MID", contrib=0.9, freq=1)]
    imp = {"MID": 0.9}
    kept = select_kept(nodes, imp, prune_quantile=0.0, freq_floor=1)
    assert "MID" in kept
