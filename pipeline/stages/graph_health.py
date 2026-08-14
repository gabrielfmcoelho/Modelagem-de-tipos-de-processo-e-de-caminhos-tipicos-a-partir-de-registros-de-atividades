
from __future__ import annotations

import argparse
import sys as _sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_ROOT = next((p.parent for p in _HERE.parents if p.name == "pipeline"), _HERE.parents[2])
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))

from ..core._stage_base import RunContext, StageMeta
from pipeline.cli import add_standard_args, resolve_settings
from ..core.logging_setup import configure_logging
from ..core.neo4j_driver import build_driver
from ..core.registry import stage

log = configure_logging(__name__)


_ISOLATED_PRED = "NOT (a)-[:SEGUIDA_POR]-()"
_ORPHAN_PRED = "NOT (a)-[:SEGUIDA_POR]-() AND NOT (a)-[:SEGUIDO_INDEPENDENTEMENTE_POR]-()"
_DISCONNECTED_PRED = _ORPHAN_PRED + " AND NOT (a)-[:REFERENCIA_DOCUMENTO]->()"

PROBE_TOTALS = {
    "atividades": "MATCH (a:Atividade) RETURN count(a) AS c",
    "processos": "MATCH (p:Processo) RETURN count(p) AS c",
    "seguida_por": "MATCH ()-[r:SEGUIDA_POR]->() RETURN count(r) AS c",
    "independente": "MATCH ()-[r:SEGUIDO_INDEPENDENTEMENTE_POR]->() RETURN count(r) AS c",
}

PROBE_ISOLATED_TOTAL = f"MATCH (a:Atividade) WHERE {_ISOLATED_PRED} RETURN count(a) AS c"
PROBE_ISOLATED_BY_TYPE = (
    f"MATCH (a:Atividade) WHERE {_ISOLATED_PRED} "
    "RETURN a.tipo_acao AS t, count(*) AS c ORDER BY c DESC LIMIT 12"
)
PROBE_ORPHAN_TOTAL = f"MATCH (a:Atividade) WHERE {_ORPHAN_PRED} RETURN count(a) AS c"
PROBE_ORPHAN_BY_TYPE = (
    f"MATCH (a:Atividade) WHERE {_ORPHAN_PRED} "
    "RETURN a.tipo_acao AS t, count(*) AS c ORDER BY c DESC LIMIT 12"
)
PROBE_DISCONNECTED_TOTAL = f"MATCH (a:Atividade) WHERE {_DISCONNECTED_PRED} RETURN count(a) AS c"
PROBE_DISCONNECTED_BY_TYPE = (
    f"MATCH (a:Atividade) WHERE {_DISCONNECTED_PRED} "
    "RETURN a.tipo_acao AS t, count(*) AS c ORDER BY c DESC LIMIT 12"
)
PROBE_ISOLATED_CONCLUSIONS = (
    "MATCH (a:Atividade) "
    "WHERE a.tipo_acao IN ['CONCLUSAO-AUTOMATICA-UNIDADE','CONCLUSAO-PROCESSO-UNIDADE'] "
    f"AND {_ISOLATED_PRED} RETURN count(a) AS c"
)
PROBE_START_TYPES = (
    "MATCH (:Processo)-[:INICIOU_PROCESSO]->(a:Atividade) "
    "RETURN a.tipo_acao AS t, count(*) AS c ORDER BY c DESC LIMIT 8"
)
PROBE_SITUACAO = (
    "MATCH (p:Processo) RETURN coalesce(p.situacao,'(null)') AS s, count(*) AS c "
    "ORDER BY c DESC"
)


def _scalar(session, cypher: str) -> int:
    rec = session.run(cypher).single()
    return int(rec["c"]) if rec and rec["c"] is not None else 0


def _pairs(session, cypher: str, key: str) -> list[tuple[str, int]]:
    return [(r[key], int(r["c"])) for r in session.run(cypher)]


def collect_health(driver) -> dict:
    with driver.session() as session:
        totals = {name: _scalar(session, q) for name, q in PROBE_TOTALS.items()}
        stats = {
            "totals": totals,
            "isolated_flow": {
                "total": _scalar(session, PROBE_ISOLATED_TOTAL),
                "by_type": _pairs(session, PROBE_ISOLATED_BY_TYPE, "t"),
            },
            "orphaned": {
                "total": _scalar(session, PROBE_ORPHAN_TOTAL),
                "by_type": _pairs(session, PROBE_ORPHAN_BY_TYPE, "t"),
            },
            "disconnected": {
                "total": _scalar(session, PROBE_DISCONNECTED_TOTAL),
                "by_type": _pairs(session, PROBE_DISCONNECTED_BY_TYPE, "t"),
            },
            "isolated_conclusions": _scalar(session, PROBE_ISOLATED_CONCLUSIONS),
            "start_types": _pairs(session, PROBE_START_TYPES, "t"),
            "situacao": _pairs(session, PROBE_SITUACAO, "s"),
        }
    return stats


def _pct(part: int, whole: int) -> str:
    return f"{(100.0 * part / whole) if whole else 0.0:.1f}%"


def _by_type_lines(rows: list[tuple[str, int]]) -> list[str]:
    return [f"    {tipo:<34} {count:>8,}" for tipo, count in rows]


def format_health_report(stats: dict) -> str:
    t = stats["totals"]
    atv = t["atividades"]
    iso = stats["isolated_flow"]
    orp = stats["orphaned"]
    dis = stats["disconnected"]

    lines: list[str] = []
    lines.append("═══════════════════════ Graph health ═══════════════════════")
    lines.append(f"  atividades:                {atv:>10,}")
    lines.append(f"  processos:                 {t['processos']:>10,}")
    lines.append(f"  SEGUIDA_POR:               {t['seguida_por']:>10,}")
    lines.append(f"  SEGUIDO_INDEPENDENTEMENTE_POR: {t['independente']:>7,}")
    lines.append("")
    lines.append(
        f"Isolated from flow (no SEGUIDA_POR): {iso['total']:,} "
        f"({_pct(iso['total'], atv)})"
    )
    lines.extend(_by_type_lines(iso["by_type"]))
    lines.append(f"  of which conclusions (floating ends): {stats['isolated_conclusions']:,}")
    lines.append("")
    lines.append(
        "Truly orphaned (no SEGUIDA_POR and no SEGUIDO_INDEPENDENTEMENTE_POR): "
        f"{orp['total']:,} ({_pct(orp['total'], atv)})"
    )
    lines.extend(_by_type_lines(orp["by_type"]))
    lines.append("")
    lines.append(
        "Fully disconnected (also no REFERENCIA_DOCUMENTO — the floating floor): "
        f"{dis['total']:,} ({_pct(dis['total'], atv)})"
    )
    lines.extend(_by_type_lines(dis["by_type"]))
    lines.append("")
    lines.append("Start activity types (INICIOU_PROCESSO):")
    lines.extend(_by_type_lines(stats["start_types"]))
    lines.append("")
    lines.append("Situação:")
    lines.extend(_by_type_lines(stats["situacao"]))
    lines.append("═════════════════════════════════════════════════════════════")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Read-only graph-health report")
    add_standard_args(parser)
    args = parser.parse_args()

    settings = resolve_settings(args)
    configure_logging(__name__, settings.log_level)

    driver = build_driver(settings)
    log.info("Connected to Neo4j: %s", settings.neo4j_uri)
    try:
        report = format_health_report(collect_health(driver))
    finally:
        driver.close()
    print(report)


@stage(StageMeta(
    name="graph-health",
    phase="operations",
    question="O grafo de fluxo esta conectado, ou ha nos isolados?",
    deterministic=True,
    description="Relatório read-only de conectividade do fluxo (nós isolados por tipo).",
    type="op",
    depends_on=(),
    soft_depends_on=("timeline",),
    modes=("neo4j",),
    can_skip_when_done=False,
    estimated_duration="<1min",
))
def run(ctx: RunContext) -> None:
    driver = ctx.require_driver()
    stats = collect_health(driver)
    report = format_health_report(stats)
    for line in report.splitlines():
        log.info("%s", line)
    ctx.cache["graph_health"] = stats


if __name__ == "__main__":
    main()
