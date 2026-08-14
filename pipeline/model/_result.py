from __future__ import annotations



from dataclasses import dataclass, field

from typing import Any



import numpy as np



NOISE_LABEL = -1





@dataclass
class ClusterAssignment:

    protocolo: str
    macro_label: int
    macro_strength: float
    micro_label: int
    micro_strength: float
    reclassificada: bool

@dataclass
class ClusterDescriptor:

    macro_label: int
    micro_label: int | None
    nivel: str
    member_protocolos: list[str]
    centroid: np.ndarray
    sample_ranks: list[int] = field(default_factory=list)

@dataclass
class ClusterCatalog:

    run_id: str
    macro_clusters: list[ClusterDescriptor]
    micro_clusters: list[ClusterDescriptor]
    assignments: dict[str, ClusterAssignment]

@dataclass
class ClusterResult:

    algo: str
    labels: np.ndarray
    strengths: np.ndarray
    params: dict
