
from __future__ import annotations

import json
import logging
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ._dispatch import fit
from .._result import NOISE_LABEL, ClusterAssignment, ClusterCatalog, ClusterDescriptor, ClusterResult


from ..cluster_metrics import compute_dbcv
from ...core.deployment import ORGAO_GOVERNO, ORGAO_SUFIXO

log = logging.getLogger(__name__)


__all__ = ["compute_dbcv"]

def _category_id(run_id: str, level: str, label: int, parent_label: int | None = None) -> str:
    if parent_label is None:
        return f"{run_id}|{level}|{label}"
    return f"{run_id}|{level}|{parent_label}|{label}"


def cluster_macro(features: np.ndarray, *, min_cluster_size: int = 20):
    res = fit(features, "hdbscan", min_cluster_size=min_cluster_size)
    return res.labels, res.strengths


def cluster_micro_within(
    features: np.ndarray,
    macro_labels: np.ndarray,
    *,
    min_cluster_size: int = 5,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n = features.shape[0]
    micro_labels = np.full(n, NOISE_LABEL, dtype=int)
    micro_strengths = np.zeros(n, dtype=float)
    reclassificada = np.zeros(n, dtype=bool)

    unique_macros = sorted({int(x) for x in macro_labels if int(x) != NOISE_LABEL})
    for m in unique_macros:
        idx = np.where(macro_labels == m)[0]
        sub_res = fit(features[idx], "hdbscan", min_cluster_size=min_cluster_size)
        micro_labels[idx] = sub_res.labels
        micro_strengths[idx] = sub_res.strengths

    outlier_idx = np.where(macro_labels == NOISE_LABEL)[0]
    if outlier_idx.size > 0:
        sub_res = fit(features[outlier_idx], "hdbscan", min_cluster_size=min_cluster_size)
        micro_labels[outlier_idx] = sub_res.labels
        micro_strengths[outlier_idx] = sub_res.strengths
        reclassificada[outlier_idx] = sub_res.labels != NOISE_LABEL

    return micro_labels, micro_strengths, reclassificada


def dedupe_macro_labels(
    features: np.ndarray, macro_labels: np.ndarray, *, threshold: float = 0.0,
) -> np.ndarray:
    if threshold <= 0:
        return macro_labels
    labels = sorted({int(x) for x in macro_labels if int(x) != NOISE_LABEL})
    if len(labels) < 2:
        return macro_labels

    sizes: dict[int, int] = {}
    centroids: dict[int, np.ndarray] = {}
    radii: dict[int, float] = {}
    for m in labels:
        pts = features[macro_labels == m].astype(np.float64)
        c = pts.mean(axis=0)
        centroids[m] = c
        radii[m] = float(np.linalg.norm(pts - c, axis=1).mean()) if len(pts) else 0.0
        sizes[m] = len(pts)

    parent = {m: m for m in labels}

    def find(x: int) -> int:
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root

    for i, a in enumerate(labels):
        for b in labels[i + 1:]:
            gap = float(np.linalg.norm(centroids[a] - centroids[b]))
            denom = radii[a] + radii[b]
            sep = (gap / denom) if denom > 0 else (0.0 if gap == 0 else float("inf"))
            if sep <= threshold:
                ra, rb = find(a), find(b)
                if ra != rb:
                    keep, drop = (ra, rb) if (sizes[ra], -ra) >= (sizes[rb], -rb) else (rb, ra)
                    parent[drop] = keep

    out = macro_labels.copy()
    for m in labels:
        root = find(m)
        if root != m:
            out[macro_labels == m] = root
    return out


def build_catalog(
    run_id: str,
    protocolos: Sequence[str],
    features: np.ndarray,
    macro_labels: np.ndarray,
    macro_strengths: np.ndarray,
    micro_labels: np.ndarray,
    micro_strengths: np.ndarray,
    reclassificada: np.ndarray,
) -> ClusterCatalog:
    n = len(protocolos)
    assert features.shape[0] == n == macro_labels.shape[0] == micro_labels.shape[0]

    assignments: dict[str, ClusterAssignment] = {}
    for i, pf in enumerate(protocolos):
        assignments[pf] = ClusterAssignment(
            protocolo=pf,
            macro_label=int(macro_labels[i]),
            macro_strength=float(macro_strengths[i]),
            micro_label=int(micro_labels[i]),
            micro_strength=float(micro_strengths[i]),
            reclassificada=bool(reclassificada[i]),
        )

    macro_clusters: list[ClusterDescriptor] = []
    for m in sorted({int(x) for x in macro_labels if int(x) != NOISE_LABEL}):
        idx = np.where(macro_labels == m)[0]
        sort_order = idx[np.argsort(-macro_strengths[idx])]
        macro_clusters.append(ClusterDescriptor(
            macro_label=m, micro_label=None, nivel="macro",
            member_protocolos=[protocolos[i] for i in sort_order],
            centroid=features[idx].mean(axis=0),
            sample_ranks=[int(i) for i in sort_order],
        ))

    micro_clusters: list[ClusterDescriptor] = []
    micro_keys: set[tuple[int, int]] = set()
    for i in range(n):
        m, sub = int(macro_labels[i]), int(micro_labels[i])
        if sub == NOISE_LABEL:
            continue
        micro_keys.add((m, sub))

    for (m, sub) in sorted(micro_keys):
        idx = np.where((macro_labels == m) & (micro_labels == sub))[0]
        sort_order = idx[np.argsort(-micro_strengths[idx])]
        nivel = "reclassificada" if m == NOISE_LABEL else "micro"
        micro_clusters.append(ClusterDescriptor(
            macro_label=m, micro_label=sub, nivel=nivel,
            member_protocolos=[protocolos[i] for i in sort_order],
            centroid=features[idx].mean(axis=0),
            sample_ranks=[int(i) for i in sort_order],
        ))

    return ClusterCatalog(
        run_id=run_id,
        macro_clusters=macro_clusters,
        micro_clusters=micro_clusters,
        assignments=assignments,
    )


def category_id(run_id: str, level: str, label: int, parent_label: int | None = None) -> str:
    return _category_id(run_id, level, label, parent_label)
