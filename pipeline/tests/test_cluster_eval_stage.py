
from __future__ import annotations

import json

import numpy as np
import pytest

from ..core._stage_base import RunContext
from ..core.config import Settings
from pipeline.stages import cluster_eval


class FakeSession:
    def __init__(self, rows):
        self._rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def run(self, cypher, **params):
        return list(self._rows)


class FakeDriver:
    def __init__(self, rows):
        self._rows = rows

    def session(self):
        return FakeSession(self._rows)


class FakeRecord(dict):
    def get(self, key, default=None):
        return dict.get(self, key, default)


def _fixture(tmp_path, monkeypatch, n=30):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cluster_eval, "_ARTIFACT_ROOT",
                        tmp_path / "artifacts" / "clustering")
    monkeypatch.setattr(cluster_eval, "TIPO_CACHE",
                        tmp_path / "artifacts" / "cache" / "tipo_procedimento.json")
    rng = np.random.default_rng(0)
    a = rng.normal([0, 0, 0], 0.05, (n // 2, 3))
    b = rng.normal([5, 5, 5], 0.05, (n - n // 2, 3))
    features = np.vstack([a, b]).astype(np.float32)
    protocolos = np.array([f"P{i}" for i in range(n)])
    npz = tmp_path / "features.npz"
    np.savez(npz, protocolos=protocolos, features=features)

    labels_file = tmp_path / "labels.json"
    frozen = {
        "meta": {"run_id": "t"},
        "labels": {
            f"P{i}": {"macro": f"t|macro|{0 if i < n // 2 else 1}", "micro": None}
            for i in range(n - 2)
        },
    }
    labels_file.write_text(json.dumps(frozen), encoding="utf-8")

    ref_rows = [FakeRecord(protocolo=f"P{i}", tipo_procedimento="tipo-a" if i < n // 2 else "tipo-b")
                for i in range(n)]
    return npz, labels_file, FakeDriver(ref_rows)


def _ctx(tmp_path, driver, **flags):
    return RunContext(
        settings=Settings(),
        mode="neo4j",
        flags=flags,
        state_dir=tmp_path,
        driver=driver,
    )


def test_stage_requires_run_id(tmp_path):
    with pytest.raises(ValueError, match="run_id"):
        cluster_eval.run(_ctx(tmp_path, None))


def test_frozen_labels_mode_writes_only_metrics(tmp_path, monkeypatch):
    npz, labels_file, driver = _fixture(tmp_path, monkeypatch)
    ctx = _ctx(tmp_path, driver, run_id="t", algos="hdbscan",
               features_file=str(npz), labels_file=str(labels_file))
    cluster_eval.run(ctx)

    out_dir = tmp_path / "artifacts" / "clustering" / "t" / "hdbscan"
    assert (out_dir / "metrics.json").exists()
    assert not (out_dir / "labels.json").exists()

    metrics = json.loads((out_dir / "metrics.json").read_text())
    assert metrics["n_clusters"] == 2
    assert metrics["meta"]["algo"] == "hdbscan"
    assert metrics["meta"]["params"]["source"] == "labels_file"
    assert metrics["dbcv"] is not None
    assert metrics["extrinsic"]["purity"] == 1.0
    assert metrics["noise_ratio"] == pytest.approx(2 / 30)
    summary = ctx.cache["cluster_eval_summary"]
    assert summary["run_id"] == "t"
    assert "hdbscan" in summary["algos"]


def test_fit_mode_writes_labels_and_metrics_with_schema(tmp_path, monkeypatch):
    npz, _, driver = _fixture(tmp_path, monkeypatch)
    ctx = _ctx(tmp_path, driver, run_id="t2", algos="kmeans", k="2", features_file=str(npz))
    cluster_eval.run(ctx)

    out_dir = tmp_path / "artifacts" / "clustering" / "t2" / "kmeans"
    labels = json.loads((out_dir / "labels.json").read_text())
    assert set(labels.keys()) == {"_meta", "meta", "labels"}
    assert labels["meta"]["run_id"] == "t2"
    assert len(labels["labels"]) == 30
    assert all(isinstance(v, int) for v in labels["labels"].values())
    metrics = json.loads((out_dir / "metrics.json").read_text())
    assert metrics["meta"]["params"]["k"] == 2


def test_respects_no_overwrite(tmp_path, monkeypatch):
    npz, labels_file, driver = _fixture(tmp_path, monkeypatch)
    ctx = _ctx(tmp_path, driver, run_id="t", algos="hdbscan",
               features_file=str(npz), labels_file=str(labels_file))
    cluster_eval.run(ctx)
    with pytest.raises(FileExistsError):
        cluster_eval.run(ctx)
    ctx.flags["force"] = "true"
    cluster_eval.run(ctx)


def test_kmeans_without_k_and_without_hdbscan_errors(tmp_path, monkeypatch):
    npz, _, driver = _fixture(tmp_path, monkeypatch)
    ctx = _ctx(tmp_path, driver, run_id="t3", algos="kmeans", features_file=str(npz))
    with pytest.raises(ValueError, match="k"):
        cluster_eval.run(ctx)


def test_kmeans_k_defaults_to_hdbscan_cluster_count(tmp_path, monkeypatch):
    npz, _, driver = _fixture(tmp_path, monkeypatch)
    ctx = _ctx(tmp_path, driver, run_id="t4", algos="hdbscan,kmeans",
               features_file=str(npz), min_cluster_size="5")
    cluster_eval.run(ctx)
    metrics = json.loads(
        (tmp_path / "artifacts" / "clustering" / "t4" / "kmeans" / "metrics.json").read_text())
    hdb = json.loads(
        (tmp_path / "artifacts" / "clustering" / "t4" / "hdbscan" / "metrics.json").read_text())
    assert metrics["meta"]["params"]["k"] == hdb["n_clusters"]
