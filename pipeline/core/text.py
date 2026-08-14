
from __future__ import annotations

import unicodedata


def strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def collapse_whitespace(text: str) -> str:
    return " ".join(text.split())


def normalize(text: str) -> str:
    return collapse_whitespace(strip_accents(text).lower())
