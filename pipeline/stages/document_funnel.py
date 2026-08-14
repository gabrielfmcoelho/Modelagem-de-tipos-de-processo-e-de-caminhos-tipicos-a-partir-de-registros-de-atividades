from __future__ import annotations

import logging

from ..core._stage_base import RunContext, StageMeta
from ..core.registry import stage
from ..evidence.compose.census import document_funnel
from ..evidence.compose.envelope import write_composed

log = logging.getLogger(__name__)


@stage(StageMeta(
    name="document-funnel",
    phase="documents",
    question="De cada documento baixado, quantos sobreviveram a leitura, a anonimizacao, a "
             "extracao de entidades e a vetorizacao — e onde se perderam?",
    deterministic='conditional',
    nondeterminism="conta o disco e o grafo ao vivo; fixo para um estado dado de ambos",
    description="Funil documental carimbado. A atricao entre baixado, lido, anonimizado e "
                "embutido era contada com `ls | wc -l` no momento do relatorio; agora e um "
                "artefato com a perda declarada em cada passo.",
    type="op",
    depends_on=("parse",),
    modes=("neo4j", "fs"),
    can_skip_when_done=False,
    estimated_duration="~1-2min",
))
def run(ctx: RunContext) -> None:
    driver = ctx.driver if ctx.mode == "neo4j" else None
    path, payload = document_funnel(driver)
    write_composed(payload, path, stage="document-funnel")
    res = payload["results"]
    log.info("document-funnel: corpus %s (%d processos loaded)",
             " -> ".join(f"{s['step']}={s['n']}" for s in res["corpus_documents"]["funnel"]),
             res["corpus_documents"]["n_processos_loaded"])
    log.info("document-funnel: on disk %s, of which %d orphan",
             " -> ".join(f"{s['step']}={s['n']}" for s in res["fetched_on_disk"]["funnel"]),
             res["fetched_on_disk"]["orphan_on_disk"])
    log.info("document-funnel: referenced %s -> %s",
             " -> ".join(f"{s['step']}={s['n']}" for s in res["referenced_documents"]["funnel"]),
             path.name)
