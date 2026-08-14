from __future__ import annotations

import json
import logging
import subprocess
import sys
from pathlib import Path

from ..core._stage_base import RunContext, StageMeta
from ..core.paths import ARTIFACTS, ROOT
from ..core.registry import stage
from ..evidence.artifact import write_artifact
from ..model.typical_eval import ALPHABET_NAMES

log = logging.getLogger(__name__)

SCRIPT = ROOT / "scripts" / "conformance_pm4py.py"


@stage(StageMeta(
    name="conformance",
    phase="evidence",
    question="Quanto do comportamento observado o modelo descoberto reproduz, e quanto "
             "comportamento a mais ele permite?",
    deterministic=True,
    description="Conformance por cluster (fitness e precision, token replay) via pm4py, sobre "
                "as traces congeladas. pm4py é AGPL v3: o cálculo vive em "
                "scripts/conformance_pm4py.py e é invocado por subprocesso, nunca importado, "
                "para que a licença não alcance o produto entregável. O stage existe para dar "
                "procedência ao artefato — o resultado passa a declarar o stage que o produziu.",
    type="op",
    depends_on=("export-traces",),
    modes=("neo4j", "fs"),
    can_skip_when_done=False,
    estimated_duration="~5-20min por célula",
))
def run(ctx: RunContext) -> None:
    run_id = str(ctx.flags.get("run_id") or "")
    algo = str(ctx.flags.get("algo") or "")
    alphabet = str(ctx.flags.get("alphabet") or "procedure")
    if alphabet not in ALPHABET_NAMES:
        raise ValueError(f"conformance: unknown alphabet {alphabet!r}, expected one of "
                         f"{ALPHABET_NAMES}")
    if not run_id or not algo:
        raise ValueError(
            "conformance needs --flag run_id=<clustering> and --flag algo=<algorithm>; "
            "it scores one cell at a time because pm4py alignment is expensive.")
    if not SCRIPT.is_file():
        raise FileNotFoundError(
            f"{SCRIPT} is missing. The pm4py computation deliberately lives outside pipeline/ "
            "so that an AGPL dependency never enters the deployable package.")

    out = ARTIFACTS / "conformance" / run_id / algo / alphabet / "pm4py.json"
    argv = [sys.executable, str(SCRIPT), "--run-id", run_id, "--algo", algo,
            "--alphabet", alphabet, "--out", str(out)]
    if ctx.flags.get("max_clusters"):
        argv += ["--max-clusters", str(ctx.flags["max_clusters"])]

    log.info("conformance: %s", " ".join(argv))
    proc = subprocess.run(argv, cwd=ROOT, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"conformance: {SCRIPT.name} exited {proc.returncode}")
    if not out.is_file():
        raise RuntimeError(
            f"conformance: {SCRIPT.name} exited 0 but wrote nothing to {out}. A subprocess that "
            "succeeds without producing its artifact is the failure mode this check exists for.")

    payload = json.loads(out.read_text(encoding="utf-8"))
    traces = ARTIFACTS / "traces" / "protocol_traces.json.gz"
    grouping = ARTIFACTS / "traces" / run_id / algo / "grouping.json.gz"
    write_artifact(payload, out, stage="conformance",
                   params={"run_id": run_id, "algo": algo, "alphabet": alphabet,
                           "engine": "pm4py", "licence": "AGPL-3.0",
                           "invoked_as": "subprocess"},
                   inputs=[p for p in (traces, grouping) if p.is_file()])
    agg = payload.get("aggregate") or {}
    ctx.cache["conformance_aggregate"] = agg
    log.info("conformance: %s/%s/%s -> %s", run_id, algo, alphabet, agg or "no aggregate")
