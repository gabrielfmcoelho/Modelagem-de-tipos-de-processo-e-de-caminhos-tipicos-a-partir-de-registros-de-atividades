from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np

from ..core._stage_base import RunContext, StageMeta, truthy as _truthy
from ..evidence.artifact import write_artifact
from ..model.cluster_metrics import evaluate_clustering, internal_metrics
from ..core.cypher import READ_PROCESSO_TIPO_CYPHER
from ..core.registry import stage
from ..model.clustering.consensus.consensus_model import DEFAULT_K as _DEFAULT_K
from ..model.clustering.consensus import consensus_model
from ..core.state import now_iso
from ..core.paths import ARTIFACTS

log = logging.getLogger(__name__)

_ARTIFACT_ROOT = ARTIFACTS / "clustering"
_DEFAULT_ALGOS = "hdbscan,kmeans,leiden"
_DEFAULT_K_GRID = "20,40,60,80,100,120,140,160,180,200"
_SEED = 42


def _load_labels(path: Path) -> dict[str, int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {pf: int(lab) for pf, lab in (data.get("labels") or data).items()}




def comparable_internal(run_id: str, protocolos: list[str], labels) -> dict | None:
    path = ARTIFACTS / "features" / f"{run_id}.npz"
    if not path.is_file():
        return None
    z = np.load(path, allow_pickle=True)
    by_protocolo = dict(zip((str(p) for p in z["protocolos"]), z["features"]))
    if not all(p in by_protocolo for p in protocolos):
        return None
    feat = np.vstack([by_protocolo[p] for p in protocolos])
    return internal_metrics(feat, np.asarray(labels), space="umap50-cosine")


def _fetch_reference(driver, protocolos: list[str]) -> list:
    if driver is None:
        return [None] * len(protocolos)
    ref: dict[str, str | None] = {}
    with driver.session() as session:
        for r in session.run(READ_PROCESSO_TIPO_CYPHER):
            ref[r["protocolo"]] = r.get("tipo_procedimento")
    return [ref.get(p) for p in protocolos]


@stage(StageMeta(
    name="cluster-consensus",
    phase="clustering",
    question="Que particao emerge do acordo entre HDBSCAN, k-means e Leiden?",
    deterministic=True,
    description="Co-association (CSPA) consensus across HDBSCAN/KMeans/Leiden labels → one canonical clustering.",
    type="op",
    depends_on=("cluster-eval",),
    modes=("neo4j",),
    can_skip_when_done=False,
    estimated_duration="~1min (KMeans on co-association one-hot)",
))
def run(ctx: RunContext) -> None:
    run_id = ctx.flags.get("run_id")
    if not run_id:
        raise ValueError("cluster-consensus requires --flag run_id=<id>")
    algos = [a.strip() for a in str(ctx.flags.get("algos") or _DEFAULT_ALGOS).split(",") if a.strip()]
    k = int(ctx.flags.get("k") or _DEFAULT_K)
    force = _truthy(ctx.flags.get("force"))

    label_maps: dict[str, dict[str, int]] = {}
    for algo in algos:
        p = _ARTIFACT_ROOT / run_id / algo / "labels.json"
        if not p.is_file():
            raise FileNotFoundError(f"labels.json not found for algo '{algo}': {p}. Run cluster-eval first.")
        label_maps[algo] = _load_labels(p)

    protocolos = sorted(set.intersection(*[set(m) for m in label_maps.values()]))
    if not protocolos:
        raise ValueError("no protocolos shared across the input clusterings")

    k_selection = None
    if ctx.flags.get("k"):
        k_selection = {"mode": "fixed", "k": k,
                       "rationale": "k supplied with --flag k; no sweep performed"}
    else:
        grid = [int(v) for v in str(ctx.flags.get("k_grid") or _DEFAULT_K_GRID).split(",") if v]
        rows = consensus_model.sweep_k(label_maps, algos, protocolos, grid, seed=_SEED)
        chosen, why = consensus_model.best_k(rows)
        if chosen is None:
            raise ValueError(
                f"consensus k sweep over {grid} produced no usable partition: {why}. "
                "Supply --flag k=<n> to bypass the sweep.")
        k = chosen
        k_selection = {"mode": "swept", "k": k, "grid": grid, "rationale": why, "sweep": rows}
        sweep_path = _ARTIFACT_ROOT / run_id / "consensus" / "k_sweep.json"
        write_artifact({"run_id": run_id, "algos": algos, "n_protocolos": len(protocolos),
                        "selection": k_selection},
                       sweep_path, stage="cluster-consensus", force=True,
                       params={"run_id": run_id, "algos": algos, "grid": grid},
                       inputs=[_ARTIFACT_ROOT / run_id / a / "labels.json" for a in algos])
        log.info("cluster-consensus: swept k over %s -> k=%d (%s)", grid, k, why)

    result, x = consensus_model.fit(label_maps, algos, protocolos, k=k)
    labels = result.labels

    reference = _fetch_reference(ctx.driver, protocolos)
    n_ref = sum(1 for r in reference if r is not None and str(r).strip())
    params = result.params
    metrics = evaluate_clustering(x, labels, algo="consensus", params=params,
                                  reference=reference if n_ref else None,
                                  space="coassoc-onehot")
    metrics["internal_comparable"] = comparable_internal(run_id, protocolos, labels)

    out_dir = _ARTIFACT_ROOT / run_id / "consensus"
    cc_params = {"run_id": run_id, "algos": algos, "k": k, "method": "cspa",
                 "k_mode": k_selection["mode"]}
    cc_inputs = [_ARTIFACT_ROOT / run_id / a / "labels.json" for a in algos]
    labels_payload = {
        "meta": {"run_id": run_id, "algo": "consensus", "method": "cspa",
                 "algos": algos, "k": k, "k_selection": k_selection,
                 "generated_at": now_iso(), "n": len(protocolos)},
        "labels": {pf: int(lab) for pf, lab in zip(protocolos, labels)},
    }
    write_artifact(labels_payload, out_dir / "labels.json", force=force,
                   stage="cluster-consensus", params=cc_params, inputs=cc_inputs)
    write_artifact(metrics, out_dir / "metrics.json", force=force,
                   stage="cluster-consensus", params=cc_params, inputs=cc_inputs)

    log.info("cluster-consensus[%s]: %d algos → k=%d  silhouette=%s  purity=%s",
             run_id, len(algos), k,
             f"{metrics['silhouette']:.4f}" if metrics["silhouette"] is not None else "n/a",
             f"{(metrics['extrinsic'] or {}).get('purity')}")
    ctx.cache["cluster_consensus_summary"] = {
        "run_id": run_id, "k": k, "algos": algos,
        "silhouette": metrics["silhouette"],
        "purity": (metrics["extrinsic"] or {}).get("purity"),
    }
