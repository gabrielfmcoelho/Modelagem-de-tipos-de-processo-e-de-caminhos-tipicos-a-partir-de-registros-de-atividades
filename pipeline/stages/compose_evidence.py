from __future__ import annotations

import json
import logging

from ..core._stage_base import RunContext, StageMeta
from ..core.registry import stage
from ..evidence.compose import cell_key
from ..evidence.compose.compare import (ablation_cells, compare_algorithms, compare_arms,
                                        compare_models, compare_populations)
from ..evidence.compose.envelope import IncompleteAggregate, write_composed
from ..evidence.shared.paths import RUN_MANIFEST
from ..evidence.compose.lattice import ALPHABETS, ARMS, MODELS
from ..evidence.compose.levels import (agreement, arm_path_summary, arm_summary, by_alphabet,
                                       by_model, clusters_index)
from ..evidence.typical_path.figures import load_cells

log = logging.getLogger(__name__)


def _check_manifest(cells: list[dict], *, allow_missing: bool) -> None:
    if not RUN_MANIFEST.is_file():
        log.warning(
            "compose-evidence: %s is absent, so completeness is judged against whatever is on "
            "disk. A cell that died during the sweep is indistinguishable from one that was "
            "never attempted. Run `matrix` to produce it.", RUN_MANIFEST)
        return
    manifest = json.loads(RUN_MANIFEST.read_text(encoding="utf-8"))
    present = {cell_key(c) for c in cells}
    succeeded = set(manifest.get("succeeded") or ())
    failed = sorted(manifest.get("failed") or ())
    lost = sorted(succeeded - present)
    stale = sorted(present - set(manifest.get("attempted") or ())) if manifest.get(
        "scope", {}).get("full_sweep", True) else []
    if not manifest.get("scope", {}).get("full_sweep", True):
        log.warning("compose-evidence: the manifest records a partial sweep (%s); completeness "
                    "is checked only over the cells it covers.", manifest.get("scope"))
    problems = []
    if failed:
        problems.append(f"{len(failed)} cell(s) failed during the sweep: {', '.join(failed)}")
    if lost:
        problems.append(f"{len(lost)} cell(s) the sweep recorded as succeeded are not on disk: "
                        f"{', '.join(lost)}")
    if stale:
        problems.append(f"{len(stale)} cell(s) are on disk that the last full sweep never "
                        f"attempted, so they are left over from an earlier run and would be "
                        f"aggregated as if current: {', '.join(stale)}")
    if problems and not allow_missing:
        raise IncompleteAggregate(
            "; ".join(problems) + ". Every aggregate below would exclude them without saying "
            "so, which is how a skipped GPU cell becomes a headline number. Re-run the missing "
            "cells, or pass --flag allow_missing=true to compose over what survives.")
    for p in problems:
        log.warning("compose-evidence: %s (allowed by --flag allow_missing)", p)


@stage(StageMeta(
    name="compose-evidence",
    phase="delivery",
    question="Como cada nivel da grade experimental se compara ao seu vizinho, sobre uma "
             "populacao declarada e um conjunto de membros completo?",
    deterministic=True,
    description="Deriva os artefatos compostos a partir das celulas: resumo por braco (L1), "
                "concordancia entre agrupamentos (L2), indices por cluster (L5), recortes por "
                "modelo e por alfabeto (L4) e as cinco comparacoes transversais. Todo artefato "
                "declara o ponto da grade que ocupa, a populacao que cobre e os membros que "
                "agregou; um agregado incompleto falha em vez de encolher o denominador.",
    type="op",
    depends_on=("matrix",),
    modes=("neo4j", "fs"),
    can_skip_when_done=False,
    estimated_duration="<1min",
))
def run(ctx: RunContext) -> None:
    cells = load_cells()
    if not cells:
        raise FileNotFoundError(
            "compose-evidence found no typical-path cells. It derives every composed artifact "
            "from artifacts/typical/<run_id>/<algo>/<alphabet>/metrics.json; run `matrix` and "
            "`typical-cells` first.")

    written = []

    def _emit(path, payload, inputs=()):
        write_composed(payload, path, stage="compose-evidence", inputs=inputs)
        written.append(path)

    _check_manifest(cells, allow_missing=str(ctx.flags.get("allow_missing") or "").lower()
                    in ("1", "true", "yes"))

    alphabets = [a for a in ALPHABETS if any(c["alphabet"] == a for c in cells)]
    absent = [a for a in ALPHABETS if a not in alphabets]
    if absent:
        log.warning("compose-evidence: no cells for alphabet(s) %s — every artifact below is "
                    "composed over %s only. Run `matrix --flag alphabets=%s` to complete the "
                    "grid; nothing here pools one alphabet into another.",
                    ", ".join(absent), ", ".join(alphabets), ",".join(absent))

    arms = sorted({c["arm"] for c in cells} & set(ARMS))
    for arm in arms:
        _emit(*arm_summary(arm, cells))
        for alphabet in alphabets:
            _emit(*arm_path_summary(arm, alphabet, cells))

    siblings = sorted({(c["run_id"], c["algo"]) for c in cells})
    for run_id, algo in siblings:
        same_arm = [(r, a) for r, a in siblings
                    if ("anon" in r) == ("anon" in run_id)]
        _emit(*agreement(run_id, algo, same_arm))

    for cell in cells:
        _emit(*clusters_index(cell))

    for alphabet in alphabets:
        for model in MODELS:
            _emit(*by_model(model, alphabet, cells))
        _emit(*by_alphabet(alphabet, cells))
        for fn in (compare_arms, compare_algorithms, compare_models, compare_populations):
            _emit(*fn(cells, alphabet))
    for path, payload in ablation_cells(cells):
        _emit(path, payload)

    ctx.cache["compose_evidence"] = {"cells": len(cells), "artifacts": len(written)}
    log.info("compose-evidence: %d cells -> %d composed artifacts", len(cells), len(written))
    log.info("compose-evidence: cells covered %s", ", ".join(sorted(cell_key(c) for c in cells)))
