
from __future__ import annotations


def parent_unidade(sigla: str) -> str | None:
    parts = sigla.split("/")
    if len(parts) <= 1:
        return None
    return "/".join(parts[:-1])


def all_ancestor_unidades(sigla: str) -> list[str]:
    ancestors: list[str] = []
    current = sigla
    while True:
        parent = parent_unidade(current)
        if parent is None:
            break
        ancestors.append(parent)
        current = parent
    return ancestors
