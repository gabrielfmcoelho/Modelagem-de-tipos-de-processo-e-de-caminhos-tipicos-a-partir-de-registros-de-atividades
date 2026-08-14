
from __future__ import annotations

import logging

from ..core._stage_base import RunContext, StageMeta
from ..core.cypher import CLEAR_TIMELINE_EDGES_CYPHER, LOAD_TIMELINE_CYPHER
from ..readers import GraphReader
from ..core.registry import stage
from ..model.timeline import build_edges_for_processo
from ..writers import GraphWriter

log = logging.getLogger(__name__)


def build_timeline(reader: GraphReader, writer: GraphWriter, progress=None) -> None:
    log.info("Phase C: Building timeline DAG (unidade-context)...")

    total = reader.count_processos()
    log.info("  Processing %d processos...", total)
    if progress is not None:
        progress.set_total(total)

    batch_size = 500
    total_edges = 0
    total_inicio = 0
    processed = 0

    for batch in reader.iter_processo_batches(batch_size=batch_size):
        all_flow_edges: list[dict] = []
        all_independent_edges: list[dict] = []
        inicio_rows: list[dict] = []
        batch_protocolos: list[str] = []
        for processo in batch:
            pf = processo.protocolo_formatado
            activities = processo.activities
            if not activities:
                continue

            batch_protocolos.append(pf)
            flow_edges, independent_edges = build_edges_for_processo(activities)
            all_flow_edges.extend(flow_edges)
            all_independent_edges.extend(independent_edges)

            inicio_rows.append({
                "protocolo_formatado": pf,
                "first_id": activities[0]["source_id"],
            })

        if batch_protocolos:
            for name, cypher in CLEAR_TIMELINE_EDGES_CYPHER:
                writer.execute_template(
                    name, cypher, {"protocolos": batch_protocolos}, phase="C",
                )

        if all_flow_edges:
            for i in range(0, len(all_flow_edges), 500):
                sub = all_flow_edges[i:i + 500]
                writer.execute_template(
                    "load_timeline", LOAD_TIMELINE_CYPHER,
                    {"edges": sub}, phase="C",
                )
            total_edges += len(all_flow_edges)

        if all_independent_edges:
            writer.write_edges(
                "SEGUIDO_INDEPENDENTEMENTE_POR",
                "Atividade", {"from_id": "source_id"},
                "Atividade", {"to_id": "source_id"},
                all_independent_edges,
                phase="C",
                props=["ref_id"],
            )
            total_edges += len(all_independent_edges)

        if inicio_rows:
            writer.write_edges(
                "INICIOU_PROCESSO",
                "Processo", {"protocolo_formatado": "protocolo_formatado"},
                "Atividade", {"first_id": "source_id"},
                inicio_rows,
                phase="C",
            )
            total_inicio += len(inicio_rows)

        processed += len(batch)
        if progress is not None:
            progress.advance(len(batch))
        if processed % 5000 == 0 or processed >= total:
            log.info(
                "  Progress: %d/%d processos, %d edges, %d inicio",
                min(processed, total), total, total_edges, total_inicio,
            )

    log.info(
        "Phase C complete: %d edges (SEGUIDA_POR + SEGUIDO_INDEPENDENTEMENTE_POR) + %d INICIOU_PROCESSO",
        total_edges, total_inicio,
    )


@stage(StageMeta(
    name="timeline",
    phase="graph",
    question="Qual a aresta SEGUIDA_POR entre atividades de um mesmo processo?",
    deterministic=True,
    description="Constrói SEGUIDA_POR/PRECEDIDA_POR via tracking de unidade.",
    type="core",
    depends_on=("atividades",),
    modes=("neo4j", "json-emit", "json-replay"),
    estimated_duration="~5-15min para 100k processos",
))
def run(ctx: RunContext) -> None:
    reader = ctx.require_reader()
    writer = ctx.require_writer()
    writer.open_phase("C")
    try:
        build_timeline(reader, writer, progress=ctx.progress)
    finally:
        writer.close_phase("C")
