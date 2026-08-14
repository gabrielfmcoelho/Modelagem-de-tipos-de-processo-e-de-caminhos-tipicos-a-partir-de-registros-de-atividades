
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


def _env_model(*values: str | None, default: str) -> str:
    for v in values:
        if v:
            return v
    return default


OPENAI_BASE_URL = _settings.openai_base_url


OPENAI_API_KEY = _settings.openai_api_key


MODEL_VISAO = _env_model(
    _settings.openai_model_visao, _settings.openai_model,
    default="Qwen/Qwen3-Omni-30B-A3B-Instruct")


MODEL_TEXTO = _env_model(
    _settings.openai_model_texto, _settings.openai_model, default="soberano-alpha-local")


OPENAI_TIMEOUT = _settings.openai_timeout


VISION_SYSTEM_PROMPT = (
    f"Você é um assistente de análise documental do {ORGAO_GOVERNO_CURTO}. "
    "Transcreva e descreva o conteúdo do documento apresentado de forma fiel e completa. "
    "Inclua todo texto visível, tabelas, valores, datas, nomes e assinaturas. "
    "Se houver imagens, gráficos ou selos, descreva-os brevemente. "
    "Responda apenas com o conteúdo extraído, sem comentários adicionais."
)


VISION_USER_PROMPT_PDF = "Transcreva o conteúdo completo das páginas do documento PDF abaixo:"


VISION_USER_PROMPT_IMAGE = "Transcreva e descreva o conteúdo completo desta imagem de documento:"


def _get_client():
    import httpx as _httpx
    from openai import OpenAI
    return OpenAI(
        base_url=OPENAI_BASE_URL,
        api_key=OPENAI_API_KEY,
        timeout=_httpx.Timeout(float(OPENAI_TIMEOUT), connect=10.0),
    )


PAGES_PER_BATCH = 3


IMAGE_MAX_DIMENSION = 1280


def _resize_image(img, max_dim: int = IMAGE_MAX_DIMENSION):
    w, h = img.size
    if w <= max_dim and h <= max_dim:
        return img
    scale = min(max_dim / w, max_dim / h)
    new_size = (int(w * scale), int(h * scale))
    try:
        from PIL import Image as _PILImage
        resample = _PILImage.Resampling.LANCZOS
    except AttributeError:
        resample = 1
    return img.resize(new_size, resample=resample)


def _image_to_base64(img, max_dim: int = IMAGE_MAX_DIMENSION) -> str:
    img = _resize_image(img, max_dim)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _assemble_vision_text(batch_texts: list[str]) -> str:
    return "\n\n".join(t.strip() for t in batch_texts if t and t.strip())


def parse_pdf_vision(filepath: Path, client, max_pages: int) -> tuple[str, str]:
    from pdf2image import convert_from_path

    images = convert_from_path(str(filepath), first_page=1, last_page=max_pages)
    total_pages = len(images)
    log.info("  PDF: %d page(s), processing in batches of %d", total_pages, PAGES_PER_BATCH)

    ok_parts: list[str] = []
    failed_batches = 0

    for batch_start in range(0, total_pages, PAGES_PER_BATCH):
        batch = images[batch_start:batch_start + PAGES_PER_BATCH]
        batch_end = batch_start + len(batch)
        page_range = f"{batch_start + 1}-{batch_end}"

        image_contents = []
        for img in batch:
            b64 = _image_to_base64(img)
            image_contents.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
            })

        prompt = f"Transcreva o conteúdo completo das páginas {page_range} (de {total_pages}) do documento PDF abaixo:"
        user_content = [{"type": "text", "text": prompt}] + image_contents

        try:
            resp = client.chat.completions.create(
                model=MODEL_VISAO,
                messages=[
                    {"role": "system", "content": VISION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.3,
                max_tokens=4096,
            )
            chunk_text = resp.choices[0].message.content.strip()
            ok_parts.append(chunk_text)
            log.info("  PDF batch %s/%d OK (%d chars)", page_range, total_pages, len(chunk_text))
        except Exception as e:
            log.warning("  PDF batch %s/%d FAILED: %s", page_range, total_pages, e)
            failed_batches += 1

    text = _assemble_vision_text(ok_parts)
    method = f"vision-pdf ({total_pages} pages, {len(ok_parts)} ok, {failed_batches} failed)"
    return text, method


def parse_image_vision(filepath: Path, client) -> tuple[str, str]:
    from PIL import Image

    img = Image.open(filepath)
    b64 = _image_to_base64(img)

    user_content = [
        {"type": "text", "text": VISION_USER_PROMPT_IMAGE},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
    ]

    resp = client.chat.completions.create(
        model=MODEL_VISAO,
        messages=[
            {"role": "system", "content": VISION_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.3,
        max_tokens=4096,
    )
    text = resp.choices[0].message.content.strip()
    return text, "vision-image"
