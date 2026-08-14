import json
from pathlib import Path

import pytest

from pipeline.stages.ner_extract import discover_parsed_documents


def _make(root: Path, doc_id: str, protocolo: str, text: str = "texto"):
    d = root / doc_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "text.txt").write_text(text, encoding="utf-8")
    (d / "metadata.json").write_text(
        json.dumps({"protocolo": protocolo, "source_file": "a.html"}), encoding="utf-8"
    )


def test_discover_reads_folder_and_metadata(tmp_path: Path):
    _make(tmp_path, "D1", "00002.000001/2025-10")
    docs = discover_parsed_documents(tmp_path)
    assert len(docs) == 1
    d = docs[0]
    assert d["documento_numero"] == "D1"
    assert d["protocolo"] == "00002.000001/2025-10"
    assert d["text_path"].read_text(encoding="utf-8") == "texto"


def test_discover_filters_by_protocolo_and_limit(tmp_path: Path):
    _make(tmp_path, "D1", "00002.000001/2025-10")
    _make(tmp_path, "D2", "00002.000002/2025-20")
    got = discover_parsed_documents(tmp_path, protocolos=["00002.000001_2025-10"])
    assert [d["documento_numero"] for d in got] == ["D1"]
    assert len(discover_parsed_documents(tmp_path, limit=1)) == 1


def test_discover_skips_folder_without_text(tmp_path: Path):
    (tmp_path / "empty").mkdir()
    assert discover_parsed_documents(tmp_path) == []


def test_discover_shards_partition_corpus(tmp_path: Path):
    for i in range(7):
        _make(tmp_path, f"D{i}", f"00002.00000{i}/2025-10")
    shards = [
        [d["documento_numero"] for d in discover_parsed_documents(tmp_path, shard=f"{k}/3")]
        for k in range(3)
    ]
    combined = sorted(doc for s in shards for doc in s)
    assert combined == [f"D{i}" for i in range(7)]
    assert all(shards)
    with pytest.raises(ValueError):
        discover_parsed_documents(tmp_path, shard="3/3")
