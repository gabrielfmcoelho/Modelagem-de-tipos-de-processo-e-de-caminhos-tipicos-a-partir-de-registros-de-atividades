
from __future__ import annotations

from pipeline.readers.base import ProcessoTimeline
from pipeline.stages.situacao import _process_batch


class _CapturingWriter:

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def open_phase(self, phase: str) -> None:
        pass

    def close_phase(self, phase: str) -> None:
        pass

    def execute_template(self, name, cypher, params, *, phase):
        self.calls.append((name, dict(params)))

    def write_nodes(self, *args, **kwargs):
        raise NotImplementedError

    def write_edges(self, *args, **kwargs):
        raise NotImplementedError


def _atv(source_id, data_hora, unidade, tipo_acao):
    return {
        "source_id": source_id,
        "data_hora": data_hora,
        "unidade": unidade,
        "tipo_acao": tipo_acao,
        "source_unidade": None,
        "ref_id": None,
    }


def test_situacao_stage_emits_expected_rows_for_mixed_batch():
    batch = [
        ProcessoTimeline(
            protocolo_formatado="PRC-1",
            activities=[
                _atv(1, "2025-01-01T10:00:00", "A", "GERACAO-PROCEDIMENTO"),
                _atv(2, "2025-01-02T10:00:00", "A", "CONCLUSAO-PROCESSO-UNIDADE"),
            ],
        ),
        ProcessoTimeline(
            protocolo_formatado="PRC-2",
            activities=[
                _atv(3, "2025-02-01T10:00:00", "B", "GERACAO-PROCEDIMENTO"),
                _atv(4, "2025-02-05T10:00:00", "C", "PROCESSO-REMETIDO-UNIDADE"),
            ],
        ),
    ]

    writer = _CapturingWriter()
    counts = _process_batch(batch, writer, ctx=None)

    assert counts["processos"] == 2
    assert counts["ciclos"] == 3
    assert counts["ciclos_concluidos"] == 1
    assert counts["situacao_unidade"] == 3
    assert counts["em_aberto_unidade"] == 2
    assert counts["ultima_atividade_em_aberto"] == 2
    assert counts["atividade_mais_recente"] == 2

    template_names = [c[0] for c in writer.calls]
    assert template_names[0] == "clear_situacao"
    cleared_protocolos = writer.calls[0][1]["protocolos"]
    assert set(cleared_protocolos) == {"PRC-1", "PRC-2"}


def test_situacao_stage_skips_processos_without_activities():
    batch = [
        ProcessoTimeline(protocolo_formatado="PRC-X", activities=[]),
        ProcessoTimeline(
            protocolo_formatado="PRC-Y",
            activities=[_atv(1, "2025-01-01T10:00:00", "A", "GERACAO-PROCEDIMENTO")],
        ),
    ]
    writer = _CapturingWriter()
    counts = _process_batch(batch, writer, ctx=None)
    assert counts["processos"] == 1
    assert counts["situacao_unidade"] == 1
    cleared = writer.calls[0][1]["protocolos"]
    assert cleared == ["PRC-Y"]


def test_situacao_stage_concluded_processo_emits_no_em_aberto_edges():
    batch = [ProcessoTimeline(
        protocolo_formatado="PRC-DONE",
        activities=[
            _atv(1, "2025-01-01T10:00:00", "A", "GERACAO-PROCEDIMENTO"),
            _atv(2, "2025-01-02T10:00:00", "A", "CONCLUSAO-PROCESSO-UNIDADE"),
        ],
    )]
    writer = _CapturingWriter()
    counts = _process_batch(batch, writer, ctx=None)
    assert counts["em_aberto_unidade"] == 0
    assert counts["em_aberto_orgao"] == 0
    assert counts["ultima_atividade_em_aberto"] == 0
    assert counts["atividade_mais_recente"] == 1
    assert counts["ciclos"] == 1
    assert counts["ciclos_concluidos"] == 1


def test_situacao_stage_reabertura_creates_two_cycles():
    batch = [ProcessoTimeline(
        protocolo_formatado="PRC-REOP",
        activities=[
            _atv(1, "2025-01-01T10:00:00", "A", "GERACAO-PROCEDIMENTO"),
            _atv(2, "2025-01-05T10:00:00", "A", "CONCLUSAO-PROCESSO-UNIDADE"),
            _atv(3, "2025-02-01T10:00:00", "A", "REABERTURA-PROCESSO-UNIDADE"),
        ],
    )]
    writer = _CapturingWriter()
    counts = _process_batch(batch, writer, ctx=None)
    assert counts["ciclos"] == 2
    assert counts["ciclos_concluidos"] == 1
    assert counts["em_aberto_unidade"] == 1
