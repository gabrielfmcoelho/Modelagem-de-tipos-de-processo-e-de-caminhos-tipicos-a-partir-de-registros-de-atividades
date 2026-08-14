from __future__ import annotations

from .process_state import CONCLUSION_TYPES

END = "<END>"


def state_tipo(state: str) -> str:
    return (state or "").split("@", 1)[0]


def is_conclusion_state(state: str) -> bool:
    return state_tipo(state) in CONCLUSION_TYPES
