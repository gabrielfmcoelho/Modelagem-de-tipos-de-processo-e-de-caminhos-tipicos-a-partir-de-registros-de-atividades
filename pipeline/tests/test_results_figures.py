from __future__ import annotations

import json
from pathlib import Path

from pipeline.core.paths import ROOT

import pytest

ROOT = ROOT
from pipeline.evidence.results import results_figures as rf


def _stored(run_id: str, algo: str) -> dict:
    p = ROOT / "artifacts" / "clustering" / run_id / algo / "metrics.json"
    if not p.is_file():
        pytest.skip(f"{p} not present")
    return json.loads(p.read_text(encoding="utf-8")).get("extrinsic") or {}


@pytest.mark.parametrize("run_id,algo", [("exp-anon", "hdbscan"), ("exp-raw", "hdbscan")])
def test_taxonomy_agrees_with_the_pipelines_own_extrinsic_metrics(run_id, algo):
    tax = rf.taxonomy().get(f"{run_id}/{algo}")
    if not tax:
        pytest.skip("taxonomy cache absent")
    mine, theirs = tax["all"], _stored(run_id, algo)
    if not theirs.get("purity"):
        pytest.skip("no stored extrinsic metrics")
    assert mine["n"] == theirs["n_evaluated"]
    for key in ("purity", "nmi", "ari"):
        assert abs(mine[key] - theirs[key]) < 1e-3, (
            f"{key}: aggregator {mine[key]} vs pipeline {theirs[key]} — the report must not "
            "compute a different number from the one cluster-eval stored"
        )


def test_excluding_the_catch_all_uses_fewer_processos():
    tax = rf.taxonomy()
    if not tax:
        pytest.skip("taxonomy cache absent")
    for cell, v in tax.items():
        if v.get("all") and v.get("no_catch_all"):
            assert v["no_catch_all"]["n"] < v["all"]["n"], cell


def test_shuffled_partitions_are_excluded_from_taxonomy():
    assert not [k for k in rf.taxonomy() if "shuffled" in k]


def test_cluster_counts_exclude_noise_from_the_cluster_total():
    cc = rf.cluster_counts()
    if not cc:
        pytest.skip("no clusterings on disk")
    for cell, v in cc.items():
        labels = json.loads(
            (ROOT / "artifacts" / "clustering" / cell / "labels.json").read_text(encoding="utf-8"))["labels"]
        assert v["n_clusters"] == len(set(labels.values()) - {-1}), cell
        assert v["noise"] == sum(1 for x in labels.values() if x == -1), cell


def test_audit_prefers_a_run_specific_features_file(tmp_path):
    from pipeline.stages.cluster_audit import features_name
    from pipeline.stages.cluster_eval import _arm_of

    (tmp_path / "exp-anon-cut0.5.npz").write_bytes(b"")
    assert features_name("exp-anon-cut0.5", _arm_of("exp-anon-cut0.5"), tmp_path) \
        == "exp-anon-cut0.5", (
        "an ablation variant has its own features; refitting it against the base arm's "
        "features compares different inputs and reports a bogus MISMATCH"
    )
    assert features_name("exp-anon-kelbow", _arm_of("exp-anon-kelbow"), tmp_path) == "exp-anon", (
        "a parameter-only variant shares the arm's features and must still resolve to the arm"
    )
    assert features_name("exp-anon", _arm_of("exp-anon"), tmp_path) == "exp-anon"
