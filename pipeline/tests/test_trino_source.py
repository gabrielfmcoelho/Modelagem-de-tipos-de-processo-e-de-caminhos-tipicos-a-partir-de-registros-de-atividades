
from __future__ import annotations

from ..core.config import ConfigError, Settings
from ..core.trino_source import build_date_filter, build_orgao_filter, sql_quote_list


def test_sql_quote_list_basic():
    assert sql_quote_list(["a", "b"]) == "'a','b'"
    assert sql_quote_list(["00019.000123/2025-01"]) == "'00019.000123/2025-01'"


def test_sql_quote_list_escapes_quotes_and_handles_empty():
    assert sql_quote_list(["O'Brien"]) == "'O''Brien'"
    assert sql_quote_list([]) == "NULL"


def test_build_date_filter_both_bounds_pads_dates():
    frag, params = build_date_filter("2025-01-01", "2026-01-01")
    assert frag == "AND data_hora >= CAST(? AS TIMESTAMP) AND data_hora < CAST(? AS TIMESTAMP)"
    assert params == ["2025-01-01 00:00:00", "2026-01-01 00:00:00"]


def test_build_date_filter_single_and_none():
    assert build_date_filter("2025-01-01", None) == (
        "AND data_hora >= CAST(? AS TIMESTAMP)", ["2025-01-01 00:00:00"])
    assert build_date_filter(None, "2025-06-01") == (
        "AND data_hora < CAST(? AS TIMESTAMP)", ["2025-06-01 00:00:00"])
    assert build_date_filter(None, None) == ("", [])


def test_build_date_filter_preserves_full_datetime():
    frag, params = build_date_filter("2025-01-01 08:30:00", None)
    assert params == ["2025-01-01 08:30:00"]


def test_build_orgao_filter():
    assert build_orgao_filter("SEAD-PI") == ("AND split_part(unidade, '/', 1) = ?", ["SEAD-PI"])
    assert build_orgao_filter(None) == ("", [])
    assert build_orgao_filter("") == ("", [])


def test_require_trino_missing_fields_raises():
    s = Settings(trino_host=None, trino_user=None, trino_password=None)
    try:
        s.require_trino()
        raise AssertionError("expected ConfigError")
    except ConfigError as e:
        msg = str(e)
        assert "TRINO_HOST" in msg and "TRINO_USER" in msg and "TRINO_PASSWORD" in msg


def test_require_trino_all_fields_passes():
    Settings(trino_host="h", trino_user="u", trino_password="p").require_trino()


def test_build_status_filter_semi_joins_gold_metadata():
    from ..core.trino_source import build_status_filter
    sql, params = build_status_filter("concluido")
    assert "iceberg.sei_gold.processos_metadados" in sql
    assert "protocolo_formatado IN" in sql
    assert params == ["concluido"]
    assert build_status_filter(None) == ("", [])


def test_find_processos_sql_has_a_slot_for_every_filter():
    from ..core import sql
    for tmpl in (sql.FIND_PROCESSOS_SQL, sql.WINDOW_PROTOCOLOS_SUBQUERY):
        for slot in ("{date_filter}", "{orgao_filter}", "{status_filter}"):
            assert slot in tmpl, f"{slot} missing"


def test_discover_threads_status_into_both_templates():
    from pathlib import Path
    src = Path("pipeline/model/discovery.py").read_text(encoding="utf-8")
    assert src.count("status_filter=status_filter") == 2


def test_literal_date_filter_bounds_the_activity_window():
    from ..core.trino_source import literal_date_filter
    f = literal_date_filter("2025-01-01", "2026-01-01")
    assert "data_hora >= TIMESTAMP '2025-01-01 00:00:00'" in f
    assert "data_hora < TIMESTAMP '2026-01-01 00:00:00'" in f
    assert literal_date_filter(None, None) == ""


def test_date_literals_are_validated_against_injection():
    import pytest
    from ..core.trino_source import literal_date_filter
    with pytest.raises(ValueError):
        literal_date_filter("2025-01-01'; DROP TABLE x --", None)


def test_status_filter_carries_the_finish_boundary():
    from ..core.trino_source import build_status_filter
    sql, params = build_status_filter("concluido", concluded_before="2026-01-01")
    assert "status = ?" in sql
    assert "dt_ultimo_andamento < TIMESTAMP '2026-01-01 00:00:00'" in sql
    assert params == ["concluido"]


def test_andamentos_fetch_has_a_date_slot():
    from ..core import sql
    assert "{date_filter}" in sql.FETCH_ANDAMENTOS_SQL


def test_no_sql_references_a_column_absent_from_sei_atividades():
    import re

    from ..core import sql

    known = sql.SEI_ATIVIDADES_COLUMNS
    suspects = set()
    for name in dir(sql):
        if not name.endswith(("_SQL", "_SUBQUERY")):
            continue
        for tok in re.findall(r"\b[a-z][a-z0-9_]{3,}\b", getattr(sql, name)):
            if tok.startswith("id_") or tok in {"unidade", "usuario", "data_hora",
                                                "protocolo_formatado", "descricao_replace",
                                                "tipo_procedimento"}:
                suspects.add(tok)
    unknown = {t for t in suspects if t not in known}
    assert not unknown, f"columns not in sei_atividades: {sorted(unknown)}"
