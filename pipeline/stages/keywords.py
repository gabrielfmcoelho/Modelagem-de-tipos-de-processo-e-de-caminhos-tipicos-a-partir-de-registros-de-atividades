from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ..core._stage_base import RunContext, StageMeta
from ..evidence.artifact import write_sidecar
from ..model.keywords import VOCAB_PATH, KEYWORDS_PATH, load_keywords_store, save_keywords_store, load_vocab, normalize_batch, save_vocab, vocab_prompt_block
from ..core.corpus import corpus_protocolos
from ..core.parsed_store import iter_parsed_documents
from ..core.registry import stage
from ..core.state import now_iso
from ..core.deployment import ORGAO_GOVERNO_CURTO

log = logging.getLogger(__name__)

MAX_CHARS = 8000
PASSES = 2
PASS1_WORKERS = 10
PASS1_BATCH = 10
PASS1_VOCAB_TOP = 150
PASS2_WORKERS = 10
PASS2_BATCH = 30
PASS2_VOCAB_TOP = 300

SYSTEM_PROMPT = """\
Você extrai palavras-chave de documentos administrativos do {ORGAO_GOVERNO_CURTO} (SEI).

Devolva NO MÁXIMO 6 palavras-chave (menos, se o documento não justificar) que identifiquem o ASSUNTO do processo — o objeto concreto \
(ex.: "ata registro precos", "adesao ata", "controle frequencia", "suprimento fundos", \
"contratacao estagiario"). Evite termos genéricos como "processo", "documento", "solicitacao" \
sozinhos, e não inclua nomes de pessoas.

REUTILIZE termos do vocabulário já existente sempre que descreverem o mesmo assunto; \
só crie um termo novo quando nenhum existente servir. Isso mantém o vocabulário consistente \
entre processos.

Retorne APENAS JSON: {"keywords": ["...", "..."]}
""".replace("{ORGAO_GOVERNO_CURTO}", ORGAO_GOVERNO_CURTO)


def _parse_keywords(raw: str) -> list[str]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.split("```")[1] if "```" in text[3:] else text.strip("`")
        text = text[4:] if text.lower().startswith("json") else text
    try:
        data = json.loads(text[text.find("{"): text.rfind("}") + 1])
    except Exception:
        return []
    kws = data.get("keywords") or []
    return [str(k) for k in kws if str(k).strip()] if isinstance(kws, list) else []


def canon_protocolo(pf: str) -> str:
    return (pf or "").strip().replace("_", "/")


def _load_corpus(path) -> set[str]:
    p = Path(path)
    if not p.is_file():
        return set()
    try:
        if p.suffix == ".npz":
            import numpy as np
            return {canon_protocolo(str(x))
                    for x in np.load(p, allow_pickle=False)["protocolos"]}
        data = json.loads(p.read_text(encoding="utf-8"))
        return {canon_protocolo(k) for k in data.get("labels", data)}
    except Exception:
        return set()


def _build_extractor(settings):
    base_url = settings.openai_base_url
    if not base_url.rstrip("/").endswith("/v1"):
        base_url = base_url.rstrip("/") + "/v1"
    model = settings.openai_model_evaluate or settings.openai_model or "soberano-alpha-local"

    import httpx
    from openai import OpenAI
    client = OpenAI(base_url=base_url, api_key=settings.openai_api_key,
                    timeout=httpx.Timeout(120.0, connect=10.0))

    def extract(text: str, vocab_block: str) -> list[str]:
        system = SYSTEM_PROMPT
        if vocab_block:
            system += f"\nVocabulário já em uso:\n{vocab_block}\n"
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": text[:MAX_CHARS]}],
            temperature=0.2, max_tokens=256,
        )
        return _parse_keywords(resp.choices[0].message.content or "")

    return extract, model


@stage(StageMeta(
    name="keywords",
    phase="documents",
    question="Que termos controlados descrevem o documento de abertura de cada processo?",
    deterministic=False,
    nondeterminism="chamada de LLM; a saida varia entre execucoes identicas",
    description="Palavras-chave normalizadas do 1º documento, com vocabulário controlado crescente.",
    type="enrich",
    depends_on=("parse",),
    modes=("fs",),
    can_skip_when_done=False,
    estimated_duration="~1-3 docs/s (LLM de texto)",
))
def run(ctx: RunContext) -> None:
    limit = int(ctx.flags.get("limit") or 0)
    force = str(ctx.flags.get("force", "")).strip().lower() in ("1", "true", "yes")
    vocab_path = Path(ctx.flags.get("vocab_path") or VOCAB_PATH)
    threshold = float(ctx.flags.get("merge_threshold") or 0.9)
    passes = max(1, int(ctx.flags.get("passes") or PASSES))
    p1 = (max(1, int(ctx.flags.get("workers") or PASS1_WORKERS)),
          max(1, int(ctx.flags.get("batch") or PASS1_BATCH)),
          max(10, int(ctx.flags.get("vocab_top") or PASS1_VOCAB_TOP)))
    p2 = (max(1, int(ctx.flags.get("pass2_workers") or PASS2_WORKERS)),
          max(1, int(ctx.flags.get("pass2_batch") or PASS2_BATCH)),
          max(10, int(ctx.flags.get("pass2_vocab_top") or PASS2_VOCAB_TOP)))

    parsed_dir = Path(ctx.flags.get("parsed_dir") or "./parsed_documents")
    variant = str(ctx.flags.get("text_variant") or "raw")

    corpus_file = ctx.flags.get("corpus_file")
    corpus = _load_corpus(corpus_file) if corpus_file else set()
    if corpus:
        log.info("keywords: corpus filter = %d processos from %s", len(corpus), corpus_file)
    else:
        corpus = corpus_protocolos(
            ctx.settings, getattr(ctx, 'driver', None),
            allow_connect=str(ctx.flags.get('corpus_filter', 'true')).lower()
            not in ('0', 'false', 'no'))
        if corpus:
            log.info("keywords: corpus filter = %d processos read from the graph", len(corpus))
        else:
            log.warning("keywords: no corpus filter — processing every parsed processo, "
                        "including documents outside the loaded corpus")

    seen_any: set[str] = set()
    first_by_processo: dict[str, tuple] = {}
    for doc in iter_parsed_documents(parsed_dir, variant=variant):
        try:
            meta = json.loads(doc.meta_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        pf = canon_protocolo(meta.get("protocolo") or "")
        numero = meta.get("documento_numero") or ""
        if not pf or not numero:
            continue
        seen_any.add(pf)
        if corpus and pf not in corpus:
            continue
        prev = first_by_processo.get(pf)
        if prev is None or numero < prev[0]:
            first_by_processo[pf] = (numero, doc)

    if corpus and seen_any and not (corpus & seen_any):
        raise ValueError(
            f"corpus filter matched 0 of {len(seen_any)} processos on disk. "
            f"corpus e.g. {sorted(corpus)[:1]}, metadata e.g. {sorted(seen_any)[:1]} "
            "— protocolo formats disagree; refusing to silently process nothing."
        )
    items = sorted(first_by_processo.items())
    if limit:
        items = items[:limit]
    log.info("keywords: %d processos with a first document", len(items))

    store_path = Path(ctx.flags.get("keywords_path") or KEYWORDS_PATH)
    store = load_keywords_store(store_path)
    log.info("keywords: sidecar store has %d processos", len(store))
    vocab = load_vocab(vocab_path)
    log.info("keywords: starting vocabulary has %d terms", len(vocab))
    extract, model = _build_extractor(ctx.settings)

    def _one(entry, block, redo):
        pf, (numero, doc) = entry
        try:
            meta = json.loads(doc.meta_path.read_text(encoding="utf-8"))
        except Exception:
            return pf, doc, None, None
        if meta.get("keywords") and not redo:
            return pf, doc, meta, "skip"
        try:
            text = doc.text_path.read_text(encoding="utf-8", errors="replace").strip()
            return pf, doc, meta, extract(text, block)
        except Exception as e:
            log.warning("keywords: %s failed (%s)", pf, e)
            return pf, doc, meta, None

    done = skipped = failed = empty_raw = empty_canon = 0

    def _run_pass(pass_no: int, n_workers: int, size: int, top: int, redo: bool):
        nonlocal done, skipped, failed, empty_raw, empty_canon
        log.info("keywords pass %d/%d: %d workers, batch=%d, vocab_top=%d, "
                 "vocabulary starts at %d terms",
                 pass_no, passes, n_workers, size, top, len(vocab))
        with ThreadPoolExecutor(max_workers=n_workers) as pool:
            for start in range(0, len(items), size):
                batch = items[start:start + size]
                block = vocab_prompt_block(vocab, limit=top)
                results = list(pool.map(lambda e: _one(e, block, redo), batch))
                for pf, doc, meta, raw in sorted(results, key=lambda r: r[0]):
                    if meta is None or raw is None:
                        failed += 1
                        continue
                    if raw == "skip":
                        skipped += 1
                        continue
                    if not raw:
                        empty_raw += 1
                        continue
                    canon = normalize_batch(raw, vocab, threshold=threshold)
                    if not canon:
                        empty_canon += 1
                        continue
                    store[pf] = canon
                    meta["keywords"] = canon
                    meta["keywords_raw"] = raw
                    meta["keywords_pass"] = pass_no
                    meta["keywords_modelo"] = model
                    meta["keywords_at"] = now_iso()
                    doc.meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                                             encoding="utf-8")
                    done += 1
                save_vocab(vocab, vocab_path)
                save_keywords_store(store, store_path)
                log.info("keywords pass %d: %d/%d, vocabulary %d terms",
                         pass_no, min(start + size, len(items)), len(items), len(vocab))

    _run_pass(1, p1[0], p1[1], p1[2], force)
    for extra in range(2, passes + 1):
        before = len(vocab)
        singles_before = sum(1 for c in vocab.values() if c == 1)
        _run_pass(extra, p2[0], p2[1], p2[2], True)
        singles_after = sum(1 for c in vocab.values() if c == 1)
        log.info("keywords pass %d: vocabulary %d -> %d terms, singletons %d -> %d",
                 extra, before, len(vocab), singles_before, singles_after)

    save_vocab(vocab, vocab_path)
    save_keywords_store(store, store_path)
    write_sidecar(vocab_path, stage="keywords",
                  params={"n_terms": len(vocab), "cache": "controlled keyword vocabulary"})
    write_sidecar(store_path, stage="keywords",
                  params={"n_processos": len(store), "cache": "keywords per processo"})
    summary = {"processos": len(items), "extracted": done, "skipped": skipped,
               "failed": failed, "empty_llm_response": empty_raw,
               "empty_after_normalization": empty_canon,
               "passes": passes, "vocab_terms": len(vocab),
               "vocab_singletons": sum(1 for c in vocab.values() if c == 1),
               "model": model}
    ctx.cache["keywords_summary"] = summary
    log.info("keywords complete: %s", summary)
