
from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np

from ..core._stage_base import RunContext, StageMeta, truthy as _truthy
from ..evidence.artifact import write_artifact
from ..model.cluster_metrics import assign_noise_to_nearest, evaluate_clustering
from ..model.clustering import NOISE_LABEL, fit
from ..core.cypher import READ_ALL_CLUSTER_FEATURES_CYPHER, READ_PROCESSO_TIPO_CYPHER
from ..core.registry import stage
from ..core.state import now_iso
from ..core.paths import ARTIFACTS

log = logging.getLogger(__name__)

_ARM_PREFIXES = ("exp-anon", "exp-raw")


def _arm_of(run_id: str) -> str | None:
    for prefix in _ARM_PREFIXES:
        if run_id == prefix or run_id.startswith(prefix + "-"):
            return prefix
    return None

_ARTIFACT_ROOT = ARTIFACTS / "clustering"
TIPO_CACHE = ARTIFACTS / "cache" / "tipo_procedimento.json"
_DEFAULT_ALGOS = "hdbscan,kmeans,leiden"


_ARM_VARIANT = {"exp-raw": "raw", "exp-anon": "anon"}


def _load_features_from_npz(path: str) -> tuple[list[str], np.ndarray, dict]:
    z = np.load(path, allow_pickle=False)
    protocolos = [str(p) for p in z["protocolos"]]
    features = np.asarray(z["features"], dtype=np.float64)
    stamp = {k: str(z[k]) for k in ("digest", "text_variant") if k in z.files}
    return protocolos, features, stamp


def _read_features_from_neo4j(driver) -> tuple[list[str], np.ndarray]:
    protocolos: list[str] = []
    rows: list[list[float]] = []
    with driver.session() as session:
        for r in session.run(READ_ALL_CLUSTER_FEATURES_CYPHER):
            f = r.get("features")
            if not f:
                continue
            protocolos.append(r["protocolo"])
            rows.append(list(f))
    return protocolos, np.asarray(rows, dtype=np.float64)


def _fetch_reference(driver) -> dict[str, str | None]:
    if driver is None:
        return {}
    out: dict[str, str | None] = {}
    with driver.session() as session:
        for r in session.run(READ_PROCESSO_TIPO_CYPHER):
            out[r["protocolo"]] = r.get("tipo_procedimento")
    return out


def _load_frozen_macro_labels(path: str, protocolos: list[str]) -> np.ndarray:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    table = data.get("labels", data)
    out: list[int] = []
    for pf in protocolos:
        entry = table.get(pf)
        if entry is None:
            out.append(NOISE_LABEL)
        elif isinstance(entry, dict):
            macro = entry.get("macro")
            out.append(NOISE_LABEL if macro is None else int(str(macro).split("|")[-1]))
        else:
            out.append(int(entry))
    return np.asarray(out, dtype=int)


def _params_for(algo: str, flags: dict, hdbscan_n_clusters: int | None) -> dict:
    if algo == "hdbscan":
        params = {"min_cluster_size": int(flags.get("min_cluster_size") or 20)}
        if flags.get("min_samples") is not None:
            params["min_samples"] = int(flags["min_samples"])
        if flags.get("cluster_selection_epsilon") is not None:
            params["cluster_selection_epsilon"] = float(flags["cluster_selection_epsilon"])
        if flags.get("cluster_selection_method") is not None:
            params["cluster_selection_method"] = str(flags["cluster_selection_method"])
        return params
    if algo == "kmeans":
        k = flags.get("k")
        if k is not None:
            return {"k": int(k)}
        if hdbscan_n_clusters is not None:
            return {"k": hdbscan_n_clusters}
        raise ValueError(
            "kmeans needs a 'k': pass --flag k=<n>, or include 'hdbscan' in --flag algos "
            "so k defaults to the number of macro clusters it finds"
        )
    if algo == "leiden":
        params: dict = {}
        if flags.get("n_neighbors") is not None:
            params["n_neighbors"] = int(flags["n_neighbors"])
        if flags.get("resolution") is not None:
            params["resolution"] = float(flags["resolution"])
        return params
    return {}


@stage(StageMeta(
    name="cluster-eval",
    phase="clustering",
    question="Que particao cada algoritmo produz, e com que validade interna?",
    deterministic='conditional',
    nondeterminism="UMAP e HDBSCAN sao fixados pelo seed registrado em params",
    description="Read-only avaliação de clustering (HDBSCAN/KMeans/Leiden) + métricas persistidas em artifacts/.",
    type="op",
    depends_on=("processo-embed",),
    modes=("neo4j",),
    can_skip_when_done=False,
    estimated_duration="~2-10min por algoritmo",
))
def run(ctx: RunContext) -> None:
    run_id = ctx.flags.get("run_id")
    if not run_id:
        raise ValueError("cluster-eval requires --flag run_id=<id>")

    algos = [a.strip() for a in str(ctx.flags.get("algos") or _DEFAULT_ALGOS).split(",") if a.strip()]
    features_file = ctx.flags.get("features_file")
    labels_file = ctx.flags.get("labels_file")
    force = _truthy(ctx.flags.get("force"))

    driver = ctx.driver
    arm = _arm_of(run_id)
    if arm and not features_file:
        guess = f"artifacts/features/{arm}.npz"
        raise ValueError(
            f"run_id={run_id!r} names the {arm!r} arm, but no features_file was given. "
            f"Neo4j cluster_features hold whichever arm was embedded last, so this would "
            f"silently cluster the wrong arm. Pass --flag features_file={guess}"
        )
    if features_file:
        protocolos, features, stamp = _load_features_from_npz(features_file)
        log.info("cluster-eval: loaded %d×%d features from %s (digest=%s variant=%s)",
                 *features.shape, features_file,
                 stamp.get("digest", "-"), stamp.get("text_variant", "-"))
        want = _ARM_VARIANT.get(arm or "")
        got = stamp.get("text_variant")
        if want and got and got not in ("unknown", want):
            raise ValueError(
                f"run_id={run_id!r} is the {want!r} arm but {features_file} was built from "
                f"text_variant={got!r}. Refusing to produce a mislabelled clustering."
            )
    else:
        driver = ctx.require_driver()
        stamp = {}
        protocolos, features = _read_features_from_neo4j(driver)
        log.info("cluster-eval: read %d×%d features from Neo4j (no arm implied by run_id)",
                 *features.shape)

    ref_map = _fetch_reference(driver)
    if ref_map:
        write_artifact({"tipos": ref_map}, TIPO_CACHE, force=True, stage="cluster-eval",
                       params={"n": len(ref_map), "source": "neo4j:tipo_procedimento"})
    reference = [ref_map.get(pf) for pf in protocolos]
    n_ref = sum(1 for r in reference if r is not None and str(r).strip())
    if n_ref == 0:
        log.warning("cluster-eval: no tipo_procedimento reference available — extrinsic metrics will be None")

    summary: dict[str, dict] = {}
    hdbscan_n_clusters: int | None = None
    assign_noise = str(ctx.flags.get("assign_noise", "true")).lower() \
        not in ("0", "false", "no")

    for algo in algos:
        if labels_file:
            labels = _load_frozen_macro_labels(labels_file, protocolos)
            params = {"source": "labels_file", "labels_file": str(labels_file)}
        else:
            params = _params_for(algo, ctx.flags, hdbscan_n_clusters)
            result = fit(features, algo, **params)
            labels = result.labels
            params = result.params

        n_noise_before = int((labels == NOISE_LABEL).sum())
        if labels_file and n_noise_before:
            log.info("cluster-eval[%s]: frozen labels — the %d unassigned cases are left as they "
                     "are; this mode evaluates a given partition, it does not alter it",
                     algo, n_noise_before)
        elif assign_noise and n_noise_before:
            labels = assign_noise_to_nearest(features, labels)
            params = {**params, "assign_noise": True,
                      "noise_ratio_before_assignment": round(n_noise_before / len(labels), 4),
                      "n_reassigned": n_noise_before}
            log.info("cluster-eval[%s]: assigned %d noise points to their nearest cluster so "
                     "every algorithm is scored on the same %d cases",
                     algo, n_noise_before, len(labels))
        elif n_noise_before:
            params = {**params, "assign_noise": False,
                      "noise_ratio_before_assignment": round(n_noise_before / len(labels), 4)}

        n_clusters = len({int(x) for x in labels} - {NOISE_LABEL})
        if algo == "hdbscan" and hdbscan_n_clusters is None:
            hdbscan_n_clusters = n_clusters

        metrics = evaluate_clustering(features, labels, algo=algo, params=params, reference=reference)
        out_dir = _ARTIFACT_ROOT / run_id / algo

        if not labels_file:
            labels_payload = {
                "meta": {"run_id": run_id, "algo": algo, "generated_at": now_iso(), "n": len(protocolos)},
                "labels": {pf: int(lab) for pf, lab in zip(protocolos, labels)},
            }
            write_artifact(labels_payload, out_dir / "labels.json", force=force,
                           stage="cluster-eval",
                           params={"run_id": run_id, "algo": algo, **params},
                           inputs=[features_file] if features_file else [])

        write_artifact(metrics, out_dir / "metrics.json", force=force,
                       stage="cluster-eval",
                       params={"run_id": run_id, "algo": algo, **params},
                       inputs=[features_file] if features_file else [])

        log.info(
            "cluster-eval[%s]: n_clusters=%d noise_ratio=%.3f dbcv=%s silhouette=%s",
            algo, metrics["n_clusters"], metrics["noise_ratio"],
            f"{metrics['dbcv']:.4f}" if metrics["dbcv"] is not None else "n/a",
            f"{metrics['silhouette']:.4f}" if metrics["silhouette"] is not None else "n/a",
        )
        summary[algo] = {
            "n_clusters": metrics["n_clusters"],
            "noise_ratio": metrics["noise_ratio"],
            "dbcv": metrics["dbcv"],
            "silhouette": metrics["silhouette"],
            "metrics_path": str(out_dir / "metrics.json"),
        }

    ctx.cache["cluster_eval_summary"] = {"run_id": run_id, "algos": summary, "n_processos": len(protocolos)}
    log.info("cluster-eval complete: %s", summary)
