from __future__ import annotations

import json

import pytest

from ..evidence.compose import cell_key, coord_of_cell, parse_run_id
from ..evidence.compose.compare import (ablation_cells, compare_algorithms, compare_arms,
                                        compare_models, compare_populations)
from ..evidence.compose.envelope import (IncompleteAggregate, compose, members_block,
                                         population_block, write_composed)
from ..evidence.compose.levels import arm_path_summary, arm_summary, by_alphabet, by_model
from ..evidence.compose.metrics import model_rows, summarise_model
from ..model.typical_eval import ALPHABET_NAMES

MODELS = ("markov", "dfg", "gru")


def _cluster(cid: str, n: int, top1: dict, protos: list[str]) -> dict:
    return {
        "n_traces": n, "n_train": int(n * 0.7), "n_test": n - int(n * 0.7),
        "edge_coverage": 0.8, "edge_usage": 0.7, "edge_f1": 0.75,
        "baseline": {"top1_successor": 0.40, "top1_global_model": 0.50},
        "test_protocolos": protos,
        "path_reference": {"medoid_itinerary": ["U1", "U2"]},
        "models": {m: {"top1": v, "top3": v + 0.1, "suffix_dl": 3.0,
                       "flow_validity_step": 0.9, "flow_validity_trace": 0.8,
                       "typical_path_distance": 2.0} for m, v in top1.items()},
    }


def _cell(run_id: str, algo: str, alphabet: str, top1: dict, protos: list[str]) -> dict:
    clusters = {f"{run_id}|macro|{i}": _cluster(f"c{i}", 50 + i * 10, top1, protos)
                for i in range(2)}
    return {"run_id": run_id, "algo": algo, "alphabet": alphabet,
            "arm": "anon" if "anon" in run_id else "raw",
            "control": "shuffled" in run_id,
            "clusters": clusters, "aggregate": {}, "by_size": {},
            "path": f"artifacts/typical/{run_id}/{algo}/{alphabet}/metrics.json"}


@pytest.fixture
def cells():
    shared = ["p1", "p2", "p3"]
    out = []
    for run_id in ("exp-raw", "exp-anon"):
        for algo in ("hdbscan", "kmeans"):
            for alphabet in ALPHABET_NAMES:
                bump = 0.05 if run_id == "exp-raw" else 0.0
                out.append(_cell(run_id, algo, alphabet,
                                 {"markov": 0.60 + bump, "dfg": 0.55, "gru": 0.58}, shared))
    out.append(_cell("exp-raw-shuffled", "hdbscan", "unit",
                     {"markov": 0.30, "dfg": 0.28, "gru": 0.29}, shared))
    out.append(_cell("exp-raw-cut0.5", "hdbscan", "unit",
                     {"markov": 0.50, "dfg": 0.48, "gru": 0.49}, shared))
    return out


def test_run_id_decomposes_into_lattice_coordinates():
    assert parse_run_id("exp-raw").param == "base"
    assert parse_run_id("exp-anon-ksil").arm == "anon"
    assert parse_run_id("exp-raw-shuffled").control is True
    assert parse_run_id("exp-anon-cut0.5").ablation is True


def test_an_incomplete_aggregate_refuses_to_be_written():
    with pytest.raises(IncompleteAggregate):
        members_block(["a", "b", "c"], ["a", "b"])
    block = members_block(["a", "b", "c"], ["a", "b"], allow_missing=True)
    assert block["missing"] == ["c"]


def test_a_population_must_be_named_or_defined():
    with pytest.raises(ValueError):
        population_block("whatever-i-felt-like")
    assert population_block("non-control")["definition"]


def test_composed_artifact_without_the_envelope_is_refused(tmp_path):
    with pytest.raises(ValueError):
        write_composed({"results": {}}, tmp_path / "x.json", stage="compose-evidence")


def test_no_comparator_restricts_cells_to_a_common_test_set(cells):
    for _, payload in (compare_arms(cells, "unit"), compare_algorithms(cells, "unit"),
                       compare_models(cells, "unit"), compare_populations(cells, "unit")):
        assert payload["population"]["name"] != "shared-across-cells"
        flat = json.dumps(payload)
        assert "shared_population" not in flat and "shared-across-cells" not in flat


def test_every_arm_accuracy_carries_its_denominators(cells):
    _, payload = compare_arms(cells, "unit")
    cost = payload["results"]["anonymisation_cost_top1"]["markov"]
    for k in ("raw_n_clusters", "anon_n_clusters", "raw_n_traces", "anon_n_traces"):
        assert cost[k], f"{k} missing — an accuracy is unreadable without its population"
    for arm in ("raw", "anon"):
        assert payload["results"]["per_arm"][arm]["clusters"]["n_clusters"] > 0


def test_model_summary_reports_both_weightings_and_both_baselines(cells):
    rows = model_rows([c for c in cells if not coord_of_cell(c).control])
    s = summarise_model(rows["markov"])
    assert s["membership_weighted"]["top1"] is not None
    assert s["unweighted"]["top1"] is not None
    assert s["baselines"]["top1_global_model"] == 0.5
    assert s["gain_vs_global_model"] == round(s["membership_weighted"]["top1"] - 0.5, 4)


def test_every_composed_artifact_carries_scope_population_and_members(tmp_path, cells):
    produced = [arm_summary("raw", cells), arm_path_summary("raw", "unit", cells),
                by_model("markov", "unit", cells), by_alphabet("unit", cells),
                compare_arms(cells, "unit"), compare_algorithms(cells, "unit"),
                compare_models(cells, "unit"), compare_populations(cells, "unit")]
    assert produced
    for path, payload in produced:
        assert set(payload) == {"scope", "population", "members", "results"}, path
        assert "level" in payload["scope"], path
        assert payload["scope"].get("alphabet"), path
        assert payload["population"]["definition"], path
        assert payload["members"]["missing"] == [], path


def test_compare_arms_measures_the_anonymisation_cost_on_one_population(cells):
    _, payload = compare_arms(cells, "unit")
    assert payload["population"]["name"] == "main-cells"
    cost = payload["results"]["anonymisation_cost_top1"]["markov"]
    assert cost["anon_minus_raw"] == pytest.approx(-0.05, abs=1e-6)


def test_compare_populations_shows_the_control_beside_the_real_partition(cells):
    _, payload = compare_populations(cells, "unit")
    views = payload["results"]["views"]
    assert {"all-labelled", "shuffled-control"} == set(views)
    real = views["all-labelled"]["markov"]["top1_membership_weighted"]
    ctrl = views["shuffled-control"]["markov"]["top1_membership_weighted"]
    assert real > ctrl


def test_ablation_cells_are_scored_against_their_base_cell(cells):
    produced = ablation_cells(cells)
    assert len(produced) == 1
    path, payload = produced[0]
    assert "cut0.5" in str(path)
    assert payload["results"]["base_present"] is True
    assert payload["results"]["vs_base_top1"]["markov"]["delta"] == pytest.approx(-0.15, abs=1e-6)


def test_composed_artifacts_round_trip_to_disk(tmp_path, cells):
    _, payload = compare_models(cells, "unit")
    out = tmp_path / "compare_models.json"
    write_composed(payload, out, stage="compose-evidence")
    back = json.loads(out.read_text(encoding="utf-8"))
    assert back["_meta"]["stage"] == "compose-evidence"
    assert back["scope"]["level"] == "L0"
    assert back["results"]["per_model"]["markov"]["all_cells"]["n_clusters"] > 0


def test_cell_key_is_the_full_lattice_address(cells):
    assert cell_key(cells[0]) == "exp-raw/hdbscan/unit"


def test_an_aggregate_may_not_pool_two_alphabets(tmp_path):
    payload = compose(scope={"level": "L0", "aggregated_over": ["arm", "alphabet"]},
                      population=population_block("main-cells"),
                      members=members_block(["a"], ["a"]), results={})
    with pytest.raises(ValueError, match="alphabet"):
        write_composed(payload, tmp_path / "pooled.json", stage="compose-evidence")


def test_an_aggregate_must_name_the_alphabet_it_covers(tmp_path):
    payload = compose(scope={"level": "L0"}, population=population_block("main-cells"),
                      members=members_block(["a"], ["a"]), results={})
    with pytest.raises(ValueError, match="alphabet"):
        write_composed(payload, tmp_path / "unnamed.json", stage="compose-evidence")


def test_an_empty_shared_population_is_refused(tmp_path):
    payload = compose(scope={"level": "L0", "alphabet": "unit"},
                      population=population_block("shared-across-cells", n_cases=0),
                      members=members_block(["a"], ["a"]), results={})
    with pytest.raises(ValueError, match="zero cases"):
        write_composed(payload, tmp_path / "empty.json", stage="compose-evidence")


def test_the_shuffled_control_stays_out_of_the_arm_headline(cells):
    _, payload = arm_path_summary("raw", "unit", cells)
    assert not [k for k in payload["members"]["keys"] if "shuffled" in k]
    assert payload["results"]["by_model"]["markov"]["membership_weighted"]["top1"] > 0.6


def test_composed_members_reach_the_provenance_inputs(tmp_path, cells):
    _, payload = by_model("markov", "unit", cells)
    assert payload["members"]["files"]
    out = tmp_path / "by_model.json"
    write_composed(payload, out, stage="compose-evidence")
    meta = json.loads(out.read_text(encoding="utf-8"))["_meta"]
    assert [r["path"] for r in meta["inputs"]] == payload["members"]["files"]
