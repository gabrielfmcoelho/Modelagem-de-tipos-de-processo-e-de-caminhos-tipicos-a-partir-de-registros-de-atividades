from __future__ import annotations

import numpy as np
import pytest

from ..evidence.shared.glossary import (METRIC_GLOSSARY, NOT_A_PAPER_MEASURE, direction_of,
                                        emitted_keys, lower_is_better)
from ..model.predict import MarkovModel
from ..model.typical_eval import ALPHABET_NAMES, ModelSpec, evaluate_cluster, evaluate_matrix

_TRACES = {
    "unit": ["GERACAO-PROCEDIMENTO@U1", "ASSINATURA-DOCUMENTO@U2", "CONCLUSAO-PROCESSO-UNIDADE@U1"],
    "itinerary": ["U1", "U2", "U3"],
    "procedure": ["GERACAO-PROCEDIMENTO", "ASSINATURA-DOCUMENTO", "CONCLUSAO-PROCESSO-UNIDADE"],
}


def _cell(alphabet: str) -> dict:
    tws = [(f"2025-01-{i + 1:02d}", list(_TRACES[alphabet])) for i in range(10)]
    return evaluate_cluster(tws, [ModelSpec("markov", lambda: MarkovModel(3))],
                            alphabet=alphabet)


def _leaves(node, out: set) -> set:
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, (dict, list)):
                _leaves(v, out)
            else:
                out.add(k)
    elif isinstance(node, list):
        for v in node:
            _leaves(v, out)
    return out


def test_every_glossary_entry_is_well_formed():
    for row in METRIC_GLOSSARY:
        assert len(row) == 5, row
        name, family, arrow, emits, definition = row
        assert name and family and definition, name
        assert arrow in ("↑", "↓", "—"), name
        assert isinstance(emits, tuple) and emits, f"{name} names no emitted key"


def test_no_emitted_key_is_claimed_by_two_glossary_entries():
    seen: dict[str, str] = {}
    clashes = []
    for name, _fam, _arrow, emits, _d in METRIC_GLOSSARY:
        for k in emits:
            if k in seen:
                clashes.append(f"{k}: {seen[k]} and {name}")
            seen[k] = name
    assert not clashes, (
        "a metric key is defined by two glossary entries, so the appendix would give one "
        "number two meanings: " + "; ".join(clashes))


@pytest.mark.parametrize("alphabet", ALPHABET_NAMES)
def test_every_emitted_metric_is_documented_or_explicitly_excluded(alphabet):
    cell = _cell(alphabet)
    keys = _leaves(cell, set()) | _leaves(evaluate_matrix({"c": cell}), set())
    from ..model.cluster_metrics import internal_metrics, size_stats
    rng = np.random.default_rng(0)
    x = rng.normal(size=(40, 4))
    labels = np.array([0] * 20 + [1] * 20)
    keys |= _leaves(internal_metrics(x, labels), set()) | _leaves(size_stats(labels), set())

    undocumented = sorted(keys - emitted_keys() - NOT_A_PAPER_MEASURE)
    assert not undocumented, (
        f"the {alphabet} alphabet emits metrics that no glossary entry defines and that are not "
        "listed in NOT_A_PAPER_MEASURE. Adding a metric must be a decision, not a side effect — "
        "either give it a glossary row or say in one place that it supports no claim: "
        + ", ".join(undocumented))


def test_direction_is_declared_in_exactly_one_place():
    assert direction_of("transitions_unseen") == "↓"
    assert direction_of("top1") == "↑"
    assert direction_of("nothing_emits_this") is None
    assert "transitions_unseen" in lower_is_better()
    from ..evidence.typical_path.blocks import LOWER_IS_BETTER
    assert LOWER_IS_BETTER == lower_is_better()
