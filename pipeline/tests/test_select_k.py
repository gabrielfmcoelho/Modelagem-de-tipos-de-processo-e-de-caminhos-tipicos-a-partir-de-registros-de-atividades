import numpy as np
from sklearn.datasets import make_blobs

from pipeline.evidence.clustering.select_k import elbow_index, sweep_kmeans


def test_elbow_recovers_blob_count():
    features, _ = make_blobs(n_samples=600, centers=6, cluster_std=0.6, random_state=42)
    ks = list(range(2, 13))
    rows, sil_scope = sweep_kmeans(features.astype(np.float64), ks, 42)
    k_elbow = ks[elbow_index(ks, [row["inertia"] for row in rows])]
    assert abs(k_elbow - 6) <= 2
    assert sil_scope == "full"
    assert all(row["silhouette"] is not None for row in rows)
