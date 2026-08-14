from __future__ import annotations

import json
import logging
from pathlib import Path

from ..evidence.etl import corpus_funnel as cf
from ..core._stage_base import RunContext, StageMeta
from ..core.registry import stage
from ..core.paths import ARTIFACTS

log = logging.getLogger(__name__)

OUT = ARTIFACTS / "stats" / "corpus_funnel.json"


@stage(StageMeta(
    name="corpus-funnel",
    phase="ingest",
    question="Quantos processos foram abertos, quantos concluiram no ano e quantas atividades geraram?",
    deterministic='conditional',
    nondeterminism="consulta o Trino ao vivo; o lakehouse esta sob curadoria ativa",
    description="Conta, direto no Trino, o funil do corpus: processos abertos no ano, "
                "concluídos dentro do ano e atividades correspondentes. É a origem dos "
                "números de corpus citados na prosa dos dois manuscritos.",
    type="op",
    depends_on=(),
    modes=("neo4j", "fs"),
    can_skip_when_done=False,
    estimated_duration="~1-3min",
))
def run(ctx: RunContext) -> None:
    out = Path(ctx.flags.get("out") or OUT)
    argv = ["--year", str(ctx.flags.get("year") or 2025), "--out", str(out)]
    if ctx.flags.get("table"):
        argv += ["--table", str(ctx.flags["table"])]
    if ctx.flags.get("orgao"):
        argv += ["--orgao", str(ctx.flags["orgao"])]
    corpus = None
    if ctx.mode == "neo4j":
        from ..core.corpus import corpus_protocolos
        from ..core.config import Settings
        corpus = corpus_protocolos(Settings.from_env(), ctx.driver) or None
        if corpus:
            log.info("corpus-funnel: pinning the funnel to the %d protocolos the graph "
                     "loaded; the live gold table is re-queried only as a drift check",
                     len(corpus))
    rc = cf.main(argv, corpus=corpus)
    if rc:
        raise RuntimeError(f"corpus-funnel: exited {rc}")

    data = json.loads(out.read_text(encoding="utf-8"))
    ctx.cache["corpus_funnel_summary"] = data
    log.info("corpus-funnel: generated=%s concluded=%s activities=%s -> %s",
             data.get("n_generated"), data.get("n_conclusion_event_logged_same_year"),
             data.get("n_activities_in_concluded"), out)
