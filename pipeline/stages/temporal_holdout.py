from __future__ import annotations

import json
import logging
from pathlib import Path

from ..evidence.typical_path import temporal_holdout_matched as tho
from ..core._stage_base import RunContext, StageMeta
from ..core.registry import stage
from ..core.paths import ARTIFACTS

log = logging.getLogger(__name__)

OUT = ARTIFACTS / "stats" / "temporal_holdout_matched.json"


@stage(StageMeta(
    name="temporal-holdout",
    phase="evidence",
    question="O ganho sobrevive quando a particao ve apenas parte do historico de cada caso?",
    deterministic='conditional',
    nondeterminism="particao treino/teste fixada pelo seed registrado em params",
    description="Repontua cada truncamento de linha do tempo sobre os casos que todos avaliam, "
                "produzindo artifacts/stats/temporal_holdout_matched.json — a fonte da tabela "
                "tab:temporal-holdout dos dois manuscritos.",
    type="op",
    depends_on=("cluster-eval",),
    modes=("neo4j", "fs"),
    can_skip_when_done=False,
    estimated_duration="~5-15min",
))
def run(ctx: RunContext) -> None:
    if not tho.TRACES.is_file():
        raise FileNotFoundError(
            f"temporal-holdout: {tho.TRACES} not found — run `python -m pipeline run export-traces` "
            "first; without it every truncation would be scored on an empty population")

    out = Path(ctx.flags.get("out") or OUT)
    argv = ["--algo", str(ctx.flags.get("algo") or "hdbscan"),
            "--min-traces", str(ctx.flags.get("min_traces") or 30),
            "--train-frac", str(ctx.flags.get("train_frac") or 0.7),
            "--seed", str(ctx.flags.get("seed") or 42),
            "--out", str(out)]
    rc = tho.main(argv)
    if rc:
        raise RuntimeError(f"temporal-holdout: exited {rc}")

    payload = json.loads(out.read_text(encoding="utf-8"))
    ctx.cache["temporal_holdout_summary"] = {
        "out": str(out), "n_common_cases": payload.get("n_common_cases"),
        "retained_frac_at_25pct": payload.get("retained_frac_at_25pct"),
        "rows": len(payload.get("rows") or [])}
    log.info("temporal-holdout: %d common cases, %d rows -> %s",
             payload.get("n_common_cases"), len(payload.get("rows") or []), out)
