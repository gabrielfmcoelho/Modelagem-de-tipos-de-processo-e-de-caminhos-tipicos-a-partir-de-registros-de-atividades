from __future__ import annotations

import numpy as np

from ..._result import NOISE_LABEL, ClusterResult


def fit(features: np.ndarray, **params) -> ClusterResult:
    if params.get("k") is None:
        raise ValueError("kmeans requires an explicit 'k' (number of clusters); no default is assumed")
    k = int(params["k"])
    from sklearn.cluster import KMeans
    feat64 = features.astype(np.float64, copy=False)
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(feat64).astype(int)
    strengths = np.ones(features.shape[0], dtype=float)
    return ClusterResult("kmeans", labels, strengths, {"k": k, "n_init": 10, "random_state": 42})
