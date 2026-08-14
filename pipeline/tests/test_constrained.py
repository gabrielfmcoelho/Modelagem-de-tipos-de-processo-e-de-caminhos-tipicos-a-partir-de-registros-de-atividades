
from __future__ import annotations

import random

from ..model.constrained import FlowState, generate_constrained, generate_full, medoid_trace, valid_mask, validity_score
from ..model.predict import suffix_prefix_distance


class _Script:

    def __init__(self, steps):
        self.steps = steps

    def next_distribution(self, seq):
        i = len(seq) - 1
        if i < len(self.steps):
            return [("<END>", 0.9), (self.steps[i], 0.1)]
        return [("<END>", 1.0)]


def test_flowstate_complete_only_when_started_and_no_open_lane():
    fs = FlowState()
    assert not fs.complete()
    fs.step("GERACAO-PROCEDIMENTO@U1")
    assert not fs.complete()
    fs.step("CONCLUSAO-PROCESSO-UNIDADE@U1")
    assert fs.complete()


def test_generate_full_stitches_branches_until_all_lanes_close():
    steps = ["PROCESSO-REMETIDO-UNIDADE@U2", "PROCESSO-RECEBIDO-UNIDADE@U2",
             "CONCLUSAO-PROCESSO-UNIDADE@U1", "CONCLUSAO-PROCESSO-UNIDADE@U2"]
    model = _Script(steps)
    full = generate_full(model, "GERACAO-PROCEDIMENTO@U1", strategy="greedy")
    assert full == ["GERACAO-PROCEDIMENTO@U1"] + steps
    assert validity_score(full) == 1.0
    short = generate_constrained(model, "GERACAO-PROCEDIMENTO@U1", strategy="greedy")
    assert len(short) < len(full)


def test_valid_mask_matches_flowstate_allows():
    vocab = ["PROCESSO-RECEBIDO-UNIDADE@U2", "ASSINATURA-DOCUMENTO@U1", "GERACAO-PROCEDIMENTO@U3"]
    mask = valid_mask(["GERACAO-PROCEDIMENTO@U1"], vocab)
    assert mask == [False, True, False]


def test_validity_score_is_one_for_valid_and_lower_for_invalid():
    valid = ["GERACAO-PROCEDIMENTO@U1", "PROCESSO-REMETIDO-UNIDADE@U2",
             "PROCESSO-RECEBIDO-UNIDADE@U2", "CONCLUSAO-PROCESSO-UNIDADE@U2"]
    assert validity_score(valid) == 1.0
    invalid = ["GERACAO-PROCEDIMENTO@U1", "PROCESSO-RECEBIDO-UNIDADE@U2"]
    assert validity_score(invalid) < 1.0


def test_flowstate_rejects_recebido_without_pending_remetido():
    fs = FlowState()
    fs.step("GERACAO-PROCEDIMENTO@U1")
    assert fs.allows("PROCESSO-RECEBIDO-UNIDADE@U2") is False
    fs.step("PROCESSO-REMETIDO-UNIDADE@U2")
    assert fs.allows("PROCESSO-RECEBIDO-UNIDADE@U2") is True


def test_flowstate_rejects_second_geracao():
    fs = FlowState()
    fs.step("GERACAO-PROCEDIMENTO@U1")
    assert fs.allows("GERACAO-PROCEDIMENTO@U2") is False


def test_flowstate_conclusion_requires_open_lane():
    fs = FlowState()
    fs.step("GERACAO-PROCEDIMENTO@U1")
    assert fs.allows("CONCLUSAO-PROCESSO-UNIDADE@U1") is True
    assert fs.allows("CONCLUSAO-PROCESSO-UNIDADE@U2") is False


class _FakeModel:
    def next_distribution(self, prefix):
        return [("PROCESSO-RECEBIDO-UNIDADE@U2", 0.9), ("ASSINATURA-DOCUMENTO@U1", 0.1)]


def test_generate_constrained_never_emits_unpaired_recebido():
    seq = generate_constrained(_FakeModel(), "GERACAO-PROCEDIMENTO@U1",
                               max_steps=6, strategy="greedy", rng=random.Random(0))
    assert seq[0] == "GERACAO-PROCEDIMENTO@U1"
    assert "PROCESSO-RECEBIDO-UNIDADE@U2" not in seq


def test_medoid_trace_picks_the_central_trace():
    a = ["X", "Y", "Z"]
    b = ["X", "Y", "Z"]
    far = ["A", "B", "C", "D", "E"]
    assert medoid_trace([a, b, far]) in (a, b)


class _Always:

    def __init__(self, state):
        self.state = state

    def next_distribution(self, seq):
        return [(self.state, 1.0)]


def test_generate_constrained_seeds_flowstate_from_a_list_prefix():
    model = _Always("PROCESSO-RECEBIDO-UNIDADE@U2")
    blocked = generate_constrained(model, ["GERACAO-PROCEDIMENTO@U1"],
                                   strategy="greedy", max_steps=3)
    assert blocked == ["GERACAO-PROCEDIMENTO@U1"]
    prefix = ["GERACAO-PROCEDIMENTO@U1", "PROCESSO-REMETIDO-UNIDADE@U2"]
    allowed = generate_constrained(model, prefix, strategy="greedy", max_steps=1)
    assert allowed == prefix + ["PROCESSO-RECEBIDO-UNIDADE@U2"]
    assert validity_score(allowed) == 1.0


def test_generate_constrained_accepts_the_kwargs_the_eval_path_passes():
    seq = generate_constrained(_FakeModel(), ["GERACAO-PROCEDIMENTO@U1"], max_steps=4,
                               strategy="greedy", rng=random.Random(0),
                               is_conclusion=lambda s: False)
    assert validity_score(seq) == 1.0


def test_suffix_prefix_distance_routes_through_the_supplied_generator():
    calls = []

    def _fake(prefix, **kwargs):
        calls.append(list(prefix))
        return list(prefix) + ["X"]

    suffix_prefix_distance(_Always("Z"), [["A", "B", "C", "D"]],
                           is_conclusion=lambda s: s == "D",
                           prefix_fracs=(0.5,), generate=_fake)
    assert calls == [["A", "B"]]


def test_ordinary_actions_are_not_gated_on_an_open_lane():
    from ..model.constrained import FlowState
    fs = FlowState()
    for s in ["GERACAO-PROCEDIMENTO@U1", "CONCLUSAO-PROCESSO-UNIDADE@U1"]:
        assert fs.allows(s)
        fs.step(s)
    assert fs.allows("ASSINATURA-DOCUMENTO@U1")
    assert fs.allows("GERACAO-DOCUMENTO@U9")


def test_structural_rules_from_the_estoque_spec_still_hold():
    from ..model.constrained import FlowState
    fs = FlowState()
    assert not fs.allows("CONCLUSAO-PROCESSO-UNIDADE@U1")
    assert fs.allows("ASSINATURA-DOCUMENTO@U1")
    fs.step("GERACAO-PROCEDIMENTO@U1")
    assert not fs.allows("GERACAO-PROCEDIMENTO@U2")
    assert fs.allows("CONCLUSAO-PROCESSO-UNIDADE@U1")
    assert not fs.allows("CONCLUSAO-PROCESSO-UNIDADE@U2")


def test_flowstate_supports_alphabets_without_a_lane_separator():
    from ..model.constrained import FlowState
    fs = FlowState()
    itinerary = ["SEAD-PI/GAB/SLC/PROTSLC", "SEAD-PI/GAB/SLC/CADUF", "SEAD-PI/GAB/SLC"]
    for state in itinerary:
        assert fs.allows(state), f"itinerary state rejected: {state}"
        fs.step(state)


def test_flowstate_supports_the_procedure_alphabet():
    from ..model.constrained import FlowState
    fs = FlowState()
    for state in ["GERACAO-DOCUMENTO", "ASSINATURA-DOCUMENTO", "ARQUIVO-ANEXADO"]:
        assert fs.allows(state), state
        fs.step(state)


def test_single_geracao_rule_survives_the_fix():
    from ..model.constrained import FlowState
    fs = FlowState()
    assert fs.allows("GERACAO-PROCEDIMENTO@U1")
    fs.step("GERACAO-PROCEDIMENTO@U1")
    assert not fs.allows("GERACAO-PROCEDIMENTO@U2")
    assert fs.allows("CONCLUSAO-PROCESSO-UNIDADE@U1")
    assert not fs.allows("CONCLUSAO-PROCESSO-UNIDADE@U9")
