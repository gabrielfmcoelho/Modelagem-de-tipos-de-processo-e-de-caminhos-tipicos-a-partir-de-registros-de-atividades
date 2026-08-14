
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from .config import Settings

Mode = Literal["neo4j", "json-emit", "json-replay", "fs"]

StageType = Literal["bootstrap", "core", "enrich", "op"]

Phase = Literal[
    "ingest",
    "graph",
    "documents",
    "features",
    "clustering",
    "typical-path",
    "evidence",
    "delivery",
    "operations",
]

PHASE_ORDER: tuple[Phase, ...] = (
    "ingest", "graph", "documents", "features", "clustering",
    "typical-path", "evidence", "delivery", "operations",
)

PHASE_QUESTION: dict[Phase, str] = {
    "ingest": "De onde vêm os eventos, e que recorte do log entra no estudo?",
    "graph": "Que grafo de processo o log de eventos descreve?",
    "documents": "O que dizem os documentos, e como ficam utilizáveis sem expor pessoas?",
    "features": "Que vetor representa cada processo?",
    "clustering": "Que tipos de processo emergem, e qual partição escolher?",
    "typical-path": "Qual é o caminho típico de cada tipo, e vale mais que uma linha de base?",
    "evidence": "Os números do artigo se sustentam quando confrontados com controles?",
    "delivery": "Como a evidência vira tabela, figura e texto?",
    "operations": "Como se opera, inspeciona e audita o próprio pipeline?",
}


@dataclass(frozen=True)
class StageMeta:

    name: str
    description: str
    type: StageType
    phase: Phase = "operations"
    depends_on: tuple[str, ...] = ()
    soft_depends_on: tuple[str, ...] = ()
    modes: tuple[Mode, ...] = ()
    can_skip_when_done: bool = True
    estimated_duration: str = ""
    question: str = ""
    deterministic: bool | str = True
    nondeterminism: str = ""


class StageProgress:

    def set_total(self, total: int) -> None:
        pass

    def advance(self, n: int = 1) -> None:
        pass


@dataclass
class RunContext:
    settings: Settings
    mode: Mode
    flags: dict[str, Any]
    state_dir: Path
    cache: dict[str, Any] = field(default_factory=dict)
    writer: Any | None = None
    reader: Any | None = None
    driver: Any | None = None
    progress: StageProgress = field(default_factory=StageProgress)

    def require_writer(self) -> Any:
        if self.writer is None:
            raise RuntimeError(
                f"Stage requires a GraphWriter but mode={self.mode!r} did not "
                f"build one. Set --mode neo4j or --mode json-emit."
            )
        return self.writer

    def require_reader(self) -> Any:
        if self.reader is None:
            raise RuntimeError(
                f"Stage requires a GraphReader but mode={self.mode!r} did not "
                f"build one. Set --mode neo4j or --mode json-replay."
            )
        return self.reader

    def require_driver(self) -> Any:
        if self.driver is None:
            raise RuntimeError(
                "Stage requires a raw Neo4j driver. Use --mode neo4j."
            )
        return self.driver

    def cached(self, key: str, factory: Callable[[], Any]) -> Any:
        if key not in self.cache:
            self.cache[key] = factory()
        return self.cache[key]


StageFunc = Callable[[RunContext], None]

_TRUE = {"1", "true", "yes", "y", "on", "sim"}


def truthy(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in _TRUE
