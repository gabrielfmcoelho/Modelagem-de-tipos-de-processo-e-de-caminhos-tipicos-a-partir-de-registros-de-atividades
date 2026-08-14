from __future__ import annotations

import json
import logging
from pathlib import Path

from ..evidence.typical_path import paired_bootstrap as pb
from ..evidence.artifact import write_artifact
from ..core._stage_base import RunContext, StageMeta
from ..core.registry import stage
from ..core.state import now_iso
from ..core.paths import ARTIFACTS

log = logging.getLogger(__name__)

PRIMARY_MARGIN = 0.01
SENSITIVITY_MARGIN = 0.005
from ..model.typical_eval import ALPHABET_NAMES, MODEL_NAMES as MODELS
PAIRS = (
    ("exp-raw/hdbscan", "exp-anon/hdbscan"),
    ("exp-raw/kmeans", "exp-anon/kmeans"),
    ("exp-raw/leiden", "exp-anon/leiden"),
)


@stage(StageMeta(
    name="noninferiority",
    phase="evidence",
    question="O braco anonimizado e nao-inferior ao bruto, contra a margem pre-registrada?",
    deterministic='conditional',
    nondeterminism="bootstrap pareado, fixado pelo seed registrado em params",
    description="Bootstrap pareado processo-a-processo entre os braços raw/anon, contra a margem pré-registrada.",
    type="op",
    depends_on=("cluster-eval",),
    modes=("neo4j", "fs"),
    can_skip_when_done=False,
    estimated_duration="~1-3min",
))
def run(ctx: RunContext) -> None:
    margin = float(ctx.flags.get("margin") or PRIMARY_MARGIN)
    sensitivity = float(ctx.flags.get("sensitivity") or SENSITIVITY_MARGIN)
    topk = int(ctx.flags.get("topk") or 1)
    replicates = int(ctx.flags.get("replicates") or 2000)
    models = [m.strip() for m in str(ctx.flags.get("models") or ",".join(MODELS)).split(",") if m.strip()]
    alphabet = str(ctx.flags.get("alphabet") or "unit")
    if alphabet not in ALPHABET_NAMES:
        raise ValueError(f"noninferiority: unknown alphabet {alphabet!r}, expected one of "
                         f"{ALPHABET_NAMES}")

    results = []
    for arm_a, arm_b in PAIRS:
        ra, aa = arm_a.split("/")
        rb, ab = arm_b.split("/")
        try:
            cell_a, cell_b = pb._cell(ra, aa, alphabet), pb._cell(rb, ab, alphabet)
        except Exception as e:
            log.warning("noninferiority: skipping %s vs %s [%s] (%s)", arm_a, arm_b, alphabet, e)
            continue
        for model in models:
            pa = pb.per_process(cell_a, model, topk)
            pbp = pb.per_process(cell_b, model, topk)
            shared = set(pa) & set(pbp)
            if len(shared) < 30:
                log.warning("noninferiority: %s/%s only %d shared processos — skipped",
                            arm_a, model, len(shared))
                continue
            res = pb.paired_bootstrap(pa, pbp, n=replicates)
            diff = res["difference_b_minus_a"]
            lo = diff["ci90_one_sided_lower"]
            row = {"cell_a": arm_a, "cell_b": arm_b, "model": model, "topk": topk,
                   "n_paired": len(shared), "diff_point": diff["point"],
                   "diff_ci95": diff["ci95"], "ci90_one_sided_lower": lo,
                   "point_a": res["arm_a"]["point"], "point_b": res["arm_b"]["point"],
                   "margin": margin, "sensitivity_margin": sensitivity,
                   "non_inferior": bool(lo is not None and lo > -abs(margin)),
                   "non_inferior_sensitivity": bool(lo is not None and lo > -abs(sensitivity))}
            results.append(row)
            log.info("noninferiority: %-10s %-12s n=%d diff=%+.4f lower=%+.4f "
                     "NI@%.3f=%s NI@%.3f=%s",
                     arm_a.split("/")[1], model, len(shared), diff["point"], lo, margin,
                     row["non_inferior"], sensitivity, row["non_inferior_sensitivity"])

    payload = {"meta": {"generated_at": now_iso(), "topk": topk, "replicates": replicates,
                        "alphabet": alphabet,
                        "margin": margin, "sensitivity_margin": sensitivity,
                        "preregistration": "docs/research/non-inferiority-preregistration.md"},
               "results": results}
    out = ARTIFACTS / "stats" / alphabet / "noninferiority.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    write_artifact(payload, out, stage="noninferiority",
                   params={"margin": margin, "sensitivity_margin": sensitivity, "topk": topk,
                           "alphabet": alphabet, "replicates": replicates, "models": models})
    ctx.cache["noninferiority_summary"] = {
        "comparisons": len(results),
        "non_inferior": sum(1 for r in results if r["non_inferior"]),
        "non_inferior_sensitivity": sum(1 for r in results if r["non_inferior_sensitivity"]),
    }
    log.info("noninferiority: %d comparisons -> %s", len(results), out)
