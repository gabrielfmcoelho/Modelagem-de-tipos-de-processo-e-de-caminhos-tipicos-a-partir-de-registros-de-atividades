
from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from ..core._stage_base import RunContext, StageMeta, truthy as _truthy
from ..evidence.artifact import write_artifact

from ..model.clustering import NOISE_LABEL, _disambiguate_names, category_id, name_cluster
from ..model.clustering.naming import distinctive_keywords, near_duplicate_groups
from ..model.keywords import KEYWORDS_PATH, load_keywords_store
from ..core.registry import stage
from ..core.state import now_iso
from .processo_cluster import _build_llm_call, _build_sample_loader
from ..core.paths import ARTIFACTS

_MERGE_LINKAGE = "average"

log = logging.getLogger(__name__)

_ARTIFACT_ROOT = ARTIFACTS / "clustering"



def _load_labels(path: Path) -> dict[str, int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {pf: int(lab) for pf, lab in (data.get("labels") or data).items()}


def _name_redundancy(names: list[str], settings, threshold: float = 0.90) -> dict:
    names = [n for n in names if n]
    if len(names) < 2:
        return {"mean_nn_cosine": None, "n_pairs_ge_threshold": 0,
                "threshold": threshold, "n_names": len(names)}
    try:
        import numpy as np

        from ..model.embedding import build_embedder
        v = np.asarray(build_embedder(settings).embed_batch(names), dtype=np.float64)
        v = v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-9)
        sim = v @ v.T
        np.fill_diagonal(sim, -1.0)
        return {
            "mean_nn_cosine": round(float(sim.max(axis=1).mean()), 4),
            "n_pairs_ge_threshold": int((sim >= threshold).sum() // 2),
            "threshold": threshold,
            "n_names": len(names),
        }
    except Exception as e:
        log.warning("name-redundancy skipped (%s)", e)
        return {"mean_nn_cosine": None, "n_pairs_ge_threshold": None,
                "threshold": threshold, "n_names": len(names)}


def _merge_micros(names: list[str], settings, threshold: float) -> list[int]:
    import numpy as np
    from sklearn.cluster import AgglomerativeClustering

    from ..model.embedding import build_embedder
    v = np.asarray(build_embedder(settings).embed_batch(names), dtype=np.float64)
    v = v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-9)
    ac = AgglomerativeClustering(
        n_clusters=None, metric="cosine", linkage=_MERGE_LINKAGE,
        distance_threshold=threshold,
    )
    return [int(g) for g in ac.fit_predict(v)]


def _build_hierarchy(out, run_id, members, sample_loader, llm_call, settings,
                     *, threshold, workers, samples_per_cluster):
    cids = list(out.keys())
    if len(cids) < 2 or threshold <= 0:
        return None
    micro_names = [out[c]["nome"] for c in cids]
    groups = _merge_micros(micro_names, settings, threshold)

    by_group: dict[int, list[str]] = defaultdict(list)
    for cid, g in zip(cids, groups):
        by_group[g].append(cid)

    def _lab(cid: str) -> int:
        return int(cid.split("|")[-1])

    def _name_group(item):
        g, member_cids = item
        member_cids = sorted(member_cids, key=lambda c: -out[c].get("n_members", 1))
        n_members = sum(out[c].get("n_members", 1) for c in member_cids)
        gcid = category_id(run_id, "grupo", g)
        if len(member_cids) == 1:
            src = out[member_cids[0]]
            info = {"nome": src["nome"], "descricao": src.get("descricao", ""),
                    "marcadores": src.get("marcadores", [])}
        else:
            protos = members.get(_lab(member_cids[0]), [])
            try:
                samples = sample_loader(protos[:samples_per_cluster])
            except Exception as e:
                log.warning("hierarchy sample load failed for grupo %s: %s", g, e)
                samples = []
            info = name_cluster(samples, llm_call,
                                sub_names=[out[c]["nome"] for c in member_cids])
        info["micros"] = member_cids
        info["n_members"] = n_members
        return gcid, member_cids, info

    grupos: dict[str, dict] = {}
    items = list(by_group.items())
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for gcid, member_cids, info in pool.map(_name_group, items):
            grupos[gcid] = info
            for c in member_cids:
                out[c]["grupo"] = gcid

    _disambiguate_names(grupos, list(grupos.keys()))
    macro_red = _name_redundancy([g["nome"] for g in grupos.values()], settings)
    return {"merge_threshold": threshold, "linkage": _MERGE_LINKAGE,
            "n_grupos": len(grupos), "macro_redundancy": macro_red, "grupos": grupos}


@stage(StageMeta(
    name="cluster-name",
    phase="clustering",
    question="Que nome em linguagem natural descreve cada grupo?",
    deterministic=False,
    nondeterminism="chamada de LLM; a saida varia entre execucoes identicas",
    description="LLM naming for any flat clustering (KMeans/Leiden/HDBSCAN) from labels.json → names.json; optional macro/micro hierarchy via --flag merge_threshold.",
    type="op",
    depends_on=("cluster-eval",),
    modes=("neo4j",),
    can_skip_when_done=False,
    estimated_duration="~1 LLM call per cluster (parallel)",
))
def run(ctx: RunContext) -> None:
    run_id = ctx.flags.get("run_id")
    if not run_id:
        raise ValueError("cluster-name requires --flag run_id=<id>")
    algo = str(ctx.flags.get("algo") or "hdbscan")
    samples_per_cluster = int(ctx.flags.get("samples_per_cluster") or 5)
    workers = max(1, int(ctx.flags.get("workers") or 4))
    min_members = int(ctx.flags.get("min_members") or 1)
    limit = int(ctx.flags.get("limit") or 0)
    force = _truthy(ctx.flags.get("force"))
    merge_threshold = float(ctx.flags.get("merge_threshold") or 0.0)

    out_dir = _ARTIFACT_ROOT / run_id / algo
    labels_path = out_dir / "labels.json"
    if not labels_path.is_file():
        raise FileNotFoundError(
            f"labels.json not found: {labels_path}. Run cluster-eval first "
            f"(--flag run_id={run_id} --flag algos={algo} --flag features_file=…)."
        )
    names_path = out_dir / "names.json"
    if names_path.is_file() and not force:
        log.info("cluster-name: %s exists — skip (use --flag force=true to overwrite)", names_path)
        ctx.cache["cluster_name_summary"] = {"run_id": run_id, "algo": algo, "skipped": True}
        return

    labels = _load_labels(labels_path)
    members: dict[int, list[str]] = defaultdict(list)
    for pf, lab in labels.items():
        if lab != NOISE_LABEL:
            members[lab].append(pf)
    clusters = sorted(members.items(), key=lambda kv: -len(kv[1]))
    clusters = [(lab, protos) for lab, protos in clusters if len(protos) >= min_members]
    if limit:
        clusters = clusters[:limit]

    log.info("cluster-name[%s/%s]: naming %d clusters (workers=%d, samples=%d)",
             run_id, algo, len(clusters), workers, samples_per_cluster)

    driver = ctx.require_driver()
    sample_loader = _build_sample_loader(driver)
    llm_call = _build_llm_call(ctx.settings)


    def _name_one(item: tuple[int, list[str]]):
        lab, protos = item
        try:
            samples = sample_loader(protos[:samples_per_cluster])
        except Exception as e:
            log.warning("sample load failed for cluster %s: %s", lab, e)
            samples = []
        cid = category_id(run_id, "macro", lab)
        info = name_cluster(samples, llm_call)
        info["n_members"] = len(protos)
        return cid, info

    out: dict[str, dict] = {}
    if workers <= 1:
        for item in clusters:
            cid, info = _name_one(item)
            out[cid] = info
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = [pool.submit(_name_one, item) for item in clusters]
            for i, fut in enumerate(as_completed(futs), 1):
                cid, info = fut.result()
                out[cid] = info
                if i % 20 == 0:
                    log.info("cluster-name: %d/%d named", i, len(clusters))

    _disambiguate_names(out, list(out.keys()))

    redundancy = _name_redundancy([out[c]["nome"] for c in out], ctx.settings)

    hierarchy = None
    if merge_threshold > 0:
        log.info("cluster-name[%s/%s]: merging %d micros into macros (threshold=%.2f)",
                 run_id, algo, len(out), merge_threshold)
        hierarchy = _build_hierarchy(
            out, run_id, members, sample_loader, llm_call, ctx.settings,
            threshold=merge_threshold, workers=workers,
            samples_per_cluster=samples_per_cluster,
        )
        if hierarchy:
            log.info("cluster-name: %d micros → %d macros (macro pairs>=.90: %s)",
                     len(out), hierarchy["n_grupos"],
                     hierarchy["macro_redundancy"].get("n_pairs_ge_threshold"))

    meta = {"run_id": run_id, "algo": algo, "n_clusters": len(out),
            "samples_per_cluster": samples_per_cluster,
            "redundancy": redundancy, "generated_at": now_iso()}
    payload = {"meta": meta, "names": out}
    if hierarchy:
        meta["merge_threshold"] = merge_threshold
        meta["macro_redundancy"] = hierarchy["macro_redundancy"]
        meta["n_macros"] = hierarchy["n_grupos"]
        payload["hierarchy"] = hierarchy
    write_artifact(payload, names_path, force=True, stage="cluster-name",
                   params={"run_id": run_id, "algo": algo}, inputs=[labels_path])
    log.info("cluster-name complete: wrote %s (%d clusters)", names_path, len(out))
    ctx.cache["cluster_name_summary"] = {
        "run_id": run_id, "algo": algo, "n_clusters": len(out),
        "n_macros": hierarchy["n_grupos"] if hierarchy else None,
    }
