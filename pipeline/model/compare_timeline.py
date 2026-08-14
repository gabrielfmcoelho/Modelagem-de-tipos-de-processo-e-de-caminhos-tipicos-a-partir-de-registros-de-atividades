
from __future__ import annotations

from collections import Counter

from .dfg import _lane
from .process_state import CONCLUSION_TYPES

GERACAO = "GERACAO-PROCEDIMENTO"
REMETIDO = "PROCESSO-REMETIDO-UNIDADE"
RECEBIDO = "PROCESSO-RECEBIDO-UNIDADE"


def top_units(swimlane: dict, *, roll_depth: int | None = 2, k: int = 4) -> list[str]:
    weight: Counter = Counter()
    for n in swimlane.get("nodes", []):
        weight[_lane(n.get("lane"), roll_depth)] += (n.get("frequency") or 1)
    return [u for u, _ in weight.most_common(k)]


def handoff_pairs(swimlane: dict, *, roll_depth: int | None = 2) -> set[tuple[str, str]]:
    lane = {n["id"]: _lane(n.get("lane"), roll_depth) for n in swimlane.get("nodes", [])}
    pairs: set[tuple[str, str]] = set()
    for e in swimlane.get("edges", []):
        f, t = e.get("from"), e.get("to")
        if f in lane and t in lane and lane[f] != lane[t]:
            pairs.add((lane[f], lane[t]))
    return pairs


def handoff_count(swimlane: dict, *, roll_depth: int | None = 2) -> int:
    lane = {n["id"]: _lane(n.get("lane"), roll_depth) for n in swimlane.get("nodes", [])}
    return sum(1 for e in swimlane.get("edges", [])
               if e.get("from") in lane and e.get("to") in lane and lane[e["from"]] != lane[e["to"]])


def timeline_rules(swimlane: dict) -> dict:
    indeg: Counter = Counter()
    outdeg: Counter = Counter()
    for e in swimlane.get("edges", []):
        outdeg[e.get("from")] += 1
        indeg[e.get("to")] += 1
    label = {n["id"]: (n.get("label") or "") for n in swimlane.get("nodes", [])}
    ger = [i for i, t in label.items() if t.startswith("GERACAO-PROCEDIMENTO")]
    rem = [i for i, t in label.items() if t.startswith("PROCESSO-REMETIDO")]
    con = [i for i, t in label.items() if t in CONCLUSION_TYPES]
    return {
        "GERACAO_source": bool(ger) and all(indeg[i] == 0 for i in ger),
        "REMETIDO_has_pred": (all(indeg[i] >= 1 for i in rem) if rem else None),
        "CONCLUSAO_terminal": (all(outdeg[i] == 0 for i in con) if con else None),
    }


def timeline_rule_scores(swimlane: dict) -> dict:
    nodes = swimlane.get("nodes", [])
    label = {n["id"]: (n.get("label") or "") for n in nodes}
    freq = {n["id"]: (n.get("frequency") or 1) for n in nodes}
    in_freq: Counter = Counter()
    out_freq: Counter = Counter()
    in_deg: Counter = Counter()
    for e in swimlane.get("edges", []):
        w = e.get("frequency") or 1
        out_freq[e.get("from")] += w
        in_freq[e.get("to")] += w
        in_deg[e.get("to")] += 1
    ger = [i for i, t in label.items() if t.startswith("GERACAO-PROCEDIMENTO")]
    rem = [i for i, t in label.items() if t.startswith("PROCESSO-REMETIDO")]
    con = [i for i, t in label.items() if t in CONCLUSION_TYPES]

    def _violation_frac(ids, bad):
        tot = sum(freq[i] for i in ids)
        return max(0.0, 1 - sum(bad[i] for i in ids) / tot) if tot else None

    def _present_frac(ids):
        tot = sum(freq[i] for i in ids)
        return (sum(freq[i] for i in ids if in_deg[i] >= 1) / tot) if tot else None

    return {
        "GERACAO_source": _violation_frac(ger, in_freq),
        "REMETIDO_has_pred": _present_frac(rem),
        "CONCLUSAO_terminal": _violation_frac(con, out_freq),
    }


def recebido_paired_frac(swimlane: dict):
    nodes = swimlane.get("nodes", [])
    recs = [n for n in nodes if n.get("label") == RECEBIDO]
    if not recs:
        return None
    rems = [n for n in nodes if n.get("label") == REMETIDO]
    ok = sum(1 for r in recs
             if any(m.get("lane") == r.get("lane") and m.get("x", 0) < r.get("x", 0) for m in rems))
    return ok / len(recs)


def single_start_ok(swimlane: dict) -> bool:
    return sum(1 for n in swimlane.get("nodes", []) if n.get("label") == GERACAO) == 1


def start_unit(swimlane: dict):
    gers = [n for n in swimlane.get("nodes", []) if n.get("label") == GERACAO]
    return min(gers, key=lambda n: n.get("x", 0)).get("lane") if gers else None


def remetido_handoff_frac(swimlane: dict):
    lane = {n["id"]: n.get("lane") for n in swimlane.get("nodes", [])}
    rem_ids = {n["id"] for n in swimlane.get("nodes", []) if n.get("label") == REMETIDO}
    if not rem_ids:
        return None
    inc: dict = {}
    for e in swimlane.get("edges", []):
        inc.setdefault(e.get("to"), []).append(e.get("from"))
    ok = sum(1 for rid in rem_ids if inc.get(rid) and any(lane.get(p) != lane.get(rid) for p in inc[rid]))
    return ok / len(rem_ids)
