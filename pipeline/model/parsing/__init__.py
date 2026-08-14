
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

from .html import parse_html, parse_txt
from .pdf import parse_pdf
from .spreadsheet import parse_docx, parse_spreadsheet
from .vision import parse_image_vision, parse_pdf_vision


TEXT_EXTENSIONS = {".html", ".htm", ".txt"}


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}


PDF_EXTENSIONS = {".pdf"}


SPREADSHEET_EXTENSIONS = {".xlsx", ".xls", ".csv"}


DOCX_EXTENSIONS = {".doc", ".docx"}


ALL_SUPPORTED = TEXT_EXTENSIONS | IMAGE_EXTENSIONS | PDF_EXTENSIONS | SPREADSHEET_EXTENSIONS | DOCX_EXTENSIONS


def process_file(
    filepath: Path,
    client,
    max_pdf_pages: int,
) -> tuple[str, str]:
    ext = filepath.suffix.lower()

    if ext in (".html", ".htm"):
        return parse_html(filepath)
    elif ext == ".txt":
        return parse_txt(filepath)
    elif ext in PDF_EXTENSIONS:
        return parse_pdf(filepath, client, max_pdf_pages)
    elif ext in IMAGE_EXTENSIONS:
        return parse_image_vision(filepath, client)
    elif ext in SPREADSHEET_EXTENSIONS:
        return parse_spreadsheet(filepath, client)
    elif ext in DOCX_EXTENSIONS:
        return parse_docx(filepath)
    else:
        return "", f"unsupported ({ext})"
