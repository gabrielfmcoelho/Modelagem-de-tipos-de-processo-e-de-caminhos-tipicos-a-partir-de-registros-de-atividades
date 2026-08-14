from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

TEXT_FILENAME = "text.txt"
META_FILENAME = "metadata.json"
ANON_TEXT_FILENAME = "text_anon.txt"
ANON_META_FILENAME = "anon_meta.json"

VARIANT_FILENAMES = {"raw": TEXT_FILENAME, "anon": ANON_TEXT_FILENAME}


@dataclass(frozen=True)
class ParsedDoc:
    doc_id: str
    text_path: Path
    meta_path: Path


def doc_dir(parsed_dir, doc_id: str) -> Path:
    return Path(parsed_dir) / doc_id


def text_path(parsed_dir, doc_id: str) -> Path:
    return doc_dir(parsed_dir, doc_id) / TEXT_FILENAME


def meta_path(parsed_dir, doc_id: str) -> Path:
    return doc_dir(parsed_dir, doc_id) / META_FILENAME


def anon_text_path(parsed_dir, doc_id: str) -> Path:
    return doc_dir(parsed_dir, doc_id) / ANON_TEXT_FILENAME


def anon_meta_path(parsed_dir, doc_id: str) -> Path:
    return doc_dir(parsed_dir, doc_id) / ANON_META_FILENAME


def iter_parsed_documents(parsed_dir, variant: str = "raw") -> Iterator[ParsedDoc]:
    filename = VARIANT_FILENAMES.get(variant)
    if filename is None:
        raise ValueError(f"unknown text variant: {variant!r} (expected 'raw' or 'anon')")
    parsed_dir = Path(parsed_dir)
    if not parsed_dir.is_dir():
        return
    for sub in sorted(parsed_dir.iterdir()):
        if not sub.is_dir():
            continue
        tp = sub / filename
        if not tp.is_file():
            continue
        yield ParsedDoc(doc_id=sub.name, text_path=tp, meta_path=sub / META_FILENAME)
