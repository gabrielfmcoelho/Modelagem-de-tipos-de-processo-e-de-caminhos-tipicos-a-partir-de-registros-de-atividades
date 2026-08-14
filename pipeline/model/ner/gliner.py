DEFAULT_CHUNK_CHARS = 1800
DEFAULT_CHUNK_OVERLAP = 200


import argparse
import sys as _sys
from pathlib import Path as _Path

_HERE = _Path(__file__).resolve()
_ROOT = next((p.parent for p in _HERE.parents if p.name == "pipeline"), _HERE.parents[2])
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from ...core.deployment import ENDERECO_EXEMPLO, ORGAO_DOMINIO, ORGAO_SIGLA, ORGAOS_IRMAOS
from ...core import parsed_store
from pipeline.cli import add_standard_args, resolve_settings
from ...core.constants import LABEL_TO_KEY
from ...core.logging_setup import configure_logging
from ...core.text import normalize as _normalize

log = configure_logging(__name__)

DEFAULT_LABELS = [
    "nome completo de pessoa física, ex: João Silva, Maria de Souza",
    "nome de empresa ou pessoa jurídica, ex: ABC LTDA, Fundação XYZ, Instituto Nacional",
    f"órgão ou secretaria do governo, ex: {ORGAO_SIGLA}, {ORGAOS_IRMAOS}",
    "cargo, função ou título de autoridade, ex: Secretário, Governador do Estado, Superintendente, Presidente, Diretor",
    f"endereço de email, ex: fulano@{ORGAO_DOMINIO}",
    "número de CPF, ex: 807.713.433-53",
    "número de CNPJ, ex: 46.067.730/0001-00",
    "matrícula de servidor público, ex: 269422X, 124181-8",
    "data completa, ex: 10 de janeiro de 2025, 05/02/2025",
    "valor monetário em reais, ex: R$ 3.441,36, R$ 250.000,00",
    f"endereço ou logradouro, ex: {ENDERECO_EXEMPLO}",
    "número de telefone, ex: (86) 3216-1712",
    "número de processo SEI, ex: 00095.000323/2025-58",
    "número de lei, ex: Lei nº 6.201, Lei Complementar nº 13",
    "número de decreto, ex: Decreto nº 21.787, Decreto Estadual nº 18.142",
    "número de portaria, ex: Portaria nº 123/2025, Portaria GR nº 265",
    "número de contrato ou edital, ex: Edital 001/2025, Contrato nº 15/2024",
    "objeto ou assunto do documento, ex: progressão funcional, cessão de servidor, enquadramento",
    "objeto de licitação ou contrato, ex: prestação de serviços de TI, aquisição de equipamentos",
    "vigência ou prazo, ex: 12 meses, dois anos, 200 horas, prazo indeterminado",
    f"endereço de website ou URL, ex: http://www.{ORGAO_DOMINIO}",
]


def _dedup_entities(values: list[dict]) -> list[dict]:
    seen: dict[str, dict] = {}
    for val in values:
        text = val["text"] if isinstance(val, dict) else val
        key = _normalize(text)
        if key not in seen or len(text) > len(seen[key]["text"]):
            seen[key] = val

    keys = sorted(seen.keys(), key=len)
    merged: dict[str, dict] = {}
    for key in keys:
        is_prefix = False
        for existing_key in merged:
            if existing_key.startswith(key + " ") or key.startswith(existing_key + " "):
                if len(key) > len(existing_key):
                    merged[key] = seen[key]
                    del merged[existing_key]
                is_prefix = True
                break
        if not is_prefix:
            merged[key] = seen[key]

    return list(merged.values())


def _clean_entities(entities: dict[str, list]) -> dict[str, list]:
    import re as _re

    cleaned = {}
    for label, values in entities.items():
        key = LABEL_TO_KEY.get(label, label)
        filtered = []
        for val in values:
            text = val["text"] if isinstance(val, dict) else val
            text = text.strip()

            if len(text) < 3:
                continue

            if key == "pessoa":
                if "@" in text:
                    continue
                if text.lower() in ("visitantes", "membros", "servidores", "servidor", "servidora",
                                     "requerente", "interessado", "interessada", "signatário"):
                    continue
                if len(text.split()) == 1 and len(text) < 6:
                    continue
                if text.lower().startswith(("servidor ", "servidora ")):
                    val = {"text": _re.sub(r"^servidora?\s+", "", text, flags=_re.IGNORECASE)}
                    text = val["text"]

            if key == "pessoa_juridica":
                pessoa_texts = {v["text"].strip().lower() for v in entities.get("nome de pessoa física", entities.get("pessoa", []))} if isinstance(entities, dict) else set()
                if text.lower() in pessoa_texts:
                    continue
                if text.lower() in ("governo", "empresa", "servidora", "servidor"):
                    continue

            if key == "orgao":
                if text.lower() in ("servidora", "servidor", "s/n", "centro administrativo",
                                     "v.sa.", "v.sa", "vossa senhoria"):
                    continue

            if key == "cargo":
                if _re.search(r"secretaria d[aeo]|governo d[oe]", text, _re.IGNORECASE):
                    continue

            if key == "cpf":
                if "CEP" in text.upper() or _re.fullmatch(r"\d{5}-\d{3}", text):
                    continue
                if _re.fullmatch(r"[0-9A-F]{6,}", text):
                    continue
                if _re.fullmatch(r"0\d{8}", text):
                    continue
                if _re.search(r"\d{5}\.\d{6}/\d{4}-\d{2}", text):
                    continue
                if _re.fullmatch(r"\d{2}\.\d{3}-\d{3}", text):
                    continue

            if key == "cnpj":
                if _re.fullmatch(r"[0-9A-Fa-f]{6,}", text):
                    continue
                if not _re.search(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", text):
                    continue

            if key == "telefone":
                if "http" in text or "www" in text:
                    continue
                if _re.fullmatch(r"\d{1,2}:\d{2}", text):
                    continue
                if _re.fullmatch(r"0\d{8}", text):
                    continue
                if text.lower() in ("telefone", "tel", "fone", "fax"):
                    continue

            if key == "email":
                if "@" not in text:
                    continue
                if len(text.split("@")[0]) < 3:
                    continue

            if key == "url":
                if "http" not in text.lower() and "www" not in text.lower():
                    continue

            if key == "valor_monetario":
                if not _re.search(r"R\$", text):
                    continue

            if key == "portaria":
                if not _re.search(r"\d", text):
                    continue
                if _re.fullmatch(r"0?\d{8,9}", text):
                    continue
                if text.lower().startswith("art"):
                    continue

            if key == "contrato_edital" and not _re.search(r"\d", text):
                continue

            if key == "matricula":
                if _re.search(r"\d{5}\.\d{6}/\d{4}-\d{2}", text):
                    continue
                if not _re.search(r"\d", text):
                    continue
                if text.startswith((".", " ")):
                    val = {"text": text.lstrip(". ")}
                    text = val["text"]

            if key == "assunto":
                if text.lower() in ("documento", "assunto", "processo", "documento oficial", "autos"):
                    continue
                if len(text) < 5:
                    continue

            if key == "objeto_licitacao" and len(text) < 5:
                continue

            if key == "vigencia":
                if not _re.search(r"\d|mes|ano|dia|semana|prazo|hora", text, _re.IGNORECASE):
                    continue

            if key == "lei":
                if _re.fullmatch(r"[\d./]+", text):
                    continue

            if key == "decreto":
                if _re.fullmatch(r"[\d./]+", text):
                    continue

            filtered.append(val)

        if filtered:
            cleaned[key] = _dedup_entities(filtered)

    return cleaned


def _clean_relations(relations: dict[str, list]) -> dict[str, list]:
    GENERIC_TERMS = {"processo", "documento", "servidor", "servidora", "empresa",
                     "requerente", "portaria", "ofício", "oficio", "autos"}

    cleaned = {}
    for rel_type, pairs in relations.items():
        filtered = []
        for pair in pairs:
            if any(len(str(p).strip()) < 4 for p in pair):
                continue
            head, tail = str(pair[0]).strip(), str(pair[1]).strip()
            if head.lower() == tail.lower():
                continue
            if head.lower() in GENERIC_TERMS or tail.lower() in GENERIC_TERMS:
                continue
            if "@" in head and tail.startswith("."):
                continue
            if "@" in tail and head.startswith("."):
                continue
            if len(tail.split()) == 1 and tail.lower() in ("efeitos", "curso", "progres", "progressão"):
                continue
            filtered.append(pair)
        if filtered:
            cleaned[rel_type] = filtered
    return cleaned


def _detect_chunk_size(extractor) -> tuple[int, int]:
    try:
        max_tokens = extractor.encoder.config.max_position_embeddings
    except AttributeError:
        log.warning("Could not detect max_position_embeddings, using defaults")
        return DEFAULT_CHUNK_CHARS, DEFAULT_CHUNK_OVERLAP

    chars = int(max_tokens * 3.5 * 0.8)
    overlap = int(chars * 0.1)

    log.info("Encoder max tokens: %d → chunk size: %d chars, overlap: %d", max_tokens, chars, overlap)
    return chars, overlap


def chunk_text(text: str, max_chars: int = DEFAULT_CHUNK_CHARS, overlap: int = DEFAULT_CHUNK_OVERLAP) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    return chunks


def merge_entities(all_entities: list[dict], labels: list[str]) -> dict:
    merged = {label: [] for label in labels}

    for chunk_result in all_entities:
        entities = chunk_result.get("entities", {})
        for label in labels:
            for entity in entities.get(label, []):
                entity_text = entity["text"] if isinstance(entity, dict) else entity
                existing_texts = set()
                for e in merged[label]:
                    t = e["text"] if isinstance(e, dict) else e
                    existing_texts.add(t.strip().lower())
                if entity_text.strip().lower() not in existing_texts:
                    merged[label].append(entity)

    return {k: v for k, v in merged.items() if v}
