
from __future__ import annotations

from ..model.cohort import normalize_dt_bound, parse_protocolo_list, resolve_cohort


def _base(*entries):
    return {
        pf: {"data_criacao": dc, "unidades_em_aberto_count": uea}
        for pf, dc, uea in entries
    }


def test_normalize_dt_bound_pads_date_only():
    assert normalize_dt_bound("2025-01-01") == "2025-01-01T00:00:00"
    assert normalize_dt_bound("2025-01-01T08:30:00") == "2025-01-01T08:30:00"


def test_parse_protocolo_list_splits_csv_and_whitespace():
    assert parse_protocolo_list("a, b\nc  d") == ["a", "b", "c", "d"]
    assert parse_protocolo_list("") == []
    assert parse_protocolo_list(None) == []


def test_no_selector_uses_whole_baseline():
    baseline = _base(("P1", "2025-01-01", 0), ("P2", "2025-02-01", 0))
    res = resolve_cohort(
        baseline=baseline, manual=set(), cluster=set(), add=set(), remove=set(),
    )
    assert res.protocolos == ["P1", "P2"]
    assert res.source_counts == {"filter": 2}
    assert res.n_before_cap == 2 and res.n_after_cap == 2


def test_only_concluded_filters_open_processos():
    baseline = _base(("P1", "2025-01-01", 0), ("P2", "2025-02-01", 3))
    res = resolve_cohort(
        baseline=baseline, manual=set(), cluster=set(), add=set(), remove=set(),
        only_concluded=True,
    )
    assert res.protocolos == ["P1"]


def test_cluster_intersects_baseline_and_manual_outranks_cluster():
    baseline = _base(
        ("P1", "2025-01-01", 0), ("P2", "2025-02-01", 0), ("P3", "2025-03-01", 0),
    )
    res = resolve_cohort(
        baseline=baseline,
        manual={"P1"},
        cluster={"P1", "P2", "OUTSIDE"},
        add=set(), remove=set(),
    )
    by = {m.protocolo: m.source for m in res.members}
    assert by == {"P1": "manual", "P2": "cluster"}
    assert res.source_counts == {"manual": 1, "cluster": 1}


def test_remove_excludes_and_add_forces_in_bypassing_filters():
    baseline = _base(("P1", "2025-01-01", 0), ("P2", "2025-02-01", 0))
    info = _base(("P3", "2024-06-01", 5))
    res = resolve_cohort(
        baseline=baseline, manual=set(), cluster=set(),
        add={"P3"}, remove={"P2"}, info=info, only_concluded=True,
    )
    by = {m.protocolo: m.source for m in res.members}
    assert by == {"P1": "filter", "P3": "manual_override"}


def test_cap_keeps_oldest_concluded_and_never_drops_overrides():
    baseline = _base(
        ("P1", "2025-01-01", 0),
        ("P2", "2025-02-01", 0),
        ("P3", "2025-03-01", 0),
        ("P4", "2025-04-01", 0),
    )
    res = resolve_cohort(
        baseline=baseline, manual=set(), cluster=set(),
        add={"P4"}, remove=set(), cap=2, cap_order="oldest",
    )
    assert set(res.protocolos) == {"P1", "P4"}
    assert res.n_before_cap == 4 and res.n_after_cap == 2


def test_cap_newest_order():
    baseline = _base(
        ("P1", "2025-01-01", 0), ("P2", "2025-02-01", 0), ("P3", "2025-03-01", 0),
    )
    res = resolve_cohort(
        baseline=baseline, manual=set(), cluster=set(), add=set(), remove=set(),
        cap=2, cap_order="newest",
    )
    assert set(res.protocolos) == {"P2", "P3"}


def test_cap_prefers_concluded_over_open_when_not_only_concluded():
    baseline = _base(
        ("OPEN", "2024-01-01", 2),
        ("DONE", "2025-06-01", 0),
    )
    res = resolve_cohort(
        baseline=baseline, manual=set(), cluster=set(), add=set(), remove=set(),
        only_concluded=False, cap=1, cap_order="oldest",
    )
    assert res.protocolos == ["DONE"]
