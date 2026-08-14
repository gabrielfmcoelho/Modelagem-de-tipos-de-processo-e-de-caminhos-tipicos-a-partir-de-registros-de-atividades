
from __future__ import annotations

import importlib.metadata as _md
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

_NOISE = -1

_CAVEAT = (
    "internal metrics computed on UMAP-reduced space; valid for relative "
    "comparison between methods on the same embedding, not as absolute "
    "cluster-quality claims"
)


def _n_clusters(labels: np.ndarray) -> int:
    return len({int(x) for x in labels if int(x) != _NOISE})


def compute_dbcv(features: np.ndarray, labels: np.ndarray) -> float | None:
    labels = np.asarray(labels)
    if _n_clusters(labels) < 2:
        return None
    feat64 = np.asarray(features).astype(np.float64, copy=False)
    lab = labels.astype(np.intp, copy=False)
    try:
        from hdbscan.validity import validity_index
        return float(validity_index(feat64, lab))
    except Exception:
        try:
            from hdbscan.validity import validity_index
            mask = lab != _NOISE
            if len({int(x) for x in lab[mask]}) < 2:
                return None
            return float(validity_index(feat64[mask], lab[mask]))
        except Exception:
            return None


def internal_metrics(features: np.ndarray, labels: np.ndarray, *, space: str = "umap50-cosine") -> dict:
    features = np.asarray(features).astype(np.float64, copy=False)
    labels = np.asarray(labels)
    n_samples = int(features.shape[0])
    mask = labels != _NOISE
    n_noise = int((~mask).sum())
    noise_ratio = float(n_noise / n_samples) if n_samples else 0.0

    silhouette = davies_bouldin = calinski_harabasz = None
    sub_lab = labels[mask]
    if int(mask.sum()) >= 2 and len({int(x) for x in sub_lab}) >= 2:
        from sklearn.metrics import (
            calinski_harabasz_score,
            davies_bouldin_score,
            silhouette_score,
        )
        sub = features[mask]
        silhouette = float(silhouette_score(sub, sub_lab, metric="cosine"))
        davies_bouldin = float(davies_bouldin_score(sub, sub_lab))
        calinski_harabasz = float(calinski_harabasz_score(sub, sub_lab))

    return {
        "dbcv": compute_dbcv(features, labels),
        "silhouette": silhouette,
        "davies_bouldin": davies_bouldin,
        "calinski_harabasz": calinski_harabasz,
        "noise_ratio": noise_ratio,
        "n_clusters": _n_clusters(labels),
        "n_samples": n_samples,
        "space": space,
    }


def size_stats(labels: np.ndarray) -> dict:
    labels = np.asarray(labels)
    sizes = [int((labels == c).sum()) for c in sorted({int(x) for x in labels if int(x) != _NOISE})]
    if not sizes:
        return {"min": None, "p50": None, "mean": None, "p90": None, "max": None, "n_singletons": 0}
    arr = np.asarray(sizes)
    return {
        "min": int(arr.min()),
        "p50": float(np.percentile(arr, 50)),
        "mean": float(arr.mean()),
        "p90": float(np.percentile(arr, 90)),
        "max": int(arr.max()),
        "n_singletons": int((arr == 1).sum()),
    }


def separation_stats(features: np.ndarray, labels: np.ndarray) -> dict:
    features = np.asarray(features).astype(np.float64, copy=False)
    labels = np.asarray(labels)
    labs = sorted({int(x) for x in labels if int(x) != _NOISE})
    if len(labs) < 2:
        return {"mean_ratio": None, "min_ratio": None, "n_touching": 0,
                "n_overlapping": 0, "n_clusters": len(labs)}
    cents = np.array([features[labels == c].mean(0) for c in labs])
    radii = np.array([
        np.linalg.norm(features[labels == c] - cents[i], axis=1).mean()
        for i, c in enumerate(labs)
    ])
    diff = cents[:, None, :] - cents[None, :, :]
    dist = np.linalg.norm(diff, axis=2)
    np.fill_diagonal(dist, np.inf)
    ratio = dist.min(axis=1) / (radii + 1e-9)
    return {
        "mean_ratio": float(ratio.mean()),
        "min_ratio": float(ratio.min()),
        "n_touching": int((ratio < 1.0).sum()),
        "n_overlapping": int((ratio < 0.7).sum()),
        "n_clusters": len(labs),
    }


def extrinsic_metrics(labels: np.ndarray, reference) -> dict:
    from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

    labels = list(labels)
    reference = list(reference)
    n_reference_missing = 0
    pairs: list[tuple[int, Any]] = []
    for c, r in zip(labels, reference):
        if r is None or (isinstance(r, str) and not r.strip()):
            n_reference_missing += 1
            continue
        if int(c) == _NOISE:
            continue
        pairs.append((int(c), r))

    if not pairs:
        return {
            "purity": None, "nmi": None, "ari": None,
            "n_evaluated": 0, "n_reference_missing": n_reference_missing,
        }

    clusters = [c for c, _ in pairs]
    tipos = [t for _, t in pairs]
    cu = {v: i for i, v in enumerate(set(clusters))}
    tu = {v: i for i, v in enumerate(set(tipos))}
    cl = [cu[c] for c in clusters]
    tl = [tu[t] for t in tipos]
    by_cl: dict[int, Counter] = defaultdict(Counter)
    for c, t in zip(clusters, tipos):
        by_cl[c][t] += 1
    purity = sum(cnt.most_common(1)[0][1] for cnt in by_cl.values()) / len(clusters)
    return {
        "purity": float(purity),
        "nmi": float(normalized_mutual_info_score(tl, cl)),
        "ari": float(adjusted_rand_score(tl, cl)),
        "n_evaluated": len(pairs),
        "n_reference_missing": n_reference_missing,
    }


def _versions() -> dict:
    keys = {
        "numpy": "numpy",
        "sklearn": "scikit-learn",
        "hdbscan": "hdbscan",
        "umap-learn": "umap-learn",
        "igraph": "igraph",
        "leidenalg": "leidenalg",
    }
    out: dict[str, str] = {}
    for label, dist in keys.items():
        try:
            out[label] = _md.version(dist)
        except Exception:
            continue
    return out



def assign_noise_to_nearest(features: np.ndarray, labels: np.ndarray) -> np.ndarray:
    labels = np.asarray(labels).copy()
    noise = labels == _NOISE
    if not noise.any():
        return labels
    real = sorted({int(x) for x in labels if int(x) != _NOISE})
    if not real:
        return labels
    x = np.asarray(features, dtype=np.float64)
    x = x / (np.linalg.norm(x, axis=1, keepdims=True) + 1e-12)
    cent = np.stack([x[labels == c].mean(axis=0) for c in real])
    cent = cent / (np.linalg.norm(cent, axis=1, keepdims=True) + 1e-12)
    labels[noise] = np.asarray(real)[(x[noise] @ cent.T).argmax(axis=1)]
    return labels


def full_population_metrics(features: np.ndarray, labels: np.ndarray, *,
                            space: str = "umap50-cosine") -> dict:
    labels = np.asarray(labels)
    n_noise = int((labels == _NOISE).sum())
    if not n_noise:
        out = internal_metrics(features, labels, space=space)
        out["n_reassigned"] = 0
        return out
    out = internal_metrics(features, assign_noise_to_nearest(features, labels), space=space)
    out["n_reassigned"] = n_noise
    return out


def evaluate_clustering(
    features: np.ndarray,
    labels: np.ndarray,
    *,
    algo: str,
    params: dict,
    reference=None,
    space: str = "umap50-cosine",
) -> dict:
    features = np.asarray(features).astype(np.float64, copy=False)
    labels = np.asarray(labels)
    out: dict[str, Any] = {}
    out.update(internal_metrics(features, labels, space=space))
    out["full_population"] = full_population_metrics(features, labels, space=space)
    out["size_stats"] = size_stats(labels)
    out["separation"] = separation_stats(features, labels)
    out["extrinsic"] = extrinsic_metrics(labels, reference) if reference is not None else None
    out["meta"] = {
        "algo": algo,
        "params": params,
        "space": space,
        "n": int(features.shape[0]),
        "seed": 42,
        "versions": _versions(),
        "caveat": _CAVEAT,
        "generated_at": datetime.now(UTC).isoformat(),
    }
    return out
