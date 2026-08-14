from __future__ import annotations

import logging
import subprocess
import sys

from ..core._stage_base import RunContext, StageMeta
from ..core.paths import ARTIFACTS
from ..core.registry import stage
from ..model.typical_eval import ALPHABET_NAMES

log = logging.getLogger(__name__)

RUNNER = "pipeline.evidence.typical_path.run_typical_eval"

HOLDOUT_RUNS = ("exp-anon", "exp-anon-cut0.25", "exp-anon-cut0.5", "exp-anon-cut0.75")
HOLDOUT_ALPHABETS = ALPHABET_NAMES
HOLDOUT_DIR = ARTIFACTS / "typical" / "_temporal_holdout"

TRACES = ARTIFACTS / "traces" / "protocol_traces.json.gz"


def _cell(argv: list[str], label: str, failed: list[str]) -> None:
    log.info("typical-cells: %s", label)
    if subprocess.run([sys.executable, "-m", RUNNER, "--stage", "typical-cells", *argv],
                      check=False).returncode:
        log.warning("typical-cells: %s failed", label)
        failed.append(label)


@stage(StageMeta(
    name="typical-cells",
    phase="typical-path",
    question="Quanto do ganho por cluster sobrevive quando o modelo só vê o começo do "
             "histórico do processo?",
    deterministic=True,
    description="Produz artifacts/typical/_temporal_holdout/ (4 cortes x 3 alfabetos), a "
                "família de células auxiliares que o results agrega além da matriz. A família "
                "_shared_population foi removida em 2026-08-11: restringir as células a um "
                "conjunto de teste comum seleciona justamente os casos que todo método agrupou "
                "igual, e as células passaram a ser comparadas cada uma sobre a sua própria "
                "população, com os denominadores ao lado de cada número.",
    type="op",
    depends_on=("cluster-eval",),
    modes=("neo4j",),
    can_skip_when_done=False,
    estimated_duration="~10-30min (markov apenas, 12 células)",
))
def run(ctx: RunContext) -> None:
    which = str(ctx.flags.get("only") or "").strip()
    force = str(ctx.flags.get("force") or "").lower() in ("1", "true", "yes")
    if not TRACES.is_file():
        raise FileNotFoundError(
            f"typical-cells: {TRACES} is missing — run `pipeline run export-traces` first. "
            "Reading traces from Neo4j instead would evaluate a different population than the "
            "cells already on disk.")

    failed: list[str] = []
    if which in ("", "holdout"):
        HOLDOUT_DIR.mkdir(parents=True, exist_ok=True)
        for run_id in HOLDOUT_RUNS:
            for alphabet in HOLDOUT_ALPHABETS:
                out = HOLDOUT_DIR / f"{run_id}__hdbscan__{alphabet}.json"
                if out.is_file() and not force:
                    continue
                _cell(["--run-id", run_id, "--algo", "hdbscan", "--alphabet", alphabet,
                       "--models", "markov", "--traces-file", str(TRACES),
                       "--force", "--out", str(out)],
                      f"holdout {run_id}/{alphabet}", failed)

    ctx.cache["typical_cells_summary"] = {"failed": failed}
    log.info("typical-cells: done, %d failures", len(failed))
    if failed:
        raise RuntimeError(
            f"typical-cells: {len(failed)} cells failed: {', '.join(failed)}. Cells that "
            "succeeded are on disk — rerunning skips them unless --flag force=true.")
