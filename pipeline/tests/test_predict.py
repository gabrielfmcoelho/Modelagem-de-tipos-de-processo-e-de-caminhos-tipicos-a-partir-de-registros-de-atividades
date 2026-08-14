
from __future__ import annotations

import random

from ..model.predict import MarkovModel, dl_distance, flow_paths, next_step_accuracy, suffix_distance, suffix_prefix_distance, temporal_split, trace_states


def test_flow_paths_fullest_picks_the_most_lane_path():
    from ..model.predict import flow_paths as fp
    acts = [{"source_id": "g", "tipo_acao": "GERACAO-PROCEDIMENTO", "unidade": "U1"},
            {"source_id": "c1", "tipo_acao": "CONCLUSAO-PROCESSO-UNIDADE", "unidade": "U1"},
            {"source_id": "r", "tipo_acao": "PROCESSO-REMETIDO-UNIDADE", "unidade": "U2"},
            {"source_id": "c2", "tipo_acao": "CONCLUSAO-PROCESSO-UNIDADE", "unidade": "U2"}]
    edges = [{"from_id": "g", "to_id": "c1"}, {"from_id": "g", "to_id": "r"}, {"from_id": "r", "to_id": "c2"}]
    paths = fp(acts, edges, pick="fullest", rng=random.Random(0))
    assert len(paths) == 1
    lanes = {s.split("@")[1] for s in paths[0]}
    assert lanes == {"U1", "U2"}


def test_flow_paths_fullest_prefers_manual_conclusion_ending():
    from ..model.predict import flow_paths as fp
    acts = [{"source_id": "g", "tipo_acao": "GERACAO-PROCEDIMENTO", "unidade": "U1"},
            {"source_id": "cm", "tipo_acao": "CONCLUSAO-PROCESSO-UNIDADE", "unidade": "U1"},
            {"source_id": "a", "tipo_acao": "ASSINATURA-DOCUMENTO", "unidade": "U1"},
            {"source_id": "b", "tipo_acao": "ASSINATURA-DOCUMENTO", "unidade": "U1"},
            {"source_id": "ca", "tipo_acao": "CONCLUSAO-AUTOMATICA-UNIDADE", "unidade": "U1"}]
    edges = [{"from_id": "g", "to_id": "cm"}, {"from_id": "g", "to_id": "a"},
             {"from_id": "a", "to_id": "b"}, {"from_id": "b", "to_id": "ca"}]
    p = fp(acts, edges, pick="fullest", rng=random.Random(0))[0]
    assert p[-1].split("@")[0] == "CONCLUSAO-PROCESSO-UNIDADE"


def test_train_val_test_split_is_disjoint_and_time_ordered():
    from ..model.predict import train_val_test_split
    data = [(str(i), [f"s{i}"]) for i in range(10)]
    tr, va, te = train_val_test_split(data, train_frac=0.6, val_frac=0.2)
    assert [len(tr), len(va), len(te)] == [6, 2, 2]
    assert tr[0] == ["s0"] and te[-1] == ["s9"]


def test_flow_paths_rich_augments_remetido_with_source_lane():
    from ..model.predict import strip_rich
    acts = [{"source_id": "g", "tipo_acao": "GERACAO-PROCEDIMENTO", "unidade": "SEAD-PI/U1"},
            {"source_id": "r", "tipo_acao": "PROCESSO-REMETIDO-UNIDADE", "unidade": "SEAD-PI/U2",
             "source_unidade": "SEAD-PI/U1"},
            {"source_id": "c", "tipo_acao": "CONCLUSAO-PROCESSO-UNIDADE", "unidade": "SEAD-PI/U2"}]
    edges = [{"from_id": "g", "to_id": "r"}, {"from_id": "r", "to_id": "c"}]
    path = flow_paths(acts, edges, n_walks=1, rng=random.Random(0), rich=True)[0]
    rem = next(s for s in path if s.startswith("PROCESSO-REMETIDO-UNIDADE@"))
    assert rem == "PROCESSO-REMETIDO-UNIDADE@SEAD-PI/U2>SEAD-PI/U1"
    assert strip_rich(rem) == "PROCESSO-REMETIDO-UNIDADE@SEAD-PI/U2"


def test_flow_paths_walks_root_to_conclusion_leaf():
    acts = [{"source_id": "g", "tipo_acao": "GERACAO-PROCEDIMENTO", "unidade": "U1"},
            {"source_id": "r", "tipo_acao": "PROCESSO-REMETIDO-UNIDADE", "unidade": "U2"},
            {"source_id": "c", "tipo_acao": "CONCLUSAO-PROCESSO-UNIDADE", "unidade": "U2"}]
    edges = [{"from_id": "g", "to_id": "r"}, {"from_id": "r", "to_id": "c"}]
    paths = flow_paths(acts, edges, n_walks=2, rng=random.Random(1))
    assert len(paths) == 2
    for p in paths:
        assert p[0] == "GERACAO-PROCEDIMENTO@U1"
        assert p[-1] == "CONCLUSAO-PROCESSO-UNIDADE@U2"


def test_dl_distance():
    assert dl_distance(["a", "b", "c"], ["a", "b", "c"]) == 0
    assert dl_distance(["a", "b"], ["a", "x"]) == 1
    assert dl_distance(["a", "b"], ["a", "b", "c"]) == 1
    assert dl_distance(["a", "b"], ["b", "a"]) == 1
    assert dl_distance([], ["a", "b"]) == 2


def test_markov_from_counts_builds_first_order_from_edges():
    m = MarkovModel.from_counts([("A", "B", 3), ("A", "C", 1), ("B", "C", 5)])
    assert m.predict_next(["A"], topk=1) == ["B"]
    assert m.predict_next(["B"], topk=1) == ["C"]


def test_markov_order1_predict_ranks_by_frequency():
    m = MarkovModel(order=1).fit([["A", "B"], ["A", "B"], ["A", "C"]])
    assert m.predict_next(["A"], topk=1) == ["B"]
    assert set(m.predict_next(["A"])) == {"B", "C"}


def test_markov_backoff_to_lower_order():
    m = MarkovModel(order=2).fit([["A", "B", "C"], ["A", "B", "C"], ["X", "B", "D"]])
    assert set(m.predict_next(["Z", "B"])) == {"C", "D"}
    assert m.predict_next(["A", "B"], topk=1) == ["C"]


def test_markov_generate_reaches_conclusion():
    m = MarkovModel(order=1).fit([["G", "W", "C"], ["G", "W", "C"]])
    seq = m.generate("G", is_conclusion=lambda s: s == "C", max_steps=10)
    assert seq == ["G", "W", "C"]


def test_markov_generate_stops_at_max_steps_without_conclusion():
    m = MarkovModel(order=1).fit([["A", "A", "A", "A"]])
    seq = m.generate("A", is_conclusion=lambda s: s == "Z", max_steps=3)
    assert len(seq) <= 4


def test_next_step_accuracy_perfect_on_training():
    traces = [["G", "W", "C"], ["G", "W", "C"]]
    m = MarkovModel(order=1).fit(traces)
    acc = next_step_accuracy(m, traces, topk=(1, 3))
    assert acc[1] == 1.0 and acc[3] == 1.0


def test_suffix_distance_zero_when_model_reproduces():
    traces = [["G", "W", "C"], ["G", "W", "C"]]
    m = MarkovModel(order=1).fit(traces)
    d = suffix_distance(m, traces, is_conclusion=lambda s: s == "C")
    assert d == 0.0


def test_trace_states_orders_by_time_and_rolls_up_lane():
    acts = [
        {"source_id": "2", "data_hora": "2025-01-01T11:00:00",
         "tipo_acao": "ASSINATURA-DOCUMENTO", "unidade": "SEAD-PI/DG/NTGD", "source_unidade": None},
        {"source_id": "1", "data_hora": "2025-01-01T10:00:00",
         "tipo_acao": "GERACAO-PROCEDIMENTO", "unidade": "SEAD-PI/DG", "source_unidade": None},
    ]
    assert trace_states(acts, lane_depth=2) == [
        "GERACAO-PROCEDIMENTO@SEAD-PI/DG",
        "ASSINATURA-DOCUMENTO@SEAD-PI/DG",
    ]


def test_temporal_split_oldest_train_newest_test():
    tw = [("2025-03", ["a"]), ("2025-01", ["b"]), ("2025-02", ["c"]),
          ("2025-04", ["d"]), ("2025-05", ["e"])]
    train, test = temporal_split(tw, train_frac=0.6)
    assert train == [["b"], ["c"], ["a"]]
    assert test == [["d"], ["e"]]


def test_markov_sample_generation_is_reproducible():
    traces = [["G", "A", "A", "A", "C"], ["G", "A", "C"]]
    m = MarkovModel(order=1).fit(traces)
    s1 = m.generate("G", is_conclusion=lambda s: s == "C", strategy="sample",
                    rng=random.Random(7), max_steps=30)
    s2 = m.generate("G", is_conclusion=lambda s: s == "C", strategy="sample",
                    rng=random.Random(7), max_steps=30)
    assert s1 == s2 and s1[0] == "G"
    s3 = m.generate("G", is_conclusion=lambda s: s == "C", strategy="sample",
                    rng=random.Random(99), max_steps=30)
    assert isinstance(s3, list) and s3[0] == "G"


def test_suffix_prefix_distance_zero_when_model_reproduces():
    traces = [["G", "W", "X", "Y", "C"]] * 5
    m = MarkovModel(order=1).fit(traces)
    d = suffix_prefix_distance(m, traces, is_conclusion=lambda s: s == "C",
                               prefix_fracs=(0.4, 0.6))
    assert d == 0.0


def test_generation_with_end_sentinel_runs_past_mid_conclusions():
    from ..model.predict import END
    traces = [["G@U", "CONCLUSAO-PROCESSO-UNIDADE@U", "W@U", "X@U"]] * 5
    m = MarkovModel(order=1).fit([t + [END] for t in traces])
    seq = m.generate("G@U", is_conclusion=lambda s: s == END, max_steps=20)
    assert seq == ["G@U", "CONCLUSAO-PROCESSO-UNIDADE@U", "W@U", "X@U", END]


def test_lstm_predicts_and_generates_or_unavailable():
    from ..model.predict_lstm import LSTMModel
    traces = [["G@U", "W@U", "C@U"]] * 25
    m = LSTMModel(epochs=30).fit(traces)
    if not m.available:
        return
    nxt = m.predict_next(["G@U"])
    assert isinstance(nxt, list) and nxt
    seq = m.generate("G@U", is_conclusion=lambda s: s == "C@U", max_steps=10)
    assert seq[0] == "G@U"
