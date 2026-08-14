
from __future__ import annotations

import logging
from typing import Any

from .classification import extract_orgao
from .classifier import extract_source_unidade
from ..core.config import Settings
from .hierarchy import all_ancestor_unidades
from ..core.sql import FIND_DISTINCT_UNIDADES_SQL, FIND_PROCESSOS_SQL, FIND_REMETIDO_DESCRICOES_SQL, FIND_USUARIOS_SQL, WINDOW_PROTOCOLOS_SUBQUERY
from ..core.trino_source import build_date_filter, build_orgao_filter, build_status_filter, make_trino_conn, run_query

log = logging.getLogger(__name__)


def discover(
    settings: Settings,
    from_date: str | None,
    to_date: str | None,
    orgao: str | None = None,
    limit: int | None = None,
    status: str | None = None,
    concluded_before: str | None = None,
) -> dict[str, Any]:
    log.info(
        "Discovery: finding processos (creation events) from Trino "
        "(orgao=%s, status=%s, concluded_before=%s, limit=%s)...",
        orgao or "ALL", status or "ALL", concluded_before or "-", limit or "none",
    )

    date_filter, date_params = build_date_filter(from_date, to_date)
    orgao_filter, orgao_params = build_orgao_filter(orgao)
    status_filter, status_params = build_status_filter(status, concluded_before)
    params = date_params + orgao_params + status_params
    limit_clause = f"LIMIT {int(limit)}" if limit else ""
    window = WINDOW_PROTOCOLOS_SUBQUERY.format(
        date_filter=date_filter, orgao_filter=orgao_filter, status_filter=status_filter)

    conn = make_trino_conn(settings)
    try:
        find_sql = FIND_PROCESSOS_SQL.format(
            date_filter=date_filter, orgao_filter=orgao_filter,
            status_filter=status_filter, limit_clause=limit_clause,
        )
        log.info("SQL: %s", find_sql.strip()[:200])
        log.info("Params: %s", params)
        processos = run_query(conn, find_sql, params)

        protocolo_ids = [row["protocolo_formatado"] for row in processos]
        log.info("Found %d processos", len(protocolo_ids))

        if not protocolo_ids:
            return {
                "processos": [],
                "protocolo_ids": [],
                "all_unidades": set(),
                "unidade_ids": {},
                "user_orgao": {},
            }

        all_unidades: set[str] = {"DESCONHECIDA"}
        for row in processos:
            if row["unidade"]:
                all_unidades.add(row["unidade"])

        log.info("Scanning andamentos for unidades and usuarios...")
        unidade_ids: dict[str, int] = {}
        for row in run_query(conn, FIND_DISTINCT_UNIDADES_SQL.format(window=window), params):
            if row["unidade"]:
                all_unidades.add(row["unidade"])
                if row.get("id_unidade") is not None:
                    unidade_ids[row["unidade"]] = row["id_unidade"]

        for row in run_query(conn, FIND_REMETIDO_DESCRICOES_SQL.format(window=window), params):
            src = extract_source_unidade(row["descricao_replace"])
            if src:
                all_unidades.add(src)

        log.info("Found %d unique unidades", len(all_unidades))

        ancestors: set[str] = set()
        for u in list(all_unidades):
            for anc in all_ancestor_unidades(u):
                ancestors.add(anc)
        added = ancestors - all_unidades
        all_unidades |= ancestors
        if added:
            log.info("  Added %d ancestor unidades for hierarchy", len(added))

        user_orgao: dict[str, str] = {"DESCONHECIDO": "DESCONHECIDO"}
        for row in run_query(conn, FIND_USUARIOS_SQL.format(window=window), params):
            usuario = row["usuario"]
            unidade = row["unidade"]
            if usuario not in user_orgao:
                user_orgao[usuario] = extract_orgao(unidade)
    finally:
        conn.close()
    log.info("Found %d unique usuarios", len(user_orgao))

    return {
        "processos": processos,
        "protocolo_ids": protocolo_ids,
        "all_unidades": all_unidades,
        "unidade_ids": unidade_ids,
        "user_orgao": user_orgao,
    }
