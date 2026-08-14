
from __future__ import annotations

import re
from dataclasses import dataclass, field

SOURCE_PRECEDENCE = {"manual_override": 3, "manual": 2, "cluster": 1, "filter": 0}


@dataclass(frozen=True)
class CohortMember:
    protocolo: str
    source: str


@dataclass
class CohortResolution:
    members: list[CohortMember]
    n_before_cap: int
    n_after_cap: int
    source_counts: dict[str, int] = field(default_factory=dict)

    @property
    def protocolos(self) -> list[str]:
        return [m.protocolo for m in self.members]


def normalize_dt_bound(value: str) -> str:
    value = (value or "").strip()
    if "T" not in value and len(value) == 10:
        return f"{value}T00:00:00"
    return value


def parse_protocolo_list(text: str | None) -> list[str]:
    if not text:
        return []
    parts = re.split(r"[,\s]+", text.strip())
    return [p for p in (s.strip() for s in parts) if p]


def _is_concluded(pf: str, baseline: dict, info: dict) -> bool:
    data = baseline.get(pf) or info.get(pf) or {}
    return data.get("unidades_em_aberto_count") == 0


def _data_criacao(pf: str, baseline: dict, info: dict) -> str:
    data = baseline.get(pf) or info.get(pf) or {}
    return data.get("data_criacao") or ""


def resolve_cohort(
    *,
    baseline: dict[str, dict],
    manual: set[str],
    cluster: set[str],
    add: set[str],
    remove: set[str],
    info: dict[str, dict] | None = None,
    only_concluded: bool = True,
    cap: int | None = None,
    cap_order: str = "oldest",
) -> CohortResolution:
    info = info or {}

    sources: dict[str, str] = {}
    if manual or cluster:
        for pf in cluster:
            if pf in baseline:
                sources[pf] = "cluster"
        for pf in manual:
            if pf in baseline:
                sources[pf] = "manual"
    else:
        for pf in baseline:
            sources[pf] = "filter"

    if only_concluded:
        sources = {
            pf: s for pf, s in sources.items()
            if _is_concluded(pf, baseline, info)
        }

    for pf in remove:
        sources.pop(pf, None)

    for pf in add:
        if pf not in remove:
            sources[pf] = "manual_override"

    n_before_cap = len(sources)

    members_pf = list(sources.keys())
    if cap is not None and cap >= 0 and len(members_pf) > cap:
        forced = [pf for pf in members_pf if sources[pf] == "manual_override"]
        rest = [pf for pf in members_pf if sources[pf] != "manual_override"]
        rest.sort(
            key=lambda pf: _data_criacao(pf, baseline, info),
            reverse=(cap_order == "newest"),
        )
        rest.sort(key=lambda pf: 0 if _is_concluded(pf, baseline, info) else 1)
        keep = max(cap - len(forced), 0)
        members_pf = forced + rest[:keep]

    members = sorted(
        (CohortMember(pf, sources[pf]) for pf in members_pf),
        key=lambda m: m.protocolo,
    )
    source_counts: dict[str, int] = {}
    for m in members:
        source_counts[m.source] = source_counts.get(m.source, 0) + 1

    return CohortResolution(
        members=members,
        n_before_cap=n_before_cap,
        n_after_cap=len(members),
        source_counts=source_counts,
    )
