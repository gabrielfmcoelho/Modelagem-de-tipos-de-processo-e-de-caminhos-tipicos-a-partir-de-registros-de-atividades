
from __future__ import annotations

import json
import logging

import pytest

from pipeline.model import graph_summary
from pipeline.stages import resumo


def test_bar_returns_empty_when_max_is_zero():
    assert graph_summary._bar(5, 0) == ""


def test_bar_scales_fill_to_width():
    out = graph_summary._bar(5, 10, width=10)
    assert out == "█████░░░░░"


def test_fmt_hours_switches_units():
    assert graph_summary._fmt_hours(None) == "—"
    assert graph_summary._fmt_hours(5) == "5.0h"
    assert graph_summary._fmt_hours(48) == "2.0d"
    assert graph_summary._fmt_hours(24 * 400) == "1.1a"


def test_fmt_date_handles_none_str_and_datetime():
    from datetime import datetime
    assert graph_summary._fmt_date(None) == "—"
    assert graph_summary._fmt_date("2025-01-02T03:04:05.000Z") == "2025-01-02T03:04:05"
    assert graph_summary._fmt_date(datetime(2025, 1, 2, 3, 4)) == "2025-01-02 03:04"


def test_pct_avoids_division_by_zero():
    assert graph_summary._pct(1, 0) == "—"
    assert graph_summary._pct(1, 4) == "25.0%"


def test_orgao_match_filters_when_orgao_given():
    assert "CRIADO_NO_ORGAO" in graph_summary._orgao_match("p", "SEAD-PI")
    assert "CRIADO_NO_ORGAO" not in graph_summary._orgao_match("p", None)


def _write_ndjson(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def test_run_summary_json_logs_instead_of_printing(tmp_path, capsys, caplog):
    emit_dir = tmp_path / "out"
    _write_ndjson(emit_dir / "nodes" / "Processo.ndjson", [{"a": 1}, {"a": 2}])
    _write_ndjson(emit_dir / "edges" / "SEGUIDA_POR.ndjson", [{"a": 1}])
    _write_ndjson(emit_dir / "templates" / "load_atividades.ndjson", [
        {"params": {"rows": [{"tipo_acao": "GERACAO-PROCEDIMENTO"}]}},
    ])

    with caplog.at_level(logging.INFO, logger="pipeline.stages.resumo"):
        resumo.run_summary_json(emit_dir, top=5)

    captured = capsys.readouterr()
    assert captured.out == ""

    text = "\n".join(r.message for r in caplog.records)
    assert "Processo" in text
    assert "2" in text
    assert "GERACAO-PROCEDIMENTO" in text


def test_run_summary_json_exits_when_dir_missing(tmp_path, caplog):
    missing = tmp_path / "nope"
    with caplog.at_level(logging.ERROR, logger="pipeline.stages.resumo"):
        with pytest.raises(SystemExit):
            resumo.run_summary_json(missing, top=5)
    assert any("not found" in r.message for r in caplog.records)
