
from __future__ import annotations

from ..model.link_score import score_process, speed_scores_from_durations
from ..model.process_state import compute_processo_state


def _atv(source_id, data_hora, unidade, tipo_acao):
    return {
        "source_id": source_id,
        "data_hora": data_hora,
        "unidade": unidade,
        "tipo_acao": tipo_acao,
        "source_unidade": None,
        "ref_id": None,
    }


def _score(activities, speed=0.5, **kw):
    state = compute_processo_state(activities, protocolo_formatado="P")
    return score_process(activities, state, speed=speed, **kw)


def test_speed_scores_invert_duration_percentile():
    speed = speed_scores_from_durations({"P1": 10.0, "P2": 20.0, "P3": 30.0})
    assert speed["P1"] == 1.0
    assert speed["P2"] == 0.5
    assert speed["P3"] == 0.0


def test_linear_concluded_process_all_advancing_no_rework():
    acts = [
        _atv(1, "2025-01-01T10:00:00", "U1", "GERACAO-PROCEDIMENTO"),
        _atv(2, "2025-01-01T11:00:00", "U1", "ASSINATURA-DOCUMENTO"),
        _atv(3, "2025-01-01T12:00:00", "U1", "CONCLUSAO-PROCESSO-UNIDADE"),
    ]
    edges, nodes = _score(acts, speed=1.0)
    assert all(n["node_advancement_score"] == 1.0 for n in nodes.values())
    assert all(not n["rework"] for n in nodes.values())
    assert all(e["advancement_score"] == 1.0 for e in edges)
    assert all(not e["rework_flag"] and not e["idle_flag"] for e in edges)
    assert all(e["contrib_score"] == 1.0 for e in edges)


def test_reabertura_marks_rework_legs():
    acts = [
        _atv(1, "2025-01-01T10:00:00", "U1", "GERACAO-PROCEDIMENTO"),
        _atv(2, "2025-01-02T10:00:00", "U1", "CONCLUSAO-PROCESSO-UNIDADE"),
        _atv(3, "2025-02-01T10:00:00", "U1", "REABERTURA-PROCESSO-UNIDADE"),
        _atv(4, "2025-02-02T10:00:00", "U1", "CONCLUSAO-PROCESSO-UNIDADE"),
    ]
    edges, nodes = _score(acts, speed=0.0, rework_penalty=0.5)
    assert nodes[1]["rework"] is False and nodes[2]["rework"] is False
    assert nodes[3]["rework"] is True and nodes[4]["rework"] is True
    assert nodes[3]["node_advancement_score"] == 0.5
    cd = [e for e in edges if e["from_id"] == 3 and e["to_id"] == 4]
    assert cd and cd[0]["rework_flag"] is True
    assert cd[0]["advancement_score"] == 0.5
    ab = [e for e in edges if e["from_id"] == 1 and e["to_id"] == 2]
    assert ab and ab[0]["rework_flag"] is False and ab[0]["advancement_score"] == 1.0


def test_idle_edge_flagged_and_penalized():
    acts = [
        _atv(1, "2025-01-01T10:00:00", "U1", "GERACAO-PROCEDIMENTO"),
        _atv(2, "2025-01-01T11:00:00", "U1", "ASSINATURA-DOCUMENTO"),
        _atv(3, "2025-06-01T11:00:00", "U1", "ASSINATURA-DOCUMENTO"),
        _atv(4, "2025-06-01T12:00:00", "U1", "CONCLUSAO-PROCESSO-UNIDADE"),
    ]
    edges, _ = _score(acts, speed=1.0, idle_penalty=0.4, idle_factor=3.0, idle_floor_h=24.0)
    by = {(e["from_id"], e["to_id"]): e for e in edges}
    assert by[(2, 3)]["idle_flag"] is True
    assert by[(2, 3)]["advancement_score"] == 0.6
    assert by[(1, 2)]["idle_flag"] is False
    assert by[(1, 2)]["advancement_score"] == 1.0


def test_scores_stay_in_unit_interval():
    acts = [
        _atv(1, "2025-01-01T10:00:00", "U1", "GERACAO-PROCEDIMENTO"),
        _atv(2, "2025-01-02T10:00:00", "U1", "CONCLUSAO-PROCESSO-UNIDADE"),
    ]
    edges, nodes = _score(acts, speed=0.7)
    for e in edges:
        assert 0.0 <= e["contrib_score"] <= 1.0
        assert 0.0 <= e["advancement_score"] <= 1.0
    for n in nodes.values():
        assert 0.0 <= n["node_contrib_score"] <= 1.0
