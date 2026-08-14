#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from ...core.paths import ROOT as _ROOT

from ...evidence.artifact import write_artifact
from ...model.cluster_metrics import _versions
from ...model.clustering import fit

SILHOUETTE_BUDGET_SECONDS = 60.0
SILHOUETTE_SUBSAMPLE_N = 5000

ELBOW_METHOD = (
    "max perpendicular distance from the inertia curve to the chord joining its "
    "endpoints, with k and inertia min-max normalized to [0, 1]"
)


def elbow_index(xs, ys) -> int:
    x = np.asarray(xs, dtype=np.float64)
    y = np.asarray(ys, dtype=np.float64)
    x = (x - x.min()) / (x.max() - x.min())
    span = y.max() - y.min()
    y = (y - y.min()) / span if span > 0 else np.zeros_like(y)
    dx = x[-1] - x[0]
    dy = y[-1] - y[0]
    dist = np.abs(dx * (y - y[0]) - dy * (x - x[0])) / np.hypot(dx, dy)
    return int(np.argmax(dist))


def _internal(features: np.ndarray, labels: np.ndarray, sil_idx: np.ndarray | None) -> dict:
    from sklearn.metrics import (
        calinski_harabasz_score,
        davies_bouldin_score,
        silhouette_score,
    )
    out: dict = {"silhouette": None, "calinski_harabasz": None, "davies_bouldin": None}
    if len(set(labels.tolist())) < 2:
        return out
    out["calinski_harabasz"] = float(calinski_harabasz_score(features, labels))
    out["davies_bouldin"] = float(davies_bouldin_score(features, labels))
    sub, sub_lab = (features, labels) if sil_idx is None else (features[sil_idx], labels[sil_idx])
    if len(set(sub_lab.tolist())) >= 2:
        out["silhouette"] = float(silhouette_score(sub, sub_lab, metric="cosine"))
    return out


def sweep_kmeans(features: np.ndarray, ks: list[int], seed: int) -> tuple[list[dict], str]:
    from sklearn.cluster import KMeans
    rows: list[dict] = []
    sil_idx: np.ndarray | None = None
    sil_scope = "full"
    for k in ks:
        km = KMeans(n_clusters=k, random_state=seed, n_init=10)
        labels = km.fit_predict(features).astype(int)
        t0 = time.time()
        metrics = _internal(features, labels, sil_idx)
        elapsed = time.time() - t0
        if (
            sil_idx is None
            and elapsed > SILHOUETTE_BUDGET_SECONDS
            and features.shape[0] > SILHOUETTE_SUBSAMPLE_N
        ):
            rng = np.random.default_rng(seed)
            sil_idx = np.sort(rng.choice(features.shape[0], SILHOUETTE_SUBSAMPLE_N, replace=False))
            sil_scope = f"fixed-seed subsample of {SILHOUETTE_SUBSAMPLE_N} (full-matrix silhouette exceeded {SILHOUETTE_BUDGET_SECONDS:.0f}s)"
            metrics = _internal(features, labels, sil_idx)
        red = _redundancy(features, labels)
        rows.append({"k": int(k), "n_clusters": len(set(labels.tolist())), "inertia": float(km.inertia_),
                     "redundancy": red, **metrics})
        print(f"k={k}: inertia={km.inertia_:.1f} silhouette={metrics['silhouette']} touching={red['n_touching']}", file=sys.stderr)
    return rows, sil_scope


def sweep_leiden(features: np.ndarray, resolutions: list[float]) -> list[dict]:
    rows: list[dict] = []
    for r in resolutions:
        result = fit(features, "leiden", resolution=r)
        metrics = _internal(features, result.labels, None)
        red = _redundancy(features, result.labels)
        rows.append({
            "resolution": float(r),
            "n_clusters": len(set(result.labels.tolist())),
            "params": result.params,
            "redundancy": red,
            **metrics,
        })
        print(f"resolution={r}: n_clusters={rows[-1]['n_clusters']} silhouette={metrics['silhouette']} touching={red['n_touching']}", file=sys.stderr)
    return rows


def _redundancy(features: np.ndarray, labels: np.ndarray) -> dict:
    from ...model.cluster_metrics import separation_stats
    sep = separation_stats(features, labels)
    n = sep.get("n_clusters") or 0
    frac = (sep["n_touching"] / n) if n else 0.0
    return {"touching_frac": round(float(frac), 4),
            "n_touching": sep["n_touching"], "mean_ratio": sep["mean_ratio"]}


def _best_by_silhouette(rows: list[dict], key: str):
    scored = [(row["silhouette"], row[key]) for row in rows if row["silhouette"] is not None]
    return max(scored)[1] if scored else None


def _best_by_combined(rows: list[dict], key: str, lam: float):
    scored = []
    for row in rows:
        if row.get("silhouette") is None:
            continue
        frac = (row.get("redundancy") or {}).get("touching_frac", 0.0)
        scored.append((row["silhouette"] - lam * frac, row[key]))
    return max(scored)[1] if scored else None


def _meta(args, features: np.ndarray, elapsed: float) -> dict:
    return {
        "features_file": str(args.features),
        "n": int(features.shape[0]),
        "dim": int(features.shape[1]),
        "versions": _versions(),
        "elapsed_seconds": round(elapsed, 1),
        "generated_at": datetime.now(UTC).isoformat(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Model-selection sweep: elbow-method k for kmeans, resolution grid for leiden."
    )
    parser.add_argument("--features", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--algo", choices=("kmeans", "leiden"), default="kmeans")
    parser.add_argument("--res-min", type=float, default=0.4)
    parser.add_argument("--res-max", type=float, default=4.0)
    parser.add_argument("--res-step", type=float, default=0.2)
    parser.add_argument("--k-min", type=int, default=20)
    parser.add_argument("--k-max", type=int, default=320)
    parser.add_argument("--step", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--redundancy-lambda", type=float, default=0.05,
                        help="Penalty weight on the touching-cluster fraction in the combined objective.")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing sweep artifact.")
    args = parser.parse_args()

    z = np.load(args.features, allow_pickle=False)
    features = np.asarray(z["features"], dtype=np.float64)

    t_start = time.time()
    if args.algo == "kmeans":
        ks = list(range(args.k_min, args.k_max + 1, args.step))
        rows, sil_scope = sweep_kmeans(features, ks, args.seed)
        k_elbow = ks[elbow_index(ks, [row["inertia"] for row in rows])]
        k_best_sil = _best_by_silhouette(rows, "k")
        k_combined = _best_by_combined(rows, "k", args.redundancy_lambda)
        payload = {
            "algo": "kmeans",
            "grid": rows,
            "k_elbow": k_elbow,
            "k_best_silhouette": k_best_sil,
            "k_combined": k_combined,
            "redundancy_lambda": args.redundancy_lambda,
            "elbow_method": ELBOW_METHOD,
            "selection": "k_elbow is primary (regra do cotovelo); k_combined maximizes silhouette − lambda*touching_frac; k_best_silhouette reported for comparison",
            "silhouette_metric": "cosine",
            "silhouette_scope": sil_scope,
            "seed": args.seed,
            "kmeans_params": {"n_init": 10, "random_state": args.seed},
            "grid_spec": {"k_min": args.k_min, "k_max": args.k_max, "step": args.step},
            "meta": _meta(args, features, time.time() - t_start),
        }
        out_path = _ROOT / "artifacts" / "clustering" / args.run_id / "kmeans" / "k_sweep.json"
        summary = f"k_elbow={k_elbow} k_best_silhouette={k_best_sil} k_combined={k_combined}"
    else:
        n_res = int(round((args.res_max - args.res_min) / args.res_step)) + 1
        resolutions = [round(args.res_min + args.res_step * i, 2) for i in range(n_res)]
        rows = sweep_leiden(features, resolutions)
        best_resolution = _best_by_silhouette(rows, "resolution")
        best_resolution_combined = _best_by_combined(rows, "resolution", args.redundancy_lambda)
        payload = {
            "algo": "leiden",
            "grid": rows,
            "best_resolution": best_resolution,
            "best_resolution_combined": best_resolution_combined,
            "redundancy_lambda": args.redundancy_lambda,
            "selection": "best_resolution_combined maximizes silhouette − lambda*touching_frac; best_resolution (max silhouette) reported for comparison",
            "silhouette_metric": "cosine",
            "silhouette_scope": "full",
            "seed": 42,
            "grid_spec": {"resolution_min": args.res_min, "resolution_max": args.res_max, "step": args.res_step},
            "meta": _meta(args, features, time.time() - t_start),
        }
        out_path = _ROOT / "artifacts" / "clustering" / args.run_id / "leiden" / "resolution_sweep.json"
        summary = f"best_resolution={best_resolution} combined={best_resolution_combined}"

    write_artifact(payload, out_path, force=args.force, stage="select-k",
                   params={"run_id": args.run_id, "algo": args.algo, "seed": args.seed},
                   inputs=[args.features])
    print(f"Wrote {out_path} ({summary}, {payload['meta']['elapsed_seconds']}s)")


if __name__ == "__main__":
    raise SystemExit(main())
