from __future__ import annotations

import json

import numpy as np
import pytest

from pipeline.model.cluster_metrics import assign_noise_to_nearest
from pipeline.model.clustering import NOISE_LABEL, fit
from pipeline.stages.cluster_audit import audit_all

RUN_ID = "exp-raw"
ALGO = "hdbscan"
MIN_CLUSTER_SIZE = 5


def _features() -> np.ndarray:
    rng = np.random.default_rng(0)
    blobs = [rng.normal(c, 0.05, size=(12, 4)) for c in (0.0, 5.0, 10.0)]
    strays = np.array([[50.0, 50.0, 50.0, 50.0], [-40.0, -40.0, -40.0, -40.0]])
    return np.vstack([*blobs, strays])


def _write_cell(tmp_path, labels, params):
    protos = [f"P{i:04d}" for i in range(len(labels))]
    features_dir = tmp_path / "features"
    features_dir.mkdir(parents=True, exist_ok=True)
    np.savez(features_dir / f"{RUN_ID}.npz", protocolos=np.array(protos),
             features=_features(), digest=np.str_("d0"), text_variant=np.str_("raw"))
    cell = tmp_path / "clustering" / RUN_ID / ALGO
    cell.mkdir(parents=True, exist_ok=True)
    (cell / "labels.json").write_text(json.dumps(
        {"labels": {pf: int(lab) for pf, lab in zip(protos, labels)}}), encoding="utf-8")
    (cell / "metrics.json").write_text(json.dumps(
        {"meta": {"algo": ALGO, "params": params}}), encoding="utf-8")
    return tmp_path / "clustering", features_dir


def _statuses(tmp_path, labels, params):
    clustering_dir, features_dir = _write_cell(tmp_path, labels, params)
    report = audit_all(clustering_dir=clustering_dir, features_dir=features_dir)
    return [r["status"] for r in report["rows"]]


@pytest.fixture
def base_labels():
    labels = fit(_features(), ALGO, min_cluster_size=MIN_CLUSTER_SIZE).labels
    assert (np.asarray(labels) == NOISE_LABEL).any()
    return np.asarray(labels)


def test_stored_labels_with_noise_assigned_reproduce(tmp_path, base_labels):
    assigned = assign_noise_to_nearest(_features(), base_labels)
    assert not (assigned == NOISE_LABEL).any()
    params = {"min_cluster_size": MIN_CLUSTER_SIZE, "assign_noise": True,
              "n_reassigned": int((base_labels == NOISE_LABEL).sum())}
    assert _statuses(tmp_path, assigned, params) == ["OK"]


def test_declaring_assignment_without_applying_it_is_caught(tmp_path, base_labels):
    params = {"min_cluster_size": MIN_CLUSTER_SIZE, "assign_noise": True}
    assert _statuses(tmp_path, base_labels, params) == ["MISMATCH"]


def test_unassigned_cell_still_reproduces(tmp_path, base_labels):
    params = {"min_cluster_size": MIN_CLUSTER_SIZE, "assign_noise": False}
    assert _statuses(tmp_path, base_labels, params) == ["OK"]


def test_post_fit_params_are_not_passed_to_fit(tmp_path, base_labels):
    assigned = assign_noise_to_nearest(_features(), base_labels)
    params = {"min_cluster_size": MIN_CLUSTER_SIZE, "assign_noise": True,
              "macro_dedup_threshold": 0.0, "noise_ratio_before_assignment": 0.1,
              "n_reassigned": 2}
    assert _statuses(tmp_path, assigned, params) == ["OK"]
