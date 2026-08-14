
from __future__ import annotations

from ..model.comum_graph import build_swimlane, find_spine, layer_assignment, longitudinal_rank, order_lanes


def _n(key, lane, *, tipo=None, freq=5, procs=5, act=False, con=False, grupo="tramitacao"):
    return {
        "state_key": key,
        "tipo_acao": tipo or key.split("@")[0],
        "unidade_lane": lane,
        "frequency": freq,
        "n_processos": procs,
        "is_activation": act,
        "is_conclusion": con,
        "grupo": grupo,
    }


def _e(f, t, *, freq=5, procs=5, interval=2.0):
    return {
        "from_key": f, "to_key": t,
        "frequency": freq, "n_processos": procs,
        "mean_intervalo_horas": interval,
    }


def test_longitudinal_rank_chain():
    nodes = [_n("G@UA", "UA", act=True), _n("A@UA", "UA"), _n("C@UB", "UB", con=True)]
    edges = [_e("G@UA", "A@UA"), _e("A@UA", "C@UB")]
    ranks = longitudinal_rank(nodes, edges)
    assert ranks["G@UA"] == 0
    assert ranks["A@UA"] == 1
    assert ranks["C@UB"] == 2


def test_longitudinal_rank_handles_cycle():
    nodes = [_n("A", "U", act=True), _n("B", "U"), _n("C", "U", con=True)]
    edges = [_e("A", "B"), _e("B", "C"), _e("C", "B")]
    ranks = longitudinal_rank(nodes, edges)
    assert ranks["A"] == 0 and ranks["B"] == 1 and ranks["C"] == 2


def test_order_lanes_by_mean_rank():
    nodes = [_n("G@UA", "UA", act=True), _n("A@UA", "UA"), _n("C@UB", "UB", con=True)]
    edges = [_e("G@UA", "A@UA"), _e("A@UA", "C@UB")]
    lanes = order_lanes(nodes, longitudinal_rank(nodes, edges))
    assert lanes == ["UA", "UB"]


def test_find_spine_picks_highest_coverage_path():
    nodes = [_n("S", "U", act=True), _n("X", "U"), _n("Y", "U"), _n("E", "U", con=True)]
    edges = [
        _e("S", "X", procs=9), _e("X", "E", procs=9),
        _e("S", "Y", procs=2), _e("Y", "E", procs=2),
    ]
    assert find_spine(nodes, edges) == ["S", "X", "E"]


def test_build_swimlane_classifies_within_vs_handoff():
    nodes = [
        _n("G@UA", "UA", act=True), _n("R@UA", "UA"),
        _n("RC@UB", "UB"), _n("C@UB", "UB", con=True),
    ]
    edges = [_e("G@UA", "R@UA"), _e("R@UA", "RC@UB"), _e("RC@UB", "C@UB")]
    sw = build_swimlane(nodes, edges, total_processos=10)

    by = {(e["from"], e["to"]): e for e in sw["edges"]}
    assert by[("G@UA", "R@UA")]["kind"] == "within"
    assert by[("R@UA", "RC@UB")]["kind"] == "handoff"
    assert [lane["unidade"] for lane in sw["lanes"]] == ["UA", "UB"]
    assert sw["spine"][0] == "G@UA" and sw["spine"][-1] == "C@UB"

    g = next(n for n in sw["nodes"] if n["id"] == "G@UA")
    assert g["coverage"] == 0.5 and g["is_start"] is True


def test_build_swimlane_coverage_floor_drops_rare_edges():
    nodes = [_n("S", "U", act=True), _n("E", "U", con=True)]
    edges = [_e("S", "E", procs=1)]
    sw = build_swimlane(nodes, edges, total_processos=10, coverage_floor=0.5)
    assert sw["edges"] == []
    assert sw["nodes"] == []


def test_layer_assignment_longest_path():
    nodes = [_n("S", "U", act=True), _n("A", "U"), _n("B", "U"), _n("D", "U", con=True)]
    edges = [_e("S", "A"), _e("A", "B"), _e("B", "D"), _e("S", "D")]
    layers = layer_assignment(nodes, edges)
    assert layers["S"] == 0
    assert layers["A"] == 1
    assert layers["B"] == 2
    assert layers["D"] == 3


def test_build_swimlane_x_is_longest_path():
    nodes = [_n("S", "U", act=True), _n("A", "U"), _n("B", "U"), _n("D", "U", con=True)]
    edges = [_e("S", "A"), _e("A", "B"), _e("B", "D"), _e("S", "D")]
    sw = build_swimlane(nodes, edges, total_processos=1)
    x = {n["id"]: n["x"] for n in sw["nodes"]}
    assert x["D"] == 3


def test_lane_spans_open_close():
    nodes = [
        _n("G@GAB", "GAB", act=True), _n("A@GAB", "GAB"), _n("R@GAB", "GAB"),
        _n("RC@SGACG", "SGACG"), _n("W@SGACG", "SGACG"), _n("C@SGACG", "SGACG", con=True),
    ]
    edges = [
        _e("G@GAB", "A@GAB"), _e("A@GAB", "R@GAB"), _e("R@GAB", "RC@SGACG"),
        _e("RC@SGACG", "W@SGACG"), _e("W@SGACG", "C@SGACG"),
    ]
    sw = build_swimlane(nodes, edges, total_processos=1)
    lanes = {lane["unidade"]: lane for lane in sw["lanes"]}
    assert lanes["GAB"]["x_start"] == 0 and lanes["GAB"]["x_end"] == 2
    assert lanes["SGACG"]["x_start"] == 3 and lanes["SGACG"]["x_end"] == 5


def test_node_phases_start_middle_end():
    nodes = [_n("S", "U", act=True), _n("M", "U"), _n("E", "U", con=True)]
    edges = [_e("S", "M"), _e("M", "E")]
    sw = build_swimlane(nodes, edges, total_processos=1)
    phase = {n["id"]: n["phase"] for n in sw["nodes"]}
    assert phase["S"] == "start"
    assert phase["M"] == "middle"
    assert phase["E"] == "end"


def test_semantic_start_end_ignores_filter_orphaned_nodes():
    nodes = [
        _n("GERACAO-PROCEDIMENTO@U", "U", tipo="GERACAO-PROCEDIMENTO"),
        _n("ENVIO-EMAIL@U", "U", tipo="ENVIO-EMAIL"),
        _n("MID@U", "U", tipo="OUTROS"),
        _n("CONCLUSAO-PROCESSO-UNIDADE@U", "U", tipo="CONCLUSAO-PROCESSO-UNIDADE", con=True),
    ]
    edges = [
        _e("GERACAO-PROCEDIMENTO@U", "MID@U"),
        _e("ENVIO-EMAIL@U", "MID@U"),
        _e("MID@U", "CONCLUSAO-PROCESSO-UNIDADE@U"),
    ]
    sw = build_swimlane(nodes, edges, total_processos=1)
    by = {n["id"]: n for n in sw["nodes"]}
    assert by["GERACAO-PROCEDIMENTO@U"]["is_start"] is True
    assert by["GERACAO-PROCEDIMENTO@U"]["phase"] == "start"
    assert by["ENVIO-EMAIL@U"]["is_start"] is False
    assert by["ENVIO-EMAIL@U"]["phase"] == "middle"
    assert by["CONCLUSAO-PROCESSO-UNIDADE@U"]["is_end"] is True


def test_build_swimlane_passes_through_gcn_overlay():
    nodes = [
        _n("S", "U", act=True),
        {**_n("M", "U"), "gcn_importance": 0.7, "in_ideal_graph": True},
        _n("E", "U", con=True),
    ]
    edges = [_e("S", "M"), _e("M", "E")]
    sw = build_swimlane(nodes, edges, total_processos=5)
    m = next(n for n in sw["nodes"] if n["id"] == "M")
    assert m["gcn_importance"] == 0.7
    assert m["gcn_kept"] is True


def test_build_swimlane_drops_nodes_left_isolated_by_floor():
    nodes = [
        _n("S", "U", act=True), _n("MID", "U"),
        _n("RARE", "U"), _n("E", "U", con=True),
    ]
    edges = [
        _e("S", "MID", procs=8), _e("MID", "E", procs=8),
        _e("S", "RARE", procs=1),
    ]
    sw = build_swimlane(nodes, edges, total_processos=10, coverage_floor=0.5)
    ids = {n["id"] for n in sw["nodes"]}
    assert "RARE" not in ids
    assert {"S", "MID", "E"} <= ids


def test_remetido_activation_is_not_a_false_start():
    nodes = [
        _n("G", "UA", act=True),
        {**_n("REM", "UA"), "is_activation": True},
        _n("RC", "UB"),
        _n("C", "UB", con=True),
    ]
    edges = [_e("G", "REM"), _e("REM", "RC"), _e("RC", "C")]
    sw = build_swimlane(nodes, edges, total_processos=5)
    by = {n["id"]: n for n in sw["nodes"]}
    assert by["G"]["is_start"] is True
    assert by["REM"]["is_start"] is False
    assert by["C"]["is_end"] is True
    assert sw["spine"][0] == "G" and sw["spine"][-1] == "C"
