
from __future__ import annotations

import argparse
import shutil
import sys as _sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_ROOT = next((p.parent for p in _HERE.parents if p.name == "pipeline"), _HERE.parents[2])
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))

from ..core._stage_base import RunContext, StageMeta
from pipeline.cli import add_standard_args, resolve_settings
from ..core.logging_setup import configure_logging
from ..core.neo4j_driver import build_driver
from ..core.registry import stage

log = configure_logging(__name__)


def clean_neo4j(driver) -> dict:
    with driver.session() as session:
        result = session.run("MATCH (n) RETURN count(n) AS nodes")
        rec = result.single()
    total_nodes = rec["nodes"]
    log.info("Found %d nodes to delete", total_nodes)

    deleted_rels = 0
    while True:
        with driver.session() as session:
            result = session.run(
                "MATCH ()-[r]->() WITH r LIMIT 5000 DELETE r RETURN count(*) AS cnt"
            )
            batch = result.single()["cnt"]
        if batch == 0:
            break
        deleted_rels += batch
        if deleted_rels % 50000 == 0 or batch < 5000:
            log.info("  Deleted %d relationships", deleted_rels)

    log.info("All %d relationships deleted", deleted_rels)

    deleted_nodes = 0
    while True:
        with driver.session() as session:
            result = session.run(
                "MATCH (n) WITH n LIMIT 10000 DELETE n RETURN count(*) AS cnt"
            )
            batch = result.single()["cnt"]
        if batch == 0:
            break
        deleted_nodes += batch
        if deleted_nodes % 50000 == 0 or batch < 10000:
            log.info("  Deleted %d / %d nodes", deleted_nodes, total_nodes)

    log.info("All %d nodes deleted", deleted_nodes)

    with driver.session() as session:
        result = session.run("SHOW CONSTRAINTS")
        constraints = [r["name"] for r in result]
    for name in constraints:
        with driver.session() as session:
            session.run(f"DROP CONSTRAINT {name} IF EXISTS")
        log.info("  Dropped constraint: %s", name)

    with driver.session() as session:
        result = session.run("SHOW INDEXES")
        indexes = [r["name"] for r in result if r["type"] != "LOOKUP"]
    for name in indexes:
        with driver.session() as session:
            session.run(f"DROP INDEX {name} IF EXISTS")
        log.info("  Dropped index: %s", name)

    log.info("Cleanup complete")
    return {
        "deleted_nodes": deleted_nodes,
        "deleted_rels": deleted_rels,
        "dropped_constraints": len(constraints),
        "dropped_indexes": len(indexes),
    }


clean = clean_neo4j


def clean_json_dir(emit_dir: Path) -> dict:
    if not emit_dir.exists():
        log.info("Emit directory %s does not exist — nothing to clean.", emit_dir)
        return {"deleted_dir": False, "path": str(emit_dir)}
    shutil.rmtree(emit_dir)
    log.info("Removed emit directory: %s", emit_dir)
    return {"deleted_dir": True, "path": str(emit_dir)}


def main():
    parser = argparse.ArgumentParser(description="Clean graph state (Neo4j or emit-dir)")
    parser.add_argument("--force", action="store_true", help="Skip confirmation")
    add_standard_args(parser)
    args = parser.parse_args()

    settings = resolve_settings(args)
    configure_logging(__name__, settings.log_level)

    if settings.emit_json_dir is not None:
        target = Path(settings.emit_json_dir)
        if not args.force:
            answer = input(f"This will DELETE {target}. Continue? [y/N] ")
            if answer.lower() != "y":
                log.info("Aborted")
                return
        clean_json_dir(target)
        return

    driver = build_driver(settings)
    log.info("Connected to Neo4j: %s", settings.neo4j_uri)
    try:
        if not args.force:
            answer = input("This will DELETE ALL DATA in Neo4j. Continue? [y/N] ")
            if answer.lower() != "y":
                log.info("Aborted")
                return
        clean_neo4j(driver)
    finally:
        driver.close()


@stage(StageMeta(
    name="clean",
    phase="operations",
    question="Operacional: remover estado para comecar do zero.",
    deterministic=True,
    description="Apaga estado do grafo (Neo4j) ou diretório de emit JSON.",
    type="op",
    depends_on=(),
    modes=("neo4j", "json-emit"),
    can_skip_when_done=False,
    estimated_duration="<1min",
))
def run(ctx: RunContext) -> None:
    if ctx.mode == "json-emit":
        emit_dir = Path(ctx.flags.get("emit_dir") or ctx.settings.emit_json_dir or "./graphify-out")
        ctx.cache["clean_summary"] = clean_json_dir(emit_dir)
        return

    driver = ctx.require_driver()
    ctx.cache["clean_summary"] = clean_neo4j(driver)


if __name__ == "__main__":
    main()
