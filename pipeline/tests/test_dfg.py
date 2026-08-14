
from __future__ import annotations

from ..model.dfg import NODE_FEATURE_DIM, build_dfg, node_key


def _act(protocolo, tipo, band=0.5):
    return {
        "protocolo": protocolo, "tipo_acao": tipo,
        "node_contrib_score": 1.0, "node_advancement_score": 1.0,
        "node_speed_score": 0.5, "activity_band_score": band,
    }


def _edge(protocolo, f, t, interval=2.0):
    return {
        "protocolo": protocolo, "from_tipo": f, "to_tipo": t,
        "contrib_score": 1.0, "advancement_score": 1.0,
        "speed_score": 0.5, "intervalo_horas": interval,
    }


def test_two_instances_aggregate_to_three_node_dfg():
    chain = ["GERACAO-PROCEDIMENTO", "PROCESSO-REMETIDO-UNIDADE", "CONCLUSAO-PROCESSO-UNIDADE"]
    acts, edges = [], []
    for p in ("P1", "P2"):
        for tipo in chain:
            acts.append(_act(p, tipo))
        edges.append(_edge(p, chain[0], chain[1]))
        edges.append(_edge(p, chain[1], chain[2]))

    nodes, dfg = build_dfg(acts, edges, total_processos=2)

    assert len(nodes) == 3
    assert len(dfg) == 2
    for e in dfg:
        assert e["frequency"] == 2 and e["n_processos"] == 2

    by = {n["state_key"]: n for n in nodes}
    assert by["GERACAO-PROCEDIMENTO"]["is_activation"] is True
    assert by["CONCLUSAO-PROCESSO-UNIDADE"]["is_conclusion"] is True
    for n in nodes:
        assert n["feature_dim"] == NODE_FEATURE_DIM
        assert len(n["features"]) == NODE_FEATURE_DIM
        assert n["n_processos"] == 2


def test_node_count_bounded_and_process_coverage():
    acts = [
        _act("P1", "GERACAO-PROCEDIMENTO"),
        _act("P2", "GERACAO-PROCEDIMENTO"),
        _act("P1", "ASSINATURA-DOCUMENTO"),
    ]
    nodes, _ = build_dfg(acts, [], total_processos=2)
    by = {n["state_key"]: n for n in nodes}
    assert by["GERACAO-PROCEDIMENTO"]["features"][1] == 1.0
    assert by["ASSINATURA-DOCUMENTO"]["features"][1] == 0.5


def test_node_identity_grupo_variant():
    assert node_key("GERACAO-PROCEDIMENTO", "tipo_acao_grupo") == "GERACAO-PROCEDIMENTO@abertura"
    assert node_key("GERACAO-PROCEDIMENTO") == "GERACAO-PROCEDIMENTO"


def test_edge_endpoint_creates_node_and_null_interval():
    nodes, dfg = build_dfg(
        [],
        [{"protocolo": "P1", "from_tipo": "A", "to_tipo": "B",
          "contrib_score": 0.5, "advancement_score": 0.5, "speed_score": 0.5,
          "intervalo_horas": None}],
        total_processos=1,
    )
    assert {n["state_key"] for n in nodes} == {"A", "B"}
    assert dfg[0]["mean_intervalo_horas"] is None


def _act_u(protocolo, tipo, unidade, band=0.5):
    d = _act(protocolo, tipo, band)
    d["unidade"] = unidade
    return d


def _edge_u(protocolo, f, t, fu, tu, interval=2.0):
    d = _edge(protocolo, f, t, interval)
    d["from_unidade"], d["to_unidade"] = fu, tu
    return d


def test_node_identity_unidade_variant():
    assert (
        node_key("ASSINATURA-DOCUMENTO", "tipo_acao_unidade", "SEAD-PI/DG")
        == "ASSINATURA-DOCUMENTO@SEAD-PI/DG"
    )
    assert node_key("ASSINATURA-DOCUMENTO", "tipo_acao", "SEAD-PI/DG") == "ASSINATURA-DOCUMENTO"
    assert (
        node_key("GERACAO-PROCEDIMENTO", "tipo_acao_grupo", "SEAD-PI/DG")
        == "GERACAO-PROCEDIMENTO@abertura"
    )


def test_unidade_identity_splits_same_tipo_across_lanes():
    acts = [
        _act_u("P1", "GERACAO-PROCEDIMENTO", "UA"),
        _act_u("P1", "ASSINATURA-DOCUMENTO", "UA"),
        _act_u("P1", "ASSINATURA-DOCUMENTO", "UB"),
    ]
    nodes, _ = build_dfg(acts, [], total_processos=1, node_identity="tipo_acao_unidade")
    by = {n["state_key"]: n for n in nodes}
    assert set(by) == {
        "GERACAO-PROCEDIMENTO@UA",
        "ASSINATURA-DOCUMENTO@UA",
        "ASSINATURA-DOCUMENTO@UB",
    }
    assert by["ASSINATURA-DOCUMENTO@UB"]["unidade_lane"] == "UB"
    assert by["ASSINATURA-DOCUMENTO@UB"]["tipo_acao"] == "ASSINATURA-DOCUMENTO"
    assert by["GERACAO-PROCEDIMENTO@UA"]["is_activation"] is True


def test_unidade_identity_edges_use_lane_endpoints():
    edges = [
        _edge_u("P1", "GERACAO-PROCEDIMENTO", "PROCESSO-REMETIDO-UNIDADE", "UA", "UA"),
        _edge_u("P1", "PROCESSO-REMETIDO-UNIDADE", "PROCESSO-RECEBIDO-UNIDADE", "UA", "UB"),
    ]
    nodes, dfg = build_dfg([], edges, total_processos=1, node_identity="tipo_acao_unidade")
    pairs = {(e["from_key"], e["to_key"]) for e in dfg}
    assert ("PROCESSO-REMETIDO-UNIDADE@UA", "PROCESSO-RECEBIDO-UNIDADE@UB") in pairs
    assert any(n["state_key"] == "PROCESSO-RECEBIDO-UNIDADE@UB" for n in nodes)


def test_lane_depth_rolls_up_unidade():
    acts = [_act_u("P1", "ASSINATURA-DOCUMENTO", "SEAD-PI/DG/NTGD")]
    nodes, _ = build_dfg(
        acts, [], total_processos=1, node_identity="tipo_acao_unidade", lane_depth=2,
    )
    assert nodes[0]["unidade_lane"] == "SEAD-PI/DG"
    assert nodes[0]["state_key"] == "ASSINATURA-DOCUMENTO@SEAD-PI/DG"
