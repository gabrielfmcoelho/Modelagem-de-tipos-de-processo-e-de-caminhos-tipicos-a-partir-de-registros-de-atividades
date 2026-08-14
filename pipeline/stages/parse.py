
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

from ..core.deployment import ORGAO_DOMINIO, ORGAO_GOVERNO_CURTO

if TYPE_CHECKING:
    import pandas as pd

_HERE = Path(__file__).resolve()
_ROOT = next((p.parent for p in _HERE.parents if p.name == "pipeline"), _HERE.parents[2])
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ..core import parsed_store
from pipeline.cli import add_standard_args, resolve_settings
from ..model.parsing.vision import MODEL_TEXTO, MODEL_VISAO, OPENAI_API_KEY, _get_client
from ..model.parsing import (
    ALL_SUPPORTED,
    DOCX_EXTENSIONS,
    IMAGE_EXTENSIONS,
    PDF_EXTENSIONS,
    SPREADSHEET_EXTENSIONS,
    TEXT_EXTENSIONS,
    process_file,
)
from ..core.config import Settings
from ..core.logging_setup import configure_logging

_settings = Settings.from_env()
log = configure_logging(__name__)





OPENAI_BASE_URL = _settings.openai_base_url






































































def discover_documents(
    input_dir: Path,
    protocolos: list[str] | None = None,
    extensions: set[str] | None = None,
) -> list[dict]:
    allowed_exts = extensions if extensions else ALL_SUPPORTED
    documents = []
    if not input_dir.exists():
        log.error("Input directory does not exist: %s", input_dir)
        sys.exit(1)

    allowed_dirs = None
    if protocolos:
        allowed_dirs = set()
        for p in protocolos:
            allowed_dirs.add(p)
            allowed_dirs.add(p.replace("/", "_"))
            allowed_dirs.add(p.replace("_", "/"))

    for protocolo_dir in sorted(input_dir.iterdir()):
        if not protocolo_dir.is_dir():
            continue
        protocolo = protocolo_dir.name
        if allowed_dirs and protocolo not in allowed_dirs:
            continue
        for doc_dir in sorted(protocolo_dir.iterdir()):
            if not doc_dir.is_dir():
                continue
            documento_numero = doc_dir.name
            for fp in doc_dir.iterdir():
                if fp.is_file() and fp.suffix.lower() in allowed_exts:
                    documents.append({
                        "protocolo": protocolo,
                        "documento_numero": documento_numero,
                        "filepath": fp,
                    })
    return documents


def process_document(
    doc: dict,
    output_dir: Path,
    client,
    max_pdf_pages: int,
    skip_existing: bool,
) -> str:
    doc_id = doc["documento_numero"]
    output_txt = parsed_store.text_path(output_dir, doc_id)
    output_json = parsed_store.meta_path(output_dir, doc_id)

    if skip_existing and output_txt.exists():
        return "skipped"

    filepath = doc["filepath"]
    start = time.monotonic()

    try:
        text, method = process_file(filepath, client, max_pdf_pages)
    except Exception as e:
        log.error("  FAILED %s/%s (%s): %s", doc["protocolo"], doc_id, filepath.name, e)
        return "failed"

    elapsed = time.monotonic() - start

    if not text or len(text.strip()) < 5:
        log.warning("  Empty result for %s/%s (%s)", doc["protocolo"], doc_id, method)
        return "empty"

    output_txt.parent.mkdir(parents=True, exist_ok=True)
    output_txt.write_text(text, encoding="utf-8")

    meta = {
        "documento_numero": doc_id,
        "protocolo": doc["protocolo"],
        "source_file": filepath.name,
        "source_extension": filepath.suffix.lower(),
        "parse_method": method,
        "text_length": len(text),
        "elapsed_seconds": round(elapsed, 2),
        "parsed_at": datetime.now(UTC).isoformat(),
    }
    output_json.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    log.info(
        "  OK %s/%s → %s (%d chars, %.1fs)",
        doc["protocolo"], doc_id, method, len(text), elapsed,
    )
    return "ok"


class _NullProgress:
    def set_total(self, total: int) -> None: ...
    def advance(self, n: int = 1) -> None: ...


def _execute(args, settings, progress=None) -> dict:
    progress = progress or _NullProgress()
    input_dir = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    ext_filter = None
    if args.ext:
        ext_filter = {e if e.startswith(".") else f".{e}" for e in args.ext}
        unsupported = ext_filter - ALL_SUPPORTED
        if unsupported:
            log.warning("Unsupported extensions will be ignored: %s", unsupported)
            ext_filter = ext_filter & ALL_SUPPORTED
        if not ext_filter:
            log.error("No supported extensions in --ext filter")
            sys.exit(1)
        log.info("Extension filter: %s", ", ".join(sorted(ext_filter)))

    needs_llm = ext_filter is None or bool(ext_filter & (IMAGE_EXTENSIONS | PDF_EXTENSIONS | SPREADSHEET_EXTENSIONS))
    if needs_llm and not OPENAI_API_KEY:
        log.error("OPENAI_API_KEY not set in .env — cannot call LLM/vision models")
        sys.exit(1)

    if needs_llm:
        log.info("Models: vision=%s, text=%s", MODEL_VISAO, MODEL_TEXTO)
        log.info("API: %s", OPENAI_BASE_URL)

    documents = discover_documents(input_dir, args.processo, ext_filter)
    if args.limit > 0:
        documents = documents[:args.limit]

    log.info("Found %d documents to parse in %s", len(documents), input_dir)

    if not documents:
        log.info("Nothing to parse.")
        return {"total": 0, "ok": 0, "skipped": 0, "failed": 0, "empty": 0}

    from collections import Counter
    ext_counts = Counter(d["filepath"].suffix.lower() for d in documents)
    for ext, count in ext_counts.most_common():
        ext_is_llm = ext in (IMAGE_EXTENSIONS | PDF_EXTENSIONS | SPREADSHEET_EXTENSIONS)
        tag = " (LLM)" if ext_is_llm else " (local)"
        log.info("  %s: %d files%s", ext, count, tag)

    if args.skip_existing:
        pending = []
        pre_skipped = 0
        for d in documents:
            if parsed_store.text_path(output_dir, d["documento_numero"]).exists():
                pre_skipped += 1
            else:
                pending.append(d)
    else:
        pending = list(documents)
        pre_skipped = 0
    log.info("To parse: %d  (already parsed/skipped: %d of %d discovered)",
             len(pending), pre_skipped, len(documents))
    progress.set_total(len(pending))

    client = _get_client() if (needs_llm and pending) else None

    stats = Counter()

    if args.workers <= 1:
        for i, doc in enumerate(pending):
            log.info("[%d/%d] %s/%s (%s)",
                     i + 1, len(pending), doc["protocolo"],
                     doc["documento_numero"], doc["filepath"].name)
            status = process_document(doc, output_dir, client, args.max_pdf_pages, args.skip_existing)
            stats[status] += 1
            progress.advance()
    else:
        def _do(doc):
            return process_document(doc, output_dir, client, args.max_pdf_pages, args.skip_existing)

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(_do, d): d for d in pending}
            for i, future in enumerate(as_completed(futures)):
                doc = futures[future]
                try:
                    status = future.result()
                except Exception as e:
                    log.error("[%d/%d] %s/%s ERROR: %s",
                              i + 1, len(pending), doc["protocolo"], doc["documento_numero"], e)
                    status = "failed"
                stats[status] += 1
                progress.advance()
                if (i + 1) % 50 == 0:
                    log.info("Progress: %d/%d (ok=%d, skipped=%d, failed=%d, empty=%d)",
                             i + 1, len(pending), stats["ok"], stats["skipped"],
                             stats["failed"], stats["empty"])

    stats["skipped"] += pre_skipped
    log.info(
        "DONE. Total: %d | Parsed: %d | Skipped: %d | Failed: %d | Empty: %d",
        len(documents), stats["ok"], stats["skipped"], stats["failed"], stats["empty"],
    )
    return {
        "total": len(documents),
        "ok": stats["ok"],
        "skipped": stats["skipped"],
        "failed": stats["failed"],
        "empty": stats["empty"],
    }


def main():
    parser = argparse.ArgumentParser(
        description="Parse downloaded SEI documents into plain text using LLM/vision models"
    )
    parser.add_argument("--input", default="./documentos_sead",
                        help="Download directory (default: ./documentos_sead)")
    parser.add_argument("--output", default="./parsed_documents",
                        help="Output directory for parsed text (default: ./parsed_documents)")
    parser.add_argument("--processo", nargs="+", default=None,
                        help="Filter by specific protocolo(s)")
    parser.add_argument("--limit", type=int, default=0,
                        help="Limit number of documents (0=all)")
    parser.add_argument("--skip-existing", action="store_true",
                        help="Skip documents already parsed")
    parser.add_argument("--max-pdf-pages", type=int, default=10,
                        help="Max PDF pages to process per document (default: 10)")
    parser.add_argument("--ext", nargs="+", default=None,
                        help="Only process these extensions (e.g. --ext .html .pdf)")
    parser.add_argument("--workers", type=int, default=1,
                        help="Parallel workers for LLM calls (default: 1, be careful with rate limits)")
    add_standard_args(parser, skip={
        "--neo4j-uri", "--neo4j-user", "--neo4j-password", "--neo4j-database",
        "--batch-size", "--workers", "--emit-json", "--read-json",
    })
    args = parser.parse_args()
    settings = resolve_settings(args)
    configure_logging(__name__, settings.log_level)
    _execute(args, settings)


from argparse import Namespace as _Namespace

from ..core._stage_base import RunContext, StageMeta
from ..core.registry import stage


def _split_flag_list(value):
    if value is None or value == "":
        return None
    if isinstance(value, (list, tuple)):
        return list(value)
    parts = [x for x in re.split(r"[,\s]+", str(value).strip()) if x]
    return parts or None


@stage(StageMeta(
    name="parse",
    phase="documents",
    question="Qual o texto plano de cada documento baixado?",
    deterministic=False,
    nondeterminism="LLM de visao / OCR; a saida varia entre execucoes identicas",
    description="Converte arquivos baixados em texto plano (HTML strip / PDF vision / OCR LLM).",
    type="enrich",
    depends_on=("download",),
    modes=("fs",),
    estimated_duration="1-2 docs/s (depende do LLM)",
))
def run(ctx: RunContext) -> None:
    args = _Namespace(
        input=ctx.flags.get("input", "./documentos_sead"),
        output=ctx.flags.get("output", "./parsed_documents"),
        processo=_split_flag_list(ctx.flags.get("processo")),
        limit=int(ctx.flags.get("limit") or 0),
        skip_existing=bool(ctx.flags.get("skip_existing", True)),
        max_pdf_pages=int(ctx.flags.get("max_pdf_pages") or 10),
        ext=_split_flag_list(ctx.flags.get("ext")),
        workers=int(ctx.flags.get("workers") or 1),
    )
    summary = _execute(args, ctx.settings, ctx.progress) or {}
    ctx.cache["parse_summary"] = summary


if __name__ == "__main__":
    main()
