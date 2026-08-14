from __future__ import annotations

import json
import logging
from pathlib import Path

from ..evidence.etl import export_traces as et
from ..core._stage_base import RunContext, StageMeta
from ..core.registry import stage
from ..core.paths import ARTIFACTS

log = logging.getLogger(__name__)

OUT_DIR = ARTIFACTS / "traces"


@stage(StageMeta(
    name="export-traces",
    phase="typical-path",
    question="Qual a sequencia de estados de cada processo do corpus?",
    deterministic='conditional',
    nondeterminism="reflete o estado do grafo no momento da leitura",
    description="Lê o Neo4j uma única vez e congela as traces de todo o corpus em "
                "artifacts/traces/, com um agrupamento por clusterização. Todo o trabalho "
                "downstream sobre traces roda sem Neo4j. É também a origem das siglas de "
                "unidade que o results usa para cegar a tabela de catálogo.",
    type="op",
    depends_on=("situacao",),
    modes=("neo4j",),
    can_skip_when_done=False,
    estimated_duration="~5-15min",
))
def run(ctx: RunContext) -> None:
    out_dir = Path(ctx.flags.get("out_dir") or OUT_DIR)
    argv = ["--min-traces", str(ctx.flags.get("min_traces") or 30),
            "--out-dir", str(out_dir)]
    rc = et.main(argv)
    if rc:
        raise RuntimeError(f"export-traces: exited {rc}")

    corpus = out_dir / "protocol_traces.json.gz"
    if not corpus.is_file():
        raise RuntimeError(f"export-traces: reported success but {corpus} is absent")
    index = json.loads((out_dir / "index.json").read_text(encoding="utf-8"))
    ctx.cache["export_traces_summary"] = {
        "out_dir": str(out_dir), "n_processos": index.get("n_processos"),
        "cells": len(index.get("cells") or [])}
    log.info("export-traces: %s processos, %d groupings -> %s",
             index.get("n_processos"), len(index.get("cells") or []), out_dir)
