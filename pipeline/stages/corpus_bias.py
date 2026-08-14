from __future__ import annotations

import datetime
import json
import logging
from pathlib import Path

from ..evidence.artifact import write_artifact
from ..core._stage_base import RunContext, StageMeta
from ..core.registry import stage
from ..core.state import now_iso
from ..core.paths import ARTIFACTS

log = logging.getLogger(__name__)

OUT_PATH = ARTIFACTS / "stats" / "corpus_bias.json"

READ_LIFETIMES_CYPHER = """
MATCH (p:Processo)
WHERE p.data_criacao IS NOT NULL AND p.duracao_lifetime_dias IS NOT NULL
RETURN substring(toString(p.data_criacao), 0, 7) AS mes,
       p.duracao_lifetime_dias AS dias,
       p.protocolo_formatado AS protocolo
"""


def days_available(month: str, boundary: str) -> int:
    y, m = (int(x) for x in month.split("-"))
    end = datetime.date.fromisoformat(boundary)
    return (end - datetime.date(y, m, 1)).days


def estimate_censoring(rows, boundary: str, reference_month: str) -> dict:
    by_month: dict[str, list[float]] = {}
    for mes, dias in rows:
        by_month.setdefault(mes, []).append(float(dias))
    if reference_month not in by_month:
        raise RuntimeError(
            f"corpus-bias: reference month {reference_month} absent; cannot estimate censoring")
    ref = sorted(by_month[reference_month])

    def frac_longer(x: float) -> float:
        return sum(1 for d in ref if d > x) / len(ref)

    months = []
    total_obs = 0
    total_true = 0.0
    for mes in sorted(by_month):
        obs = len(by_month[mes])
        avail = days_available(mes, boundary)
        p_excl = frac_longer(avail)
        true = obs / (1 - p_excl) if p_excl < 0.95 else None
        durations = sorted(by_month[mes])
        months.append({
            "month": mes,
            "observed": obs,
            "days_available": avail,
            "median_lifetime": durations[len(durations) // 2],
            "max_lifetime": durations[-1],
            "estimated_excluded_frac": round(p_excl, 4),
            "estimated_true_n": round(true) if true else None,
        })
        total_obs += obs
        if true:
            total_true += true
    return {
        "reference_month": reference_month,
        "boundary": boundary,
        "months": months,
        "observed_total": total_obs,
        "estimated_true_total": round(total_true),
        "estimated_missing": round(total_true) - total_obs,
        "estimated_missing_frac": round(1 - total_obs / total_true, 4) if total_true else None,
    }


@stage(StageMeta(
    name="corpus-bias",
    phase="evidence",
    question="Quanto o recorte anual descarta processos longos por censura a direita?",
    deterministic=True,
    description="Quantifica o viés de duração do recorte anual: processos longos não cabem na "
                "janela nascimento+conclusão no mesmo ano civil.",
    type="op",
    depends_on=("situacao",),
    modes=("neo4j",),
    can_skip_when_done=False,
    estimated_duration="<1min",
))
def run(ctx: RunContext) -> None:
    boundary = str(ctx.flags.get("boundary") or "2026-01-01")
    reference = str(ctx.flags.get("reference_month") or "2025-01")

    driver = ctx.driver
    if driver is None:
        raise RuntimeError("corpus-bias requires a Neo4j driver")
    with driver.session() as ses:
        rows = [(r["mes"], r["dias"]) for r in ses.run(READ_LIFETIMES_CYPHER)]
    if not rows:
        raise RuntimeError("corpus-bias: no processos with a computed lifetime")

    payload = estimate_censoring(rows, boundary, reference)
    payload["generated_at"] = now_iso()
    payload["caveat"] = (
        f"Lower bound. The reference month {reference} is itself censored at "
        f"{days_available(reference, boundary)} days, so processos longer than that are "
        "missing from the reference distribution too."
    )
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_artifact(payload, OUT_PATH, stage="corpus-bias", params={})
    ctx.cache["corpus_bias_summary"] = payload
    log.info("corpus-bias: observed=%d estimated_true=%d missing=%d (%.1f%%) -> %s",
             payload["observed_total"], payload["estimated_true_total"],
             payload["estimated_missing"], 100 * payload["estimated_missing_frac"], OUT_PATH)
