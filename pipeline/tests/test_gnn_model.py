from __future__ import annotations

import pytest

from ..model._sequence import END
from ..model.typical_path.dfg.dfg_model import DfgModel
from ..model.typical_path.gnn.gnn_model import GcnModel
from ..model.typical_path.markov.markov_model import MarkovModel

torch = pytest.importorskip("torch")

TRACES = [["A", "B", "C", END]] * 20 + [["A", "B", "D", END]] * 10 + [["A", "E", "C", END]] * 5


def _fit(**kw):
    return GcnModel(epochs=120, **kw).fit(TRACES)


def test_it_learns_the_observed_branching_ratio():
    m = _fit()
    dist = dict(m.next_distribution(["A", "B"]))
    assert dist["C"] > dist["D"] > 0
    assert dist["C"] + dist["D"] == pytest.approx(1.0, abs=0.05)


def test_it_generalises_across_the_graph_where_the_counting_models_cannot():
    gcn = _fit()
    markov = MarkovModel(1).fit(TRACES)
    after_e = dict(gcn.next_distribution(["A", "E"]))
    assert after_e.get("D", 0) > 0.05, (
        "the GCN should borrow from structurally similar neighbours; D never follows E in the "
        "training data but does follow B, which shares E's neighbourhood")
    assert "D" not in dict(markov.next_distribution(["A", "E"])), (
        "the order-1 counting model must not propose an unobserved successor — if it does, the "
        "contrast this model exists to demonstrate is gone")


def test_a_terminal_state_predicts_nothing():
    m = _fit()
    assert m._counts([END]) == {}
    assert m.generate("A", max_steps=8)[-1] == END


def test_generation_terminates_like_the_baselines():
    gcn = _fit()
    markov = MarkovModel(3).fit(TRACES)
    dfg = DfgModel().fit(TRACES)
    for other in (markov, dfg):
        assert gcn.generate("A", max_steps=8) == other.generate("A", max_steps=8)


def test_it_is_reproducible_under_a_fixed_seed():
    a = _fit(seed=7)
    b = _fit(seed=7)
    assert a.next_distribution(["A", "B"]) == b.next_distribution(["A", "B"])


def test_reproducibility_holds_on_a_graph_large_enough_to_expose_thread_nondeterminism():
    import random

    import numpy as np

    rng = random.Random(7)
    states = [f"ACT{i}@UN{i % 6}" for i in range(30)]
    traces = []
    for _ in range(300):
        traces.append([rng.choice(states) for _ in range(rng.randint(4, 12))] + [END])
    runs = [GcnModel(epochs=200).fit(traces)._probs for _ in range(2)]
    assert runs[0].shape[0] > 25, "the toy graph passed even before the fix; this one must not"
    assert np.array_equal(runs[0], runs[1]), (
        "two fits with the same seed diverged. Multi-threaded float32 GEMM reduces in a "
        "non-fixed order, so fit() pins torch to one thread; if that pin is removed this "
        "fails and the card's bit-reproducibility claim becomes false.")


def test_it_declines_instead_of_crashing_when_there_is_no_graph():
    m = GcnModel(epochs=5).fit([["A"]])
    assert m.available is False
    assert "two distinct states" in m.reason


def test_an_unseen_prefix_yields_no_prediction_rather_than_a_guess():
    m = _fit()
    assert m.predict_next(["NEVER-SEEN"]) == []


def test_the_coverage_floor_separates_dfg_from_order_one_markov():
    traces = [["A", "B", "C", END]] * 40 + [["A", "X", "C", END]]
    markov1 = MarkovModel(1).fit(traces)
    inert = DfgModel(coverage_floor=0.0).fit(traces)
    live = DfgModel(coverage_floor=0.05).fit(traces)
    assert inert.predict_next(["A"]) == markov1.predict_next(["A"]), (
        "with a zero floor the DFG is exactly the order-1 counting model, which is why the "
        "default was raised")
    assert live.predict_next(["A"]) == ["B"]
    assert len(live.edges) < len(inert.edges)
