from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from ..core.paths import ARTIFACTS

VOCAB_PATH = ARTIFACTS / "cache" / "keyword_vocab.json"
KEYWORDS_PATH = ARTIFACTS / "cache" / "keywords_by_processo.json"


def load_keywords_store(path=KEYWORDS_PATH) -> dict[str, list[str]]:
    p = Path(path)
    if not p.is_file():
        return {}
    try:
        return {str(k): list(v) for k, v in json.loads(p.read_text(encoding="utf-8")).items() if v}
    except Exception:
        return {}


def save_keywords_store(store: dict[str, list[str]], path=KEYWORDS_PATH) -> None:
    if not store:
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(dict(sorted(store.items())), ensure_ascii=False, indent=0) + "\n",
                 encoding="utf-8")

STOPWORDS = frozenset({
    "de", "da", "do", "das", "dos", "e", "a", "o", "as", "os", "em", "no", "na",
    "nos", "nas", "para", "por", "com", "ao", "aos", "the", "of",
})

ORGAO_TERMS = frozenset({
    "sead", "sead-pi", "sesapi", "sesapi-pi", "seduc", "seduc-pi", "ssp", "ssp-pi",
    "sefaz", "sefaz-pi", "seplan", "seplan-pi", "pge", "pge-pi", "cge", "cge-pi",
    "detran", "detran-pi", "segov", "segov-pi", "sejus", "sejus-pi", "sasc", "sasc-pi",
    "setur", "setur-pi", "secult", "secult-pi", "semarh", "semarh-pi", "seinfra",
    "seinfra-pi", "piauiprev", "piauiprev-pi", "etipi", "etipi-pi", "governo",
    "governo estado", "estado piaui", "piaui", "administracao publica",
    "teresina", "municipio teresina", "capital",
    "exercicio 2025", "ano 2025", "exercicio financeiro", "exercicio corrente",
    "processo administrativo", "procedimento administrativo", "documento oficial",
})

_YEARISH = re.compile(r"^(exercicio|ano|periodo)?\s*(19|20)\d{2}$")

_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s/-]")


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text)
                   if unicodedata.category(c) != "Mn")


def collapse_unit_path(token: str) -> str:
    if "/" not in token:
        return token
    parts = [p for p in token.split("/") if p.strip()]
    return parts[-1].strip() if parts else token


def normalize_keyword(raw: str) -> str:
    if not raw:
        return ""
    t = strip_accents(str(raw)).lower().strip()
    t = " ".join(collapse_unit_path(w) for w in t.split())
    t = _PUNCT.sub(" ", t)
    t = _WS.sub(" ", t).strip()
    words = [w for w in t.split() if w and w not in STOPWORDS]
    return " ".join(words)


def _bigrams(s: str) -> set[str]:
    return {s[i:i + 2] for i in range(len(s) - 1)} or {s}


def similarity(a: str, b: str) -> float:
    if a == b:
        return 1.0
    ga, gb = _bigrams(a), _bigrams(b)
    return 2 * len(ga & gb) / (len(ga) + len(gb)) if (ga or gb) else 0.0


def merge_into_vocab(term: str, vocab: dict[str, int], *, threshold: float = 0.9) -> str | None:
    t = normalize_keyword(term)
    if not t or len(t) < 3:
        return None
    if t in ORGAO_TERMS or _YEARISH.match(t):
        return None
    if t in vocab:
        vocab[t] += 1
        return t
    for known in vocab:
        if t == known or t in known.split() or known in t.split():
            vocab[known] += 1
            return known
        if (t.startswith(known + " ") or known.startswith(t + " ")
                or t.replace("-", " ") == known.replace("-", " ")):
            keep = known if len(known) <= len(t) else t
            if keep != known:
                vocab[keep] = vocab.pop(known) + 1
            else:
                vocab[known] += 1
            return keep
    best, score = None, 0.0
    for known in vocab:
        sc = similarity(t, known)
        if sc > score:
            best, score = known, sc
    if best is not None and score >= threshold:
        vocab[best] += 1
        return best
    vocab[t] = 1
    return t


def normalize_batch(terms, vocab: dict[str, int], *, threshold: float = 0.9) -> list[str]:
    out: list[str] = []
    for term in terms or []:
        canon = merge_into_vocab(term, vocab, threshold=threshold)
        if canon and canon not in out:
            out.append(canon)
    return out


def load_vocab(path: Path = VOCAB_PATH) -> dict[str, int]:
    p = Path(path)
    if not p.is_file():
        return {}
    return {str(k): int(v) for k, v in json.loads(p.read_text(encoding="utf-8")).items()}


def save_vocab(vocab: dict[str, int], path: Path = VOCAB_PATH) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    ordered = dict(sorted(vocab.items(), key=lambda kv: (-kv[1], kv[0])))
    p.write_text(json.dumps(ordered, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")


def vocab_prompt_block(vocab: dict[str, int], *, limit: int = 400) -> str:
    if not vocab:
        return ""
    top = [k for k, _ in sorted(vocab.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]]
    return " · ".join(top)
