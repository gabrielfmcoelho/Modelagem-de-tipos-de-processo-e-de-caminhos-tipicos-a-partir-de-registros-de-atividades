from __future__ import annotations

import json
from pathlib import Path

import pytest

from ..core import parsed_store as ps
from ..core._stage_base import RunContext
from ..model.anonymize import AnonStats, placeholder
from ..core.config import Settings
from pipeline.stages import anonymize as an

VALID_CPF = "529.982.247-25"


def _doc(root: Path, doc_id: str, text: str, meta: dict | None = None):
    d = root / doc_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "text.txt").write_text(text, encoding="utf-8")
    (d / "metadata.json").write_text(json.dumps(meta or {}), encoding="utf-8")


def _ner(root: Path, doc_id: str, entities: dict):
    root.mkdir(parents=True, exist_ok=True)
    (root / f"{doc_id}.json").write_text(
        json.dumps({"documento_numero": doc_id, "entities": entities}, ensure_ascii=False),
        encoding="utf-8",
    )


def _ctx(parsed: Path, ner: Path, **flags) -> RunContext:
    return RunContext(
        settings=Settings.from_env(),
        mode="fs",
        flags={"input": str(parsed), "ner_dir": str(ner), **flags},
        state_dir=parsed,
    )


def test_run_writes_anon_files_and_keeps_raw(tmp_path: Path):
    parsed, ner = tmp_path / "parsed", tmp_path / "ner"
    raw = f"CPF {VALID_CPF} de Maria Souza Lima"
    _doc(parsed, "D1", raw)
    _ner(ner, "D1", {"pessoa": [{"text": "Maria Souza Lima", "canonical": "Maria Souza Lima"}]})

    ctx = _ctx(parsed, ner, verify="true")
    an.run(ctx)

    anon = ps.anon_text_path(parsed, "D1").read_text(encoding="utf-8")
    assert VALID_CPF not in anon and "Maria Souza Lima" not in anon
    assert placeholder("PESSOA", "Maria Souza Lima") in anon
    assert (parsed / "D1" / "text.txt").read_text(encoding="utf-8") == raw

    meta = json.loads(ps.anon_meta_path(parsed, "D1").read_text(encoding="utf-8"))
    assert meta["ner_available"] is True
    assert meta["replacements"] == {"CPF": 1, "PESSOA": 1}
    assert meta["residual_regex_hits"] == 0
    assert ctx.cache["anonymize_summary"]["processed"] == 1
    assert ctx.cache["anonymize_summary"]["residual_regex_hits"] == 0


def test_run_degrades_to_regex_only_without_ner_file(tmp_path: Path):
    parsed, ner = tmp_path / "parsed", tmp_path / "ner"
    _doc(parsed, "D1", f"CPF {VALID_CPF} de Maria Souza Lima")

    ctx = _ctx(parsed, ner, verify="true")
    an.run(ctx)

    anon = ps.anon_text_path(parsed, "D1").read_text(encoding="utf-8")
    assert VALID_CPF not in anon
    assert "Maria Souza Lima" in anon
    meta = json.loads(ps.anon_meta_path(parsed, "D1").read_text(encoding="utf-8"))
    assert meta["ner_available"] is False
    assert ctx.cache["anonymize_summary"]["degraded_regex_only"] == 1


def test_run_is_idempotent_and_skips_unchanged(tmp_path: Path):
    parsed, ner = tmp_path / "parsed", tmp_path / "ner"
    _doc(parsed, "D1", f"CPF {VALID_CPF}")

    an.run(_ctx(parsed, ner))
    first = ps.anon_text_path(parsed, "D1").read_text(encoding="utf-8")

    ctx2 = _ctx(parsed, ner)
    an.run(ctx2)
    assert ctx2.cache["anonymize_summary"]["skipped"] == 1
    assert ctx2.cache["anonymize_summary"]["processed"] == 0
    assert ps.anon_text_path(parsed, "D1").read_text(encoding="utf-8") == first


def test_run_reprocesses_when_source_changes(tmp_path: Path):
    parsed, ner = tmp_path / "parsed", tmp_path / "ner"
    _doc(parsed, "D1", f"CPF {VALID_CPF}")
    an.run(_ctx(parsed, ner))

    (parsed / "D1" / "text.txt").write_text("texto novo sem pii", encoding="utf-8")
    ctx = _ctx(parsed, ner)
    an.run(ctx)
    assert ctx.cache["anonymize_summary"]["processed"] == 1
    assert ps.anon_text_path(parsed, "D1").read_text(encoding="utf-8") == "texto novo sem pii"


def test_run_verify_raises_on_residual(tmp_path: Path, monkeypatch):
    parsed, ner = tmp_path / "parsed", tmp_path / "ner"
    _doc(parsed, "D1", f"CPF {VALID_CPF}")
    monkeypatch.setattr(an, "anonymize_text", lambda text, entities: (text, AnonStats()))

    with pytest.raises(RuntimeError, match="residual"):
        an.run(_ctx(parsed, ner, verify="true"))


def test_run_missing_parsed_dir(tmp_path: Path):
    ctx = _ctx(tmp_path / "nope", tmp_path / "ner")
    an.run(ctx)
    assert ctx.cache["anonymize_summary"]["error"] == "missing_dir"


def test_iter_variant_anon_only_yields_anonymized(tmp_path: Path):
    _doc(tmp_path, "A", "com anon")
    _doc(tmp_path, "B", "sem anon")
    ps.anon_text_path(tmp_path, "A").write_text("anon A", encoding="utf-8")

    raw = list(ps.iter_parsed_documents(tmp_path))
    anon = list(ps.iter_parsed_documents(tmp_path, variant="anon"))
    assert [d.doc_id for d in raw] == ["A", "B"]
    assert [d.doc_id for d in anon] == ["A"]
    assert anon[0].text_path == tmp_path / "A" / "text_anon.txt"
    assert anon[0].meta_path == tmp_path / "A" / "metadata.json"


def test_iter_variant_rejects_unknown(tmp_path: Path):
    with pytest.raises(ValueError, match="variant"):
        list(ps.iter_parsed_documents(tmp_path, variant="typo"))
