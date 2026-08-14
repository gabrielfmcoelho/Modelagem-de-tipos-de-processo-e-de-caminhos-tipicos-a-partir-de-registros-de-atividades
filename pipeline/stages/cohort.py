
from __future__ import annotations

import json
import logging
from pathlib import Path

from ..core._stage_base import RunContext, StageMeta, truthy as _truthy
from ..model.cohort import normalize_dt_bound, parse_protocolo_list, resolve_cohort
from ..core.cypher import CLEAR_COORTE_CYPHER, COHORT_BASELINE_BORN_CREATION_UNIT_CYPHER, COHORT_BASELINE_BORN_ORGAO_CYPHER, COHORT_CLUSTER_MEMBERS_CYPHER, COHORT_PROCESSO_INFO_CYPHER, LOAD_COORTE_CYPHER, LOAD_MEMBRO_DA_COORTE_CYPHER
from ..core.neo4j_driver import run_query
from ..core.registry import stage
from ..core.state import now_iso
from ..core.deployment import ORGAO_SIGLA

log = logging.getLogger(__name__)

DEFAULT_FROM = "2025-01-01T00:00:00"
DEFAULT_TO = "2026-01-01T00:00:00"
DEFAULT_ORGAO = ORGAO_SIGLA

def _resolve_protocolo_flag(value: str | None) -> set[str]:
    if not value:
        return set()
    value = value.strip()
    if value.startswith("@"):
        path = Path(value[1:]).expanduser()
        if not path.exists():
            log.warning("cohort: protocolo file not found: %s", path)
            return set()
        return set(parse_protocolo_list(path.read_text(encoding="utf-8")))
    return set(parse_protocolo_list(value))


@stage(StageMeta(
    name="cohort",
    phase="typical-path",
    question="Que subconjunto de processos compoe a coorte sob analise?",
    deterministic=True,
    description="Materializa coorte curada (born-in órgão + janela de data + clusters/lista manual, cap por contagem).",
    type="enrich",
    depends_on=("situacao",),
    soft_depends_on=("processo-cluster", "permanencia"),
    modes=("neo4j",),
    can_skip_when_done=False,
    estimated_duration="~1min",
))
def run(ctx: RunContext) -> None:
    driver = ctx.require_driver()
    writer = ctx.require_writer()
    flags = ctx.flags

    cohort_id = (flags.get("cohort_id") or "").strip()
    if not cohort_id:
        raise ValueError("cohort stage requires --flag cohort_id=<id>")

    label = (flags.get("cohort_label") or cohort_id).strip()
    orgao = (flags.get("orgao_prefix") or DEFAULT_ORGAO).strip()
    from_date = normalize_dt_bound(flags.get("from_date") or flags.get("from") or DEFAULT_FROM)
    to_date = normalize_dt_bound(flags.get("to_date") or flags.get("to") or DEFAULT_TO)
    only_concluded = _truthy(flags.get("only_concluded"), default=True)
    born_via = (flags.get("born_via") or "orgao_edge").strip()
    cap_raw = flags.get("cap")
    cap = int(cap_raw) if cap_raw not in (None, "", "none", "None") else None
    cap_order = (flags.get("cap_order") or "oldest").strip()

    manual = _resolve_protocolo_flag(flags.get("manual_protocolos"))
    cluster_ids = parse_protocolo_list(flags.get("cluster_ids"))
    add = _resolve_protocolo_flag(flags.get("add_protocolos"))
    remove = _resolve_protocolo_flag(flags.get("remove_protocolos"))

    base_cypher = (
        COHORT_BASELINE_BORN_CREATION_UNIT_CYPHER
        if born_via == "creation_activity"
        else COHORT_BASELINE_BORN_ORGAO_CYPHER
    )
    base_rows = run_query(driver, base_cypher, {"orgao": orgao, "from": from_date, "to": to_date})
    baseline = {r["protocolo"]: r for r in base_rows}
    log.info("cohort %s: baseline=%d (orgao=%s, %s..%s, born_via=%s)",
             cohort_id, len(baseline), orgao, from_date, to_date, born_via)

    cluster_members: set[str] = set()
    if cluster_ids:
        rows = run_query(driver, COHORT_CLUSTER_MEMBERS_CYPHER, {"cluster_ids": cluster_ids})
        cluster_members = {r["protocolo"] for r in rows}
        log.info("cohort %s: cluster selector matched %d processos across %d clusters",
                 cohort_id, len(cluster_members), len(cluster_ids))

    extra = (manual | add) - set(baseline)
    info: dict[str, dict] = {}
    if extra:
        rows = run_query(driver, COHORT_PROCESSO_INFO_CYPHER, {"protocolos": sorted(extra)})
        info = {r["protocolo"]: r for r in rows}

    resolution = resolve_cohort(
        baseline=baseline,
        manual=manual,
        cluster=cluster_members,
        add=add,
        remove=remove,
        info=info,
        only_concluded=only_concluded,
        cap=cap,
        cap_order=cap_order,
    )
    log.info("cohort %s: resolved %d members (before cap=%d) sources=%s",
             cohort_id, resolution.n_after_cap, resolution.n_before_cap,
             resolution.source_counts)

    computed_at = now_iso()
    writer.open_phase("cohort")
    try:
        writer.execute_template(
            "clear_coorte", CLEAR_COORTE_CYPHER, {"cohort_id": cohort_id}, phase="cohort",
        )
        writer.execute_template("load_coorte", LOAD_COORTE_CYPHER, {
            "id": cohort_id,
            "label": label,
            "orgao_prefix": orgao,
            "from_date": from_date,
            "to_date": to_date,
            "cap": cap,
            "cap_order": cap_order,
            "only_concluded": only_concluded,
            "n_before_cap": resolution.n_before_cap,
            "n_after_cap": resolution.n_after_cap,
            "source_counts_json": json.dumps(resolution.source_counts, ensure_ascii=False),
            "computed_at": computed_at,
        }, phase="cohort")

        rows = [
            {"protocolo": m.protocolo, "source": m.source, "confidence": 1.0}
            for m in resolution.members
        ]
        for i in range(0, len(rows), 500):
            writer.execute_template(
                "load_membro_da_coorte", LOAD_MEMBRO_DA_COORTE_CYPHER,
                {"rows": rows[i:i + 500], "cohort_id": cohort_id, "computed_at": computed_at},
                phase="cohort",
            )
    finally:
        writer.close_phase("cohort")

    emit_dir = flags.get("emit_dir")
    if emit_dir:
        out = Path(emit_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / f"cohort-{cohort_id}.json").write_text(json.dumps({
            "cohort_id": cohort_id,
            "label": label,
            "orgao_prefix": orgao,
            "from_date": from_date,
            "to_date": to_date,
            "cap": cap,
            "cap_order": cap_order,
            "only_concluded": only_concluded,
            "n_before_cap": resolution.n_before_cap,
            "n_after_cap": resolution.n_after_cap,
            "source_counts": resolution.source_counts,
            "members": [{"protocolo": m.protocolo, "source": m.source} for m in resolution.members],
            "computed_at": computed_at,
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    ctx.cache["cohort_summary"] = {
        "cohort_id": cohort_id,
        "baseline": len(baseline),
        "n_before_cap": resolution.n_before_cap,
        "n_after_cap": resolution.n_after_cap,
        "source_counts": resolution.source_counts,
    }
