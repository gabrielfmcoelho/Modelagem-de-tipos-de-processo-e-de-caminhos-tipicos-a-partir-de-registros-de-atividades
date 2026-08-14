from __future__ import annotations

import numpy as np

from .._result import ClusterResult
from .hdbscan.hdbscan_model import fit as _fit_hdbscan
from .kmeans.kmeans_model import fit as _fit_kmeans
from .leiden.leiden_model import fit as _fit_leiden

_FITTERS = {"hdbscan": _fit_hdbscan, "kmeans": _fit_kmeans, "leiden": _fit_leiden}


def fit(features: np.ndarray, algo: str = "hdbscan", **params) -> ClusterResult:
    fitter = _FITTERS.get(algo)
    if fitter is None:
        raise ValueError(f"unknown algo {algo!r}; available: {', '.join(sorted(_FITTERS))}")
    return fitter(features, **params)
