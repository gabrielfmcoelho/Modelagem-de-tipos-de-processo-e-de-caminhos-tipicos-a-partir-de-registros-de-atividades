from __future__ import annotations

from pipeline.stages import precreate


class FakeWriter:

    def __init__(self):
        self.nodes = []
        self.edges = []
        self.templates = []

    def open_phase(self, phase): pass
    def close_phase(self, phase): pass

    def write_nodes(self, label, key_fields, rows, *, phase, props=None):
        rows = list(rows)
        self.nodes.append((label, list(key_fields), rows, props))
        return len(rows)

    def write_edges(self, rel_type, from_label, from_key, to_label, to_key, rows, *, phase, props=None):
        rows = list(rows)
        self.edges.append((rel_type, rows))
        return len(rows)

    def execute_template(self, name, cypher, params, *, phase):
        self.templates.append((name, params))
        return 1


def _unidade_rows(w):
    for label, _keys, rows, props in w.nodes:
        if label == "Unidade":
            return rows, props
    raise AssertionError("Unidade nodes were never written")


def _processo_rows(w):
    out = []
    for name, params in w.templates:
        if name == "precreate_processos":
            out.extend(params["rows"])
    return out


PROCESSOS = [
    {"protocolo_formatado": "00002.000001/2025-10", "data_hora": "2025-01-02T09:00:00",
     "unidade": "SEAD-PI/GAB", "usuario": "ana@x", "tipo_procedimento": "Oficio",
     "id_processo": 4242},
]
USER_ORGAO = {"ana@x": "SEAD-PI"}


def test_unidade_id_comes_from_data_not_csv():
    w = FakeWriter()
    precreate.precreate_shared_nodes(
        w, PROCESSOS, {"SEAD-PI/GAB", "SEAD-PI/SGACG"}, USER_ORGAO,
        unidade_ids={"SEAD-PI/GAB": 110001, "SEAD-PI/SGACG": 110002},
    )
    rows, props = _unidade_rows(w)
    by_sigla = {r["sigla"]: r for r in rows}
    assert by_sigla["SEAD-PI/GAB"]["id_unidade"] == 110001
    assert by_sigla["SEAD-PI/SGACG"]["id_unidade"] == 110002
    assert props == ["id_unidade"]
    assert "descricao" not in by_sigla["SEAD-PI/GAB"]


def test_unidade_without_source_id_gets_none():
    w = FakeWriter()
    precreate.precreate_shared_nodes(
        w, PROCESSOS, {"SEAD-PI/GAB", "DERIVED/UNIT"}, USER_ORGAO,
        unidade_ids={"SEAD-PI/GAB": 110001},
    )
    rows, _ = _unidade_rows(w)
    by_sigla = {r["sigla"]: r for r in rows}
    assert by_sigla["DERIVED/UNIT"]["id_unidade"] is None


def test_processo_carries_id_processo():
    w = FakeWriter()
    precreate.precreate_shared_nodes(
        w, PROCESSOS, {"SEAD-PI/GAB"}, USER_ORGAO, unidade_ids={"SEAD-PI/GAB": 110001},
    )
    rows = _processo_rows(w)
    assert rows and rows[0]["id_processo"] == 4242
    assert rows[0]["protocolo_formatado"] == "00002.000001/2025-10"


def test_csv_helpers_removed():
    assert not hasattr(precreate, "_load_unidade_csv")
    assert not hasattr(precreate, "_default_csv_path")


def test_precreate_ensures_schema_constraints():
    from ..core.cypher import SETUP_CONSTRAINTS
    w = FakeWriter()
    precreate.precreate_shared_nodes(
        w, PROCESSOS, {"SEAD-PI/GAB"}, USER_ORGAO, unidade_ids={"SEAD-PI/GAB": 110001},
    )
    n_setup = sum(1 for (name, _p) in w.templates if name == "setup_constraint")
    assert n_setup == len(SETUP_CONSTRAINTS)
