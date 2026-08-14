from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np

from ..evidence.artifact import write_artifact
from ..core._stage_base import RunContext, StageMeta
from ..model.cluster_metrics import assign_noise_to_nearest
from ..model.clustering import dedupe_macro_labels, fit
from ..core.registry import stage
from ..core.paths import ARTIFACTS

log = logging.getLogger(__name__)

CLUSTERING_DIR = ARTIFACTS / "clustering"
FEATURES_DIR = ARTIFACTS / "features"


def features_name(run_id: str, arm: str, features_dir: Path = FEATURES_DIR) -> str:
    return run_id if (Path(features_dir) / f"{run_id}.npz").is_file() else arm


def audit_all(clustering_dir: Path = CLUSTERING_DIR,
              features_dir: Path = FEATURES_DIR,
              tolerance: float = 0.999) -> dict:
    from .cluster_eval import _arm_of, _load_features_from_npz

    cache: dict[str, tuple | None] = {}

    def feats(run_id: str, arm: str):
        name = features_name(run_id, arm, features_dir)
        if name not in cache:
            path = Path(features_dir) / f"{name}.npz"
            cache[name] = _load_features_from_npz(str(path)) if path.is_file() else None
        return cache[name]

    rows = []
    for metrics_path in sorted(Path(clustering_dir).glob("*/*/metrics.json")):
        run_id, algo_dir = metrics_path.parts[-3], metrics_path.parts[-2]
        arm = _arm_of(run_id)
        if arm is None:
            continue
        meta = json.loads(metrics_path.read_text(encoding="utf-8")).get("meta", {})
        algo = meta.get("algo")
        labels_path = metrics_path.parent / "labels.json"
        if algo not in ("hdbscan", "kmeans", "leiden") or not labels_path.is_file():
            continue
        stored = json.loads(labels_path.read_text(encoding="utf-8"))["labels"]
        loaded = feats(run_id, arm)
        if loaded is None:
            rows.append({"run_id": run_id, "algo": algo_dir, "status": "NO_FEATURES"})
            continue
        protos, X, stamp = loaded
        if len(protos) != len(stored):
            rows.append({"run_id": run_id, "algo": algo_dir, "status": "SIZE_MISMATCH",
                         "stored_n": len(stored), "features_n": len(protos)})
            continue
        declared = dict(meta.get("params") or {})
        dedup = float(declared.pop("macro_dedup_threshold", 0) or 0)
        do_assign = bool(declared.pop("assign_noise", False))
        for k in ("noise_ratio_before_assignment", "n_reassigned", "source", "labels_file"):
            declared.pop(k, None)
        try:
            res = fit(X, algo, **declared)
            refit = np.asarray(res.labels)
            if dedup > 0:
                refit = dedupe_macro_labels(X, refit, threshold=dedup)
            if do_assign:
                refit = assign_noise_to_nearest(X, refit)
        except Exception as e:
            rows.append({"run_id": run_id, "algo": algo_dir, "status": "REFIT_FAILED",
                         "error": f"{type(e).__name__}: {e}"})
            continue
        got = {pf: int(lab) for pf, lab in zip(protos, refit)}
        agree = sum(1 for pf in protos if int(stored.get(pf, -99)) == got[pf])
        frac = agree / len(protos)
        rows.append({"run_id": run_id, "algo": algo_dir,
                     "status": "OK" if frac >= tolerance else "MISMATCH",
                     "agreement": round(frac, 6),
                     "clusters_stored": len(set(stored.values())),
                     "clusters_refit": len(set(got.values())),
                     "digest": stamp.get("digest"),
                     "text_variant": stamp.get("text_variant")})

    problems = [r for r in rows if r["status"] != "OK"]
    return {"audited": len(rows), "problems": len(problems), "rows": rows}


@stage(StageMeta(
    name="cluster-audit",
    phase="clustering",
    question="Cada clustering armazenado se reproduz a partir das features que ele declara?",
    deterministic=True,
    description="Refaz cada clustering a partir do npz stampado e compara com os labels salvos.",
    type="op",
    depends_on=("cluster-eval",),
    modes=("neo4j", "fs"),
    can_skip_when_done=False,
    estimated_duration="~2min",
))
def run(ctx: RunContext) -> None:
    strict = str(ctx.flags.get("strict", "true")).strip().lower() not in ("false", "0", "no")
    report = audit_all(tolerance=float(ctx.flags.get("tolerance") or 0.999))
    for r in report["rows"]:
        log.info("cluster-audit: %-34s %-14s %s", f"{r['run_id']}/{r['algo']}",
                 r["status"], r.get("agreement", "-"))
    out = ARTIFACTS / "stats" / "clustering-audit.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    write_artifact(report, out, stage="cluster-audit",
                   params={"tolerance": float(ctx.flags.get("tolerance") or 0.999),
                           "strict": strict})
    ctx.cache["cluster_audit_summary"] = {"audited": report["audited"],
                                          "problems": report["problems"]}
    log.info("cluster-audit: %d audited, %d problem(s) -> %s",
             report["audited"], report["problems"], out)
    if report["problems"] and strict:
        bad = [f"{r['run_id']}/{r['algo']}:{r['status']}" for r in report["rows"]
               if r["status"] != "OK"]
        raise ValueError(f"cluster-audit found {len(bad)} non-reproducible clustering(s): {bad}")
