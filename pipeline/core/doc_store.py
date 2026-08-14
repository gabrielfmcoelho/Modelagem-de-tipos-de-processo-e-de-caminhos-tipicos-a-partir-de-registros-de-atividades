from __future__ import annotations

import json
import threading
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path


def _safe(protocolo: str) -> str:
    return protocolo.replace("/", "_")


class DocumentStore(ABC):

    @abstractmethod
    def exists(self, protocolo: str, doc_numero: str) -> bool:
        pass

    @abstractmethod
    def put(self, protocolo: str, doc_numero: str, filename: str, content: bytes) -> str:
        pass


class FsDocumentStore(DocumentStore):

    def __init__(self, base_dir: Path | str) -> None:
        self.base = Path(base_dir)

    def _doc_dir(self, protocolo: str, doc_numero: str) -> Path:
        return self.base / _safe(protocolo) / doc_numero

    def exists(self, protocolo: str, doc_numero: str) -> bool:
        d = self._doc_dir(protocolo, doc_numero)
        return d.exists() and any(d.iterdir())

    def put(self, protocolo: str, doc_numero: str, filename: str, content: bytes) -> str:
        d = self._doc_dir(protocolo, doc_numero)
        d.mkdir(parents=True, exist_ok=True)
        path = d / filename
        path.write_bytes(content)
        return str(path)


_TERMINAL = frozenset({"ok", "cancelled"})


class OutcomeLedger:

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()
        self._terminal: dict[tuple[str, str], str] = self._load_terminal()

    def _load_terminal(self) -> dict[tuple[str, str], str]:
        seen: dict[tuple[str, str], str] = {}
        if not self.path.exists():
            return seen
        with self.path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("status") in _TERMINAL:
                    seen[(rec.get("protocolo"), rec.get("doc"))] = rec["status"]
        return seen

    def seen_terminal(self, protocolo: str, doc_numero: str) -> str | None:
        return self._terminal.get((protocolo, doc_numero))

    def record(
        self,
        protocolo: str,
        doc_numero: str,
        status: str,
        *,
        ts: str | None = None,
        http: int | None = None,
        unidades_tried: list[str] | None = None,
        detail: str | None = None,
    ) -> None:
        rec = {
            "ts": ts or datetime.now(UTC).isoformat(timespec="seconds"),
            "protocolo": protocolo,
            "doc": doc_numero,
            "status": status,
            "http": http,
            "unidades_tried": unidades_tried or [],
            "detail": detail,
        }
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if status in _TERMINAL:
                self._terminal[(protocolo, doc_numero)] = status
