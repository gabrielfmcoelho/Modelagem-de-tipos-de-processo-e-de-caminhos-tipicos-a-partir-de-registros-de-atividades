from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor
import subprocess
import sys

from ..core._stage_base import RunContext, StageMeta
from ..core.registry import stage
from ..evidence.artifact import write_artifact
from ..evidence.shared.paths import RUN_MANIFEST, SHUFFLED
from ..model.typical_eval import ALPHABET_NAMES

log = logging.getLogger(__name__)

REAL_CELLS = (
    ("exp-raw", "hdbscan"), ("exp-anon", "hdbscan"),
    ("exp-raw", "kmeans"), ("exp-anon", "kmeans"),
    ("exp-raw", "leiden"), ("exp-anon", "leiden"),
    ("exp-raw-kelbow", "kmeans"), ("exp-anon-kelbow", "kmeans"),
    ("exp-raw-ksil", "kmeans"), ("exp-anon-ksil", "kmeans"),
    ("exp-raw-lres", "leiden"), ("exp-anon-lres", "leiden"),
    ("exp-raw-hcoarse", "hdbscan"), ("exp-anon-hcoarse", "hdbscan"),
)
CELLS = REAL_CELLS + tuple((run_id + SHUFFLED, algo) for run_id, algo in REAL_CELLS)
ALPHABETS = ALPHABET_NAMES


@stage(StageMeta(
    name="matrix",
    phase="typical-path",
    question="Quanto um modelo por familia preve melhor o proximo passo que os baselines?",
    deterministic='conditional',
    nondeterminism="as familias neurais treinam em GPU; markov e dfg sao deterministicos",
    description="Avalia os modelos de caminho típico em cada célula run_id×algo×alfabeto, "
                "produzindo artifacts/typical/<run_id>/<algo>/<alfabeto>/metrics.json — a base "
                "que o stage results agrega. Cada alfabeto tem a sua matriz completa e nada "
                "agrega através deles. Retomável: uma célula com metrics.json é pulada.",
    type="op",
    depends_on=("cluster-eval",),
    modes=("neo4j",),
    can_skip_when_done=False,
    estimated_duration="~20-24h (84 células: 28 combos x 3 alfabetos)",
))
def run(ctx: RunContext) -> None:
    raw_alpha = str(ctx.flags.get("alphabets") or " ".join(ALPHABETS)).replace(",", " ")
    alphabets = [a for a in raw_alpha.split() if a]
    unknown = [a for a in alphabets if a not in ALPHABET_NAMES]
    if unknown:
        raise ValueError(f"matrix: unknown alphabet(s) {unknown}")

    only_run = str(ctx.flags.get("run_id") or "").strip()
    only_algo = str(ctx.flags.get("algo") or "").strip()
    cells = [(r, a) for r, a in CELLS
             if (not only_run or r == only_run) and (not only_algo or a == only_algo)]
    if not cells:
        raise ValueError(
            f"matrix: no cell matches run_id={only_run!r} algo={only_algo!r} — "
            f"known cells: {sorted({r for r, _ in CELLS})}")

    force = str(ctx.flags.get("force") or "").lower() in ("1", "true", "yes")
    extra = [t for t in str(ctx.flags.get("args") or "").split() if t]

    total = len(cells) * len(alphabets)
    workers = max(1, int(ctx.flags.get("workers") or 1))
    jobs = []
    for alphabet in alphabets:
        for run_id, algo in cells:
            argv = [sys.executable, "-m", "pipeline.evidence.typical_path.run_typical_eval",
                    "--run-id", run_id, "--algo", algo, "--alphabet", alphabet,
                    "--emit-traces"]
            if force:
                argv.append("--force")
            argv.extend(extra)
            jobs.append((f"{run_id}/{algo}/{alphabet}", argv))

    failed: list[str] = []

    threads = max(1, (os.cpu_count() or 4) // workers)
    cell_env = dict(os.environ)
    for var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                "NUMEXPR_NUM_THREADS"):
        cell_env[var] = str(threads)

    def _run_cell(job):
        cell, argv = job
        return cell, subprocess.run(argv, check=False, env=cell_env).returncode

    if workers == 1:
        for i, job in enumerate(jobs, 1):
            log.info("matrix [%d/%d] %s", i, total, job[0])
            cell, rc = _run_cell(job)
            if rc:
                log.warning("matrix: %s exited %d", cell, rc)
                failed.append(cell)
    else:
        log.info("matrix: %d cells across %d workers. Cells are independent — each reads the "
                 "frozen traces and writes its own metrics.json — but the neural families share "
                 "one GPU, so raise this only as far as memory allows.", total, workers)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for i, (cell, rc) in enumerate(pool.map(_run_cell, jobs), 1):
                log.info("matrix [%d/%d] %s -> %s", i, total, cell, "ok" if not rc else f"rc={rc}")
                if rc:
                    failed.append(cell)

    attempted = [c for c, _ in jobs]
    write_artifact(
        {"attempted": sorted(attempted),
         "succeeded": sorted(set(attempted) - set(failed)),
         "failed": sorted(failed),
         "scope": {"alphabets": alphabets, "run_id": only_run or None,
                   "algo": only_algo or None,
                   "full_sweep": not (only_run or only_algo)
                                 and set(alphabets) == set(ALPHABETS)},
         "reading": "what this sweep tried, not what happened to be on disk afterwards. "
                    "compose-evidence reads it so a cell that died mid-run raises instead of "
                    "quietly shrinking the denominator of every aggregate it belonged to."},
        RUN_MANIFEST, stage="matrix",
        params={"alphabets": ",".join(alphabets), "workers": workers,
                "run_id": only_run, "algo": only_algo})
    ctx.cache["matrix_summary"] = {"cells": total, "alphabets": alphabets,
                                   "workers": workers, "failed": failed}
    log.info("matrix: %d cells attempted, %d failed -> %s", total, len(failed), RUN_MANIFEST)
    if failed:
        raise RuntimeError(
            f"matrix: {len(failed)}/{total} cells failed: {', '.join(failed)}. "
            "Cells that succeeded are checkpointed on disk — rerunning skips them.")
