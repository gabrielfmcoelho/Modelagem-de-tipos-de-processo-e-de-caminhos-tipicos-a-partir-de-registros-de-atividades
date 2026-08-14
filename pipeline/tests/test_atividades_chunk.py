
from __future__ import annotations

import pipeline.stages.atividades as atividades


class _FakeCursor:
    _COLS = ["id", "protocolo_formatado", "data_hora", "unidade",
             "usuario", "tipo_procedimento", "descricao_replace"]

    def __init__(self, events):
        self._events = events
        self.description = [(c,) for c in self._COLS]

    def execute(self, sql, params=None):
        self._events.append("trino_execute")

    def fetchall(self):
        self._events.append("trino_fetchall")
        return [
            (1, "P1", "2025-01-01T10:00:00", "SEAD-PI/GAB", "user", "contratacao",
             "Processo gerado"),
            (2, "P1", "2025-01-02T10:00:00", "SEAD-PI/GAB", "user", "contratacao",
             "Conclusão do processo"),
        ]

    def close(self):
        self._events.append("trino_cursor_close")


class _FakeConn:
    def __init__(self, events):
        self._events = events

    def cursor(self):
        return _FakeCursor(self._events)

    def close(self):
        self._events.append("trino_conn_close")


class _FakeWriter:
    def __init__(self, events):
        self._events = events

    def execute_template(self, *a, **k):
        self._events.append("neo4j_write")

    def write_edges(self, *a, **k):
        self._events.append("neo4j_write")

    def write_nodes(self, *a, **k):
        self._events.append("neo4j_write")


def test_trino_fully_read_and_released_before_any_neo4j_write():
    events: list[str] = []
    original = atividades.make_trino_conn
    atividades.make_trino_conn = lambda settings: _FakeConn(events)
    try:
        total, stats, _unclassified, _unidades = atividades.process_chunk(
            ["P1"], _FakeWriter(events), dry_run=False, batch_size=500, settings=object(),
        )
    finally:
        atividades.make_trino_conn = original

    assert total == 2
    assert "trino_fetchall" in events and "neo4j_write" in events
    first_write = events.index("neo4j_write")
    assert events.index("trino_conn_close") < first_write, (
        f"Neo4j write happened while Trino was still open: {events}"
    )


def test_load_batch_writes_nodes_before_dimension_edges():
    calls: list[str] = []

    class _RecordingWriter:
        def execute_template(self, name, *a, **k):
            calls.append(name)

        def write_edges(self, rel_type, *a, **k):
            calls.append("EDGE:" + rel_type)

        def write_nodes(self, *a, **k):
            calls.append("write_nodes")

    batch = [{
        "source_id": 1, "protocolo_formatado": "P1", "data_hora": "2025-01-01T10:00:00",
        "descricao": "x", "tipo_acao": "GERACAO-PROCEDIMENTO", "grupo": "abertura",
        "ref_id": None, "seq": 1, "unidade": "SEAD-PI/X", "usuario": "u",
        "source_unidade": "SEAD-PI/Y",
        "doc_info": {"numero": "123", "tipo": "OFICIO", "serie_id": None},
    }]
    atividades.load_atividades_batch(_RecordingWriter(), batch)

    assert calls[0] == "load_atividade_nodes"
    for dim in ("load_unidade_edges", "load_tipo_acao_edges", "load_usuario_edges", "load_documento_edges"):
        assert dim in calls, f"missing {dim}"
        assert calls.index("load_atividade_nodes") < calls.index(dim)
    assert not any(c.startswith("EDGE:") for c in calls)


def test_dimension_statements_touch_a_single_shared_dimension():
    from ..core import cypher as c
    u, t, s = c.LOAD_UNIDADE_EDGES_CYPHER, c.LOAD_TIPO_ACAO_EDGES_CYPHER, c.LOAD_USUARIO_EDGES_CYPHER
    assert "Unidade" in u and "TipoAcao" not in u and "Usuario" not in u
    assert "TipoAcao" in t and "Unidade" not in t and "Usuario" not in t
    assert "Usuario" in s and "Unidade" not in s and "TipoAcao" not in s


def test_no_writes_when_trino_returns_nothing():
    events: list[str] = []

    class _EmptyCursor(_FakeCursor):
        def fetchall(self):
            self._events.append("trino_fetchall")
            return []

    class _EmptyConn(_FakeConn):
        def cursor(self):
            return _EmptyCursor(self._events)

    original = atividades.make_trino_conn
    atividades.make_trino_conn = lambda settings: _EmptyConn(events)
    try:
        total, _stats, _unc, _uni = atividades.process_chunk(
            ["P1"], _FakeWriter(events), dry_run=False, batch_size=500, settings=object(),
        )
    finally:
        atividades.make_trino_conn = original

    assert total == 0
    assert "neo4j_write" not in events
