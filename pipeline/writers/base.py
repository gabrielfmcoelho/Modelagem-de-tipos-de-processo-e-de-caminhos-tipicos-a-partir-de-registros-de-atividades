
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from typing import Any


class WriterError(RuntimeError):
    pass


class GraphWriter(ABC):


    def open_phase(self, phase: str) -> None:
        pass

    def close_phase(self, phase: str) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass

    def __enter__(self) -> GraphWriter:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


    @abstractmethod
    def write_nodes(
        self,
        label: str,
        key_fields: list[str],
        rows: Iterable[Mapping[str, Any]],
        *,
        phase: str,
        props: list[str] | None = None,
    ) -> int:
        pass

    @abstractmethod
    def write_edges(
        self,
        rel_type: str,
        from_label: str,
        from_key: Mapping[str, str],
        to_label: str,
        to_key: Mapping[str, str],
        rows: Iterable[Mapping[str, Any]],
        *,
        phase: str,
        props: list[str] | None = None,
    ) -> int:
        pass


    @abstractmethod
    def execute_template(
        self,
        name: str,
        cypher: str,
        params: Mapping[str, Any],
        *,
        phase: str,
    ) -> int:
        pass
