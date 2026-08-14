#!/usr/bin/env python
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

DESCRIPTION = (
    "Delete derived artifacts so the pipeline can be re-run clean. Never touches the expensive "
    "irreplaceable inputs: downloaded documents, parsed text, and NER output. Dry-run by "
    "default; pass --yes to actually delete."
)

NEVER_TOUCH = (
    "documentos_sead",
    "parsed_documents",
    "ner_results",
)

TARGETS = {
    "artifacts": ("artifacts", "clustering, traces, typical, features, stats, conformance"),
    "cache": ("artifacts/cache", "document and topic embeddings, tipo reference — expensive to "
                                 "rebuild (LLM calls), keep unless the embedder changed"),
    "reports": ("reports/out", "generated markdown reports, charts and explorer.html"),
    "state": (".pipeline-state", "stage checkpoints — delete to force every stage to re-run"),
}

GRAPH_GROUP = "graph"
DEFAULT_GROUPS = ("artifacts", "state", GRAPH_GROUP)


def _entries(path: Path, keep_cache: bool) -> list[Path]:
    if not path.is_dir():
        return []
    out = []
    for child in sorted(path.iterdir()):
        if keep_cache and path.name == "artifacts" and child.name == "cache":
            continue
        out.append(child)
    return out


def _size(paths: list[Path]) -> tuple[int, int]:
    n_files = n_bytes = 0
    for p in paths:
        if p.is_file():
            n_files += 1
            n_bytes += p.stat().st_size
        else:
            for f in p.rglob("*"):
                if f.is_file():
                    n_files += 1
                    n_bytes += f.stat().st_size
    return n_files, n_bytes


def _human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024.0
    return f"{n:.1f}GB"


def _graph_counts() -> tuple[int, int] | None:
    try:
        from pipeline.core.config import Settings
        from pipeline.core.neo4j_driver import build_driver
        driver = build_driver(Settings.from_env())
        with driver.session() as s:
            nodes = s.run("MATCH (n) RETURN count(n) AS n").single()["n"]
            rels = s.run("MATCH ()-[r]->() RETURN count(r) AS n").single()["n"]
        driver.close()
        return nodes, rels
    except Exception:
        return None


def _wipe_graph() -> None:
    from pipeline.core.config import Settings
    from pipeline.core.neo4j_driver import build_driver
    from pipeline.stages.clean import clean_neo4j
    driver = build_driver(Settings.from_env())
    try:
        stats = clean_neo4j(driver)
    finally:
        driver.close()
    print(f"  graph wiped: {stats['deleted_nodes']} nodes, {stats['deleted_rels']} "
          f"relationships, {stats['dropped_constraints']} constraints dropped")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=DESCRIPTION)
    ap.add_argument("--group", action="append", choices=sorted(TARGETS) + [GRAPH_GROUP],
                    help=f"what to clean (repeatable). Default: {' '.join(DEFAULT_GROUPS)}")
    ap.add_argument("--all", action="store_true",
                    help="every group — adds the embedding cache and the generated reports")
    ap.add_argument("--yes", action="store_true", help="actually delete (default is dry-run)")
    args = ap.parse_args(argv)

    groups = (sorted(TARGETS) + [GRAPH_GROUP]) if args.all else (args.group or list(DEFAULT_GROUPS))
    keep_cache = "cache" not in groups
    wipe_graph = GRAPH_GROUP in groups

    for name in NEVER_TOUCH:
        p = _ROOT / name
        if p.exists():
            n, b = _size([p])
            print(f"  keep   {name:<18} {n:>7} files  {_human(b):>8}")

    print()
    doomed: list[Path] = []
    for g in groups:
        if g == GRAPH_GROUP:
            continue
        rel, what = TARGETS[g]
        if g == "cache" and "artifacts" in groups:
            continue
        entries = _entries(_ROOT / rel, keep_cache if g == "artifacts" else False)
        n, b = _size(entries)
        note = " (cache preserved)" if g == "artifacts" and keep_cache else ""
        if g == "artifacts" and not keep_cache:
            note = " (cache included)"
        print(f"  DELETE {rel:<18} {n:>7} files  {_human(b):>8}  — {what}{note}")
        doomed += entries

    if wipe_graph:
        counts = _graph_counts()
        if counts is None:
            print(f"  WIPE   {'neo4j':<18} {'unreachable':>7}"
                  "          — cannot connect; start it with `docker compose up -d neo4j`")
        else:
            print(f"  WIPE   {'neo4j':<18} {counts[0]:>7} nodes  {counts[1]:>8} rels"
                  "  — all nodes, relationships, constraints and indexes")

    total_files, total_bytes = _size(doomed)
    print(f"\n  total: {total_files} files, {_human(total_bytes)}"
          + (" + the whole graph" if wipe_graph else ""))

    if wipe_graph and "state" not in groups:
        print("\n  WARNING: wiping the graph without --group state leaves the stage checkpoints "
              "in place,\n  so the reload will skip every completed stage and quietly do nothing.")

    if not doomed and not wipe_graph:
        print("\nnothing to clean.")
        return 0
    if not args.yes:
        print("\ndry run — nothing deleted. Re-run with --yes to clean.")
        return 0

    for p in doomed:
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
    print(f"\ndeleted {total_files} files ({_human(total_bytes)}).")
    if wipe_graph:
        _wipe_graph()
    print("Reload from the top: `pipeline run etl --from … --to … --flag orgao=…`, then the "
          "document, feature, clustering and typical-path phases. "
          "`pipeline run artifact-audit --flag strict=true` must stay clean throughout.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
