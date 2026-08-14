
from __future__ import annotations

import random

from ..model.compare_timeline import timeline_rules
from ..model.comum_graph import build_swimlane
from ..model.predict import flow_paths, trace_states
from ..model.swimlane_agg import aggregate_swimlane_graph, processo_timeline, sequence_swimlane


def test_flow_order_representative_has_terminal_conclusions_unlike_chronological():
    acts = [
        {"source_id": "g", "tipo_acao": "GERACAO-PROCEDIMENTO", "unidade": "U1", "data_hora": "2025-01-01T10:00"},
        {"source_id": "r", "tipo_acao": "PROCESSO-REMETIDO-UNIDADE", "unidade": "U2", "data_hora": "2025-01-01T11:00"},
        {"source_id": "c1", "tipo_acao": "CONCLUSAO-AUTOMATICA-UNIDADE", "unidade": "U1", "data_hora": "2025-01-01T11:30"},
        {"source_id": "rc", "tipo_acao": "PROCESSO-RECEBIDO-UNIDADE", "unidade": "U2", "data_hora": "2025-01-01T12:00"},
        {"source_id": "c2", "tipo_acao": "CONCLUSAO-PROCESSO-UNIDADE", "unidade": "U2", "data_hora": "2025-01-01T13:00"},
    ]
    flow_edges = [{"from_id": "g", "to_id": "r"}, {"from_id": "g", "to_id": "c1"},
                  {"from_id": "r", "to_id": "rc"}, {"from_id": "rc", "to_id": "c2"}]

    def rep(traces):
        nodes, edges, total = aggregate_swimlane_graph(traces)
        return build_swimlane(nodes, edges, total_processos=total, coverage_floor=0.0)

    flow_rep = rep(flow_paths(acts, flow_edges, n_walks=6, rng=random.Random(0)))
    chrono_rep = rep([trace_states(acts)])
    assert timeline_rules(flow_rep)["CONCLUSAO_terminal"] is True
    assert timeline_rules(chrono_rep)["CONCLUSAO_terminal"] is False


def test_aggregate_swimlane_graph_counts_nodes_and_edges():
    traces = [
        ["GERACAO-PROCEDIMENTO@U1", "ASSINATURA-DOCUMENTO@U1"],
        ["GERACAO-PROCEDIMENTO@U1", "ASSINATURA-DOCUMENTO@U2"],
    ]
    nodes, edges, total = aggregate_swimlane_graph(traces)
    by = {n["state_key"]: n for n in nodes}
    assert by["GERACAO-PROCEDIMENTO@U1"]["frequency"] == 2
    assert by["GERACAO-PROCEDIMENTO@U1"]["n_processos"] == 2
    assert by["GERACAO-PROCEDIMENTO@U1"]["is_activation"] is True
    assert by["GERACAO-PROCEDIMENTO@U1"]["unidade_lane"] == "U1"
    epairs = {(e["from_key"], e["to_key"]): e for e in edges}
    assert epairs[("GERACAO-PROCEDIMENTO@U1", "ASSINATURA-DOCUMENTO@U1")]["frequency"] == 1
    assert total == 2


def test_sequence_swimlane_one_node_per_step_and_handoff():
    sw = sequence_swimlane(["G@U1", "A@U1", "R@U2", "C@U2"])
    assert [n["x"] for n in sw["nodes"]] == [0, 1, 2, 3]
    assert sw["nodes"][0]["is_start"] is True and sw["nodes"][-1]["is_end"] is True
    assert sw["max_x"] == 3 and sw["spine"] == ["s0", "s1", "s2", "s3"]
    e = next(e for e in sw["edges"] if e["from"] == "s1" and e["to"] == "s2")
    assert e["kind"] == "handoff"
    assert [lane["unidade"] for lane in sw["lanes"]] == ["U1", "U2"]


def test_processo_timeline_orders_by_time_with_real_edges_and_intervals():
    acts = [
        {"source_id": "a2", "data_hora": "2025-01-01T11:00:00",
         "tipo_acao": "PROCESSO-REMETIDO-UNIDADE", "unidade": "SEAD-PI/U2"},
        {"source_id": "a1", "data_hora": "2025-01-01T10:00:00",
         "tipo_acao": "GERACAO-PROCEDIMENTO", "unidade": "SEAD-PI/U1"},
        {"source_id": "a3", "data_hora": "2025-01-01T12:00:00",
         "tipo_acao": "CONCLUSAO-PROCESSO-UNIDADE", "unidade": "SEAD-PI/U2"},
    ]
    edges = [{"from_id": "a1", "to_id": "a2", "intervalo_horas": 1.0, "mesma_unidade": False},
             {"from_id": "a2", "to_id": "a3", "intervalo_horas": 1.0, "mesma_unidade": True}]
    sw = processo_timeline(acts, edges)
    assert [n["id"] for n in sw["nodes"]] == ["a1", "a2", "a3"]
    by = {n["id"]: n for n in sw["nodes"]}
    assert by["a1"]["x"] == 0 and by["a1"]["is_start"] is True
    assert by["a3"]["x"] == 2 and by["a3"]["is_end"] is True
    assert by["a2"]["is_end"] is False
    e = next(e for e in sw["edges"] if e["from"] == "a1" and e["to"] == "a2")
    assert e["kind"] == "handoff" and e["mean_interval_h"] == 1.0
    assert [lane["unidade"] for lane in sw["lanes"]] == ["SEAD-PI/U1", "SEAD-PI/U2"]
