from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path

import numpy as np

from ..evidence.artifact import write_artifact
from ..core._stage_base import RunContext, StageMeta
from ..model.clustering import NOISE_LABEL, fit
from ..core.registry import stage
from ..core.state import now_iso
from ..core.paths import ARTIFACTS

log = logging.getLogger(__name__)


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    u = len(a | b)
    return len(a & b) / u if u else 0.0


def bootstrap_stability(protocolos, features, algo, params, *, draws=25,
                        sample_frac=0.8, seed=42) -> dict:
    ref = fit(features, algo, **params)
    ref_sets: dict[int, set] = defaultdict(set)
    for i, lab in enumerate(np.asarray(ref.labels)):
        if int(lab) != NOISE_LABEL:
            ref_sets[int(lab)].add(protocolos[i])

    rng = np.random.default_rng(seed)
    n = features.shape[0]
    take = max(2, int(n * sample_frac))
    best: dict[int, list] = {c: [] for c in ref_sets}
    for d in range(draws):
        idx = rng.choice(n, size=take, replace=False)
        sub_protos = [protocolos[i] for i in idx]
        try:
            res = fit(features[idx], algo, **params)
        except Exception as e:
            log.warning("cluster-stability: draw %d failed (%s)", d, e)
            continue
        got: dict[int, set] = defaultdict(set)
        for j, lab in enumerate(np.asarray(res.labels)):
            if int(lab) != NOISE_LABEL:
                got[int(lab)].add(sub_protos[j])
        present = set(sub_protos)
        for c, members in ref_sets.items():
            restricted = members & present
            if len(restricted) >= 2:
                best[c].append(max((_jaccard(restricted, g) for g in got.values()), default=0.0))

    rows = []
    for c, vals in best.items():
        if vals:
            rows.append({"cluster": c, "size": len(ref_sets[c]), "draws": len(vals),
                         "jaccard_mean": round(float(np.mean(vals)), 4),
                         "jaccard_p10": round(float(np.percentile(vals, 10)), 4)})
    rows.sort(key=lambda r: -r["jaccard_mean"])
    means = [r["jaccard_mean"] for r in rows]
    return {
        "meta": {"algo": algo, "params": params, "draws": draws,
                 "sample_frac": sample_frac, "seed": seed,
                 "n_reference_clusters": len(ref_sets),
                 "limitation": "clusterer refit only; UMAP not refit -> lower bound",
                 "generated_at": now_iso()},
        "aggregate": {
            "jaccard_mean": round(float(np.mean(means)), 4) if means else None,
            "jaccard_median": round(float(np.median(means)), 4) if means else None,
            "n_stable_above_0.75": int(sum(1 for m in means if m >= 0.75)),
            "n_stable_above_0.60": int(sum(1 for m in means if m >= 0.60)),
            "n_unstable_below_0.60": int(sum(1 for m in means if m < 0.60)),
            "n_clusters_scored": len(means),
        },
        "clusters": rows,
    }


@stage(StageMeta(
    name="cluster-stability",
    phase="clustering",
    question="Quanto de cada cluster sobrevive a reamostragem do corpus?",
    deterministic='conditional',
    nondeterminism="bootstrap por reamostragem, fixado pelo seed registrado em params",
    description="Bootstrap Jaccard estabilidade por cluster (clusterboot) a partir do npz stampado.",
    type="op",
    depends_on=("cluster-eval",),
    modes=("neo4j",),
    can_skip_when_done=False,
    estimated_duration="~1-5min por arm",
))
def run(ctx: RunContext) -> None:
    from .cluster_eval import _ARM_VARIANT, _arm_of, _load_features_from_npz

    run_id = ctx.flags.get("run_id")
    if not run_id:
        raise ValueError("cluster-stability requires --flag run_id=<id>")
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
            f"text_variant={got!r}. Refusing to produce a mislabelled stability report."
        )

    algo = str(ctx.flags.get("algo") or "hdbscan")
    params = json.loads(ctx.flags.get("params") or '{"min_cluster_size": 20}')
    draws = int(ctx.flags.get("draws") or 25)

    payload = bootstrap_stability(protocolos, features, algo, params, draws=draws)
    payload["meta"]["run_id"] = run_id
    payload["meta"]["features_file"] = features_file
    payload["meta"]["digest"] = stamp.get("digest")

    out = ARTIFACTS / "clustering" / run_id / algo / "stability.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    write_artifact(payload, out, stage="cluster-stability",
                   params={"run_id": run_id, "algo": algo, "params": params, "draws": draws,
                           "sample_frac": 0.8, "seed": 42},
                   inputs=[features_file] if features_file else [])
    ctx.cache["cluster_stability_summary"] = payload["aggregate"]
    log.info("cluster-stability: wrote %s  %s", out, payload["aggregate"])
