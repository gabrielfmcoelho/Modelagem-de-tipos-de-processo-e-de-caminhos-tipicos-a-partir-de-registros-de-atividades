from __future__ import annotations

import json
import logging
from pathlib import Path

from ..core._stage_base import RunContext, StageMeta
from ..core.registry import stage
from . import (
    cluster_audit,
    cluster_eval,
    cluster_stability,
    processo_embed,
    select_k,
)
from ..core.paths import ARTIFACTS

log = logging.getLogger(__name__)

HDBSCAN_PARAMS = '{"min_cluster_size": 20}'
HCOARSE_EPSILON = "0.5"
STABILITY_DRAWS = "25"


def _substage(ctx: RunContext, module, flags: dict) -> None:
    name = module.__name__.rsplit(".", 1)[-1]
    log.info("build-arm: %s %s", name, " ".join(f"{k}={v}" for k, v in flags.items()))
    module.run(RunContext(
        settings=ctx.settings, mode=ctx.mode, flags=dict(flags),
        state_dir=ctx.state_dir, cache=ctx.cache, writer=ctx.writer,
        reader=ctx.reader, driver=ctx.driver, progress=ctx.progress,
    ))


@stage(StageMeta(
    name="build-arm",
    phase="clustering",
    question="Macro: um braco inteiro, das features ao catalogo auditado.",
    deterministic='conditional',
    nondeterminism="herda a determinismo de cada sub-stage que executa",
    description="Constrói um braço inteiro: features, seleção de parâmetros, as cinco "
                "clusterizações (base, kelbow, ksil, lres, hcoarse), consenso, estabilidade "
                "e auditoria. Substitui o antigo scripts/build_arm.sh.",
    type="op",
    depends_on=("processo-embed",),
    modes=("neo4j",),
    can_skip_when_done=False,
    estimated_duration="~40-90min por braço",
))
def run(ctx: RunContext) -> None:
    arm = str(ctx.flags.get("run_id") or "").strip()
    if not arm:
        raise ValueError("build-arm requires --flag run_id=<exp-raw|exp-anon|...>")
    features_file = str(ctx.flags.get("features_file")
                        or f"artifacts/features/{arm}.npz")
    situacao = str(ctx.flags.get("only_situacao") or "concluido")
    skip_embed = str(ctx.flags.get("skip_embed") or "").lower() in ("1", "true", "yes")

    if skip_embed:
        if not Path(features_file).is_file():
            raise FileNotFoundError(
                f"build-arm: skip_embed=true but {features_file} does not exist")
        log.info("build-arm: skip_embed=true, reusing %s", features_file)
    else:
        _substage(ctx, processo_embed, {
            "force_all": "true", "only_situacao": situacao,
            "export_features": features_file})

    _substage(ctx, select_k, {"run_id": arm, "features_file": features_file})

    selection_path = ARTIFACTS / "clustering" / arm / "selection.json"
    if not selection_path.is_file():
        raise FileNotFoundError(f"build-arm: select-k did not write {selection_path}")
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    k_elbow = selection["kmeans"]["k_elbow"]
    k_sil = selection["kmeans"]["k_best_silhouette"]
    resolution = selection["leiden"]["best_resolution_combined"]
    edge = [k for k, v in (selection.get("at_grid_edge") or {}).items() if v]
    if edge:
        log.warning("build-arm: %s selected at a grid edge (%s) — widen the sweep before "
                    "trusting this arm", arm, ", ".join(edge))
    log.info("build-arm %s: k_elbow=%s k_silhouette=%s resolution=%s",
             arm, k_elbow, k_sil, resolution)

    base = {"features_file": features_file, "force": "true"}
    _substage(ctx, cluster_eval, {"run_id": arm, **base})
    _substage(ctx, cluster_eval, {"run_id": f"{arm}-kelbow", "algos": "kmeans",
                                  "k": str(k_elbow), **base})
    _substage(ctx, cluster_eval, {"run_id": f"{arm}-ksil", "algos": "kmeans",
                                  "k": str(k_sil), **base})
    _substage(ctx, cluster_eval, {"run_id": f"{arm}-lres", "algos": "leiden",
                                  "resolution": str(resolution), **base})
    _substage(ctx, cluster_eval, {"run_id": f"{arm}-hcoarse", "algos": "hdbscan",
                                  "min_cluster_size": "20",
                                  "cluster_selection_epsilon": HCOARSE_EPSILON, **base})
    _substage(ctx, cluster_stability, {"run_id": arm, "algo": "hdbscan",
                                       "params": HDBSCAN_PARAMS, "draws": STABILITY_DRAWS,
                                       "features_file": features_file})
    _substage(ctx, cluster_audit, {})

    summary = {"arm": arm, "features_file": features_file, "k_elbow": k_elbow,
               "k_silhouette": k_sil, "resolution": resolution, "at_grid_edge": edge,
               "clusterings": [arm, f"{arm}-kelbow", f"{arm}-ksil", f"{arm}-lres",
                               f"{arm}-hcoarse"]}
    ctx.cache["build_arm_summary"] = summary
    log.info("build-arm %s: done — 4 clusterings, stability and audit", arm)
