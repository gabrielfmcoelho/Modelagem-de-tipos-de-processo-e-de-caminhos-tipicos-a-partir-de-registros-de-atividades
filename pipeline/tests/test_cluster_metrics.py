
from __future__ import annotations

import json

import numpy as np
import pytest

from ..evidence.artifact import write_artifact
from ..model.cluster_metrics import evaluate_clustering, extrinsic_metrics, internal_metrics, size_stats


def test_perfect_partition_gives_perfect_extrinsic_scores():
    labels = np.array([0, 0, 1, 1, 2, 2])
    reference = ["a", "a", "b", "b", "c", "c"]
    out = extrinsic_metrics(labels, reference)
    assert out["purity"] == 1.0
    assert out["nmi"] == 1.0
    assert out["ari"] == 1.0
    assert out["n_evaluated"] == 6
    assert out["n_reference_missing"] == 0


def test_extrinsic_excludes_missing_reference_rows():
    labels = np.array([0, 0, 1, 1])
    reference = ["a", None, "b", ""]
    out = extrinsic_metrics(labels, reference)
    assert out["n_reference_missing"] == 2
    assert out["n_evaluated"] == 2


def test_extrinsic_all_missing_is_none_safe():
    out = extrinsic_metrics(np.array([0, 1]), [None, None])
    assert out["purity"] is None and out["nmi"] is None and out["ari"] is None
    assert out["n_reference_missing"] == 2


def test_internal_metrics_all_noise_is_none_safe():
    feat = np.random.default_rng(0).normal(size=(10, 3))
    out = internal_metrics(feat, np.full(10, -1))
    assert out["dbcv"] is None
    assert out["silhouette"] is None
    assert out["davies_bouldin"] is None
    assert out["calinski_harabasz"] is None
    assert out["noise_ratio"] == 1.0
    assert out["n_clusters"] == 0


def test_internal_metrics_computes_on_non_noise_rows():
    rng = np.random.default_rng(0)
    a = rng.normal([0, 0], 0.05, (20, 2))
    b = rng.normal([5, 5], 0.05, (20, 2))
    feat = np.vstack([a, b])
    labels = np.array([0] * 20 + [1] * 15 + [-1] * 5)
    out = internal_metrics(feat, labels)
    assert out["n_clusters"] == 2
    assert out["noise_ratio"] == pytest.approx(5 / 40)
    assert out["silhouette"] is not None
    assert out["davies_bouldin"] is not None
    assert out["calinski_harabasz"] is not None


def test_size_stats_on_known_label_vector():
    labels = np.array([0, 0, 0, 1, 2, 2, -1, -1])
    out = size_stats(labels)
    assert out["min"] == 1
    assert out["max"] == 3
    assert out["mean"] == 2.0
    assert out["p50"] == 2.0
    assert out["n_singletons"] == 1


def test_size_stats_empty_when_all_noise():
    out = size_stats(np.array([-1, -1]))
    assert out["min"] is None
    assert out["n_singletons"] == 0


def test_write_artifact_refuses_overwrite_without_force(tmp_path):
    path = tmp_path / "sub" / "metrics.json"
    write_artifact({"a": 1}, path, stage="cluster-eval", force=False)
    assert json.loads(path.read_text())["a"] == 1
    with pytest.raises(FileExistsError):
        write_artifact({"a": 2}, path, stage="cluster-eval", force=False)
    write_artifact({"a": 3}, path, stage="cluster-eval", force=True)
    assert json.loads(path.read_text())["a"] == 3


def test_evaluate_clustering_meta_is_complete():
    feat = np.random.default_rng(0).normal(size=(20, 4))
    labels = np.array([0] * 10 + [1] * 10)
    out = evaluate_clustering(feat, labels, algo="kmeans", params={"k": 2}, reference=["x"] * 20)
    meta = out["meta"]
    assert meta["algo"] == "kmeans"
    assert meta["params"] == {"k": 2}
    assert meta["space"] == "umap50-cosine"
    assert meta["n"] == 20
    assert meta["seed"] == 42
    assert "numpy" in meta["versions"] and "sklearn" in meta["versions"]
    assert "UMAP-reduced space" in meta["caveat"]
    assert meta["generated_at"]
    assert out["size_stats"]["max"] == 10
    assert out["extrinsic"]["n_evaluated"] == 20


def test_evaluate_clustering_without_reference_has_null_extrinsic():
    feat = np.random.default_rng(0).normal(size=(10, 3))
    out = evaluate_clustering(feat, np.zeros(10, dtype=int), algo="hdbscan", params={})
    assert out["extrinsic"] is None
