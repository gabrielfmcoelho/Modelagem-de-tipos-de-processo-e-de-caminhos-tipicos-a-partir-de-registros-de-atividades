
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any


class ReaderError(RuntimeError):
    pass


@dataclass
class ProcessoTimeline:
    protocolo_formatado: str
    activities: list[dict[str, Any]]


class GraphReader(ABC):


    def __enter__(self) -> GraphReader:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    @abstractmethod
    def close(self) -> None:
        pass


    @abstractmethod
    def count_processos(self) -> int:
        pass

    @abstractmethod
    def iter_processo_batches(
        self, *, batch_size: int = 500,
    ) -> Iterator[list[ProcessoTimeline]]:
        pass
