
from __future__ import annotations

from ..model.classifier import extract_source_unidade


def test_source_unidade_with_internal_space_is_not_truncated():
    txt = "Processo remetido pela unidade SEAD-PI/DL /DLASSESSORIA4"
    assert extract_source_unidade(txt) == "SEAD-PI/DL /DLASSESSORIA4"


def test_source_unidade_simple_unchanged():
    assert (
        extract_source_unidade("Processo remetido pela unidade SEAD-PI/GABINETE")
        == "SEAD-PI/GABINETE"
    )


def test_source_unidade_trailing_whitespace_stripped():
    assert (
        extract_source_unidade("Processo remetido pela unidade SEAD-PI/GAB/SLC   ")
        == "SEAD-PI/GAB/SLC"
    )


def test_source_unidade_none_when_no_match():
    assert extract_source_unidade("Processo recebido na unidade") is None
    assert extract_source_unidade(None) is None
