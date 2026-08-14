from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

from ..core._stage_base import RunContext, StageMeta, truthy as _truthy
from ..model.anonymize import anonymize_text, ner_entities, regex_entities
from ..core.parsed_store import anon_meta_path, anon_text_path, iter_parsed_documents
from ..core.registry import stage
from ..core.state import now_iso

log = logging.getLogger(__name__)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_ner_payload(path: Path) -> tuple[dict | None, str]:
    if not path.is_file():
        return None, ""
    try:
        raw = path.read_bytes()
        return json.loads(raw.decode("utf-8")), _sha256(raw)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
        log.warning("could not load NER payload %s: %s — regex-only for this doc", path, e)
        return None, ""


@stage(StageMeta(
    name="anonymize",
    phase="documents",
    question="Que PII permanece detectavel no texto apos a substituicao por placeholders tipados?",
    deterministic=True,
    description="Gera text_anon.txt + anon_meta.json por documento (PII → placeholders tipados determinísticos).",
    type="enrich",
    depends_on=("parse",),
    soft_depends_on=("ner-extract",),
    modes=("fs",),
    estimated_duration="~5-50ms/doc (regex + string match)",
))
def run(ctx: RunContext) -> None:
    parsed_dir = Path(ctx.flags.get("input") or ctx.flags.get("parsed_dir") or "./parsed_documents")
    ner_dir = Path(ctx.flags.get("ner_dir") or "./ner_results")
    limit = int(ctx.flags.get("limit") or 0)
    force = _truthy(ctx.flags.get("force"))
    verify = _truthy(ctx.flags.get("verify"))

    if not parsed_dir.is_dir():
        log.error("parsed-documents dir not found: %s", parsed_dir)
        ctx.cache["anonymize_summary"] = {"total": 0, "processed": 0, "skipped": 0, "error": "missing_dir"}
        return
    if not ner_dir.is_dir():
        log.warning("NER results dir not found: %s — all docs will be regex-only", ner_dir)

    docs = list(iter_parsed_documents(parsed_dir))
    if limit:
        docs = docs[:limit]
    ctx.progress.set_total(len(docs))
    log.info("anonymize: %d parsed documents in %s (verify=%s force=%s)", len(docs), parsed_dir, verify, force)

    processed = skipped = degraded = failed = 0
    residual_hits = 0
    by_label: dict[str, int] = {}

    for doc in docs:
        try:
            text = doc.text_path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            log.warning("could not read %s: %s", doc.text_path, e)
            failed += 1
            ctx.progress.advance()
            continue
        if not text.strip():
            skipped += 1
            ctx.progress.advance()
            continue

        payload, ner_hash = _load_ner_payload(ner_dir / f"{doc.doc_id}.json")
        src_hash = _sha256(text.encode("utf-8"))
        out_path = anon_text_path(parsed_dir, doc.doc_id)
        meta_path = anon_meta_path(parsed_dir, doc.doc_id)

        if not force and out_path.is_file() and meta_path.is_file():
            try:
                prev = json.loads(meta_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                prev = {}
            if prev.get("source_sha256") == src_hash and prev.get("ner_sha256") == ner_hash:
                skipped += 1
                ctx.progress.advance()
                continue

        entities = regex_entities(text) + ner_entities(text, payload)
        anon, stats = anonymize_text(text, entities)
        residual = len(regex_entities(anon)) if verify else None

        out_path.write_text(anon, encoding="utf-8")
        meta_path.write_text(json.dumps({
            "documento_numero": doc.doc_id,
            "source_sha256": src_hash,
            "ner_sha256": ner_hash,
            "ner_available": payload is not None,
            "replacements": stats.replacements,
            "total_replacements": stats.total,
            "residual_regex_hits": residual,
            "anonymized_at": now_iso(),
        }, ensure_ascii=False, indent=2), encoding="utf-8")

        processed += 1
        if payload is None:
            degraded += 1
        for label, n in stats.replacements.items():
            by_label[label] = by_label.get(label, 0) + n
        if residual:
            residual_hits += residual
            log.error("anonymize: %d residual regex hit(s) in %s", residual, out_path)
        ctx.progress.advance()

    summary = {
        "total": len(docs),
        "processed": processed,
        "skipped": skipped,
        "degraded_regex_only": degraded,
        "failed": failed,
        "replacements_by_label": by_label,
        "residual_regex_hits": residual_hits if verify else None,
    }
    ctx.cache["anonymize_summary"] = summary
    log.info(
        "anonymize complete: processed=%d skipped=%d degraded=%d failed=%d replacements=%s",
        processed, skipped, degraded, failed, by_label,
    )
    if verify and residual_hits:
        raise RuntimeError(f"anonymize verify failed: {residual_hits} residual regex hit(s) in output")
