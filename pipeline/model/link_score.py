
from __future__ import annotations

import bisect
from collections import defaultdict, deque
from typing import Any

from .process_state import CONCLUSION_TYPES
from .timeline import build_edges_for_processo

DEFAULT_W_ADV = 0.5
DEFAULT_W_SPEED = 0.2

DEFAULT_REWORK_PENALTY = 0.5
DEFAULT_IDLE_PENALTY = 0.4
DEFAULT_IDLE_FACTOR = 3.0
DEFAULT_IDLE_FLOOR_H = 24.0


def percentile_ranks(values: dict[str, float]) -> dict[str, float]:
    items = [(k, v) for k, v in values.items() if v is not None]
    n = len(items)
    if n == 0:
        return {}
    if n == 1:
        return {items[0][0]: 0.5}
    sorted_vals = sorted(v for _, v in items)
    out: dict[str, float] = {}
    for k, v in items:
        lo = bisect.bisect_left(sorted_vals, v)
        out[k] = min(lo / (n - 1), 1.0)
    return out


def speed_scores_from_durations(durations: dict[str, float]) -> dict[str, float]:
    ranks = percentile_ranks(durations)
    return {k: round(1.0 - r, 4) for k, r in ranks.items()}


def _median(xs) -> float | None:
    vals = sorted(v for v in xs if v is not None)
    if not vals:
        return None
    n = len(vals)
    m = n // 2
    return vals[m] if n % 2 else (vals[m - 1] + vals[m]) / 2.0


def _reaches_conclusion(flow_edges: list[dict], conclusion_ids: set[str]) -> set[str]:
    radj: dict[str, list[str]] = defaultdict(list)
    for e in flow_edges:
        radj[e["to_id"]].append(e["from_id"])
    reachable: set[str] = set(conclusion_ids)
    dq = deque(conclusion_ids)
    while dq:
        node = dq.popleft()
        for pred in radj[node]:
            if pred not in reachable:
                reachable.add(pred)
                dq.append(pred)
    return reachable


def assign_rework(activities: list[dict], state: dict[str, Any]) -> dict[str, bool]:
    by_unit = {u["unidade"]: u.get("ciclos", []) for u in state.get("unidades", [])}
    result: dict[str, bool] = {}
    for atv in activities:
        unit = atv.get("unidade")
        sid = atv.get("source_id")
        dh = atv.get("data_hora")
        rework = False
        chosen = None
        for c in by_unit.get(unit, []):
            ent = c.get("entrada")
            sai = c.get("saida")
            if not ent:
                continue
            if sai is None:
                if dh and dh >= ent:
                    chosen = c
            elif dh and ent <= dh <= sai:
                chosen = c
                break
        if chosen is not None and (chosen.get("ordem", 0) > 0 or chosen.get("implicit_close")):
            rework = True
        if atv.get("tipo_acao") == "REABERTURA-PROCESSO-UNIDADE":
            rework = True
        result[sid] = rework
    return result


def score_process(
    activities: list[dict],
    state: dict[str, Any],
    *,
    speed: float,
    flow_edges: list[dict] | None = None,
    w_adv: float = DEFAULT_W_ADV,
    w_speed: float = DEFAULT_W_SPEED,
    rework_penalty: float = DEFAULT_REWORK_PENALTY,
    idle_penalty: float = DEFAULT_IDLE_PENALTY,
    idle_factor: float = DEFAULT_IDLE_FACTOR,
    idle_floor_h: float = DEFAULT_IDLE_FLOOR_H,
) -> tuple[list[dict], dict[str, dict]]:
    if flow_edges is None:
        flow_edges, _ = build_edges_for_processo(list(activities))

    conclusion_ids = [
        a["source_id"] for a in activities if a.get("tipo_acao") in CONCLUSION_TYPES
    ]
    if not conclusion_ids and activities:
        conclusion_ids = [activities[-1]["source_id"]]
    reachable = _reaches_conclusion(flow_edges, set(conclusion_ids))
    rework = assign_rework(activities, state)
    med = _median([e.get("intervalo_horas") for e in flow_edges])

    denom = (w_adv + w_speed) or 1.0

    def blend(adv: float) -> float:
        return round((w_adv * adv + w_speed * speed) / denom, 4)

    node_scores: dict[str, dict] = {}
    for a in activities:
        sid = a["source_id"]
        adv = 1.0 if sid in reachable else 0.0
        if rework.get(sid):
            adv *= (1.0 - rework_penalty)
        node_scores[sid] = {
            "source_id": sid,
            "node_advancement_score": round(adv, 4),
            "node_speed_score": round(speed, 4),
            "node_contrib_score": blend(adv),
            "rework": bool(rework.get(sid)),
        }

    edge_scores: list[dict] = []
    for e in flow_edges:
        from_id, to_id = e["from_id"], e["to_id"]
        adv = 1.0 if to_id in reachable else 0.0
        rw = bool(rework.get(from_id) or rework.get(to_id))
        if rw:
            adv *= (1.0 - rework_penalty)
        ih = e.get("intervalo_horas")
        idle = (
            ih is not None and med not in (None, 0)
            and ih > idle_factor * med and ih > idle_floor_h
        )
        if idle:
            adv *= (1.0 - idle_penalty)
        edge_scores.append({
            "from_id": from_id,
            "to_id": to_id,
            "advancement_score": round(adv, 4),
            "speed_score": round(speed, 4),
            "rework_flag": rw,
            "idle_flag": bool(idle),
            "contrib_score": blend(adv),
        })

    return edge_scores, node_scores
