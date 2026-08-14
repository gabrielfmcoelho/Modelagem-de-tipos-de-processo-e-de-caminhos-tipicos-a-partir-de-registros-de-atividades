
from __future__ import annotations

from pipeline.stages.embed import _hash_for, _iter_parsed_docs


def test_hash_for_deterministic():
    h1 = _hash_for("texto", "BAAI/bge-m3")
    h2 = _hash_for("texto", "BAAI/bge-m3")
    assert h1 == h2 and len(h1) == 64


def test_hash_for_changes_when_text_changes():
    a = _hash_for("a", "m")
    b = _hash_for("b", "m")
    assert a != b


def test_hash_for_changes_when_model_changes():
    a = _hash_for("a", "m1")
    b = _hash_for("a", "m2")
    assert a != b


def _make_doc(root, doc_id, text):
    d = root / doc_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "text.txt").write_text(text, encoding="utf-8")


def test_iter_parsed_docs_skips_empty(tmp_path):
    _make_doc(tmp_path, "doc1", "hello")
    _make_doc(tmp_path, "empty", "   \n  ")
    _make_doc(tmp_path, "doc2", "world")
    out = list(_iter_parsed_docs(tmp_path))
    assert len(out) == 2
    assert {n for n, _ in out} == {"doc1", "doc2"}


def test_iter_parsed_docs_yields_text_content(tmp_path):
    _make_doc(tmp_path, "x", "Olá mundo SEI")
    out = dict(_iter_parsed_docs(tmp_path))
    assert out["x"] == "Olá mundo SEI"


def test_iter_parsed_docs_ignores_folders_without_text(tmp_path):
    _make_doc(tmp_path, "x", "yes")
    (tmp_path / "meta_only").mkdir()
    (tmp_path / "meta_only" / "metadata.json").write_text("{}", encoding="utf-8")
    out = list(_iter_parsed_docs(tmp_path))
    assert len(out) == 1


def test_iter_parsed_docs_anon_variant(tmp_path):
    _make_doc(tmp_path, "d1", "texto cru com CPF")
    (tmp_path / "d1" / "text_anon.txt").write_text("texto limpo <CPF_ab12>", encoding="utf-8")
    _make_doc(tmp_path, "d2", "sem versão anon")
    out = dict(_iter_parsed_docs(tmp_path, variant="anon"))
    assert out == {"d1": "texto limpo <CPF_ab12>"}


def test_hash_for_changes_when_variant_changes_content():
    assert _hash_for("texto cru", "m") != _hash_for("texto <PESSOA_ab12>", "m")
