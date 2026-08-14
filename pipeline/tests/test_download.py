from __future__ import annotations

import argparse

import pytest

from ..core import sei_client
from ..core.config import Settings
from pipeline.stages import download


def _doc(numero, ordem):
    return {"numero": numero, "tipo": "pdf", "ordem": ordem}


def test_orders_docs_by_first_reference():
    docs = [_doc("D2", "2025-03-01T10:00:00"),
            _doc("D1", "2025-01-01T10:00:00"),
            _doc("D3", "2025-02-01T10:00:00")]
    out = download._order_and_limit_docs(docs, only_first_doc=False)
    assert [d["numero"] for d in out] == ["D1", "D3", "D2"]


def test_only_first_doc_keeps_the_initiating_document():
    docs = [_doc("D2", "2025-03-01T10:00:00"), _doc("D1", "2025-01-01T10:00:00")]
    out = download._order_and_limit_docs(docs, only_first_doc=True)
    assert [d["numero"] for d in out] == ["D1"]


def test_docs_without_timestamp_sort_last():
    docs = [_doc("DX", None), _doc("D1", "2025-01-01T10:00:00")]
    out = download._order_and_limit_docs(docs, only_first_doc=False)
    assert [d["numero"] for d in out] == ["D1", "DX"]
    assert download._order_and_limit_docs(docs, only_first_doc=True)[0]["numero"] == "D1"


def test_empty_doc_list_is_safe():
    assert download._order_and_limit_docs([], only_first_doc=True) == []


def test_query_orders_documents_by_reference_time():
    for q in (download.QUERY_PROCESSOS_BY_ORGAO, download.QUERY_PROCESSOS_BY_PROTOCOLO):
        assert "REFERENCIA_DOCUMENTO" in q
        assert "ordem" in q


def test_download_document_uses_default_sei_base_url(monkeypatch):
    seen = {}

    def _fake_request(client, url, headers, params):
        seen["url"] = url
        resp = type("R", (), {"status_code": 200, "headers": {}, "content": b"x", "text": ""})()
        return resp

    monkeypatch.setattr(sei_client, "_sei_request", _fake_request)
    sei_client.download_document(object(), "tok", "42", "D1")
    assert seen["url"] == f"{download.DEFAULT_SEI_BASE_URL}/unidades/42/documentos/baixar"


def test_download_document_uses_configured_sei_base_url(monkeypatch):
    seen = {}

    def _fake_request(client, url, headers, params):
        seen["url"] = url
        resp = type("R", (), {"status_code": 200, "headers": {}, "content": b"x", "text": ""})()
        return resp

    monkeypatch.setattr(sei_client, "_sei_request", _fake_request)
    sei_client.download_document(object(), "tok", "42", "D1", sei_base_url="https://custom.example/v1")
    assert seen["url"] == "https://custom.example/v1/unidades/42/documentos/baixar"


def _args(token=None, usuario=None, senha=None, orgao="SEAD-PI"):
    return argparse.Namespace(token=token, usuario=usuario, senha=senha, orgao=orgao)


def test_token_flag_beats_env():
    s = Settings(sei_token="ENVTOK", sei_api_user="u", sei_api_password="p")
    assert download.resolve_token(_args(token="FLAGTOK"), s) == "FLAGTOK"


def test_falls_back_to_env_token():
    assert download.resolve_token(_args(), Settings(sei_token="ENVTOK")) == "ENVTOK"


def test_falls_back_to_env_user_pass(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        sei_client, "sei_login",
        lambda u, p, o, sei_base_url=None: seen.update(u=u, p=p, o=o, sei_base_url=sei_base_url) or "MINTED")
    tok = download.resolve_token(_args(), Settings(sei_api_user="envuser", sei_api_password="envpass"))
    assert tok == "MINTED"
    assert seen == {"u": "envuser", "p": "envpass", "o": "SEAD-PI",
                     "sei_base_url": download.DEFAULT_SEI_BASE_URL}


def test_flag_user_pass_overrides_env(monkeypatch):
    seen = {}
    monkeypatch.setattr(sei_client, "sei_login", lambda u, p, o, sei_base_url=None: seen.setdefault("u", u) or "T")
    download.resolve_token(_args(usuario="flaguser", senha="flagpass"),
                           Settings(sei_api_user="envuser", sei_api_password="envpass"))
    assert seen["u"] == "flaguser"


def test_resolve_token_threads_configured_sei_base_url(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        sei_client, "sei_login",
        lambda u, p, o, sei_base_url=None: seen.update(sei_base_url=sei_base_url) or "T")
    download.resolve_token(
        _args(),
        Settings(sei_api_user="u", sei_api_password="p", sei_base_url="https://custom.example/v1"),
    )
    assert seen["sei_base_url"] == "https://custom.example/v1"


def test_no_credentials_anywhere_exits():
    with pytest.raises(SystemExit):
        download.resolve_token(_args(), Settings())


def _processo(docs, unidades=(("SEAD-PI/X", "1"),)):
    return {"protocolo": "PRC-1",
            "documentos": [{"numero": n} for n in docs],
            "unidades": [{"sigla": s, "id_unidade": i} for s, i in unidades],
            "doc_creators": {}}


def _store_and_ledger(tmp_path):
    from ..core.doc_store import FsDocumentStore, OutcomeLedger
    return FsDocumentStore(tmp_path), OutcomeLedger(tmp_path / "log.ndjson")


def test_skips_known_cancelled_docs(tmp_path, monkeypatch):
    store, ledger = _store_and_ledger(tmp_path)
    ledger.record("PRC-1", "DCANCEL", "cancelled", ts="t")
    attempted = []
    monkeypatch.setattr(download, "try_download_with_unidades",
        lambda c, t, numero, u, **k: (attempted.append(numero) or
            ({"filename": numero + ".pdf", "content": b"x", "tipo": "pdf"}, "U1", "ok")))
    stats = download.download_processo_docs(_processo(["DCANCEL", "DNEW"]), "tok", store, ledger)
    assert attempted == ["DNEW"]
    assert store.exists("PRC-1", "DNEW") and stats["downloaded"] == 1
    assert stats["skipped"] == 1


def test_records_cancelled_outcome(tmp_path, monkeypatch):
    store, ledger = _store_and_ledger(tmp_path)
    monkeypatch.setattr(download, "try_download_with_unidades", lambda *a, **k: (None, None, "cancelled"))
    stats = download.download_processo_docs(_processo(["D1"]), "tok", store, ledger)
    assert stats["cancelled"] == 1
    assert ledger.seen_terminal("PRC-1", "D1") == "cancelled"


def test_records_success_and_stores(tmp_path, monkeypatch):
    store, ledger = _store_and_ledger(tmp_path)
    monkeypatch.setattr(download, "try_download_with_unidades",
        lambda *a, **k: ({"filename": "f.pdf", "content": b"abc", "tipo": "pdf"}, "U1", "ok"))
    stats = download.download_processo_docs(_processo(["D1"]), "tok", store, ledger)
    assert stats["downloaded"] == 1 and store.exists("PRC-1", "D1")
    assert ledger.seen_terminal("PRC-1", "D1") == "ok"


def test_skips_already_on_disk(tmp_path, monkeypatch):
    store, ledger = _store_and_ledger(tmp_path)
    store.put("PRC-1", "D1", "existing.pdf", b"old")
    called = []
    monkeypatch.setattr(download, "try_download_with_unidades",
        lambda c, t, numero, u, **k: called.append(numero))
    stats = download.download_processo_docs(_processo(["D1"]), "tok", store, ledger)
    assert called == [] and stats["skipped"] == 1
