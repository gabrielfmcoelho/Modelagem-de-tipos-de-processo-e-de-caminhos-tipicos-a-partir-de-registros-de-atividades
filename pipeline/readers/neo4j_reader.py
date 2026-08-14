
from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

from .base import GraphReader, ProcessoTimeline

log = logging.getLogger(__name__)

_COUNT_PROCESSOS_CYPHER = "MATCH (p:Processo) RETURN count(p) AS cnt"

_BATCH_PROCESSOS_CYPHER = """
MATCH (p:Processo)
WITH p ORDER BY p.protocolo_formatado SKIP $skip LIMIT $limit
MATCH (a:Atividade)-[:DO_PROCESSO]->(p)
MATCH (a)-[:EXECUTADO_PELA_UNIDADE]->(u:Unidade)
OPTIONAL MATCH (a)-[:REMETIDO_PELA_UNIDADE]->(src:Unidade)
WITH p.protocolo_formatado AS pf,
     a.source_id AS source_id,
     a.data_hora AS data_hora,
     a.tipo_acao AS tipo_acao,
     a.ref_id AS ref_id,
     u.sigla AS unidade,
     src.sigla AS source_unidade
ORDER BY pf, data_hora, source_id
RETURN pf, collect({
    source_id: source_id,
    data_hora: toString(data_hora),
    tipo_acao: tipo_acao,
    ref_id: ref_id,
    unidade: unidade,
    source_unidade: source_unidade
}) AS activities
"""


class Neo4jReader(GraphReader):
    def __init__(self, driver: Any) -> None:
        self._driver = driver

    def close(self) -> None:
        pass

    def count_processos(self) -> int:
        with self._driver.session() as session:
            record = session.run(_COUNT_PROCESSOS_CYPHER).single()
        return int(record["cnt"]) if record else 0

    def iter_processo_batches(
        self, *, batch_size: int = 500,
    ) -> Iterator[list[ProcessoTimeline]]:
        skip = 0
        total = self.count_processos()
        while skip < total:
            with self._driver.session() as session:
                result = session.run(
                    _BATCH_PROCESSOS_CYPHER, skip=skip, limit=batch_size,
                )
                batch: list[ProcessoTimeline] = [
                    ProcessoTimeline(
                        protocolo_formatado=record["pf"],
                        activities=list(record["activities"] or []),
                    )
                    for record in result
                ]
            yield batch
            skip += batch_size


_COHORT_COUNT_CYPHER = """
MATCH (p:Processo)-[:MEMBRO_DA_COORTE]->(:Coorte {id: $cohort_id})
RETURN count(p) AS cnt
"""

_COHORT_BATCH_CYPHER = """
MATCH (p:Processo)-[:MEMBRO_DA_COORTE]->(:Coorte {id: $cohort_id})
WITH p ORDER BY p.protocolo_formatado SKIP $skip LIMIT $limit
MATCH (a:Atividade)-[:DO_PROCESSO]->(p)
MATCH (a)-[:EXECUTADO_PELA_UNIDADE]->(u:Unidade)
OPTIONAL MATCH (a)-[:REMETIDO_PELA_UNIDADE]->(src:Unidade)
WITH p.protocolo_formatado AS pf,
     a.source_id AS source_id,
     a.data_hora AS data_hora,
     a.tipo_acao AS tipo_acao,
     a.ref_id AS ref_id,
     u.sigla AS unidade,
     src.sigla AS source_unidade
ORDER BY pf, data_hora, source_id
RETURN pf, collect({
    source_id: source_id,
    data_hora: toString(data_hora),
    tipo_acao: tipo_acao,
    ref_id: ref_id,
    unidade: unidade,
    source_unidade: source_unidade
}) AS activities
"""


class CohortNeo4jReader(Neo4jReader):

    def __init__(self, driver: Any, cohort_id: str) -> None:
        super().__init__(driver)
        self._cohort_id = cohort_id

    def count_processos(self) -> int:
        with self._driver.session() as session:
            record = session.run(
                _COHORT_COUNT_CYPHER, {"cohort_id": self._cohort_id},
            ).single()
        return int(record["cnt"]) if record else 0

    def iter_processo_batches(
        self, *, batch_size: int = 500,
    ) -> Iterator[list[ProcessoTimeline]]:
        skip = 0
        total = self.count_processos()
        while skip < total:
            with self._driver.session() as session:
                result = session.run(
                    _COHORT_BATCH_CYPHER,
                    {"cohort_id": self._cohort_id, "skip": skip, "limit": batch_size},
                )
                batch: list[ProcessoTimeline] = [
                    ProcessoTimeline(
                        protocolo_formatado=record["pf"],
                        activities=list(record["activities"] or []),
                    )
                    for record in result
                ]
            yield batch
            skip += batch_size
