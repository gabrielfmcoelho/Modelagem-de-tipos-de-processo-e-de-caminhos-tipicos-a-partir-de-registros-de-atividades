
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

from ..core.deployment import ENDERECO_EXEMPLO, ORGAO_DOMINIO, ORGAO_SIGLA, ORGAOS_IRMAOS
from ..core import parsed_store
from pipeline.cli import add_standard_args, resolve_settings
from ..core.constants import LABEL_TO_KEY
from ..model.ner.gliner import (
    DEFAULT_CHUNK_CHARS,
    DEFAULT_CHUNK_OVERLAP,
    _clean_entities,
    _clean_relations,
    _dedup_entities,
    _detect_chunk_size,
    chunk_text,
    merge_entities,
)
from ..core.logging_setup import configure_logging

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
















def discover_parsed_documents(
    parsed_dir,
    protocolos: list[str] | None = None,
    limit: int = 0,
    shard: str | None = None,
) -> list[dict]:
    allowed = None
    if protocolos:
        allowed = set()
        for p in protocolos:
            allowed |= {p, p.replace("/", "_"), p.replace("_", "/")}

    docs: list[dict] = []
    for pd in parsed_store.iter_parsed_documents(Path(parsed_dir)):
        meta = {}
        if pd.meta_path.is_file():
            try:
                meta = json.loads(pd.meta_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                meta = {}
        protocolo = meta.get("protocolo", "")
        if allowed is not None and protocolo not in allowed:
            continue
        docs.append({
            "documento_numero": pd.doc_id,
            "protocolo": protocolo,
            "source_file": meta.get("source_file", ""),
            "text_path": pd.text_path,
        })
    if shard:
        k, n = (int(x) for x in str(shard).split("/", 1))
        if not (n > 0 and 0 <= k < n):
            raise ValueError(f"invalid shard={shard!r} — expected K/N with 0 <= K < N")
        docs = docs[k::n]
    if limit and limit > 0:
        docs = docs[:limit]
    return docs


def main():
    parser = argparse.ArgumentParser(
        description="Extract NER entities from downloaded SEI documents using GLiNER2"
    )
    parser.add_argument(
        "--input", default="./parsed_documents",
        help="Parsed-documents directory (default: ./parsed_documents)",
    )
    parser.add_argument(
        "--output", default="./ner_results",
        help="Output directory for JSON results (default: ./ner_results)",
    )
    parser.add_argument(
        "--model", default="fastino/gliner2-base-v1",
        help="GLiNER2 model name (default: fastino/gliner2-base-v1)",
    )
    parser.add_argument(
        "--labels", nargs="+", default=None,
        help="Entity labels to extract (default: governo/admin labels)",
    )
    parser.add_argument(
        "--threshold", type=float, default=0.3,
        help="Minimum confidence threshold for entities (default: 0.3)",
    )
    parser.add_argument(
        "--flat-ner", action="store_true", default=True,
        help="Use flat NER mode (default: True)",
    )
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Limit number of documents to process (0=all)",
    )
    parser.add_argument(
        "--skip-existing", action="store_true",
        help="Skip documents that already have a JSON output file",
    )
    parser.add_argument(
        "--processo", nargs="+", default=None,
        help="Specific protocolo(s) to process (directory names, e.g. '00019.000123_2025-01')",
    )
    parser.add_argument(
        "--mode", default="hybrid", choices=["gliner2", "llm", "hybrid"],
        help="NER mode: gliner2 (fast, current), llm (Mandu only), hybrid (gliner2+llm cleanup, default)",
    )
    parser.add_argument(
        "--shard", default=None,
        help="Process only shard K/N of the corpus (e.g. 0/3), for parallel workers",
    )
    add_standard_args(parser, skip={
        "--neo4j-uri", "--neo4j-user", "--neo4j-password", "--neo4j-database",
        "--batch-size", "--workers", "--emit-json", "--read-json",
    })
    args = parser.parse_args()
    settings = resolve_settings(args)
    configure_logging(__name__, settings.log_level)
    _execute(args, settings)


def _execute(args, settings) -> dict:
    labels = args.labels or DEFAULT_LABELS
    input_dir = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    mode = (getattr(args, "mode", None) or "hybrid").lower()
    if mode not in ("gliner2", "llm", "hybrid"):
        log.error("invalid mode=%s — expected gliner2|llm|hybrid", mode)
        sys.exit(2)
    log.info("ner-extract mode: %s", mode)

    shard = getattr(args, "shard", None)
    documents = discover_parsed_documents(input_dir, args.processo, args.limit, shard=shard)

    log.info("Found %d parsed documents in %s (shard=%s)", len(documents), input_dir, shard or "-")

    if not documents:
        log.info("Nothing to process.")
        return

    extractor = None
    max_chunk_chars = 1800
    chunk_overlap = 200
    if mode in ("gliner2", "hybrid"):
        from ..core.devices import select_device

        device = select_device()
        log.info("Loading GLiNER2 model: %s on %s", args.model, device)
        try:
            from gliner2 import GLiNER2
        except ImportError:
            log.error("gliner2 is required: pip install gliner2")
            sys.exit(1)
        extractor = GLiNER2.from_pretrained(args.model, map_location=device)
        if device != "cpu":
            try:
                actual = str(next(extractor.parameters()).device)
            except (StopIteration, AttributeError):
                actual = "unknown"
            if not actual.startswith(device):
                log.warning("GLiNER2 not on %s (actual=%s) — trying .to()", device, actual)
                extractor = extractor.to(device)
        log.info("Model loaded successfully (device=%s)", device)
        max_chunk_chars, chunk_overlap = _detect_chunk_size(extractor)

    ner_llm = None
    if mode in ("llm", "hybrid"):
        from ..model.ner_llm import NerLLM, config_from_settings
        ner_llm = NerLLM(config_from_settings(settings))
        log.info("LLM ready: model=%s base_url=%s", ner_llm.config.model, ner_llm.config.base_url)

    processed = 0
    skipped = 0
    failed = 0

    for doc in documents:
        doc_id = doc["documento_numero"]
        output_file = output_dir / f"{doc_id}.json"

        if args.skip_existing and output_file.exists():
            skipped += 1
            continue

        log.info("[%d/%d] Processing %s/%s", processed + skipped + failed + 1, len(documents), doc["protocolo"], doc_id)

        text = doc["text_path"].read_text(encoding="utf-8", errors="replace")
        if not text or len(text.strip()) < 10:
            log.warning("No parsed text for %s — skipping", doc_id)
            failed += 1
            continue

        entities: dict[str, list[dict]] = {}
        classification: dict = {}
        relations: dict[str, list] = {}
        consolidation_metrics: dict = {}
        gliner_entities_before_llm: dict[str, list[dict]] = {}
        used_model_label = args.model

        if mode in ("gliner2", "hybrid"):
            chunks = chunk_text(text, max_chars=max_chunk_chars, overlap=chunk_overlap)
            all_chunk_entities = []
            all_chunk_relations = []
            all_chunk_classifications = []

            for i, chunk in enumerate(chunks):
                try:
                    ner_result = extractor.extract_entities(chunk, labels)
                    all_chunk_entities.append(ner_result.get("entities", {}))
                except Exception as e:
                    log.warning("NER failed on chunk %d of %s: %s", i, doc_id, e)

                if i == 0:
                    try:
                        cls_result = extractor.classify_text(chunk, {
                            "tipo_documento": [
                                "licitacao", "contrato", "parecer_juridico", "oficio",
                                "portaria", "despacho", "nota_tecnica", "ata",
                                "termo_referencia", "certidao", "declaracao", "requerimento",
                            ]
                        })
                        all_chunk_classifications.append(cls_result)
                    except Exception as e:
                        log.debug("Classification failed on chunk %d of %s: %s", i, doc_id, e)

                try:
                    rel_result = extractor.extract_relations(chunk, [
                        "autorizou", "assinou", "encaminhou_para", "solicitou",
                        "contratou", "nomeou", "exonerou", "designou",
                    ])
                    rel_data = rel_result.get("relation_extraction", {})
                    if any(v for v in rel_data.values()):
                        all_chunk_relations.append(rel_data)
                except Exception as e:
                    log.debug("Relation extraction failed on chunk %d of %s: %s", i, doc_id, e)

            if not all_chunk_entities:
                log.warning("No entities extracted from %s", doc_id)
                failed += 1
                continue

            for chunk_ents in all_chunk_entities:
                for label, values in chunk_ents.items():
                    if label not in entities:
                        entities[label] = []
                    for val in values:
                        text_val = val if isinstance(val, str) else str(val)
                        existing = {e["text"].strip().lower() for e in entities[label]}
                        if text_val.strip().lower() not in existing:
                            entities[label].append({"text": text_val})

            for chunk_rels in all_chunk_relations:
                for rel_type, pairs in chunk_rels.items():
                    if not pairs:
                        continue
                    if rel_type not in relations:
                        relations[rel_type] = []
                    for pair in pairs:
                        if pair not in relations[rel_type]:
                            relations[rel_type].append(pair)

            classification = all_chunk_classifications[0] if all_chunk_classifications else {}

            entities = _clean_entities(entities)
            relations = _clean_relations(relations)

            if mode == "hybrid":
                gliner_entities_before_llm = {k: list(v) for k, v in entities.items()}

        if mode == "llm":
            try:
                llm_out = ner_llm.extract(text)
                entities = llm_out.get("entities", {})
                classification = llm_out.get("classification", {}) or classification
                relations = llm_out.get("relations", {}) or relations
                used_model_label = f"llm-only:{ner_llm.config.model}"
            except Exception as e:
                log.error("LLM extract failed for %s: %s", doc_id, e)
                failed += 1
                continue

        elif mode == "hybrid":
            try:
                llm_clean = ner_llm.consolidate(text, {
                    "entities": entities, "classification": classification,
                })
                entities_after = llm_clean.get("entities", {})
                from ..model.ner_llm import diff_metrics
                consolidation_metrics = diff_metrics(gliner_entities_before_llm, entities_after)
                entities = entities_after
                if llm_clean.get("classification"):
                    classification = llm_clean["classification"]
                used_model_label = f"{args.model}+llm-cleanup:{ner_llm.config.model}"
            except Exception as e:
                log.warning("LLM consolidate failed for %s — keeping GLiNER output: %s", doc_id, e)
                used_model_label = f"{args.model}+llm-cleanup-failed"

        from ..model.ner_llm import normalize_entity_record
        normalized: dict[str, list[dict]] = {}
        for label, items in entities.items():
            normalized[label] = [normalize_entity_record(it) for it in items]
            for rec in normalized[label]:
                if rec["provenance"] not in ("gliner", "llm", "hybrid"):
                    rec["provenance"] = (
                        "gliner" if mode == "gliner2"
                        else "llm" if mode == "llm"
                        else "hybrid"
                    )
        entities = normalized

        output_data = {
            "documento_numero": doc_id,
            "protocolo": doc["protocolo"],
            "source_file": doc.get("source_file", ""),
            "model": used_model_label,
            "mode": mode,
            "labels": [LABEL_TO_KEY.get(label, label) for label in labels],
            "entities": entities,
            "classification": classification,
            "relations": relations,
            "extracted_at": datetime.now(UTC).isoformat(),
        }
        if consolidation_metrics:
            output_data["consolidation_metrics"] = consolidation_metrics

        output_file.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")
        processed += 1
        entity_count = sum(len(v) for v in entities.values())
        relation_count = sum(len(v) for v in relations.values())
        cls_label = classification.get("tipo_documento", "?")
        log.info("  → %d entities, %d relations, tipo=%s, mode=%s → %s",
                 entity_count, relation_count, cls_label, mode, output_file.name)

    log.info(
        "DONE. Processed: %d | Skipped: %d | Failed: %d | Total: %d",
        processed, skipped, failed, len(documents),
    )
    return {
        "total": len(documents),
        "processed": processed,
        "skipped": skipped,
        "failed": failed,
    }


from argparse import Namespace as _Namespace

from ..core._stage_base import RunContext, StageMeta
from ..core.registry import stage


@stage(StageMeta(
    name="ner-extract",
    phase="documents",
    question="Que entidades nomeadas aparecem no documento de abertura?",
    deterministic='conditional',
    nondeterminism="fixo enquanto a versao do modelo GLiNER2 nao muda",
    description="Extrai entidades nomeadas do texto parseado (parsed_documents) via GLiNER2.",
    type="enrich",
    depends_on=("parse",),
    modes=("fs",),
    estimated_duration="3-10s/doc dependendo do tamanho + modelo",
))
def run(ctx: RunContext) -> None:
    args = _Namespace(
        input=ctx.flags.get("input", "./parsed_documents"),
        output=ctx.flags.get("output", "./ner_results"),
        model=ctx.flags.get("model", "fastino/gliner2-base-v1"),
        labels=ctx.flags.get("labels"),
        threshold=float(ctx.flags.get("threshold") or 0.3),
        flat_ner=bool(ctx.flags.get("flat_ner", True)),
        limit=int(ctx.flags.get("limit") or 0),
        skip_existing=bool(ctx.flags.get("skip_existing", True)),
        processo=ctx.flags.get("processo"),
        mode=ctx.flags.get("mode", "hybrid"),
        shard=ctx.flags.get("shard"),
    )
    summary = _execute(args, ctx.settings) or {}
    ctx.cache["ner_extract_summary"] = summary


if __name__ == "__main__":
    main()
