
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


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


_BODY_END_RE = re.compile(
    r"\(assinado eletronicamente\)"
    r"|\bDocumento assinado eletronicamente\b"
    r"|\bA autenticidade deste documento\b"
    r"|\b(?:Atenciosamente|Respeitosamente|Cordialmente)\b"
    r"|\bCriado por\b[^.]*?\bem\b"
    r"|\bSEI\s*n[º°o]\s*\d",
    re.IGNORECASE,
)


_LEADING_HEADER_RE = re.compile(
    r"^.{0,130}?Refer[êe]ncia\s*:\s*Caso responda.{0,160}?Processo\s*n[º°o.]*\s*[\d./-]{6,}\s*\.?\s*",
    re.IGNORECASE | re.DOTALL,
)


_ADDRESS_RE = re.compile(
    r"Av\.?\s*Pedro Freitas.{0,260}?sead\.pi\.gov\.br/?",
    re.IGNORECASE | re.DOTALL,
)


def _strip_signature_and_footer(text: str) -> str:
    m = _BODY_END_RE.search(text)
    return text[: m.start()].rstrip() if m else text.strip()


def _strip_leading_header(text: str) -> str:
    m = _LEADING_HEADER_RE.match(text)
    if m:
        remainder = text[m.end():].lstrip()
        if remainder:
            return remainder
    return text


_DATELINE_RE = re.compile(
    r"^\s*.{0,230}?[A-Za-zÀ-ú]+/PI,\s*\d{1,2}\s+de\s+[A-Za-zçãéêíóôõáâà]+\s+de\s+\d{4}\s*\.?\s*",
    re.IGNORECASE | re.DOTALL,
)


_BODY_START_RE = (
    r"(?:Prezad[oa]s?\b|Senhor(?:a|es|as)?\b|Sr[a]?\.?\s|Excelent[íi]ssim[oa]\b"
    r"|Ilustr[íi]ssim[oa]\b|Car[oa]s?\b|Solicit(?:o|amos|a|ei)\b|Venho\b|Vimos\b"
    r"|Encaminh(?:o|amos|ando)\b|Considerando\b|Em\s+resposta\b|Em\s+aten[çc][ãa]o\b"
    r"|Em\s+cumprimento\b|Trata-se\b|Assunto\s*:|Cumprimentando\b|Informo\b|Informamos\b"
    r"|Comunico\b|Comunicamos\b|Segue\b|Reporto\b|Reitero\b|Reiteramos\b|Certifico\b"
    r"|Conforme\b|Favor\b|Diante\b|Atrav[ée]s\b|Por\s+meio\b)"
)


_PARA_RE = re.compile(r"^\s*PARA\s*:\s*.{0,140}?(?=" + _BODY_START_RE + r")", re.IGNORECASE | re.DOTALL)


_PROCESSO_RE = re.compile(r"^\s*PROCESSO\s*N[º°o.:]*\s*[\d./-]{6,}\s*\.?\s*", re.IGNORECASE)


_TITLE_RE = re.compile(
    r"^\s*(?:DESPACHO|MEMORANDO|OF[ÍI]CIO|COMUNICADO|PARECER|CIRCULAR)\s*N[º°o]\s*[\dA-Z./-]+\s*"
)


_DE_RE = re.compile(r"^\s*DE\s*:\s*[\w./@-]+(?:\s*[-–]\s*[\w./-]+)*\s*")


_SEAD_FRAG_RE = re.compile(r"^\s*\.?\s*" + re.escape(ORGAO_DOMINIO) + r"/?\s*",
                           re.IGNORECASE)


_LETTERHEAD_TERMINATORS = (
    _BODY_START_RE
    + r"|Designa\b|Resolve\b|Nomeia\b|Exonera\b|Institui\b|Aprova\b|Estabelece\b"
    + r"|Revoga\b|Altera\b|Determina\b|Concede\b|Autoriza\b|Delega\b|Disp[õo]e\b"
    + r"|O\s+SECRET[ÁA]RIO\b|A\s+SECRET[ÁA]RIA\b|Refer[êe]ncia\s*:"
    + r"|A[oaà]s?\s+(?:Senhor|Diretor|Excelent|Ilustr|Membro|Servidor|Gestor"
    + r"|Coordenador|Superintendent|Chefe|Presidente|Comandante)"
)


_LETTERHEAD_RE = re.compile(
    r"^\s*GOVERNO DO ESTADO DO PIAU[IÍ]\b.{0,320}?(?=(?:" + _LETTERHEAD_TERMINATORS + r"))",
    re.IGNORECASE | re.DOTALL,
)


def _strip_leading_letterhead(text: str) -> str:
    m = _LETTERHEAD_RE.match(text)
    return text[m.end():].lstrip() if m else text


def _strip_doc_header_fields(text: str) -> str:
    prev = None
    while prev != text:
        prev = text
        text = _SEAD_FRAG_RE.sub("", text)
        text = _DATELINE_RE.sub("", text)
        text = _PROCESSO_RE.sub("", text)
        text = _TITLE_RE.sub("", text)
        text = _DE_RE.sub("", text)
        text = _strip_leading_letterhead(text)
        m = _PARA_RE.match(text)
        if m:
            text = text[m.end():]
    return text.lstrip()


def parse_html(filepath: Path) -> tuple[str, str]:
    import html as html_mod

    from bs4 import BeautifulSoup

    raw = filepath.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(raw, "html.parser")

    for tag in soup(["head", "title", "style", "script", "img"]):
        tag.decompose()

    for tag in soup.find_all(attrs={"class": True}):
        classes = _strip_accents(" ".join(tag.get("class", []))).lower()
        if "cabecalho" in classes:
            tag.decompose()

    text = soup.get_text(separator=" ")
    text = html_mod.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    text = _strip_signature_and_footer(text)
    text = _ADDRESS_RE.sub(" ", text)
    text = _strip_leading_header(text)
    text = _strip_doc_header_fields(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text, "html-clean"


def parse_txt(filepath: Path) -> tuple[str, str]:
    text = filepath.read_text(encoding="utf-8", errors="replace").strip()
    return text, "passthrough"
