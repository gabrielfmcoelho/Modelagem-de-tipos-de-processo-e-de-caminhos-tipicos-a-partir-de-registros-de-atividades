from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from ..model.predict import MarkovModel
from ..model.typical_eval import DfgModel, ModelSpec, cluster_traces, evaluate_cluster, evaluate_matrix, load_labels

TRACE = ["GERACAO-PROCEDIMENTO@U1", "ASSINATURA-DOCUMENTO@U1", "CONCLUSAO-PROCESSO-UNIDADE@U1"]


def _tw(n: int = 10):
    return [(f"2025-01-{i + 1:02d}", list(TRACE)) for i in range(n)]


def _markov_specs():
    return [ModelSpec("markov", lambda: MarkovModel(3))]


def test_markov_is_perfect_on_deterministic_traces():
    res = evaluate_cluster(_tw(), _markov_specs())
    m = res["models"]["markov"]
    assert m["top1"] == 1.0
    assert m["top3"] == 1.0
    assert m["suffix_dl"] == 0.0
    assert m["flow_validity_step"] == 1.0
    assert res["edge_coverage"] == 1.0
    assert res["n_train"] == 7 and res["n_test"] == 3


def test_evaluate_cluster_needs_both_splits():
    assert evaluate_cluster(_tw(1), _markov_specs()) is None


ITIN_TRACE = ["U1", "U2", "U3"]


def _itin_tw(n: int = 10):
    return [(f"2025-01-{i + 1:02d}", list(ITIN_TRACE)) for i in range(n)]


def test_itinerary_cells_omit_the_flow_constraint_instead_of_scoring_it_vacuously():
    res = evaluate_cluster(_itin_tw(), _markov_specs(), alphabet="itinerary")
    m = res["models"]["markov"]
    assert "flow_validity_step" not in m
    assert "flow_validity_trace" not in m
    assert "suffix_dl_c" not in m
    assert "flow_validity_step_real" not in res["baseline"]
    agg = evaluate_matrix({"c": res})["models"]["markov"]["macro"]
    assert "flow_validity_step" not in agg
    assert "typical_path_distance_proc" not in agg
    assert agg["top1"] is not None


def test_a_cell_only_projects_onto_an_alphabet_its_states_can_reach():
    unit = evaluate_cluster(_tw(), _markov_specs(), alphabet="unit")["models"]["markov"]
    assert unit["typical_path_distance_proc"] is not None
    assert unit["typical_path_distance_itin"] is not None
    itin = evaluate_cluster(_itin_tw(), _markov_specs(), alphabet="itinerary")["models"]["markov"]
    assert "typical_path_distance_proc" not in itin
    assert "typical_path_distance_itin" not in itin
    assert itin["typical_path_distance"] is not None


def test_procedure_cells_report_no_unit_metrics():
    proc = [(f"2025-01-{i + 1:02d}", ["GERACAO-PROCEDIMENTO", "ASSINATURA-DOCUMENTO",
                                      "CONCLUSAO-PROCESSO-UNIDADE"]) for i in range(10)]
    res = evaluate_cluster(proc, _markov_specs(), alphabet="procedure")
    gen = res["models"]["markov"]["generalization"]
    assert "unit_recall" not in gen and "n_units_path" not in gen
    assert res["models"]["markov"]["flow_validity_step"] is not None


def test_evaluate_cluster_records_skipped_models():
    class _Unavailable:
        available = False
        reason = "no torch"

        def fit(self, traces):
            return self

    res = evaluate_cluster(_tw(), [ModelSpec("neural", _Unavailable)])
    assert res["models"]["neural"] == {"skipped": "no torch"}


def test_dfg_model_ducktypes_markov():
    traces = [["A", "B", "C"], ["A", "B", "D"], ["A", "B", "C"]]
    m = DfgModel().fit(traces)
    assert m.edges == {("A", "B"), ("B", "C"), ("B", "D")}
    assert m.predict_next(["Z", "A"]) == ["B"]
    assert m.predict_next(["B"], topk=2) == ["C", "D"]
    dist = dict(m.next_distribution(["B"]))
    assert abs(dist["C"] - 2 / 3) < 1e-9
    gen = m.generate("A", is_conclusion=lambda s: s in ("C", "D"))
    assert gen == ["A", "B", "C"]


def test_dfg_model_coverage_floor_drops_rare_edges():
    traces = [["A", "B"]] * 9 + [["A", "C"]]
    m = DfgModel(coverage_floor=0.2).fit(traces)
    assert ("A", "C") not in m.edges
    assert m.predict_next(["A"]) == ["B"]


def test_evaluate_matrix_weighted_vs_macro():
    row1 = {"top1": 1.0, "top3": 1.0, "suffix_dl": 0.0, "flow_validity_step": 1.0}
    row2 = {"top1": 0.5, "top3": 0.5, "suffix_dl": 0.4, "flow_validity_step": 0.5}
    results = {
        "c1": {"n_traces": 10, "edge_coverage": 1.0, "models": {"markov": row1}},
        "c2": {"n_traces": 30, "edge_coverage": 0.5, "models": {"markov": row2, "gru": {"skipped": "x"}}},
    }
    agg = evaluate_matrix(results)
    assert agg["n_clusters"] == 2 and agg["n_traces"] == 40
    assert agg["models"]["markov"]["macro"]["top1"] == 0.75
    assert agg["models"]["markov"]["weighted"]["top1"] == 0.625
    assert agg["models"]["markov"]["weighted"]["suffix_dl"] == 0.3
    assert agg["edge_coverage"] == {"macro": 0.75, "weighted": 0.625}
    assert "gru" not in agg["models"]


def test_load_labels_and_cluster_traces_handle_both_formats(tmp_path):
    labels_file = tmp_path / "labels.json"
    labels_file.write_text(json.dumps({
        "meta": {},
        "labels": {
            "p1": {"macro": "exp-raw|macro|94", "micro": None},
            "p2": {"macro": None, "micro": "exp-raw|reclassificada|-1|137"},
            "p3": 7,
            "p4": -1,
        },
    }), encoding="utf-8")
    labels = load_labels(labels_file)
    assert labels == {"p1": "exp-raw|macro|94", "p2": None, "p3": "7", "p4": None}
    traces = {f"p{i}": ("t", ["A", "B"]) for i in range(1, 6)}
    groups = cluster_traces(labels, traces, min_traces=1)
    assert set(groups) == {"exp-raw|macro|94", "7"}
    assert cluster_traces(labels, traces, min_traces=2) == {}


def _load_gen13():
    path = Path(__file__).resolve().parents[2] / "reports" / "gen_13_matrix.py"
    spec = importlib.util.spec_from_file_location("gen_13_matrix", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_gen_13_renders_from_artifact_fixtures_alone(tmp_path):
    gen13 = _load_gen13()
    metrics = tmp_path / "typical" / "exp-raw" / "hdbscan" / "unit" / "metrics.json"
    metrics.parent.mkdir(parents=True)
    metrics.write_text(json.dumps({
        "meta": {"skipped_models": {"gru": "cuda unavailable"}},
        "aggregate": {
            "n_clusters": 2,
            "n_traces": 40,
            "edge_coverage": {"macro": 0.75, "weighted": 0.625},
            "models": {"markov": {
                "macro": {"top1": 0.75, "top3": 0.9, "suffix_dl": 0.2, "flow_validity_step": 1.0},
                "weighted": {"top1": 0.625, "top3": 0.8, "suffix_dl": 0.3, "flow_validity_step": 0.9},
                "n_clusters": 2,
            }},
        },
    }), encoding="utf-8")
    payload = gen13.load_matrix(tmp_path)
    assert [r["found"] for r in payload["rows"]] == [True] + [False] * (len(gen13.COMBOS) - 1)
    md = gen13.render_md(payload)
    assert "raw · hdbscan" in md
    assert "0.750" in md and "pending" in md
    assert "gru (cuda unavailable)" in md


def test_default_specs_skips_neural_without_cuda(monkeypatch):
    import pipeline.model.typical_eval as te

    monkeypatch.setattr(te, "_cuda_available", lambda: False)
    specs, skipped = te.default_specs()
    assert [s.name for s in specs] == ["markov", "dfg", "gnn"]
    assert skipped == {"gru": "cuda unavailable", "lstm": "cuda unavailable", "transformer": "cuda unavailable"}


def test_default_specs_allow_cpu_and_unknown_model(monkeypatch):
    import pipeline.model.typical_eval as te

    monkeypatch.setattr(te, "_cuda_available", lambda: False)
    specs, skipped = te.default_specs(["markov", "transformer"], allow_cpu=True)
    assert [s.name for s in specs] == ["markov", "transformer"]
    assert skipped == {}
    with pytest.raises(ValueError):
        te.default_specs(["markov", "bogus"])


def test_per_trace_records_align_with_test_protocolos_and_reproduce_top1():
    traces, labels = {}, {}
    for i in range(40):
        pf = f"00002.{i:06d}/2025-{i:02d}"
        traces[pf] = (f"2025-{1 + i % 12:02d}-01", list(TRACE))
        labels[pf] = "c1"
    groups = cluster_traces(labels, traces, min_traces=30)
    tw = groups["c1"]
    assert len(tw[0]) == 3

    res = evaluate_cluster(tw, _markov_specs(), seed=0)
    records = res["models"]["markov"]["per_trace"]
    protos = res["test_protocolos"]
    assert len(records) == res["n_test"] == len(protos)
    assert len(set(protos)) == len(protos)
    assert all(r[0] <= r[1] <= r[2] for r in records)

    total_hits = sum(r[0] for r in records)
    total_steps = sum(r[2] for r in records)
    assert abs(total_hits / total_steps - res["models"]["markov"]["top1"]) < 1e-4


def test_evaluate_cluster_still_accepts_two_tuples_without_protocolos():
    res = evaluate_cluster(_tw(40), _markov_specs(), seed=0)
    assert "test_protocolos" not in res
    assert "per_trace" in res["models"]["markov"]


def test_procedure_alphabet_strips_lane_and_collapses_repeats():
    from ..model.typical_eval import procedure_alphabet
    seq = ["GERACAO-DOCUMENTO@A/B", "GERACAO-DOCUMENTO@A/B", "ASSINATURA@A/B",
           "GERACAO-DOCUMENTO@C/D", "<END>"]
    assert procedure_alphabet(seq) == ["GERACAO-DOCUMENTO", "ASSINATURA", "GERACAO-DOCUMENTO"]


def test_identical_path_has_zero_distance_and_differing_path_is_positive():
    from ..model.typical_eval import mean_path_distance
    seqs = [["a", "b", "c"], ["a", "b", "c"]]
    assert mean_path_distance(["a", "b", "c"], seqs) == 0.0
    assert mean_path_distance(["x", "y", "z"], seqs) > 0.0


def test_normalized_medoid_beats_every_other_observed_trace():
    import random

    from ..model.typical_eval import mean_path_distance, medoid_by_normalized_dl

    rng = random.Random(7)
    for trial in range(20):
        seqs = [[rng.choice("abcd") for _ in range(rng.randint(3, 8))]
                for _ in range(rng.randint(4, 8))]
        med = medoid_by_normalized_dl(seqs)
        best = mean_path_distance(med, [s for s in seqs if s is not med])
        for cand in seqs:
            others = [s for s in seqs if s is not cand]
            assert mean_path_distance(cand, others) >= best - 1e-9, f"trial {trial}"


def test_raw_medoid_is_not_optimal_under_the_normalized_metric():
    import random

    from ..model.constrained import medoid_trace
    from ..model.typical_eval import mean_path_distance, medoid_by_normalized_dl

    rng = random.Random(7)
    disagreements = 0
    for _ in range(40):
        seqs = [[rng.choice("abcd") for _ in range(rng.randint(3, 8))] for _ in range(6)]
        raw = mean_path_distance(medoid_trace(seqs), seqs)
        norm = mean_path_distance(medoid_by_normalized_dl(seqs), seqs)
        if raw > norm + 1e-9:
            disagreements += 1
    assert disagreements > 0, (
        "raw-DL medoid and normalized-DL medoid never disagreed; "
        "if this holds the two references can be unified"
    )


def test_dispersion_is_zero_for_identical_traces_and_positive_otherwise():
    from ..model.typical_eval import trace_dispersion
    assert trace_dispersion([["a", "b"], ["a", "b"], ["a", "b"]]) == 0.0
    assert trace_dispersion([["a", "b"], ["c", "d"]]) > 0.0


def test_edge_usage_and_coverage_are_complementary_directions():
    from ..model.typical_eval import edge_coverage, edge_f1, edge_usage
    edges = {("a", "b"), ("b", "c"), ("c", "d")}
    traces = [["a", "b", "x"]]
    cov = edge_coverage(edges, traces)
    use = edge_usage(edges, traces)
    assert cov == round(1 / 2, 4)
    assert use == round(1 / 3, 4)
    assert 0 < edge_f1(cov, use) < 1


def test_edge_coverage_is_gameable_alone_but_f1_is_not():
    from ..model.typical_eval import edge_coverage, edge_f1, edge_usage
    traces = [["a", "b", "c"]]
    fat = {(x, y) for x in "abcdefgh" for y in "abcdefgh"}
    assert edge_coverage(fat, traces) == 1.0
    assert edge_usage(fat, traces) < 0.1
    assert edge_f1(edge_coverage(fat, traces), edge_usage(fat, traces)) < 0.2


def test_successor_baseline_predicts_the_most_frequent_next_state():
    from ..model.typical_eval import successor_baseline_accuracy
    train = [["a", "b"], ["a", "b"], ["a", "c"]]
    assert successor_baseline_accuracy(train, [["a", "b"]]) == 1.0
    assert successor_baseline_accuracy(train, [["a", "c"]]) == 0.0


def test_real_flow_validity_returns_step_and_trace_rates():
    from ..model.typical_eval import real_flow_validity
    step, trace = real_flow_validity([
        ["GERACAO-PROCEDIMENTO@U", "GERACAO-DOCUMENTO@U"],
        ["GERACAO-DOCUMENTO@Z", "GERACAO-DOCUMENTO@Z"],
    ])
    assert step is not None and trace is not None
    assert 0.0 <= step <= 1.0 and 0.0 <= trace <= 1.0


def test_itinerary_collapses_consecutive_visits_and_keeps_returns():
    from ..model.typical_eval import itinerary_alphabet, itinerary_visits
    seq = ["GERACAO@U1", "ASSINATURA@U1", "REMETIDO@U2", "RECEBIDO@U2",
           "ASSINATURA@U1", "CONCLUSAO@U1", "<END>"]
    assert itinerary_alphabet(seq) == ["U1", "U2", "U1"]
    assert itinerary_visits(seq) == [["U1", 2], ["U2", 2], ["U1", 2]]


def test_annotate_itinerary_reports_median_actions_per_visit():
    from ..model.typical_eval import annotate_itinerary
    path = ["GERACAO@U1", "REMETIDO@U2"]
    seqs = [
        ["a@U1", "b@U1", "c@U2"],
        ["a@U1", "b@U1", "c@U1", "d@U2", "e@U2"],
    ]
    ann = annotate_itinerary(path, seqs)
    assert [a["unidade"] for a in ann] == ["U1", "U2"]
    assert ann[0]["n_matching"] == 2
    assert ann[0]["median_actions"] in (2, 3)


def test_itinerary_distance_ignores_action_type_but_not_routing():
    from ..model.typical_eval import mean_path_distance
    same_route = [["GERACAO@U1", "REMETIDO@U2"]]
    assert mean_path_distance(["OUTRA-ACAO@U1", "QUALQUER@U2"], same_route, mode="itinerary") == 0.0
    assert mean_path_distance(["GERACAO@U1", "REMETIDO@U9"], same_route, mode="itinerary") > 0.0


def test_cluster_eval_refuses_ambient_features_for_an_arm_run():
    from pipeline.stages.cluster_eval import _arm_of
    assert _arm_of("exp-raw") == "exp-raw"
    assert _arm_of("exp-raw-kelbow") == "exp-raw"
    assert _arm_of("exp-anon-hcoarse") == "exp-anon"
    assert _arm_of("sweep-anon") is None
    assert _arm_of("exp-rawish") is None


def test_cluster_eval_guard_message_names_the_expected_npz():
    from pathlib import Path
    src = Path("pipeline/stages/cluster_eval.py").read_text(encoding="utf-8")
    assert "silently cluster the wrong arm" in src
    assert "artifacts/features/{arm}.npz" in src


def test_canonical_unidade_collapses_reorganised_paths():
    from ..model.dfg import canonical_unidade
    assert canonical_unidade("SEAD-PI/GAB/SGP") == canonical_unidade("SEAD-PI/SGP")
    assert canonical_unidade("SESAPI-PI/DUDOH/HGV") == canonical_unidade("SESAPI-PI/SUGMAC/DUDOH/HGV")
    assert canonical_unidade("SEAD-PI/GAB/SLC/CADUF") == "SEAD-PI/CADUF"
    from ..model.dfg import _lane
    assert _lane("SEAD-PI/DG/NTGD", 2) == "SEAD-PI/DG"


def test_canonical_unidade_keeps_distinct_orgaos_apart():
    from ..model.dfg import canonical_unidade
    assert canonical_unidade("SEAD-PI/GAB") != canonical_unidade("SESAPI-PI/GAB")
    assert canonical_unidade("SEAD-PI") == "SEAD-PI"
    assert canonical_unidade(None) == "?"
    assert canonical_unidade("") == "?"
