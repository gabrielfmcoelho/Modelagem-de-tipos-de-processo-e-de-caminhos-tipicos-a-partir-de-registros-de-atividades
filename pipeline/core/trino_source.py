
from __future__ import annotations

import re

from typing import Any

from .config import Settings


def make_trino_conn(settings: Settings) -> Any:
    settings.require_trino()
    from trino.auth import BasicAuthentication
    from trino.dbapi import connect

    auth = (
        BasicAuthentication(settings.trino_user, settings.trino_password)
        if settings.trino_password else None
    )
    if not settings.trino_verify_ssl:
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        except Exception:
            pass

    return connect(
        host=settings.trino_host,
        port=settings.trino_port,
        user=settings.trino_user,
        http_scheme=settings.trino_http_scheme or "https",
        auth=auth,
        catalog=settings.trino_catalog,
        schema=settings.trino_schema,
        verify=settings.trino_verify_ssl,
    )


def fetch_dicts(cursor) -> list[dict]:
    cols = [c[0] for c in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def run_query(conn, sql: str, params: list | None = None) -> list[dict]:
    cur = conn.cursor()
    try:
        cur.execute(sql, params or [])
        return fetch_dicts(cur)
    finally:
        cur.close()


def sql_quote_list(values) -> str:
    if not values:
        return "NULL"
    return ",".join("'" + str(v).replace("'", "''") + "'" for v in values)


def build_date_filter(from_date: str | None, to_date: str | None) -> tuple[str, list[str]]:
    def _norm(d: str) -> str:
        d = d.strip()
        return f"{d} 00:00:00" if len(d) == 10 else d

    if from_date and to_date:
        return (
            "AND data_hora >= CAST(? AS TIMESTAMP) AND data_hora < CAST(? AS TIMESTAMP)",
            [_norm(from_date), _norm(to_date)],
        )
    if from_date:
        return "AND data_hora >= CAST(? AS TIMESTAMP)", [_norm(from_date)]
    if to_date:
        return "AND data_hora < CAST(? AS TIMESTAMP)", [_norm(to_date)]
    return "", []


def build_orgao_filter(orgao: str | None) -> tuple[str, list[str]]:
    if orgao:
        return "AND split_part(unidade, '/', 1) = ?", [orgao]
    return "", []


GOLD_METADADOS_TABLE = "iceberg.sei_gold.processos_metadados"


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?$")


def _safe_ts(value: str) -> str:
    v = value.strip()
    if not _DATE_RE.match(v):
        raise ValueError(f"unsafe date literal: {value!r}")
    return f"{v} 00:00:00" if len(v) == 10 else v


def build_status_filter(status: str | None,
                        concluded_before: str | None = None) -> tuple[str, list[str]]:
    conds: list[str] = []
    params: list[str] = []
    if status:
        conds.append("status = ?")
        params.append(status)
    if concluded_before:
        conds.append(f"dt_ultimo_andamento < TIMESTAMP '{_safe_ts(concluded_before)}'")
    if not conds:
        return "", []
    return (
        "AND protocolo_formatado IN (SELECT protocolo_formatado FROM "
        f"{GOLD_METADADOS_TABLE} WHERE {' AND '.join(conds)})",
        params,
    )


def literal_date_filter(from_date: str | None, to_date: str | None) -> str:
    parts: list[str] = []
    if from_date:
        parts.append(f"AND data_hora >= TIMESTAMP '{_safe_ts(from_date)}'")
    if to_date:
        parts.append(f"AND data_hora < TIMESTAMP '{_safe_ts(to_date)}'")
    return " ".join(parts)
