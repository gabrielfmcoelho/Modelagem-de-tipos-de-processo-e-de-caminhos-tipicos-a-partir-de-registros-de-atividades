from __future__ import annotations

import json as _json
from pathlib import Path

from ..core._stage_base import RunContext
from ..core.config import Settings
from pipeline.stages import evaluate as ev


def test_needs_evaluation():
    assert ev._needs_evaluation({}, force=False) is True
    assert ev._needs_evaluation({"topic": ""}, force=False) is True
    assert ev._needs_evaluation({"topic": "X"}, force=False) is False
    assert ev._needs_evaluation({"topic": "X"}, force=True) is True


def test_parse_llm_json_fenced():
    raw = '```json\n{"topic": "Licitação", "summary": "Pedido de dados."}\n```'
    topic, summary, status = ev._parse_llm_json(raw)
    assert (topic, summary, status) == ("Licitação", "Pedido de dados.", "ok")


def test_parse_llm_json_plain():
    topic, summary, status = ev._parse_llm_json('{"topic":"T","summary":"S"}')
    assert (topic, summary, status) == ("T", "S", "ok")


def test_parse_llm_json_degrades_on_garbage():
    topic, summary, status = ev._parse_llm_json("isto não é json\n\nsegundo parágrafo")
    assert status == "degraded"
    assert topic == ev.SENTINEL_TOPIC
    assert summary == "isto não é json"


def test_merge_evaluation_preserves_existing_keys():
    meta = {"documento_numero": "D1", "protocolo": "P"}
    out = ev._merge_evaluation(meta, "T", "S", "model-x", "ok")
    assert out["documento_numero"] == "D1" and out["protocolo"] == "P"
    assert out["topic"] == "T" and out["summary"] == "S"
    assert out["evaluation_modelo"] == "model-x" and out["evaluation_status"] == "ok"
    assert "evaluated_at" in out
    assert meta == {"documento_numero": "D1", "protocolo": "P"}


class FakeWriter:
    def __init__(self):
        self.templates = []
    def open_phase(self, phase): pass
    def close_phase(self, phase): pass
    def execute_template(self, name, cypher, params, *, phase):
        self.templates.append((name, params))
        return len(params.get("rows", []))


def _doc(root: Path, doc_id: str, text: str, meta: dict):
    d = root / doc_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "text.txt").write_text(text, encoding="utf-8")
    (d / "metadata.json").write_text(_json.dumps(meta), encoding="utf-8")


def _ctx(tmp_path, *, writer=None, mode="fs", evaluator=None, force=False, load_existing=None):
    return RunContext(
        settings=Settings.from_env(),
        mode=mode,
        flags={"input": str(tmp_path), "force": force,
               "_evaluator": evaluator, "_model": "test-model",
               **({} if load_existing is None else {"load_existing": load_existing})},
        state_dir=tmp_path,
        writer=writer,
    )


def test_run_writes_topic_summary_to_json(tmp_path):
    _doc(tmp_path, "D1", "corpo do documento", {"documento_numero": "D1"})

    def stub(text, meta):
        return ("Tópico X", "Resumo Y", "ok")

    ev.run(_ctx(tmp_path, evaluator=stub))
    meta = _json.loads((tmp_path / "D1" / "metadata.json").read_text(encoding="utf-8"))
    assert meta["topic"] == "Tópico X"
    assert meta["summary"] == "Resumo Y"
    assert meta["documento_numero"] == "D1"


def test_run_skips_already_evaluated(tmp_path):
    _doc(tmp_path, "D1", "x", {"topic": "já tem"})
    calls = []

    def stub(text, meta):
        return calls.append(1) or ("a", "b", "ok")

    ctx = _ctx(tmp_path, evaluator=stub)
    ev.run(ctx)
    assert calls == []
    assert ctx.cache["evaluate_summary"]["skipped"] == 1


def test_run_force_string_true_reevaluates_all(tmp_path):
    _doc(tmp_path, "D1", "x", {"topic": "já tem"})
    calls = []

    def stub(text, meta):
        calls.append(1)
        return ("novo", "b", "ok")

    ctx = _ctx(tmp_path, evaluator=stub, force="true")
    ev.run(ctx)
    assert calls == [1]
    assert ctx.cache["evaluate_summary"]["evaluated"] == 1
    meta = _json.loads((tmp_path / "D1" / "metadata.json").read_text(encoding="utf-8"))
    assert meta["topic"] == "novo"


def test_run_force_string_false_does_not_force(tmp_path):
    _doc(tmp_path, "D1", "x", {"topic": "já tem"})
    calls = []

    def stub(text, meta):
        calls.append(1)
        return ("a", "b", "ok")

    ctx = _ctx(tmp_path, evaluator=stub, force="false")
    ev.run(ctx)
    assert calls == []
    assert ctx.cache["evaluate_summary"]["skipped"] == 1


def test_load_existing_string_false_stays_off(tmp_path):
    _doc(tmp_path, "D1", "x", {"topic": "T", "summary": "S"})
    w = FakeWriter()
    ctx = _ctx(tmp_path, writer=w, mode="neo4j", evaluator=lambda t, m: ("a", "b", "ok"))
    ctx.flags["load_existing"] = "false"
    ev.run(ctx)
    assert w.templates == []


def test_run_loads_rows_into_writer(tmp_path):
    _doc(tmp_path, "D1", "x", {})
    w = FakeWriter()

    def stub(text, meta):
        return ("T", "S", "ok")

    ev.run(_ctx(tmp_path, writer=w, mode="neo4j", evaluator=stub))
    assert w.templates, "no graph write happened"
    name, params = w.templates[0]
    assert name == "load_documento_evaluation"
    row = params["rows"][0]
    assert row["documento_numero"] == "D1"
    assert row["topic"] == "T"
    assert row["summary"] == "S"
    assert row["status"] == "ok"
    assert row["modelo"] == "test-model"
    assert "computed_at" in row


def test_evaluation_cypher_sets_status():
    from ..core.cypher import LOAD_DOCUMENTO_EVALUATION_CYPHER as C
    assert "r.status" in C
    assert "d.evaluation_status" in C


def test_load_existing_pushes_skipped_evals_to_graph_without_llm(tmp_path):
    _doc(tmp_path, "D1", "x", {
        "topic": "Tópico pronto", "summary": "Resumo pronto",
        "evaluation_modelo": "old-model", "evaluation_status": "ok",
    })
    w = FakeWriter()
    calls = []

    def stub(text, meta):
        return calls.append(1) or ("nao", "deve", "rodar")

    ctx = _ctx(tmp_path, writer=w, mode="neo4j", evaluator=stub)
    ctx.flags["load_existing"] = True
    ev.run(ctx)
    assert calls == []
    assert ctx.cache["evaluate_summary"]["skipped"] == 1
    assert w.templates, "load_existing did not write the existing eval to the graph"
    row = w.templates[0][1]["rows"][0]
    assert row["documento_numero"] == "D1"
    assert row["topic"] == "Tópico pronto"
    assert row["summary"] == "Resumo pronto"
    assert row["modelo"] == "old-model"


def test_skipped_docs_are_resynced_to_neo4j_by_default(tmp_path):
    _doc(tmp_path, "D1", "x", {"topic": "já tem", "summary": "s"})
    w = FakeWriter()

    def stub(text, meta):
        raise AssertionError("must not re-evaluate a document that already has a topic")

    ev.run(_ctx(tmp_path, writer=w, mode="neo4j", evaluator=stub))
    rows = [r for name, params in w.templates if name == "load_documento_evaluation"
            for r in params["rows"]]
    assert [r["topic"] for r in rows] == ["já tem"]


def test_load_existing_can_be_turned_off(tmp_path):
    _doc(tmp_path, "D1", "x", {"topic": "já tem", "summary": "s"})
    w = FakeWriter()
    ev.run(_ctx(tmp_path, writer=w, mode="neo4j", evaluator=lambda t, m: ("a", "b", "ok"),
                load_existing="false"))
    assert not w.templates


def test_run_parallel_workers_evaluates_all(tmp_path):
    import threading
    for i in range(6):
        _doc(tmp_path, f"D{i}", f"corpo {i}", {})
    lock = threading.Lock()
    calls = []

    def stub(text, meta):
        with lock:
            calls.append(text)
        return ("T", "S", "ok")

    ctx = _ctx(tmp_path, evaluator=stub)
    ctx.flags["workers"] = "3"
    ev.run(ctx)
    assert ctx.cache["evaluate_summary"]["evaluated"] == 6
    assert len(calls) == 6
    for i in range(6):
        meta = _json.loads((tmp_path / f"D{i}" / "metadata.json").read_text(encoding="utf-8"))
        assert meta["topic"] == "T" and meta["evaluation_status"] == "ok"


def test_run_parallel_counts_failures(tmp_path):
    _doc(tmp_path, "OK", "corpo bom", {})
    _doc(tmp_path, "BAD", "EXPLODE", {})

    def stub(text, meta):
        if text == "EXPLODE":
            raise RuntimeError("boom")
        return ("T", "S", "ok")

    ctx = _ctx(tmp_path, evaluator=stub)
    ctx.flags["workers"] = "4"
    ev.run(ctx)
    s = ctx.cache["evaluate_summary"]
    assert s["evaluated"] == 1 and s["failed"] == 1


def test_run_text_variant_anon_reads_anon_text(tmp_path):
    _doc(tmp_path, "D1", "texto cru", {"documento_numero": "D1"})
    (tmp_path / "D1" / "text_anon.txt").write_text("texto anonimizado", encoding="utf-8")
    _doc(tmp_path, "D2", "sem anon", {"documento_numero": "D2"})
    seen = []

    def stub(text, meta):
        seen.append(text)
        return ("T", "S", "ok")

    ctx = _ctx(tmp_path, evaluator=stub)
    ctx.flags["text_variant"] = "anon"
    ev.run(ctx)
    assert seen == ["texto anonimizado"]
    assert ctx.cache["evaluate_summary"]["total"] == 1


def test_system_prompt_forbids_pii():
    assert "dados pessoais" in ev.SYSTEM_PROMPT
    assert "<PESSOA_ab12cd34>" in ev.SYSTEM_PROMPT


def test_load_existing_defaults_on_so_an_arm_switch_resyncs_neo4j():
    import inspect
    from pipeline.stages import evaluate as ev
    src = inspect.getsource(ev.run)
    assert '_truthy(ctx.flags.get("load_existing", True))' in src, (
        "on-disk evaluations must be pushed to Neo4j by default, else switching text arms "
        "leaves :Documento.topic stale and the topic feature block silently zeroes"
    )


def test_processo_embed_refuses_an_all_zero_topic_block():
    from pathlib import Path
    src = Path("pipeline/stages/processo_embed.py").read_text(encoding="utf-8")
    assert "if pending and n_topic == 0:" in src
    assert "would be all zeros" in src
