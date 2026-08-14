
from __future__ import annotations

from datetime import datetime

from ..model.classifier import transform_row


def _row(descricao: str) -> dict:
    return {
        "id": "x1",
        "protocolo_formatado": "P-1",
        "data_hora": datetime(2025, 1, 1, 10, 0, 0),
        "unidade": "U",
        "usuario": "user",
        "tipo_procedimento": None,
        "descricao_replace": descricao,
    }


def test_geracao_is_start_not_conclusion():
    r = transform_row(_row("Processo 0001 gerado"), seq=0)
    assert r["tipo_acao"] == "GERACAO-PROCEDIMENTO"
    assert r["is_start"] is True
    assert r["is_conclusion"] is False


def test_conclusao_automatica_is_conclusion_not_start():
    r = transform_row(_row("Conclusão automática na unidade"), seq=5)
    assert r["tipo_acao"] == "CONCLUSAO-AUTOMATICA-UNIDADE"
    assert r["is_conclusion"] is True
    assert r["is_start"] is False


def test_conclusao_processo_is_conclusion():
    r = transform_row(_row("Conclusão do processo"), seq=4)
    assert r["tipo_acao"] == "CONCLUSAO-PROCESSO-UNIDADE"
    assert r["is_conclusion"] is True


def test_ordinary_activity_is_neither():
    r = transform_row(_row("Assinado Documento 123"), seq=2)
    assert r["tipo_acao"] == "ASSINATURA-DOCUMENTO"
    assert r["is_start"] is False
    assert r["is_conclusion"] is False
