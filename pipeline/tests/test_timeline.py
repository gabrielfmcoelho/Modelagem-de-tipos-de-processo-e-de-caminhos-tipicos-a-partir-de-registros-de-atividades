
from __future__ import annotations

from ..model import process_state
from ..model.timeline import FLOW_ACTIVATION_TYPES, build_edges_for_processo


def _atv(sid, dh, tipo, uni, src=None, ref=None):
    d = {"source_id": sid, "data_hora": dh, "tipo_acao": tipo, "unidade": uni}
    if src is not None:
        d["source_unidade"] = src
    if ref is not None:
        d["ref_id"] = ref
    return d


def _edges_set(flow):
    return {(e["from_id"], e["to_id"]) for e in flow}


def test_flow_activation_matches_process_state():
    assert FLOW_ACTIVATION_TYPES == process_state.ACTIVATION_TYPES
    assert "PROCESSO-REMETIDO-UNIDADE" in FLOW_ACTIVATION_TYPES
    assert "PROCESSO-RECEBIDO-UNIDADE" not in FLOW_ACTIVATION_TYPES


def test_unit_activated_by_remetido_without_recebido():
    acts = [
        _atv("g", "2025-01-01T10:00:00", "GERACAO-PROCEDIMENTO", "A"),
        _atv("r", "2025-01-01T11:00:00", "PROCESSO-REMETIDO-UNIDADE", "B", src="A"),
        _atv("w", "2025-01-01T12:00:00", "GERACAO-DOCUMENTO", "B"),
        _atv("c", "2025-01-01T13:00:00", "CONCLUSAO-AUTOMATICA-UNIDADE", "B"),
    ]
    flow, _ = build_edges_for_processo(acts)
    to_ids = {e["to_id"] for e in flow}
    assert "w" in to_ids and "c" in to_ids
    assert ("g", "r") in _edges_set(flow)


def test_concurrent_conclusions_all_chained():
    acts = [
        _atv("g", "2025-01-01T10:00:00", "GERACAO-PROCEDIMENTO", "U"),
        _atv("a", "2025-01-01T11:00:00", "ASSINATURA-DOCUMENTO", "U"),
        _atv("c1", "2025-01-01T12:00:00", "CONCLUSAO-AUTOMATICA-UNIDADE", "U"),
        _atv("c2", "2025-01-01T12:00:00", "CONCLUSAO-AUTOMATICA-UNIDADE", "U"),
        _atv("c3", "2025-01-01T12:00:00", "CONCLUSAO-AUTOMATICA-UNIDADE", "U"),
    ]
    flow, _ = build_edges_for_processo(acts)
    to_ids = {e["to_id"] for e in flow}
    assert {"c1", "c2", "c3"} <= to_ids
    assert _edges_set(flow) >= {("a", "c1"), ("a", "c2"), ("a", "c3")}


def test_conclusion_never_emits_outgoing_edge():
    acts = [
        _atv("a", "2025-01-01T11:00:00", "GERACAO-PROCEDIMENTO", "U"),
        _atv("c1", "2025-01-01T12:00:00", "CONCLUSAO-AUTOMATICA-UNIDADE", "U"),
        _atv("c2", "2025-01-01T12:00:00", "CONCLUSAO-AUTOMATICA-UNIDADE", "U"),
    ]
    flow, _ = build_edges_for_processo(acts)
    from_ids = {e["from_id"] for e in flow}
    assert "c1" not in from_ids and "c2" not in from_ids


def test_same_unit_chain_and_remetido_recebido_bridge():
    acts = [
        _atv("g", "2025-01-01T10:00:00", "GERACAO-PROCEDIMENTO", "A"),
        _atv("a", "2025-01-01T10:30:00", "GERACAO-DOCUMENTO", "A"),
        _atv("r", "2025-01-01T11:00:00", "PROCESSO-REMETIDO-UNIDADE", "B", src="A"),
        _atv("rec", "2025-01-01T11:30:00", "PROCESSO-RECEBIDO-UNIDADE", "B"),
    ]
    flow, _ = build_edges_for_processo(acts)
    e = _edges_set(flow)
    assert ("g", "a") in e
    assert ("a", "r") in e
    assert ("r", "rec") in e


def test_single_activity_no_edges():
    flow, indep = build_edges_for_processo([_atv("x", "2025-01-01T10:00:00", "GERACAO-PROCEDIMENTO", "U")])
    assert flow == [] and indep == []


def test_document_events_chain_when_flow_does_not_connect_them():
    acts = [
        _atv("g",  "2025-01-01T10:00:00", "GERACAO-PROCEDIMENTO", "A"),
        _atv("d1", "2025-01-01T10:10:00", "GERACAO-DOCUMENTO", "A", ref="doc:5"),
        _atv("s1", "2025-01-01T10:20:00", "ASSINATURA-DOCUMENTO", "Y", ref="doc:5"),
        _atv("s2", "2025-01-01T10:30:00", "ASSINATURA-DOCUMENTO", "Z", ref="doc:5"),
    ]
    _, indep = build_edges_for_processo(acts)
    e = _edges_set(indep)
    assert ("d1", "s1") in e and ("s1", "s2") in e
    assert ("d1", "s2") not in e
    assert all(edge["ref_id"] == "doc:5" for edge in indep)


def test_document_event_in_non_activated_unit_is_reachable():
    acts = [
        _atv("g",  "2025-01-01T10:00:00", "GERACAO-PROCEDIMENTO", "A"),
        _atv("d1", "2025-01-01T10:10:00", "GERACAO-DOCUMENTO", "A", ref="doc:9"),
        _atv("s",  "2025-01-01T10:40:00", "ASSINATURA-DOCUMENTO", "Z", ref="doc:9"),
    ]
    flow, indep = build_edges_for_processo(acts)
    flow_ids = {e["from_id"] for e in flow} | {e["to_id"] for e in flow}
    assert "s" not in flow_ids
    assert ("d1", "s") in _edges_set(indep)


def test_distinct_refs_do_not_cross_link():
    acts = [
        _atv("g",  "2025-01-01T10:00:00", "GERACAO-PROCEDIMENTO", "A"),
        _atv("a1", "2025-01-01T10:10:00", "ASSINATURA-DOCUMENTO", "A", ref="doc:1"),
        _atv("a2", "2025-01-01T10:20:00", "ASSINATURA-DOCUMENTO", "A", ref="doc:2"),
    ]
    _, indep = build_edges_for_processo(acts)
    assert ("a1", "a2") not in _edges_set(indep)


def test_doc_chain_skips_exact_flow_duplicates():
    acts = [
        _atv("g",  "2025-01-01T10:00:00", "GERACAO-PROCEDIMENTO", "A"),
        _atv("d1", "2025-01-01T10:10:00", "GERACAO-DOCUMENTO", "A", ref="doc:7"),
        _atv("d2", "2025-01-01T10:20:00", "ASSINATURA-DOCUMENTO", "A", ref="doc:7"),
    ]
    flow, indep = build_edges_for_processo(acts)
    assert ("d1", "d2") in _edges_set(flow)
    assert ("d1", "d2") not in _edges_set(indep)


def test_remit_bridges_from_source_last_real_work_across_conclusion():
    acts = [
        _atv("g", "2025-01-01T10:00:00", "GERACAO-PROCEDIMENTO", "A"),
        _atv("a", "2025-01-01T11:00:00", "ASSINATURA-DOCUMENTO", "A"),
        _atv("c", "2025-01-01T12:00:00", "CONCLUSAO-AUTOMATICA-UNIDADE", "A"),
        _atv("r", "2025-01-01T12:00:00", "PROCESSO-REMETIDO-UNIDADE", "B", src="A"),
    ]
    flow, _ = build_edges_for_processo(acts)
    assert ("a", "r") in _edges_set(flow)
    assert "r" in {e["to_id"] for e in flow}


def test_receipt_not_reordered_before_units_own_conclude_and_forward():
    acts = [
        _atv("g",    "2025-01-01T10:00:00", "GERACAO-PROCEDIMENTO", "A"),
        _atv("rA",   "2025-01-01T10:01:00", "PROCESSO-REMETIDO-UNIDADE", "B", src="A"),
        _atv("recB", "2025-01-01T10:02:00", "PROCESSO-RECEBIDO-UNIDADE", "B"),
        _atv("cB",   "2025-01-01T10:02:30", "CONCLUSAO-AUTOMATICA-UNIDADE", "B"),
        _atv("rC",   "2025-01-01T10:02:30", "PROCESSO-REMETIDO-UNIDADE", "C", src="B"),
    ]
    flow, _ = build_edges_for_processo(acts)
    e = _edges_set(flow)
    assert ("rA", "recB") in e
    assert ("recB", "cB") in e
    assert ("recB", "rC") in e


def test_reabertura_forward_links_to_next_same_unit_remit():
    acts = [
        _atv("g",    "2025-01-01T10:00:00", "GERACAO-PROCEDIMENTO", "C"),
        _atv("reab", "2025-01-01T11:00:00", "REABERTURA-PROCESSO-UNIDADE", "D"),
        _atv("w",    "2025-01-01T11:30:00", "ASSINATURA-DOCUMENTO", "C"),
        _atv("rD",   "2025-01-01T12:00:00", "PROCESSO-REMETIDO-UNIDADE", "D", src="C"),
    ]
    flow, _ = build_edges_for_processo(acts)
    e = _edges_set(flow)
    assert ("reab", "rD") in e
    assert ("w", "rD") in e


def test_reabertura_with_no_later_same_unit_work_stays_frontier():
    acts = [
        _atv("g",    "2025-01-01T10:00:00", "GERACAO-PROCEDIMENTO", "A"),
        _atv("a",    "2025-01-01T10:30:00", "ASSINATURA-DOCUMENTO", "A"),
        _atv("reab", "2025-01-01T11:00:00", "REABERTURA-PROCESSO-UNIDADE", "B"),
    ]
    flow, _ = build_edges_for_processo(acts)
    assert "reab" not in {e["from_id"] for e in flow}


def test_reabertura_takes_no_incoming_edge():
    acts = [
        _atv("g",    "2025-01-01T10:00:00", "GERACAO-PROCEDIMENTO", "U"),
        _atv("w",    "2025-01-01T10:30:00", "GERACAO-DOCUMENTO", "U"),
        _atv("reab", "2025-01-01T11:00:00", "REABERTURA-PROCESSO-UNIDADE", "U"),
        _atv("w2",   "2025-01-01T11:30:00", "GERACAO-DOCUMENTO", "U"),
    ]
    flow, _ = build_edges_for_processo(acts)
    assert "reab" not in {e["to_id"] for e in flow}
    assert ("reab", "w2") in _edges_set(flow)


def test_out_of_order_logged_remit_and_conclusion_are_repaired():
    acts = [
        _atv("g",    "2025-01-01T10:00:00", "GERACAO-PROCEDIMENTO", "A"),
        _atv("a",    "2025-01-01T10:00:05", "ASSINATURA-DOCUMENTO", "A"),
        _atv("recB", "2025-01-01T10:00:11", "PROCESSO-RECEBIDO-UNIDADE", "B"),
        _atv("cB",   "2025-01-01T10:00:11", "CONCLUSAO-AUTOMATICA-UNIDADE", "B"),
        _atv("rC",   "2025-01-01T10:00:11", "PROCESSO-REMETIDO-UNIDADE", "C", src="B"),
        _atv("rB",   "2025-01-01T10:00:14", "PROCESSO-REMETIDO-UNIDADE", "B", src="A"),
    ]
    flow, _ = build_edges_for_processo(acts)
    e = _edges_set(flow)
    assert ("rB", "recB") in e
    assert ("recB", "rC") in e
    assert ("recB", "cB") in e
    assert "rC" in {x["to_id"] for x in flow}


def test_rc5_does_not_invent_a_predecessor_when_none_exists_before():
    acts = [
        _atv("g", "2025-01-01T10:00:00", "GERACAO-PROCEDIMENTO", "A"),
        _atv("a", "2025-01-01T10:00:05", "ASSINATURA-DOCUMENTO", "A"),
        _atv("rZ", "2025-01-01T10:00:10", "PROCESSO-REMETIDO-UNIDADE", "B", src="Z"),
    ]
    flow, _ = build_edges_for_processo(acts)
    assert not any(e["to_id"] == "rZ" and e["from_id"] in {"g", "a"} for e in flow)


ESTOQUE_TIE_BREAK = {
    "PROCESSO-REMETIDO-UNIDADE": 0,
    "PROCESSO-RECEBIDO-UNIDADE": 1,
    "GERACAO-PROCEDIMENTO": 1,
    "REABERTURA-PROCESSO-UNIDADE": 1,
    "CONCLUSAO-PROCESSO-UNIDADE": 2,
    "CONCLUSAO-AUTOMATICA-UNIDADE": 2,
}


def test_tie_break_matches_the_canonical_estoque_rule():
    from ..model.timeline import transfer_priority

    mismatched = {t: (transfer_priority(t), want) for t, want in ESTOQUE_TIE_BREAK.items()
                  if transfer_priority(t) != want}
    assert not mismatched, (
        "the same-timestamp tie-break must match estoque_rules.tie_break_priority, the canonical "
        "rule that builds the estoque de processos in the sei gold DAG "
        "(data-lakehouse-sead/infra/airflow/scripts/estoque_rules.py). It orders REMETIDO before "
        "everything and CONCLUSAO last, so that a close and a re-open sharing a timestamp resolve "
        "to CLOSED. Inverting it makes those cases read as still open, and the two systems then "
        "disagree about which processos are in the corpus at all. got (ours, expected): "
        + repr(mismatched))


def test_a_close_and_a_reopen_on_one_timestamp_resolve_to_closed():
    from ..model.process_state import _walk_units
    from ..model.timeline import sort_and_fix_activities

    t = "2025-06-01T10:00:00"
    acts = [
        {"tipo_acao": "GERACAO-PROCEDIMENTO", "unidade": "GAB",
         "data_hora": "2025-01-02T09:00:00", "source_id": 1},
        {"tipo_acao": "CONCLUSAO-PROCESSO-UNIDADE", "unidade": "GAB",
         "data_hora": t, "source_id": 2},
        {"tipo_acao": "PROCESSO-REMETIDO-UNIDADE", "unidade": "GAB",
         "data_hora": t, "source_id": 3},
    ]
    records = _walk_units(sort_and_fix_activities(acts), "P1")
    assert [r["situacao"] for r in records] == ["concluida"]
