from __future__ import annotations

import logging

from ..core._stage_base import RunContext, StageMeta
from ..core.registry import stage
from ..evidence.compose.census import feature_build
from ..evidence.compose.envelope import write_composed

log = logging.getLogger(__name__)


@stage(StageMeta(
    name="feature-census",
    phase="features",
    question="Que matrizes de atributos existem, com que dimensao, que digest e de qual braco?",
    deterministic=True,
    description="Inventario das matrizes de atributos em artifacts/features/. O digest de cada "
                "matriz e a ancora de reprodutibilidade: cluster-audit reajusta cada "
                "agrupamento a partir dela, entao o que ela contem precisa ser evidencia "
                "declarada, nao um arquivo binario sem descricao.",
    type="op",
    depends_on=("processo-embed",),
    modes=("neo4j", "fs"),
    can_skip_when_done=False,
    estimated_duration="<1min",
))
def run(ctx: RunContext) -> None:
    path, payload = feature_build()
    write_composed(payload, path, stage="feature-census")
    log.info("feature-census: %d feature matrices -> %s",
             payload["results"]["n_matrices"], path.name)
