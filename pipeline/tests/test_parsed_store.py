from __future__ import annotations

from pathlib import Path

from ..core import parsed_store as ps


def test_path_helpers(tmp_path: Path):
    assert ps.text_path(tmp_path, "001") == tmp_path / "001" / "text.txt"
    assert ps.meta_path(tmp_path, "001") == tmp_path / "001" / "metadata.json"
    assert ps.doc_dir(tmp_path, "001") == tmp_path / "001"


def _make_doc(root: Path, doc_id: str, text: str = "x", with_meta: bool = True):
    d = root / doc_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "text.txt").write_text(text, encoding="utf-8")
    if with_meta:
        (d / "metadata.json").write_text("{}", encoding="utf-8")


def test_iter_yields_one_per_folder_sorted(tmp_path: Path):
    _make_doc(tmp_path, "b")
    _make_doc(tmp_path, "a")
    docs = list(ps.iter_parsed_documents(tmp_path))
    assert [d.doc_id for d in docs] == ["a", "b"]
    assert docs[0].text_path == tmp_path / "a" / "text.txt"
    assert docs[0].meta_path == tmp_path / "a" / "metadata.json"


def test_iter_skips_folder_without_text_and_loose_files(tmp_path: Path):
    _make_doc(tmp_path, "good")
    (tmp_path / "empty_dir").mkdir()
    (tmp_path / "loose.txt").write_text("nope", encoding="utf-8")
    docs = list(ps.iter_parsed_documents(tmp_path))
    assert [d.doc_id for d in docs] == ["good"]


def test_iter_missing_dir_is_empty(tmp_path: Path):
    assert list(ps.iter_parsed_documents(tmp_path / "nope")) == []
