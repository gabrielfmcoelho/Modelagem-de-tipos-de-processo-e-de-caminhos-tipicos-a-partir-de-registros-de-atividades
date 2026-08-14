from __future__ import annotations

import numpy as np

from ..._result import ClusterResult

NOISE = -1
DEFAULT_K = 120


def onehot(label_map: dict[str, int], protocolos: list[str]) -> np.ndarray:
    labels = [label_map.get(pf, NOISE) for pf in protocolos]
    uniq = sorted({lab for lab in labels if lab != NOISE})
    index = {lab: i for i, lab in enumerate(uniq)}
    out = np.zeros((len(protocolos), len(uniq)), dtype=np.float64)
    for row, lab in enumerate(labels):
        if lab != NOISE:
            out[row, index[lab]] = 1.0
    return out


def coassociation(label_maps: dict[str, dict[str, int]], algos: list[str],
                  protocolos: list[str]) -> tuple[np.ndarray, dict[str, int]]:
    blocks = [onehot(label_maps[a], protocolos) for a in algos]
    per_algo = {a: int(b.shape[1]) for a, b in zip(algos, blocks)}
    x = np.hstack(blocks)
    x = x / np.sqrt(len(algos))
    return x, per_algo


def fit(label_maps: dict[str, dict[str, int]], algos: list[str], protocolos: list[str],
        *, k: int = DEFAULT_K, seed: int = 42, n_init: int = 10) -> tuple[ClusterResult, np.ndarray]:
    from sklearn.cluster import KMeans
    x, per_algo = coassociation(label_maps, algos, protocolos)
    labels = KMeans(n_clusters=k, random_state=seed, n_init=n_init).fit_predict(x).astype(int)
    params = {"method": "coassociation-kmeans", "algos": algos, "k": k,
              "per_algo_clusters": per_algo, "n_members": len(protocolos),
              "seed": seed, "n_init": n_init}
    strengths = np.ones(len(protocolos), dtype=float)
    return ClusterResult("consensus", labels, strengths, params), x


def sweep_k(label_maps: dict[str, dict[str, int]], algos: list[str], protocolos: list[str],
            ks: list[int], *, seed: int = 42, n_init: int = 10) -> list[dict]:
    from sklearn.cluster import KMeans
    from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score, silhouette_score
    x, _ = coassociation(label_maps, algos, protocolos)
    rows = []
    for k in ks:
        if k >= len(protocolos):
            continue
        labels = KMeans(n_clusters=k, random_state=seed, n_init=n_init).fit_predict(x).astype(int)
        uniq = len(set(labels.tolist()))
        row = {"k": int(k), "n_clusters": uniq, "silhouette": None,
               "calinski_harabasz": None, "davies_bouldin": None}
        if uniq > 1:
            row["silhouette"] = float(silhouette_score(x, labels, metric="cosine"))
            row["calinski_harabasz"] = float(calinski_harabasz_score(x, labels))
            row["davies_bouldin"] = float(davies_bouldin_score(x, labels))
        rows.append(row)
    return rows


def best_k(rows: list[dict]) -> tuple[int | None, str]:
    scored = [(r["silhouette"], r["k"]) for r in rows if r["silhouette"] is not None]
    if not scored:
        return None, "no k produced more than one cluster; silhouette undefined"
    best = max(scored)
    return int(best[1]), (
        f"highest silhouette in the co-association space ({best[0]:.4f}) over "
        f"{len(scored)} candidate values of k")
