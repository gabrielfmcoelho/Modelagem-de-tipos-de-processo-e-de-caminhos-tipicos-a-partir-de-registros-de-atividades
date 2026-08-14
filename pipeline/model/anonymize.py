from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field

from ..core.constants import LABEL_TO_KEY

CPF_FORMATTED_RE = re.compile(r"(?<!\d)\d{3}\.\d{3}\.\d{3}-\d{2}(?!\d)")
CPF_BARE_RE = re.compile(r"(?<!\d)\d{11}(?!\d)")
CNPJ_FORMATTED_RE = re.compile(r"(?<!\d)\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}(?!\d)")
CNPJ_BARE_RE = re.compile(r"(?<!\d)\d{14}(?!\d)")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
MATRICULA_RE = re.compile(
    r"matr[íi]cula\s*(?:n[º°o.]*\s*)?[:\-]?\s*(\d[\d.\-]*\d[xX]?)",
    re.IGNORECASE,
)

NER_KEY_TO_LABEL = {
    "pessoa": "PESSOA",
    "pessoa_fisica": "PESSOA",
    "pessoa_juridica": "EMPRESA",
    "empresa": "EMPRESA",
    "empresa_tecnologia": "EMPRESA",
    "empresa_terceirizada": "EMPRESA",
    "email": "EMAIL",
    "cpf": "CPF",
    "cnpj": "CNPJ",
    "matricula": "MATRICULA",
    "matricula_servidor": "MATRICULA",
    "telefone": "TELEFONE",
    "rg": "DOCUMENTO",
    "cnh": "DOCUMENTO",
    "ctps": "DOCUMENTO",
    "cns": "DOCUMENTO",
    "crm": "DOCUMENTO",
    "oab": "DOCUMENTO",
    "crea": "DOCUMENTO",
    "titulo_eleitoral": "DOCUMENTO",
    "titulo_eleitor": "DOCUMENTO",
    "pis_pasep": "DOCUMENTO",
    "pispasep": "DOCUMENTO",
    "pisa_pasep": "DOCUMENTO",
    "pis": "DOCUMENTO",
    "pasep": "DOCUMENTO",
    "documento_identidade": "DOCUMENTO",
    "documento_identificacao": "DOCUMENTO",
    "documento_identificador": "DOCUMENTO",
    "conta_bancaria": "DOCUMENTO",
    "banco_conta": "DOCUMENTO",
    "conta_banco": "DOCUMENTO",
    "agencia_conta": "DOCUMENTO",
    "numero_conta": "DOCUMENTO",
    "placa": "DOCUMENTO",
    "placa_veiculo": "DOCUMENTO",
    "renavam": "DOCUMENTO",
    "chassi": "DOCUMENTO",
}

_DIGIT_LABELS = {"CPF", "CNPJ", "MATRICULA", "TELEFONE", "DOCUMENTO"}

MIN_SPAN_LEN = 3


@dataclass(frozen=True)
class Entity:
    label: str
    text: str
    canonical: str


@dataclass
class AnonStats:
    replacements: dict[str, int] = field(default_factory=dict)
    total: int = 0


def cpf_valid(digits: str) -> bool:
    if len(digits) != 11 or not digits.isdigit() or len(set(digits)) == 1:
        return False
    for pos in (9, 10):
        total = sum(int(digits[i]) * (pos + 1 - i) for i in range(pos))
        if (total * 10) % 11 % 10 != int(digits[pos]):
            return False
    return True


def cnpj_valid(digits: str) -> bool:
    if len(digits) != 14 or not digits.isdigit() or len(set(digits)) == 1:
        return False
    base = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    for pos in (12, 13):
        weights = [6, *base] if pos == 13 else base
        total = sum(int(digits[i]) * weights[i] for i in range(pos))
        rem = total % 11
        digit = 0 if rem < 2 else 11 - rem
        if digit != int(digits[pos]):
            return False
    return True


def _canonical_key(label: str, canonical: str) -> str:
    if label in _DIGIT_LABELS:
        return re.sub(r"[^0-9xX]", "", canonical).upper()
    s = unicodedata.normalize("NFKD", canonical)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().casefold()


def placeholder(label: str, canonical: str) -> str:
    key = _canonical_key(label, canonical)
    digest = hashlib.sha256(f"{label}|{key}".encode()).hexdigest()[:8]
    return f"<{label}_{digest}>"


def regex_entities(text: str) -> list[Entity]:
    out: list[Entity] = []
    seen: set[tuple[str, str]] = set()

    def add(label: str, span: str) -> None:
        key = (label, span)
        if key in seen:
            return
        seen.add(key)
        out.append(Entity(label=label, text=span, canonical=span))

    for m in CPF_FORMATTED_RE.finditer(text):
        if cpf_valid(re.sub(r"\D", "", m.group())):
            add("CPF", m.group())
    for m in CPF_BARE_RE.finditer(text):
        if cpf_valid(m.group()):
            add("CPF", m.group())
    for m in CNPJ_FORMATTED_RE.finditer(text):
        if cnpj_valid(re.sub(r"\D", "", m.group())):
            add("CNPJ", m.group())
    for m in CNPJ_BARE_RE.finditer(text):
        if cnpj_valid(m.group()):
            add("CNPJ", m.group())
    for m in EMAIL_RE.finditer(text):
        add("EMAIL", m.group())
    for m in MATRICULA_RE.finditer(text):
        span = m.group(1)
        if sum(c.isdigit() for c in span) >= 5:
            add("MATRICULA", span)
    return out


def ner_entities(text: str, ner_payload: dict | None) -> list[Entity]:
    if not ner_payload:
        return []
    text_cf = text.casefold()
    out: list[Entity] = []
    seen: set[tuple[str, str]] = set()
    for raw_key, items in (ner_payload.get("entities") or {}).items():
        label = NER_KEY_TO_LABEL.get(LABEL_TO_KEY.get(raw_key, raw_key))
        if label is None:
            continue
        for item in items or []:
            if isinstance(item, dict):
                span = str(item.get("text") or "").strip()
                canonical = str(item.get("canonical") or "").strip() or span
            else:
                span = str(item).strip()
                canonical = span
            if len(span) < MIN_SPAN_LEN or span.casefold() not in text_cf:
                continue
            key = (label, span)
            if key in seen:
                continue
            seen.add(key)
            out.append(Entity(label=label, text=span, canonical=canonical))
    return out


def anonymize_text(text: str, entities: list[Entity]) -> tuple[str, AnonStats]:
    stats = AnonStats()
    if not text or not entities:
        return text, stats
    taken: list[tuple[int, int, str]] = []
    ordered = sorted(entities, key=lambda e: (-len(e.text), e.label, e.text))
    for ent in ordered:
        span = ent.text.strip()
        if len(span) < MIN_SPAN_LEN:
            continue
        if ent.label in _DIGIT_LABELS:
            guard_l, guard_r = r"(?<!\d)", r"(?!\d)"
        elif ent.label == "EMAIL":
            guard_l, guard_r = r"(?<![A-Za-z0-9._%+\-])", r"(?![A-Za-z])"
        else:
            guard_l, guard_r = r"(?<!\w)", r"(?!\w)"
        pattern = re.compile(guard_l + re.escape(span) + guard_r, re.IGNORECASE)
        token = placeholder(ent.label, ent.canonical)
        for m in pattern.finditer(text):
            s, e = m.span()
            if any(s < end and start < e for start, end, _ in taken):
                continue
            taken.append((s, e, token))
            stats.replacements[ent.label] = stats.replacements.get(ent.label, 0) + 1
            stats.total += 1
    taken.sort()
    parts: list[str] = []
    last = 0
    for s, e, token in taken:
        parts.append(text[last:s])
        parts.append(token)
        last = e
    parts.append(text[last:])
    return "".join(parts), stats
