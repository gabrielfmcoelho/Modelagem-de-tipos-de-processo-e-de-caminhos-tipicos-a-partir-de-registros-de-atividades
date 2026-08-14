from __future__ import annotations

from ..core import cypher, sql
from ..model import discovery as disc
from ..core.config import Settings


class _FakeConn:
    def close(self): pass


def _fake_run_query(conn, sql_text, params=None):
    if "Processo remetido" in sql_text:
        return []
    if "GROUP BY usuario" in sql_text:
        return [{"usuario": "u1", "unidade": "SEAD-PI/GAB", "cnt": 1}]
    if "sei_unidades" in sql_text:
        return [{"unidade": "SEAD-PI/GAB", "id_unidade": 110001},
                {"unidade": "SEAD-PI/SGACG", "id_unidade": 110002}]
    if "ORDER BY data_hora" in sql_text:
        return [{"protocolo_formatado": "00002.000001/2025-10",
                 "data_hora": "2025-01-02T09:00:00", "unidade": "SEAD-PI/GAB",
                 "usuario": "u1", "tipo_procedimento": "T", "id_processo": 999}]
    return []


def test_discover_returns_unidade_ids_and_id_processo(monkeypatch):
    monkeypatch.setattr(disc, "make_trino_conn", lambda s: _FakeConn())
    monkeypatch.setattr(disc, "run_query", _fake_run_query)

    result = disc.discover(Settings(), "2025-01-01", "2026-01-01", "SEAD-PI", None)

    assert result["unidade_ids"]["SEAD-PI/GAB"] == 110001
    assert result["unidade_ids"]["SEAD-PI/SGACG"] == 110002
    assert result["processos"][0]["id_processo"] == 999


def test_empty_discovery_still_has_unidade_ids_key(monkeypatch):
    monkeypatch.setattr(disc, "make_trino_conn", lambda s: _FakeConn())
    monkeypatch.setattr(disc, "run_query", lambda *a, **k: [])
    result = disc.discover(Settings(), "2025-01-01", "2026-01-01", "SEAD-PI", None)
    assert result["unidade_ids"] == {}


def test_sql_projects_the_new_id_columns():
    assert "id_processo" in sql.FIND_PROCESSOS_SQL
    assert "id_unidade" in sql.FIND_DISTINCT_UNIDADES_SQL
    assert "sei_unidades" in sql.FIND_DISTINCT_UNIDADES_SQL


def test_precreate_cypher_sets_id_processo():
    assert "id_processo" in cypher.PRECREATE_PROCESSOS_CYPHER
