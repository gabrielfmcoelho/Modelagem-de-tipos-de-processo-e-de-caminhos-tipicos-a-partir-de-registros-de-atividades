
import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_ROOT = next((p.parent for p in _HERE.parents if p.name == "pipeline"), _HERE.parents[2])
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from pipeline.cli import add_standard_args, resolve_settings
from ..core.cypher import CLEAR_GLINER, LINK_CARGO, LINK_CONTRATO, LINK_EMPRESA, LINK_LEGISLACAO, LINK_ORGAO, LINK_PESSOA, NER_SETUP_CONSTRAINTS, SET_DOC_PROPERTIES
from ..core.config import ConfigError
from ..core.logging_setup import configure_logging
from ..core.neo4j_driver import build_driver
from ..core.text import normalize as _normalize
from pipeline.writers import DirectNeo4jWriter, GraphWriter, JsonFileWriter

log = configure_logging(__name__)



















def _entity_text(item: object) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        canonical = item.get("canonical")
        if canonical:
            return canonical
        return item.get("text") or ""
    return ""


def _entity_provenance(item: object) -> str:
    if isinstance(item, dict):
        prov = item.get("provenance")
        if prov in ("gliner", "llm", "hybrid"):
            return prov
    return "gliner"


def _texts(entities: dict, key: str) -> list[str]:
    return [t for t in (_entity_text(e) for e in entities.get(key, [])) if t]


def _items_with_norm(entities: dict, key: str) -> list[dict]:
    out = []
    for e in entities.get(key, []):
        nome = _entity_text(e)
        if not nome:
            continue
        out.append({
            "nome": nome,
            "norm": _normalize(nome),
            "provenance": _entity_provenance(e),
        })
    return out


def _first_text(entities: dict, key: str) -> str | None:
    texts = _texts(entities, key)
    return texts[0] if texts else None


def _load_relation(writer: GraphWriter, doc_numero: str, rel_type: str,
                   pairs: list, is_person_head: bool = True) -> None:
    if not pairs:
        return

    clean_pairs = []
    for pair in pairs:
        if len(pair) >= 2:
            head = str(pair[0]).strip()
            tail = str(pair[1]).strip()
            clean_pairs.append({
                "head": head, "head_norm": _normalize(head),
                "tail": tail, "tail_norm": _normalize(tail),
            })

    if not clean_pairs:
        return

    if is_person_head:
        cypher = f"""
        MATCH (d:Documento {{numero: $doc_numero}})
        UNWIND $pairs AS pair
        MERGE (p:PessoaFisica {{nome_normalizado: pair.head_norm}})
        ON CREATE SET p.nome = pair.head
        MERGE (p)-[r:{rel_type}]->(d)
        SET r.objeto = pair.tail
        """
    else:
        cypher = f"""
        MATCH (d:Documento {{numero: $doc_numero}})
        UNWIND $pairs AS pair
        MERGE (p:PessoaFisica {{nome_normalizado: pair.tail_norm}})
        ON CREATE SET p.nome = pair.tail
        MERGE (d)-[r:{rel_type}]->(p)
        SET r.agente = pair.head
        """

    writer.execute_template(
        f"link_rel_{rel_type.lower()}",
        cypher,
        {"doc_numero": doc_numero, "pairs": clean_pairs},
        phase="gliner",
    )



def load_document(
    writer: GraphWriter | None,
    data: dict,
    *,
    dry_run: bool = False,
    read_driver: object | None = None,
) -> bool:
    doc_numero = data["documento_numero"]
    entities = data.get("entities", {})
    classification = data.get("classification", {})
    relations = data.get("relations", {})

    if dry_run:
        ent_count = sum(len(v) for v in entities.values())
        rel_count = sum(len(v) for v in relations.values())
        log.info("  [DRY-RUN] doc %s: %d entities, %d relations, tipo=%s",
                 doc_numero, ent_count, rel_count, classification.get("tipo_documento", "?"))
        return True

    assert writer is not None, "load_document called without writer outside dry-run"

    if read_driver is not None:
        with read_driver.session() as session:
            result = session.run(
                "MATCH (d:Documento {numero: $n}) RETURN d.numero",
                n=doc_numero,
            ).single()
        if not result:
            log.warning("  Document %s not found in Neo4j — skipping", doc_numero)
            return False

    writer.execute_template(
        "set_doc_properties",
        SET_DOC_PROPERTIES,
        {
            "doc_numero": doc_numero,
            "tipo_documento": classification.get("tipo_documento"),
            "assunto": _first_text(entities, "assunto"),
            "emails": _texts(entities, "email"),
            "cpfs": _texts(entities, "cpf"),
            "cnpjs": _texts(entities, "cnpj"),
            "matriculas": _texts(entities, "matricula"),
            "telefones": _texts(entities, "telefone"),
            "urls": _texts(entities, "url"),
            "valores": _texts(entities, "valor_monetario"),
            "datas": _texts(entities, "data"),
            "enderecos": _texts(entities, "endereco"),
            "objeto_licitacao": _first_text(entities, "objeto_licitacao"),
            "vigencia": _first_text(entities, "vigencia"),
            "model": data.get("model", ""),
            "extracted_at": data.get("extracted_at", ""),
        },
        phase="gliner",
    )

    pessoas = _items_with_norm(entities, "pessoa")
    if pessoas:
        writer.execute_template("link_pessoa", LINK_PESSOA,
                                {"doc_numero": doc_numero, "items": pessoas},
                                phase="gliner")

    empresas = _items_with_norm(entities, "pessoa_juridica")
    if empresas:
        writer.execute_template("link_empresa", LINK_EMPRESA,
                                {"doc_numero": doc_numero, "items": empresas},
                                phase="gliner")

    orgao_items = [
        {"nome": _entity_text(e), "provenance": _entity_provenance(e)}
        for e in entities.get("orgao", []) if _entity_text(e)
    ]
    if orgao_items:
        writer.execute_template("link_orgao", LINK_ORGAO,
                                {"doc_numero": doc_numero, "items": orgao_items},
                                phase="gliner")

    cargos = _items_with_norm(entities, "cargo")
    if cargos:
        writer.execute_template("link_cargo", LINK_CARGO,
                                {"doc_numero": doc_numero, "items": cargos},
                                phase="gliner")

    leg_items = []
    for tipo_leg in ("lei", "decreto", "portaria"):
        for e in entities.get(tipo_leg, []):
            ref = _entity_text(e)
            if not ref:
                continue
            leg_items.append({
                "ref": ref,
                "tipo": tipo_leg,
                "provenance": _entity_provenance(e),
            })
    if leg_items:
        writer.execute_template("link_legislacao", LINK_LEGISLACAO,
                                {"doc_numero": doc_numero, "items": leg_items},
                                phase="gliner")

    contrato_items = [
        {"ref": _entity_text(e), "provenance": _entity_provenance(e)}
        for e in entities.get("contrato_edital", []) if _entity_text(e)
    ]
    if contrato_items:
        writer.execute_template("link_contrato", LINK_CONTRATO,
                                {"doc_numero": doc_numero, "items": contrato_items},
                                phase="gliner")

    PERSON_HEAD_RELS = {"assinou": "ASSINOU", "autorizou": "AUTORIZOU",
                        "solicitou": "SOLICITOU", "contratou": "CONTRATOU"}
    ENTITY_HEAD_RELS = {"nomeou": "NOMEOU", "designou": "DESIGNOU",
                        "exonerou": "EXONEROU", "encaminhou_para": "ENCAMINHOU_PARA_DOC"}

    for rel_key, rel_type in PERSON_HEAD_RELS.items():
        _load_relation(writer, doc_numero, rel_type, relations.get(rel_key, []), is_person_head=True)

    for rel_key, rel_type in ENTITY_HEAD_RELS.items():
        _load_relation(writer, doc_numero, rel_type, relations.get(rel_key, []), is_person_head=False)

    return True


def _execute(
    args,
    settings,
    *,
    writer: GraphWriter | None = None,
    driver=None,
) -> dict:
    input_dir = Path(args.input)
    if not input_dir.exists():
        log.error("Input directory not found: %s", input_dir)
        sys.exit(1)

    files = sorted(f for f in input_dir.iterdir() if f.suffix == ".json")
    if args.limit > 0:
        files = files[:args.limit]

    log.info("Found %d GLiNER result files in %s", len(files), input_dir)
    if not files:
        log.info("Nothing to load.")
        return {"total": 0, "loaded": 0, "not_found": 0, "errors": 0}

    own_writer = False
    own_driver = False
    if writer is None and not args.dry_run:
        if settings.emit_json_dir is not None:
            log.info("Emitting GLiNER writes to %s", settings.emit_json_dir)
            writer = JsonFileWriter(settings.emit_json_dir)
            own_writer = True
        else:
            try:
                driver = build_driver(settings)
                log.info("Connected to Neo4j: %s", settings.neo4j_uri)
            except ConfigError as e:
                log.error("%s", e)
                sys.exit(2)
            except Exception as e:
                log.error("Failed to connect to Neo4j at %s: %s", settings.neo4j_uri, e)
                sys.exit(1)
            writer = DirectNeo4jWriter(driver, batch_size=settings.batch_size or 1000)
            own_writer = own_driver = True

    try:
        if writer is not None:
            writer.open_phase("gliner")
            log.info("Creating constraints...")
            for cypher in NER_SETUP_CONSTRAINTS:
                try:
                    writer.execute_template("gliner_constraint", cypher, {}, phase="gliner")
                except Exception as e:
                    log.debug("Constraint: %s", e)

            if args.clear_first:
                log.info("Clearing previous GLiNER data...")
                for cypher in CLEAR_GLINER:
                    writer.execute_template("gliner_clear", cypher, {}, phase="gliner")
                log.info("Cleared.")

        loaded = 0
        skipped = 0
        not_found = 0
        for i, filepath in enumerate(files):
            log.info("[%d/%d] Loading %s", i + 1, len(files), filepath.name)
            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
                found = load_document(writer, data, dry_run=args.dry_run, read_driver=driver)
                if found:
                    loaded += 1
                else:
                    not_found += 1
            except Exception as e:
                log.error("  ERROR loading %s: %s", filepath.name, e)
                skipped += 1

        if writer is not None:
            writer.close_phase("gliner")

        log.info(
            "DONE. Loaded: %d | Not found in Neo4j: %d | Errors: %d | Total: %d",
            loaded, not_found, skipped, len(files),
        )
        return {
            "total": len(files),
            "loaded": loaded,
            "not_found": not_found,
            "errors": skipped,
        }
    finally:
        if own_writer and writer is not None:
            writer.close()
        if own_driver and driver is not None:
            driver.close()


def main():
    parser = argparse.ArgumentParser(
        description="Load GLiNER2 extraction results into Neo4j (or NDJSON via --emit-json)"
    )
    parser.add_argument("--input", default="./ner_results",
                        help="Directory with GLiNER JSON outputs (default: ./ner_results)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Only show what would be loaded")
    parser.add_argument("--clear-first", action="store_true",
                        help="Remove all previous GLiNER data before loading")
    parser.add_argument("--limit", type=int, default=0,
                        help="Limit number of files to process (0=all)")
    add_standard_args(parser, skip={"--read-json"})
    args = parser.parse_args()
    settings = resolve_settings(args)
    configure_logging(__name__, settings.log_level)
    _execute(args, settings)


from argparse import Namespace as _Namespace

from ..core._stage_base import RunContext, StageMeta
from ..core.registry import stage


@stage(StageMeta(
    name="ner-load",
    phase="documents",
    question="Como as entidades extraidas se ligam ao grafo?",
    deterministic=True,
    description="Carrega entidades GLiNER no grafo (PessoaFisica, Legislacao, Contrato, …).",
    type="enrich",
    depends_on=("ner-extract",),
    soft_depends_on=("atividades",),
    modes=("neo4j", "json-emit"),
    estimated_duration="~5-10min para 10k docs",
))
def run(ctx: RunContext) -> None:
    args = _Namespace(
        input=ctx.flags.get("input", "./ner_results"),
        dry_run=bool(ctx.flags.get("dry_run", False)),
        clear_first=bool(ctx.flags.get("clear_first", False)),
        limit=int(ctx.flags.get("limit") or 0),
    )
    summary = _execute(
        args, ctx.settings,
        writer=ctx.writer,
        driver=ctx.driver,
    ) or {}
    ctx.cache["ner_load_summary"] = summary


if __name__ == "__main__":
    main()
