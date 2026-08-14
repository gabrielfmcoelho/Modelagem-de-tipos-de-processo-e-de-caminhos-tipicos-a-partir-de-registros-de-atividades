from __future__ import annotations

import json
import logging
from pathlib import Path

from ..evidence.artifact import write_artifact
from ..core._stage_base import RunContext, StageMeta
from ..core.registry import stage
from ..core.state import now_iso
from . import cluster_eval, processo_embed
from ..core.paths import ARTIFACTS

log = logging.getLogger(__name__)

DEFAULT_VARIANTS = ("cut0.75:cutoff_frac=0.75", "cut0.5:cutoff_frac=0.5",
                    "cut0.25:cutoff_frac=0.25", "nokeyword:keyword_weight=0",
                    "notopic:topic_weight=0")
OUT_PATH = ARTIFACTS / "stats" / "ablation.json"
CLUSTERING = ARTIFACTS / "clustering"
FEATURES = ARTIFACTS / "features"


def compare_partitions(reference: dict[str, int], cut: dict[str, int]) -> dict:
    from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

    shared = sorted(set(reference) & set(cut))
    if not shared:
        raise RuntimeError("ablation: reference and cut partitions share no processos")
    a = [reference[p] for p in shared]
    b = [cut[p] for p in shared]
    return {
        "n_compared": len(shared),
        "ari": round(float(adjusted_rand_score(a, b)), 4),
        "nmi": round(float(normalized_mutual_info_score(a, b)), 4),
        "n_clusters_reference": len(set(a) - {-1}),
        "n_clusters_cut": len(set(b) - {-1}),
        "noise_reference": sum(1 for x in a if x == -1),
        "noise_cut": sum(1 for x in b if x == -1),
    }


def _labels(run_id: str, algo: str) -> dict[str, int]:
    path = CLUSTERING / run_id / algo / "labels.json"
    if not path.is_file():
        raise FileNotFoundError(f"ablation: {path} not found")
    return json.loads(path.read_text(encoding="utf-8"))["labels"]


def _substage(ctx: RunContext, module, flags: dict, cache: dict) -> None:
    log.info("ablation: %s %s", module.__name__.rsplit(".", 1)[-1],
             " ".join(f"{k}={v}" for k, v in flags.items()))
    module.run(RunContext(
        settings=ctx.settings, mode=ctx.mode, flags=dict(flags),
        state_dir=ctx.state_dir, cache=cache, writer=ctx.writer,
        reader=ctx.reader, driver=ctx.driver, progress=ctx.progress,
    ))


@stage(StageMeta(
    name="ablation",
    phase="evidence",
    question="Quanto cada bloco de feature e cada corte temporal contribui para a particao?",
    deterministic='conditional',
    nondeterminism="clustering com seed; o bloco de topico vem de LLM a montante",
    description="Reconstrói as features sob variações (corte temporal por processo, blocos "
                "desligados), reagrupa e mede ARI/NMI contra a partição completa.",
    type="op",
    depends_on=("cluster-eval",),
    modes=("neo4j",),
    can_skip_when_done=False,
    estimated_duration="~20-40min",
))
def run(ctx: RunContext) -> None:
    arm = str(ctx.flags.get("run_id") or "exp-anon")
    algo = str(ctx.flags.get("algo") or "hdbscan")
    situacao = str(ctx.flags.get("only_situacao") or "concluido")
    variants = [v.strip() for v in
                str(ctx.flags.get("variants") or ",".join(DEFAULT_VARIANTS)).split(",")
                if v.strip()]

    reference = _labels(arm, algo)
    log.info("ablation: reference %s/%s has %d processos, %d clusters",
             arm, algo, len(reference), len(set(reference.values()) - {-1}))

    results = []
    for variant in variants:
        name, _, spec = variant.partition(":")
        if not spec or "=" not in spec:
            raise ValueError(f"ablation: variant {variant!r} must look like 'name:flag=value'")
        var_id = f"{arm}-{name}"
        npz = FEATURES / f"{var_id}.npz"
        key, _, value = spec.partition("=")
        cache: dict = {}
        _substage(ctx, processo_embed, {"force_all": "true", "only_situacao": situacao,
                                        key: value, "export_features": str(npz)}, cache)
        _substage(ctx, cluster_eval, {"run_id": var_id, "algos": algo,
                                      "features_file": str(npz), "force": "true"}, cache)
        cmp = compare_partitions(reference, _labels(var_id, algo))
        cmp["variant"] = name
        cmp["flag"] = spec
        cmp["run_id"] = var_id
        results.append(cmp)
        log.info("ablation: %-10s ARI=%.4f NMI=%.4f clusters=%d (was %d)",
                 name, cmp["ari"], cmp["nmi"], cmp["n_clusters_cut"], cmp["n_clusters_reference"])

    payload = {
        "generated_at": now_iso(),
        "reference": {"run_id": arm, "algo": algo,
                      "n_processos": len(reference),
                      "n_clusters": len(set(reference.values()) - {-1})},
        "variants": results,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_artifact(payload, OUT_PATH, stage="ablation",
                   params={"run_id": arm, "algo": algo, "only_situacao": situacao,
                           "variants": variants},
                   inputs=[f"artifacts/features/{arm}.npz"])
    ctx.cache["ablation_summary"] = payload
    log.info("ablation complete: wrote %s (%d variants)", OUT_PATH, len(results))
