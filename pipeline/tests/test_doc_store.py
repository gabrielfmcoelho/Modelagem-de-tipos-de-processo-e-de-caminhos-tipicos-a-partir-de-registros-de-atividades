from __future__ import annotations

import json

from ..core.doc_store import FsDocumentStore, OutcomeLedger


def test_fs_store_put_then_exists(tmp_path):
    store = FsDocumentStore(tmp_path)
    assert store.exists("00002.000001/2025-10", "D1") is False
    loc = store.put("00002.000001/2025-10", "D1", "of.pdf", b"hello")
    assert store.exists("00002.000001/2025-10", "D1") is True
    assert (tmp_path / "00002.000001_2025-10" / "D1" / "of.pdf").read_bytes() == b"hello"
    assert loc.endswith("00002.000001_2025-10/D1/of.pdf")


def test_fs_store_exists_false_for_empty_dir(tmp_path):
    store = FsDocumentStore(tmp_path)
    (tmp_path / "P" / "D1").mkdir(parents=True)
    assert store.exists("P", "D1") is False


def test_ledger_terminal_vs_transient(tmp_path):
    led = OutcomeLedger(tmp_path / "_download_log.ndjson")
    assert led.seen_terminal("P", "D1") is None
    led.record("P", "D1", "cancelled", http=422, detail="foi cancelado", ts="t0")
    led.record("P", "D2", "failed", ts="t1")
    led.record("P", "D3", "ok", unidades_tried=["U1"], ts="t2")
    assert led.seen_terminal("P", "D1") == "cancelled"
    assert led.seen_terminal("P", "D2") is None
    assert led.seen_terminal("P", "D3") == "ok"


def test_ledger_reloads_terminal_from_disk(tmp_path):
    p = tmp_path / "log.ndjson"
    OutcomeLedger(p).record("P", "D1", "cancelled", ts="t")
    assert OutcomeLedger(p).seen_terminal("P", "D1") == "cancelled"


def test_ledger_writes_valid_ndjson(tmp_path):
    p = tmp_path / "log.ndjson"
    led = OutcomeLedger(p)
    led.record("P", "D1", "ok", unidades_tried=["U1", "U2"], http=200, ts="t")
    rec = json.loads(p.read_text().splitlines()[0])
    assert rec["protocolo"] == "P" and rec["doc"] == "D1" and rec["status"] == "ok"
    assert rec["unidades_tried"] == ["U1", "U2"] and rec["http"] == 200


def test_ledger_record_defaults_timestamp(tmp_path):
    p = tmp_path / "log.ndjson"
    OutcomeLedger(p).record("P", "D1", "ok")
    rec = json.loads(p.read_text().splitlines()[0])
    assert rec["ts"]
