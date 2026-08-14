
from __future__ import annotations

import unicodedata

from ..core.text import collapse_whitespace, normalize, strip_accents


def _legacy_normalize(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    without_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    return " ".join(without_accents.lower().split())


def test_normalize_matches_legacy_on_fixed_corpus() -> None:
    samples = [
        "JACYLENNE COELHO BEZERRA",
        "Jacylenne Coêlho",
        "  João   da Silva  ",
        "SEAD-PI/GAB/SGACG",
        "Secretário de Administração",
        "R$ 3.441,36",
        "Contrato nº 15/2024",
        "",
        "   ",
        "ÁÉÍÓÚáéíóúÇç",
        "Tabs\tand\nnewlines",
    ]
    for s in samples:
        assert normalize(s) == _legacy_normalize(s), f"mismatch for {s!r}"


def test_strip_accents() -> None:
    assert strip_accents("Coêlho") == "Coelho"
    assert strip_accents("ação") == "acao"
    assert strip_accents("ABC") == "ABC"


def test_collapse_whitespace() -> None:
    assert collapse_whitespace("  a   b  c ") == "a b c"
    assert collapse_whitespace("a\tb\nc") == "a b c"
    assert collapse_whitespace("") == ""


def test_normalize_is_idempotent() -> None:
    s = normalize("  JOÃO DA Silva  ")
    assert normalize(s) == s
