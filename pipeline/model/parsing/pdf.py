
import argparse
import base64
import json
import re
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

from ...core.deployment import ORGAO_DOMINIO, ORGAO_GOVERNO_CURTO

if TYPE_CHECKING:
    import pandas as pd

_HERE = Path(__file__).resolve()
_ROOT = next((p.parent for p in _HERE.parents if p.name == "pipeline"), _HERE.parents[2])
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ...core import parsed_store
from pipeline.cli import add_standard_args, resolve_settings
from ...core.config import Settings
from ...core.logging_setup import configure_logging

_settings = Settings.from_env()
log = configure_logging(__name__)
from .vision import parse_pdf_vision



PDF_NATIVE_MIN_CHARS_PER_PAGE = 100


def _pdf_native_text(filepath: Path, max_pages: int) -> tuple[str, int]:
    import pdfplumber

    parts: list[str] = []
    pages_read = 0
    with pdfplumber.open(str(filepath)) as pdf:
        for page in pdf.pages[:max_pages]:
            parts.append(page.extract_text() or "")
            pages_read += 1
    return "\n".join(parts), pages_read


def _strip_garbled_runs(text: str, min_run: int = 6) -> str:
    toks = text.split()
    keep = [True] * len(toks)
    i, n = 0, len(toks)
    while i < n:
        if len(toks[i]) <= 2:
            j = i
            while j < n and len(toks[j]) <= 2:
                j += 1
            run = toks[i:j]
            if len(run) >= min_run and sum(1 for t in run if len(t) == 1) / len(run) >= 0.5:
                for k in range(i, j):
                    keep[k] = False
            i = j
        else:
            i += 1
    return " ".join(t for t, k in zip(toks, keep) if k)


def _single_char_fraction(text: str) -> float:
    toks = text.split()
    return sum(1 for t in toks if len(t) == 1) / len(toks) if toks else 0.0


def _should_use_native(text: str, pages_read: int,
                       min_cpp: int = PDF_NATIVE_MIN_CHARS_PER_PAGE) -> bool:
    if pages_read <= 0:
        return False
    if _single_char_fraction(text) >= 0.5:
        return False
    return len(text.strip()) / pages_read >= min_cpp


def parse_pdf(filepath: Path, client, max_pages: int) -> tuple[str, str]:
    try:
        native, pages_read = _pdf_native_text(filepath, max_pages)
    except Exception as e:
        log.warning("  PDF native extraction failed for %s: %s", filepath.name, e)
        native, pages_read = "", 0

    native = _strip_garbled_runs(native)

    if _should_use_native(native, pages_read):
        return native.strip(), f"pdf-native ({pages_read} pages)"

    if client is None:
        return native.strip(), f"pdf-native-no-client ({pages_read} pages)"

    return parse_pdf_vision(filepath, client, max_pages)
