from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from ..core._stage_base import RunContext, StageMeta, truthy as _truthy
from ..core.cypher import LOAD_DOCUMENTO_EVALUATION_CYPHER
from ..core.corpus import canon_protocolo, corpus_protocolos
from ..core.parsed_store import iter_parsed_documents
from ..core.registry import stage
from ..core.state import now_iso
from ..core.deployment import ORGAO_GOVERNO_CURTO

log = logging.getLogger(__name__)

MAX_EVAL_CHARS = 8000
SENTINEL_TOPIC = "(sem tópico)"

SYSTEM_PROMPT = (
    f"Você é um assistente de análise documental do {ORGAO_GOVERNO_CURTO}. "
    "Leia o documento e responda SOMENTE com um objeto JSON válido com as chaves "
    '"topic" (um tópico curto, no máximo 8 palavras) e "summary" (um resumo de um '
    "parágrafo). Não inclua nenhum texto fora do JSON. "
    "NUNCA inclua dados pessoais no tópico ou no resumo: nomes de pessoas físicas, "
    "CPF, CNPJ, e-mails, matrículas, telefones ou endereços. Se o texto contiver "
    "placeholders como <PESSOA_ab12cd34> ou <CPF_ab12cd34>, mantenha-os literalmente em vez "
    "de tentar reconstruir os dados originais."
)


def _needs_evaluation(meta: dict, force: bool) -> bool:
    if force:
        return True
    return not (meta.get("topic") or "").strip()


def _parse_llm_json(raw: str) -> tuple[str, str, str]:
    s = raw.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\n?", "", s)
        s = re.sub(r"\n?```$", "", s).strip()
    try:
        obj = json.loads(s)
        topic = str(obj.get("topic") or "").strip()
        summary = str(obj.get("summary") or "").strip()
        if topic or summary:
            return (topic or SENTINEL_TOPIC, summary, "ok")
    except (json.JSONDecodeError, TypeError, ValueError, AttributeError):
        pass
    first_para = raw.strip().split("\n\n", 1)[0].strip()
    return (SENTINEL_TOPIC, first_para, "degraded")


def _merge_evaluation(meta: dict, topic: str, summary: str, model: str, status: str) -> dict:
    out = dict(meta)
    out["topic"] = topic
    out["summary"] = summary
    out["evaluation_modelo"] = model
    out["evaluation_status"] = status
    out["evaluated_at"] = now_iso()
    return out


def _build_evaluator(settings):
    base_url = settings.openai_base_url
    if not base_url.rstrip("/").endswith("/v1"):
        base_url = base_url.rstrip("/") + "/v1"
    api_key = settings.openai_api_key
    model = settings.openai_model_evaluate or settings.openai_model or "soberano-alpha-local"

    import httpx
    from openai import OpenAI
    client = OpenAI(base_url=base_url, api_key=api_key,
                    timeout=httpx.Timeout(120.0, connect=10.0))

    def evaluate_one(text: str, meta: dict) -> tuple[str, str, str]:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text[:MAX_EVAL_CHARS]},
            ],
            temperature=0.2,
            max_tokens=512,
        )
        return _parse_llm_json(resp.choices[0].message.content or "")

    return evaluate_one, model


@stage(StageMeta(
    name="evaluate",
    phase="documents",
    question="Sobre o que trata cada documento de abertura?",
    deterministic=False,
    nondeterminism="chamada de LLM; a saida varia entre execucoes identicas",
    description="Gera tópico + resumo (LLM, pt-BR) por documento; grava no JSON e opcionalmente no :Documento.",
    type="enrich",
    depends_on=("parse",),
    soft_depends_on=("ner-load",),
    modes=("fs", "neo4j", "json-emit"),
    estimated_duration="~1-3 docs/s (LLM de texto)",
))
def run(ctx: RunContext) -> None:
    parsed_dir = Path(ctx.flags.get("input") or ctx.flags.get("parsed_dir") or "./parsed_documents")
    force = _truthy(ctx.flags.get("force"))
    load_existing = _truthy(ctx.flags.get("load_existing", True))
    limit = int(ctx.flags.get("limit") or 0)
    workers = max(1, int(ctx.flags.get("workers") or 1))
    variant = str(ctx.flags.get("text_variant") or "raw").lower()

    injected = ctx.flags.get("_evaluator")
    if injected is not None:
        evaluate_one, model = injected, ctx.flags.get("_model", "test-model")
    else:
        evaluate_one, model = _build_evaluator(ctx.settings)

    docs = list(iter_parsed_documents(parsed_dir, variant=variant))
    n_all = len(docs)
    corpus = corpus_protocolos(
        ctx.settings, getattr(ctx, "driver", None),
        allow_connect=str(ctx.flags.get("corpus_filter", "")).lower()
        in ("1", "true", "yes"))
    outside = 0
    if corpus:
        kept = []
        for doc in docs:
            try:
                m = json.loads(doc.meta_path.read_text(encoding="utf-8")) if doc.meta_path.is_file() else {}
            except (OSError, json.JSONDecodeError):
                m = {}
            if canon_protocolo(m.get("protocolo") or "") in corpus:
                kept.append(doc)
        outside = n_all - len(kept)
        docs = kept
        log.info("evaluate: corpus filter = %d processos; %d of %d parsed documents are outside "
                 "the corpus and are not evaluated", len(corpus), outside, n_all)
    if limit:
        docs = docs[:limit]
    ctx.progress.set_total(len(docs))

    rows: list[dict] = []
    evaluated = skipped = failed = 0

    work: list[tuple] = []
    for doc in docs:
        try:
            meta = json.loads(doc.meta_path.read_text(encoding="utf-8")) if doc.meta_path.is_file() else {}
        except (OSError, json.JSONDecodeError):
            meta = {}
        if not _needs_evaluation(meta, force):
            skipped += 1
            if load_existing and (meta.get("topic") or "").strip():
                rows.append({
                    "documento_numero": doc.doc_id,
                    "topic": meta.get("topic") or "",
                    "summary": meta.get("summary") or "",
                    "status": meta.get("evaluation_status") or "ok",
                    "modelo": meta.get("evaluation_modelo") or model,
                    "computed_at": now_iso(),
                })
            ctx.progress.advance()
            continue
        try:
            text = doc.text_path.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            text = ""
        if not text:
            failed += 1
            ctx.progress.advance()
            continue
        work.append((doc, meta, text))

    def _eval(item):
        doc, meta, text = item
        topic, summary, status = evaluate_one(text, meta)
        return doc, meta, topic, summary, status

    def _consume(result, item):
        nonlocal evaluated, failed
        if isinstance(result, BaseException):
            log.warning("evaluate failed for %s: %s", item[0].doc_id, result)
            failed += 1
        else:
            doc, meta, topic, summary, status = result
            meta = _merge_evaluation(meta, topic, summary, model, status)
            doc.meta_path.parent.mkdir(parents=True, exist_ok=True)
            doc.meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
            rows.append({
                "documento_numero": doc.doc_id, "topic": topic, "summary": summary,
                "status": status, "modelo": model, "computed_at": now_iso(),
            })
            evaluated += 1
        ctx.progress.advance()

    if workers <= 1:
        for item in work:
            try:
                res = _eval(item)
            except Exception as e:
                res = e
            _consume(res, item)
    else:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = {pool.submit(_eval, item): item for item in work}
            for fut in as_completed(futs):
                item = futs[fut]
                try:
                    res = fut.result()
                except Exception as e:
                    res = e
                _consume(res, item)

    if rows and ctx.writer is not None:
        writer = ctx.writer
        writer.open_phase("evaluate")
        try:
            for i in range(0, len(rows), 500):
                writer.execute_template(
                    "load_documento_evaluation",
                    LOAD_DOCUMENTO_EVALUATION_CYPHER,
                    {"rows": rows[i:i + 500]},
                    phase="evaluate",
                )
        finally:
            writer.close_phase("evaluate")

    ctx.cache["evaluate_summary"] = {
        "total": len(docs), "evaluated": evaluated,
        "skipped": skipped, "failed": failed, "model": model,
        "documents_outside_corpus": outside, "documents_all": n_all,
    }
    log.info("evaluate complete: evaluated=%d skipped=%d failed=%d (model=%s)",
             evaluated, skipped, failed, model)
