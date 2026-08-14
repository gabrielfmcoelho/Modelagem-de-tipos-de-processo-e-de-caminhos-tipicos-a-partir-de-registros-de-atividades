
from __future__ import annotations

from collections import Counter, defaultdict

from .classifier import get_grupo
from .dfg import _lane
from .process_state import ACTIVATION_TYPES, CONCLUSION_TYPES


def _split(state: str) -> tuple[str, str]:
    tipo, _, lane = (state or "").partition("@")
    return tipo, (lane or "?")


def aggregate_swimlane_graph(traces, *, total_processos: int | None = None):
    nfreq: Counter = Counter()
    nprocs: dict[str, set] = defaultdict(set)
    efreq: Counter = Counter()
    eprocs: dict[tuple, set] = defaultdict(set)
    for ti, tr in enumerate(traces):
        for s in tr:
            nfreq[s] += 1
            nprocs[s].add(ti)
        for a, b in zip(tr, tr[1:]):
            efreq[(a, b)] += 1
            eprocs[(a, b)].add(ti)

    total = total_processos or len(traces) or 1
    nodes = []
    for s, f in nfreq.items():
        tipo, lane = _split(s)
        nodes.append({
            "state_key": s, "tipo_acao": tipo, "unidade_lane": lane,
            "grupo": get_grupo(tipo), "frequency": f, "n_processos": len(nprocs[s]),
            "is_activation": tipo in ACTIVATION_TYPES,
            "is_conclusion": tipo in CONCLUSION_TYPES,
        })
    edges = [
        {"from_key": a, "to_key": b, "frequency": f, "n_processos": len(eprocs[(a, b)]),
         "mean_intervalo_horas": None}
        for (a, b), f in efreq.items()
    ]
    return nodes, edges, total


def sequence_swimlane(states) -> dict:
    states = list(states)
    n = len(states)
    lane_first: dict[str, int] = {}
    for i, s in enumerate(states):
        lane_first.setdefault(_split(s)[1], i)
    lanes_sorted = sorted(lane_first, key=lambda lane: lane_first[lane])
    lane_order = {lane: i for i, lane in enumerate(lanes_sorted)}

    lane_x: dict[str, list[int]] = defaultdict(list)
    lane_of: dict[str, str] = {}
    nodes = []
    for i, s in enumerate(states):
        tipo, lane = _split(s)
        lane_x[lane].append(i)
        lane_of[f"s{i}"] = lane
        nodes.append({
            "id": f"s{i}", "label": tipo, "lane": lane, "x": i, "coverage": 1.0,
            "frequency": 1, "grupo": get_grupo(tipo), "on_spine": True,
            "is_start": i == 0, "is_end": i == n - 1,
            "phase": "start" if i == 0 else "end" if i == n - 1 else "middle",
        })
    edges = []
    for i in range(n - 1):
        a, b = f"s{i}", f"s{i + 1}"
        edges.append({
            "from": a, "to": b, "coverage": 1.0, "frequency": 1, "mean_interval_h": None,
            "kind": "within" if lane_of[a] == lane_of[b] else "handoff",
            "on_spine": True,
            "back_edge": False,
        })
    return {
        "lanes": [{"unidade": lane, "order": lane_order[lane],
                   "x_start": min(lane_x[lane]), "x_end": max(lane_x[lane])}
                  for lane in lanes_sorted],
        "nodes": nodes, "edges": edges,
        "spine": [f"s{i}" for i in range(n)], "max_x": max(0, n - 1),
    }


def processo_timeline(activities, edges, *, lane_depth: int | None = None) -> dict:
    acts = sorted(activities, key=lambda a: (a.get("data_hora") or "", a.get("source_id") or ""))
    n = len(acts)
    xof: dict[str, int] = {}
    lane_of: dict[str, str] = {}
    lane_first: dict[str, int] = {}
    lane_x: dict[str, list[int]] = defaultdict(list)
    nodes = []
    for i, a in enumerate(acts):
        sid = a.get("source_id")
        tipo = a.get("tipo_acao") or "OUTROS"
        lane = _lane(a.get("unidade"), lane_depth)
        xof[sid] = i
        lane_of[sid] = lane
        lane_first.setdefault(lane, i)
        lane_x[lane].append(i)
        is_end = tipo in CONCLUSION_TYPES
        nodes.append({
            "id": sid, "label": tipo, "lane": lane, "x": i, "coverage": 1.0, "frequency": 1,
            "grupo": get_grupo(tipo), "on_spine": True, "data_hora": a.get("data_hora"),
            "is_start": i == 0, "is_end": is_end,
            "phase": "start" if i == 0 else "end" if is_end else "middle",
        })
    lanes_sorted = sorted(lane_first, key=lambda lane: lane_first[lane])
    lane_order = {lane: i for i, lane in enumerate(lanes_sorted)}
    out_edges = []
    for e in edges:
        f, t = e.get("from_id"), e.get("to_id")
        if f not in xof or t not in xof:
            continue
        within = bool(e.get("mesma_unidade")) or lane_of[f] == lane_of[t]
        out_edges.append({
            "from": f, "to": t, "coverage": 1.0, "frequency": 1,
            "mean_interval_h": e.get("intervalo_horas"),
            "kind": "within" if within else "handoff",
            "on_spine": True, "back_edge": xof[t] <= xof[f],
        })
    return {
        "lanes": [{"unidade": lane, "order": lane_order[lane],
                   "x_start": min(lane_x[lane]), "x_end": max(lane_x[lane])}
                  for lane in lanes_sorted],
        "nodes": nodes, "edges": out_edges,
        "spine": [a.get("source_id") for a in acts], "max_x": max(0, n - 1),
    }
