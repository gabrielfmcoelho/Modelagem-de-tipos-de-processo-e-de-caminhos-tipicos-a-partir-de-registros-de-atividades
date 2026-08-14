from __future__ import annotations

import numpy as np

from ..._result import NOISE_LABEL, ClusterResult


def fit(features: np.ndarray, **params) -> ClusterResult:
    min_cluster_size = int(params.get("min_cluster_size", 20))
    epsilon = float(params.get("cluster_selection_epsilon", 0.0))
    method = str(params.get("cluster_selection_method", "eom"))
    min_samples = params.get("min_samples")
    min_samples = int(min_samples) if min_samples is not None else None
    resolved = {"min_cluster_size": min_cluster_size,
                "cluster_selection_epsilon": epsilon,
                "cluster_selection_method": method,
                "min_samples": min_samples}
    n = features.shape[0]
    if n < max(2, min_cluster_size):
        labels = np.full(n, NOISE_LABEL, dtype=int)
        strengths = np.zeros(n, dtype=float)
        return ClusterResult("hdbscan", labels, strengths, resolved)
    import hdbscan
    feat64 = features.astype(np.float64, copy=False)
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        cluster_selection_epsilon=epsilon,
        cluster_selection_method=method,
        metric="euclidean",
        prediction_data=False,
    )
    labels = clusterer.fit_predict(feat64).astype(int)
    strengths = np.asarray(clusterer.probabilities_, dtype=float)
    return ClusterResult("hdbscan", labels, strengths, resolved)
