
from __future__ import annotations

from collections import defaultdict, deque
from statistics import mean

from .process_state import ACTIVATION_TYPES, CONCLUSION_TYPES


def longitudinal_rank(nodes, edges) -> dict[str, int]:
    keys = [n["state_key"] for n in nodes]
    present = set(keys)
    adj: dict[str, list[str]] = defaultdict(list)
    indeg = {k: 0 for k in keys}
    for e in edges:
        f, t = e["from_key"], e["to_key"]
        if f in present and t in present:
            adj[f].append(t)
            indeg[t] += 1

    starts = [k for k in keys if indeg[k] == 0]
    if not starts:
        starts = [n["state_key"] for n in nodes if n.get("is_activation")] or list(keys)

    rank: dict[str, int] = {}
    dq: deque[str] = deque()
    for s in starts:
        if s not in rank:
            rank[s] = 0
            dq.append(s)
    while dq:
        u = dq.popleft()
        for v in adj[u]:
            if v not in rank:
                rank[v] = rank[u] + 1
                dq.append(v)

    deepest = max(rank.values(), default=0)
    for k in keys:
        rank.setdefault(k, deepest + 1)
    return rank


def _dag_topo_and_backedges(keys, edges):
    present = set(keys)
    adj: dict[str, list[str]] = defaultdict(list)
    for e in edges:
        if e["from_key"] in present and e["to_key"] in present:
            adj[e["from_key"]].append(e["to_key"])

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {k: WHITE for k in keys}
    order: list[str] = []
    back: set[tuple[str, str]] = set()
    for s in keys:
        if color[s] != WHITE:
            continue
        color[s] = GRAY
        stack = [(s, iter(adj[s]))]
        while stack:
            node, it = stack[-1]
            for v in it:
                if color[v] == WHITE:
                    color[v] = GRAY
                    stack.append((v, iter(adj[v])))
                    break
                if color[v] == GRAY:
                    back.add((node, v))
            else:
                color[node] = BLACK
                order.append(node)
                stack.pop()
    order.reverse()
    return order, back


def layer_assignment(nodes, edges) -> dict[str, int]:
    keys = [n["state_key"] for n in nodes]
    present = set(keys)
    topo, back = _dag_topo_and_backedges(keys, edges)
    fwd_preds: dict[str, list[str]] = defaultdict(list)
    for e in edges:
        f, t = e["from_key"], e["to_key"]
        if f in present and t in present and (f, t) not in back:
            fwd_preds[t].append(f)
    layer: dict[str, int] = {}
    for k in topo:
        layer[k] = max((layer[p] + 1 for p in fwd_preds.get(k, [])), default=0)
    return layer


def order_lanes(nodes, ranks: dict[str, int]) -> list[str]:
    lane_ranks: dict[str, list[int]] = defaultdict(list)
    for n in nodes:
        lane = n.get("unidade_lane") or "?"
        lane_ranks[lane].append(ranks.get(n["state_key"], 0))
    return sorted(lane_ranks, key=lambda lane: (mean(lane_ranks[lane]), lane))


def _forward_adj(nodes, edges, ranks):
    present = {n["state_key"] for n in nodes}
    fwd: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for e in edges:
        f, t = e["from_key"], e["to_key"]
        if f in present and t in present and ranks[t] > ranks[f]:
            weight = float(e.get("n_processos") or e.get("frequency") or 0.0)
            fwd[f].append((t, weight))
    return fwd


def find_spine(nodes, edges) -> list[str]:
    ranks = layer_assignment(nodes, edges)
    keys = [n["state_key"] for n in nodes]
    is_con = {n["state_key"]: bool(n.get("is_conclusion")) for n in nodes}
    fwd = _forward_adj(nodes, edges, ranks)

    fwd_indeg = {k: 0 for k in keys}
    for u in fwd:
        for v, _w in fwd[u]:
            fwd_indeg[v] += 1
    best: dict[str, tuple[float, list[str]]] = {
        k: (0.0, [k]) for k in keys if fwd_indeg[k] == 0
    }
    for k in sorted(keys, key=lambda x: ranks[x]):
        if k not in best:
            continue
        w0, p0 = best[k]
        for t, w in fwd.get(k, []):
            cand = (w0 + w, p0 + [t])
            if t not in best or cand[0] > best[t][0]:
                best[t] = cand

    ends = [best[k] for k in keys if is_con[k] and k in best]
    if not ends:
        ends = list(best.values())
    if not ends:
        return []
    return max(ends, key=lambda wp: wp[0])[1]


def build_swimlane(nodes, edges, *, total_processos: int, coverage_floor: float = 0.0):
    total = total_processos or 1
    fedges = [e for e in edges if (e.get("n_processos") or 0) / total >= coverage_floor]

    keep: set[str] = set()
    for e in fedges:
        keep.add(e["from_key"])
        keep.add(e["to_key"])
    nodes = [n for n in nodes if n["state_key"] in keep]

    ranks = layer_assignment(nodes, fedges)
    lanes = order_lanes(nodes, ranks)
    lane_order = {lane: i for i, lane in enumerate(lanes)}
    spine = find_spine(nodes, fedges)

    lane_cols: dict[str, list[int]] = defaultdict(list)
    for n in nodes:
        lane_cols[n.get("unidade_lane") or "?"].append(ranks.get(n["state_key"], 0))
    lane_span = {lane: (min(cols), max(cols)) for lane, cols in lane_cols.items()}
    spine_set = set(spine)
    spine_edges = set(zip(spine, spine[1:]))
    lane_of = {n["state_key"]: (n.get("unidade_lane") or "?") for n in nodes}

    indeg = {n["state_key"]: 0 for n in nodes}
    outdeg = {n["state_key"]: 0 for n in nodes}
    for e in fedges:
        if e["to_key"] in indeg:
            indeg[e["to_key"]] += 1
        if e["from_key"] in outdeg:
            outdeg[e["from_key"]] += 1

    tipo_of = {n["state_key"]: n.get("tipo_acao") for n in nodes}
    act_sources = {k for k, t in tipo_of.items() if t in ACTIVATION_TYPES and indeg.get(k, 0) == 0}
    conclusions = {k for k, t in tipo_of.items() if t in CONCLUSION_TYPES}

    def _is_start(k):
        return k in act_sources if act_sources else indeg.get(k, 0) == 0

    def _is_end(n):
        k = n["state_key"]
        if conclusions:
            return k in conclusions
        return bool(n.get("is_conclusion")) or outdeg.get(k, 0) == 0

    node_out = [
        {
            "id": n["state_key"],
            "label": n.get("tipo_acao"),
            "lane": lane_of[n["state_key"]],
            "x": ranks.get(n["state_key"], 0),
            "frequency": n.get("frequency"),
            "coverage": round((n.get("n_processos") or 0) / total, 4),
            "grupo": n.get("grupo"),
            "on_spine": n["state_key"] in spine_set,
            "is_start": _is_start(n["state_key"]),
            "is_end": _is_end(n),
            "phase": ("start" if _is_start(n["state_key"]) else "end" if _is_end(n) else "middle"),
            "gcn_importance": n.get("gcn_importance"),
            "gcn_kept": n.get("in_ideal_graph"),
        }
        for n in nodes
    ]
    edge_out = [
        {
            "from": e["from_key"],
            "to": e["to_key"],
            "coverage": round((e.get("n_processos") or 0) / total, 4),
            "frequency": e.get("frequency"),
            "mean_interval_h": e.get("mean_intervalo_horas"),
            "kind": "within"
            if lane_of.get(e["from_key"]) == lane_of.get(e["to_key"])
            else "handoff",
            "on_spine": (e["from_key"], e["to_key"]) in spine_edges,
            "back_edge": ranks.get(e["to_key"], 0) <= ranks.get(e["from_key"], 0),
        }
        for e in fedges
    ]

    return {
        "lanes": [
            {"unidade": lane, "order": lane_order[lane],
             "x_start": lane_span[lane][0], "x_end": lane_span[lane][1]}
            for lane in lanes
        ],
        "nodes": node_out,
        "edges": edge_out,
        "spine": spine,
        "max_x": max(ranks.values(), default=0),
    }
