from pathlib import Path

from pipeline.apps.status import _count_parsed_docs


def _make_doc(root: Path, doc_id: str):
    d = root / doc_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "text.txt").write_text("x", encoding="utf-8")


def test_count_parsed_docs(tmp_path: Path):
    _make_doc(tmp_path, "a")
    _make_doc(tmp_path, "b")
    (tmp_path / "no_text").mkdir()
    assert _count_parsed_docs(tmp_path) == 2


def test_count_parsed_docs_missing_dir_returns_negative(tmp_path: Path):
    assert _count_parsed_docs(tmp_path / "nope") == -1
