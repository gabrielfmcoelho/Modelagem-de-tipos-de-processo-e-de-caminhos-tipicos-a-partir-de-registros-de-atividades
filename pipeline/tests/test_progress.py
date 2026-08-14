from __future__ import annotations

from pathlib import Path

from ..core._stage_base import RunContext, StageProgress
from ..core.config import Settings


def test_runcontext_default_progress_is_noop():
    ctx = RunContext(settings=Settings(), mode="neo4j", flags={}, state_dir=Path("."))
    ctx.progress.set_total(10)
    ctx.progress.advance()
    ctx.progress.advance(3)
    assert isinstance(ctx.progress, StageProgress)


def test_rich_progress_delegates_to_the_bar():
    from ..core.runner import _RichProgress

    class _FakeBar:
        def __init__(self):
            self.calls = []

        def update(self, tid, **kw):
            self.calls.append(("update", tid, kw))

        def advance(self, tid, n):
            self.calls.append(("advance", tid, n))

    bar = _FakeBar()
    rp = _RichProgress(bar, "T")
    rp.set_total(12438)
    rp.advance()
    rp.advance(5)
    assert bar.calls == [
        ("update", "T", {"total": 12438}),
        ("advance", "T", 1),
        ("advance", "T", 5),
    ]


class _Recorder:
    def __init__(self):
        self.total = None
        self.adv = []

    def set_total(self, t):
        self.total = t

    def advance(self, n=1):
        self.adv.append(n)


def test_build_timeline_drives_progress():
    from pipeline.stages import timeline

    class _Proc:
        def __init__(self, pf):
            self.protocolo_formatado = pf
            self.activities = []

    class _Reader:
        def count_processos(self):
            return 5

        def iter_processo_batches(self, batch_size):
            yield [_Proc("A"), _Proc("B")]
            yield [_Proc("C"), _Proc("D"), _Proc("E")]

    class _Writer:
        def execute_template(self, *a, **k):
            pass

        def write_edges(self, *a, **k):
            pass

    rec = _Recorder()
    timeline.build_timeline(_Reader(), _Writer(), progress=rec)
    assert rec.total == 5
    assert rec.adv == [2, 3]


def test_build_timeline_clears_timeline_edges_before_rebuild():
    from pipeline.stages import timeline

    class _Proc:
        def __init__(self, pf, acts):
            self.protocolo_formatado = pf
            self.activities = acts

    a1 = {"source_id": "a", "data_hora": "2025-01-01T10:00:00",
          "tipo_acao": "GERACAO-PROCEDIMENTO", "unidade": "U"}
    a2 = {"source_id": "b", "data_hora": "2025-01-01T11:00:00",
          "tipo_acao": "GERACAO-DOCUMENTO", "unidade": "U"}

    class _Reader:
        def count_processos(self):
            return 1

        def iter_processo_batches(self, batch_size):
            yield [_Proc("P1", [a1, a2])]

    calls = []

    class _Writer:
        def execute_template(self, name, cypher, params, *, phase):
            calls.append((name, params))

        def write_edges(self, *a, **k):
            pass

    timeline.build_timeline(_Reader(), _Writer())
    clear_names = {c[0] for c in calls if c[0].startswith("clear_")}
    assert clear_names == {
        "clear_seguida_por", "clear_precedida_por", "clear_seguido_independente"}
    assert all(c[1]["protocolos"] == ["P1"] for c in calls if c[0].startswith("clear_"))
    names = [c[0] for c in calls]
    assert names.index("clear_seguida_por") < names.index("load_timeline")
