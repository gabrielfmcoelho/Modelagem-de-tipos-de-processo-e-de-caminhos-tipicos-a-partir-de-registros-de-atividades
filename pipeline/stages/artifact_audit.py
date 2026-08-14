from __future__ import annotations

import json
import logging
from pathlib import Path

from ..core._stage_base import RunContext, StageMeta
from ..core.paths import ARTIFACTS
from ..core.registry import stage
from ..evidence.artifact import META_KEY, inputs_match, sidecar_path

log = logging.getLogger(__name__)

SKIP_DIRS = ("_backup",)
SKIP_SUFFIXES = (".log", ".tgz", ".tar")


def _candidates(root: Path):
    for f in sorted(root.rglob("*")):
        if not f.is_file():
            continue
        if any(f"/{d}/" in str(f) for d in SKIP_DIRS):
            continue
        if f.name.endswith(".meta.json") or f.suffix in SKIP_SUFFIXES:
            continue
        yield f


def _is_stamped(f: Path) -> tuple[bool, str]:
    if sidecar_path(f).is_file():
        return True, ""
    if f.suffix == ".json":
        try:
            payload = json.loads(f.read_text(encoding="utf-8"))
        except Exception as exc:
            return False, f"unreadable ({type(exc).__name__})"
        return (isinstance(payload, dict) and META_KEY in payload), ""
    return False, ""


@stage(StageMeta(
    name="artifact-audit",
    phase="operations",
    question="Todo artefato em disco declara o stage que o produziu, e suas entradas ainda "
             "batem com o que ele registrou?",
    deterministic=True,
    description="Percorre artifacts/ em todo formato e exige procedência de cada arquivo: "
                "bloco _meta para .json, sidecar <nome>.meta.json para .gz e .npz. Reporta "
                "também artefatos cujas entradas mudaram desde a escrita. --flag strict=true "
                "transforma o relatório em falha.",
    type="op",
    depends_on=(),
    modes=("neo4j", "fs"),
    can_skip_when_done=False,
    estimated_duration="<1min",
))
def run(ctx: RunContext) -> None:
    strict = str(ctx.flags.get("strict") or "").lower() in ("1", "true", "yes")
    root = Path(ctx.flags.get("root") or ARTIFACTS)

    unstamped, drifted, ok = [], [], 0
    for f in _candidates(root):
        rel = str(f.relative_to(root))
        stamped, why = _is_stamped(f)
        if not stamped:
            unstamped.append(f"{rel}{': ' + why if why else ''}")
            continue
        ok += 1
        if f.suffix == ".json":
            bad = inputs_match(f)
            if bad:
                drifted.append(f"{rel}: inputs changed {bad}")

    summary = {"stamped": ok, "unstamped": len(unstamped), "drifted": len(drifted)}
    ctx.cache["artifact_audit_summary"] = summary
    log.info("artifact-audit: %d stamped, %d without provenance, %d with drifted inputs",
             ok, len(unstamped), len(drifted))
    for x in unstamped[:20]:
        log.warning("artifact-audit: no provenance -> %s", x)
    for x in drifted:
        log.warning("artifact-audit: %s", x)
    if strict and (unstamped or drifted):
        raise RuntimeError(
            f"artifact-audit: {len(unstamped)} artifacts declare no producing stage and "
            f"{len(drifted)} have inputs that changed since they were written. An artifact "
            "without provenance cannot be traced to the question it answers — see "
            "docs/research/artifact-contract.md.")
