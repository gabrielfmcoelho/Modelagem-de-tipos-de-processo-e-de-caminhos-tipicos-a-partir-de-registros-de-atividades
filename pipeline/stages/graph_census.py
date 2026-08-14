from __future__ import annotations

import logging

from ..core._stage_base import RunContext, StageMeta
from ..core.registry import stage
from ..evidence.compose.census import graph_build
from ..evidence.compose.envelope import write_composed

log = logging.getLogger(__name__)


@stage(StageMeta(
    name="graph-census",
    phase="graph",
    question="Que grafo existe apos a carga: quantos nos por rotulo, quantas arestas por tipo, "
             "e quantos processos sobreviveram a cada filtro?",
    deterministic='conditional',
    nondeterminism="le o grafo ao vivo; o resultado e fixo para um estado dado do banco",
    description="Censo do grafo carregado. As fases de ingestao e grafo nao deixavam nenhum "
                "artefato: o corpus era reconstruido a partir do Trino no momento do relatorio. "
                "Este stage congela o estado do grafo como evidencia carimbada.",
    type="op",
    depends_on=("situacao",),
    modes=("neo4j",),
    can_skip_when_done=False,
    estimated_duration="<1min",
))
def run(ctx: RunContext) -> None:
    driver = ctx.require_driver()
    path, payload = graph_build(driver)
    write_composed(payload, path, stage="graph-census")
    r = payload["results"]
    log.info("graph-census: %d nodes, %d relationships, %d processos (%d concluded) -> %s",
             r["totals"]["nodes"], r["totals"]["relationships"],
             r["processo"]["total"], r["processo"]["concluded"], path.name)
