from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np

from ..evidence.clustering import select_k as sk
from ..evidence.artifact import write_artifact
from ..core._stage_base import RunContext, StageMeta
from ..core.registry import stage
from ..core.paths import ARTIFACTS

log = logging.getLogger(__name__)


@stage(StageMeta(
    name="select-k",
    phase="features",
    question="Que k e que resolucao as varreduras selecionam, e algum optimo caiu na borda da grade?",
    deterministic='conditional',
    nondeterminism="varreduras fixadas pelo seed registrado em params",
    description="Varre k (kmeans) e resolution (leiden) e persiste a seleção para o cluster-eval.",
    type="op",
    depends_on=("processo-embed",),
    modes=("neo4j", "fs"),
    can_skip_when_done=False,
    estimated_duration="~2-6min por arm",
))
def run(ctx: RunContext) -> None:
    from .cluster_eval import _ARM_VARIANT, _arm_of, _load_features_from_npz

    run_id = ctx.flags.get("run_id")
    if not run_id:
        raise ValueError("select-k requires --flag run_id=<id>")
    features_file = ctx.flags.get("features_file")
    arm = _arm_of(run_id)
    if arm and not features_file:
        raise ValueError(
            f"run_id={run_id!r} names the {arm!r} arm, but no features_file was given. "
            f"Pass --flag features_file=artifacts/features/{arm}.npz"
        )
    protocolos, features, stamp = _load_features_from_npz(features_file)
    want, got = _ARM_VARIANT.get(arm or ""), stamp.get("text_variant")
    if want and got and got not in ("unknown", want):
        raise ValueError(
            f"run_id={run_id!r} is the {want!r} arm but {features_file} was built from "
            f"text_variant={got!r}. Refusing to select parameters on the wrong arm."
        )

    seed = int(ctx.flags.get("seed") or 42)
    lam = float(ctx.flags.get("redundancy_lambda") or 0.05)
    k_min = int(ctx.flags.get("k_min") or 20)
    k_max = int(ctx.flags.get("k_max") or 320)
    k_step = int(ctx.flags.get("k_step") or 10)
    r_min = float(ctx.flags.get("res_min") or 0.4)
    r_max = float(ctx.flags.get("res_max") or 4.0)
    r_step = float(ctx.flags.get("res_step") or 0.2)

    X = np.asarray(features, dtype=np.float64)
    out_dir = ARTIFACTS / "clustering" / run_id

    ks = list(range(k_min, k_max + 1, k_step))
    rows, _ = sk.sweep_kmeans(X, ks, seed)
    k_elbow = ks[sk.elbow_index([r["k"] for r in rows], [r["inertia"] for r in rows])]
    k_sil = sk._best_by_silhouette(rows, "k")
    k_comb = sk._best_by_combined(rows, "k", lam)

    n_res = int(round((r_max - r_min) / r_step)) + 1
    resolutions = [round(r_min + r_step * i, 2) for i in range(n_res)]
    rrows = sk.sweep_leiden(X, resolutions)
    r_best = sk._best_by_silhouette(rrows, "resolution")
    r_comb = sk._best_by_combined(rrows, "resolution", lam)

    selection = {
        "run_id": run_id, "n": len(protocolos), "digest": stamp.get("digest"),
        "text_variant": got, "seed": seed, "redundancy_lambda": lam,
        "kmeans": {"k_elbow": k_elbow, "k_best_silhouette": k_sil, "k_combined": k_comb,
                   "grid": {"min": k_min, "max": k_max, "step": k_step}},
        "leiden": {"best_resolution": r_best, "best_resolution_combined": r_comb,
                   "grid": {"min": r_min, "max": r_max, "step": r_step}},
        "at_grid_edge": {
            "k_elbow": k_elbow in (k_min, k_max),
            "k_combined": k_comb in (k_min, k_max),
            "resolution_combined": r_comb in (resolutions[0], resolutions[-1]),
        },
    }
    out = out_dir / "selection.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    write_artifact(selection, out, stage="select-k",
                   params={"run_id": run_id, "seed": seed, "redundancy_lambda": lam,
                           "k_grid": [k_min, k_max, k_step],
                           "res_grid": [r_min, r_max, r_step]},
                   inputs=[features_file] if features_file else [])

    edge = [k for k, v in selection["at_grid_edge"].items() if v]
    if edge:
        log.warning("select-k: %s landed on a grid edge — widen the sweep before trusting it: %s",
                    run_id, edge)
    ctx.cache["select_k_summary"] = selection
    log.info("select-k %s: k_elbow=%s k_sil=%s k_comb=%s resolution=%s -> %s",
             run_id, k_elbow, k_sil, k_comb, r_comb, out)
