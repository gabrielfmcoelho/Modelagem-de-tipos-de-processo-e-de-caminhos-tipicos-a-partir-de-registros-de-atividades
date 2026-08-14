
from __future__ import annotations


def extract_orgao(unidade: str | None) -> str:
    if not unidade:
        return "DESCONHECIDO"
    return unidade.split("/")[0]
