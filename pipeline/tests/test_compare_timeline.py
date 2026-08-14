
from __future__ import annotations

from ..model.compare_timeline import handoff_count, handoff_pairs, recebido_paired_frac, single_start_ok, start_unit, timeline_rule_scores, timeline_rules, top_units


def test_handoff_count_counts_cross_lane_edges():
    sw = {"nodes": [{"id": "a", "lane": "SEAD-PI/GAB"}, {"id": "b", "lane": "SEAD-PI/GAB"},
                    {"id": "c", "lane": "SEAD-PI/SGACG"}],
          "edges": [{"from": "a", "to": "b"}, {"from": "b", "to": "c"}]}
    assert handoff_count(sw) == 1


def test_recebido_paired_frac_needs_prior_same_lane_remetido():
    sw = {"nodes": [
        {"id": "s0", "label": "GERACAO-PROCEDIMENTO", "lane": "U1", "x": 0},
        {"id": "s1", "label": "PROCESSO-REMETIDO-UNIDADE", "lane": "U2", "x": 1},
        {"id": "s2", "label": "PROCESSO-RECEBIDO-UNIDADE", "lane": "U2", "x": 2},
        {"id": "s3", "label": "PROCESSO-RECEBIDO-UNIDADE", "lane": "U3", "x": 3},
    ], "edges": []}
    assert recebido_paired_frac(sw) == 0.5


def test_single_start_ok_counts_geracao():
    one = {"nodes": [{"id": "a", "label": "GERACAO-PROCEDIMENTO", "lane": "U1", "x": 0}], "edges": []}
    two = {"nodes": [{"id": "a", "label": "GERACAO-PROCEDIMENTO", "lane": "U1", "x": 0},
                     {"id": "b", "label": "GERACAO-PROCEDIMENTO", "lane": "U2", "x": 4}], "edges": []}
    assert single_start_ok(one) is True
    assert single_start_ok(two) is False


def test_start_unit_returns_the_geracao_lane():
    sw = {"nodes": [
        {"id": "a", "label": "ASSINATURA-DOCUMENTO", "lane": "U9", "x": 3},
        {"id": "b", "label": "GERACAO-PROCEDIMENTO", "lane": "SEAD-PI/GAB", "x": 0},
    ], "edges": []}
    assert start_unit(sw) == "SEAD-PI/GAB"


def test_timeline_rule_scores_are_frequency_weighted_fractions():
    sw = {"nodes": [
        {"id": "g@U1", "label": "GERACAO-PROCEDIMENTO", "lane": "U1", "frequency": 100},
        {"id": "c@U1", "label": "CONCLUSAO-PROCESSO-UNIDADE", "lane": "U1", "frequency": 100},
        {"id": "x@U1", "label": "ASSINATURA-DOCUMENTO", "lane": "U1", "frequency": 3},
    ], "edges": [
        {"from": "g@U1", "to": "c@U1", "frequency": 100},
        {"from": "c@U1", "to": "x@U1", "frequency": 3},
    ]}
    s = timeline_rule_scores(sw)
    assert abs(s["CONCLUSAO_terminal"] - 0.97) < 1e-9
    assert s["GERACAO_source"] == 1.0
    assert s["REMETIDO_has_pred"] is None


def test_top_units_rolls_to_depth2_and_ranks_by_frequency():
    sw = {"nodes": [
        {"id": "a", "label": "X", "lane": "SEAD-PI/GAB/SGP", "frequency": 5},
        {"id": "b", "label": "Y", "lane": "SEAD-PI/GAB/DDP", "frequency": 3},
        {"id": "c", "label": "Z", "lane": "SEAD-PI/SGACG", "frequency": 1},
    ], "edges": []}
    tu = top_units(sw, roll_depth=2, k=2)
    assert tu[0] == "SEAD-PI/GAB"
    assert tu[1] == "SEAD-PI/SGACG"


def test_handoff_pairs_returns_cross_unit_pairs_only():
    sw = {"nodes": [
        {"id": "a", "label": "X", "lane": "SEAD-PI/GAB"},
        {"id": "b", "label": "Y", "lane": "SEAD-PI/GAB"},
        {"id": "c", "label": "Z", "lane": "SEAD-PI/SGACG"},
    ], "edges": [{"from": "a", "to": "b"}, {"from": "b", "to": "c"}]}
    assert handoff_pairs(sw) == {("SEAD-PI/GAB", "SEAD-PI/SGACG")}


def test_timeline_rules_all_pass_for_seguida_por_style_graph():
    sw = {"nodes": [
        {"id": "g@U1", "label": "GERACAO-PROCEDIMENTO", "lane": "U1"},
        {"id": "r@U2", "label": "PROCESSO-REMETIDO-UNIDADE", "lane": "U2"},
        {"id": "c@U2", "label": "CONCLUSAO-PROCESSO-UNIDADE", "lane": "U2"},
    ], "edges": [{"from": "g@U1", "to": "r@U2"}, {"from": "r@U2", "to": "c@U2"}]}
    assert timeline_rules(sw) == {
        "GERACAO_source": True, "REMETIDO_has_pred": True, "CONCLUSAO_terminal": True}


def test_timeline_rules_flags_nonterminal_conclusion():
    sw = {"nodes": [
        {"id": "c@U1", "label": "CONCLUSAO-AUTOMATICA-UNIDADE", "lane": "U1"},
        {"id": "x@U1", "label": "ASSINATURA-DOCUMENTO", "lane": "U1"},
    ], "edges": [{"from": "c@U1", "to": "x@U1"}]}
    assert timeline_rules(sw)["CONCLUSAO_terminal"] is False
