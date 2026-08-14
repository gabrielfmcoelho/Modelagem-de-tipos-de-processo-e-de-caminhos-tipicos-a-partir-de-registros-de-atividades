from __future__ import annotations

import json
import logging
from pathlib import Path

from ..evidence.typical_path import constraint_cost as cc
from ..core._stage_base import RunContext, StageMeta
from ..core.registry import stage
from ..core.paths import ARTIFACTS

log = logging.getLogger(__name__)

OUT = ARTIFACTS / "stats" / "constraint_cost.json"


@stage(StageMeta(
    name="constraint-cost",
    phase="evidence",
    question="Quanto o automato de fluxo custa ao gerador em cada ponto de decisao?",
    deterministic='conditional',
    nondeterminism="particao treino/teste fixada pelo seed registrado em params",
    description="Mede o que o autômato de fluxo custa ao gerador: em cada ponto de decisão "
                "retido, compara os top-k candidatos da cadeia de Markov com e sem o filtro. "
                "Produz artifacts/stats/constraint_cost.json, a evidência da segunda metade "
                "da RQ4 nos dois manuscritos.",
    type="op",
    depends_on=("cluster-eval",),
    modes=("neo4j", "fs"),
    can_skip_when_done=False,
    estimated_duration="~2-10min",
))
def run(ctx: RunContext) -> None:
    out = Path(ctx.flags.get("out") or OUT)
    argv = ["--run-id", str(ctx.flags.get("run_id") or "exp-raw"),
            "--algo", str(ctx.flags.get("algo") or "kmeans"),
            "--alphabet", str(ctx.flags.get("alphabet") or "unit"),
            "--order", str(ctx.flags.get("order") or 3),
            "--top-k", str(ctx.flags.get("top_k") or 8),
            "--min-traces", str(ctx.flags.get("min_traces") or 30),
            "--train-frac", str(ctx.flags.get("train_frac") or 0.7),
            "--seed", str(ctx.flags.get("seed") or 42),
            "--out", str(out)]
    if ctx.flags.get("traces_file"):
        argv += ["--traces-file", str(ctx.flags["traces_file"])]
    rc = cc.main(argv)
    if rc:
        raise RuntimeError(f"constraint-cost: exited {rc}")

    payload = json.loads(out.read_text(encoding="utf-8"))
    if not payload.get("n_decision_steps"):
        raise RuntimeError(
            "constraint-cost: zero decision points measured. Every fraction would render as "
            "0.0 and read as 'the constraint never binds', which is the claim the manuscripts "
            "make -- it must not be produced by an empty measurement.")
    ctx.cache["constraint_cost_summary"] = payload
    log.info("constraint-cost: %s steps over %s clusters, alters %.4f, argmax changed %.4f, "
             "no legal candidate %.4f -> %s",
             payload["n_decision_steps"], payload["n_clusters"],
             payload["constraint_alters_topk_frac"],
             payload["constraint_changes_argmax_frac"],
             payload["no_legal_candidate_frac"], out)
