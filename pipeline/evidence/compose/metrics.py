from __future__ import annotations

from collections import defaultdict
from statistics import mean

MODEL_METRICS = ("top1", "top3", "suffix_dl", "flow_validity_step", "flow_validity_trace",
                 "typical_path_distance")
CLUSTER_METRICS = ("edge_coverage", "edge_usage", "edge_f1")
BASELINES = ("top1_successor", "top1_global_model")


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _wmean(pairs):
    pairs = [(w, v) for w, v in pairs if _num(v) is not None and w]
    if not pairs:
        return None
    total = sum(w for w, _ in pairs)
    return round(sum(w * v for w, v in pairs) / total, 4) if total else None


def _mean(values):
    vals = [v for v in (_num(x) for x in values) if v is not None]
    return round(mean(vals), 4) if vals else None


def iter_clusters(cells: list[dict]):
    for cell in cells:
        for cid, rec in (cell.get("clusters") or {}).items():
            if isinstance(rec, dict):
                yield cell, cid, rec


def model_rows(cells: list[dict], restrict: set[str] | None = None) -> dict[str, list[dict]]:
    rows: dict[str, list[dict]] = defaultdict(list)
    for cell, cid, rec in iter_clusters(cells):
        if restrict is not None:
            evaluated = {str(p) for p in (rec.get("test_protocolos") or [])}
            if not evaluated & restrict:
                continue
        n = rec.get("n_traces") or 0
        for name, m in (rec.get("models") or {}).items():
            if not isinstance(m, dict) or "skipped" in m:
                continue
            rows[name].append({"cell": f"{cell['run_id']}/{cell['algo']}/{cell['alphabet']}",
                               "arm": cell["arm"], "algo": cell["algo"],
                               "alphabet": cell["alphabet"], "cluster": cid,
                               "n_traces": n, "metrics": m,
                               "baseline": rec.get("baseline") or {}})
    return rows


def summarise_model(rows: list[dict]) -> dict:
    if not rows:
        return {"n_clusters": 0}
    out = {"n_clusters": len(rows),
           "n_traces": sum(r["n_traces"] for r in rows),
           "membership_weighted": {}, "unweighted": {}}
    for key in MODEL_METRICS:
        out["membership_weighted"][key] = _wmean([(r["n_traces"], r["metrics"].get(key))
                                                  for r in rows])
        out["unweighted"][key] = _mean([r["metrics"].get(key) for r in rows])
    for base in BASELINES:
        out.setdefault("baselines", {})[base] = _wmean(
            [(r["n_traces"], r["baseline"].get(base)) for r in rows])
    gv = out.get("baselines", {}).get("top1_global_model")
    top1 = out["membership_weighted"].get("top1")
    out["gain_vs_global_model"] = (round(top1 - gv, 4)
                                   if top1 is not None and gv is not None else None)
    sv = out.get("baselines", {}).get("top1_successor")
    out["gain_vs_successor"] = (round(top1 - sv, 4)
                                if top1 is not None and sv is not None else None)
    return out


def summarise_clusters(cells: list[dict]) -> dict:
    recs = [rec for _, _, rec in iter_clusters(cells)]
    if not recs:
        return {"n_clusters": 0}
    out = {"n_clusters": len(recs), "n_traces": sum(r.get("n_traces") or 0 for r in recs)}
    for key in CLUSTER_METRICS:
        out[key] = _wmean([(r.get("n_traces") or 0, r.get(key)) for r in recs])
    return out


def best_model_per_cluster(cells: list[dict], metric: str = "top1") -> dict:
    wins: dict[str, int] = defaultdict(int)
    ties = 0
    for _, _, rec in iter_clusters(cells):
        scored = [(name, _num(m.get(metric)))
                  for name, m in (rec.get("models") or {}).items()
                  if isinstance(m, dict) and "skipped" not in m]
        scored = [(n, v) for n, v in scored if v is not None]
        if not scored:
            continue
        top = max(v for _, v in scored)
        winners = [n for n, v in scored if v == top]
        if len(winners) > 1:
            ties += 1
        for w in winners:
            wins[w] += 1
    return {"metric": metric, "wins": dict(sorted(wins.items())), "clusters_with_a_tie": ties}
