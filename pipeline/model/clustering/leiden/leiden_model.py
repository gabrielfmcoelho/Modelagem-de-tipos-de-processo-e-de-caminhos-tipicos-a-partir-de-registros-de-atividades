from __future__ import annotations

import numpy as np

from ..._result import NOISE_LABEL, ClusterResult


def fit(features: np.ndarray, **params) -> ClusterResult:
    import igraph as ig
    import leidenalg
    from sklearn.neighbors import NearestNeighbors
    n_neighbors = int(params.get("n_neighbors", 15))
    resolution = float(params.get("resolution", 1.0))
    n = features.shape[0]
    feat64 = features.astype(np.float64, copy=False)
    nn = NearestNeighbors(n_neighbors=min(n_neighbors + 1, n), metric="cosine")
    nn.fit(feat64)
    dist, idx = nn.kneighbors(feat64)
    edges: list[tuple[int, int]] = []
    weights: list[float] = []
    for i in range(n):
        for pos in range(1, idx.shape[1]):
            edges.append((i, int(idx[i, pos])))
            weights.append(max(0.0, 1.0 - float(dist[i, pos])))
    g = ig.Graph(n=n, edges=edges, directed=False)
    g.es["weight"] = weights
    part = leidenalg.find_partition(
        g,
        leidenalg.RBConfigurationVertexPartition,
        weights="weight",
        resolution_parameter=resolution,
        seed=42,
    )
    labels = np.asarray(part.membership, dtype=int)
    strengths = np.ones(n, dtype=float)
    return ClusterResult(
        "leiden", labels, strengths,
        {"n_neighbors": n_neighbors, "resolution": resolution, "metric": "cosine", "seed": 42},
    )
