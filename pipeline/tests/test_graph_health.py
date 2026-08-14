
from __future__ import annotations

from pipeline.stages.graph_health import format_health_report


def _stats():
    return {
        "totals": {"atividades": 1000, "processos": 100,
                   "seguida_por": 900, "independente": 50},
        "isolated_flow": {"total": 60, "by_type": [
            ("CONCLUSAO-AUTOMATICA-UNIDADE", 30), ("ASSINATURA-DOCUMENTO", 20)]},
        "orphaned": {"total": 10, "by_type": [("ASSINATURA-DOCUMENTO", 8)]},
        "disconnected": {"total": 5, "by_type": [("BLOCO-RETORNO", 4)]},
        "isolated_conclusions": 30,
        "start_types": [("GERACAO-PROCEDIMENTO", 98), ("PROCESSO-RECEBIDO-UNIDADE", 2)],
        "situacao": [("concluido", 70), ("em_andamento", 30)],
    }


def test_report_includes_headline_counts_and_percentages():
    out = format_health_report(_stats())
    assert "1,000" in out
    assert "6.0%" in out
    assert "1.0%" in out
    assert "CONCLUSAO-AUTOMATICA-UNIDADE" in out
    assert "GERACAO-PROCEDIMENTO" in out
    assert "concluido" in out


def test_report_separates_three_connectivity_metrics():
    out = format_health_report(_stats())
    assert "no SEGUIDA_POR" in out
    assert "SEGUIDO_INDEPENDENTEMENTE_POR" in out
    assert "REFERENCIA_DOCUMENTO" in out
    assert "BLOCO-RETORNO" in out
    assert "0.5%" in out


def test_report_handles_zero_activities_without_dividing_by_zero():
    stats = _stats()
    stats["totals"]["atividades"] = 0
    stats["isolated_flow"]["total"] = 0
    stats["orphaned"]["total"] = 0
    out = format_health_report(stats)
    assert "0.0%" in out
