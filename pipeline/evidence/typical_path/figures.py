from __future__ import annotations
import argparse
import json
from pathlib import Path
from statistics import mean, median
from ...core.paths import ROOT
from ..shared.paths import CLUSTERING, MAIN_CELLS, SHUFFLED, TYPICAL
from ..shared.stats import _round, _wmean, unseen_per_visit


CONSTRAINT_COST = ROOT / "artifacts" / "stats" / "constraint_cost.json"


SIZE_BINS = ((30, 50), (50, 75), (75, 100), (100, 150), (150, 250), (250, 10 ** 9))


from ...model.typical_eval import ALPHABET_NAMES, MODEL_NAMES as MODELS, alphabet_carries


def noninferiority_path(alphabet: str):
    return ROOT / "artifacts" / "stats" / alphabet / "noninferiority.json"


NONINFERIORITY_PATHS = tuple(noninferiority_path(a) for a in ALPHABET_NAMES)


GEN_MODEL = MODELS


GEN_KEYS = ("within_25", "within_50", "median_distance", "unit_recall", "unit_precision",
            "transition_support_mean", "transitions_unseen", "visits_in_path",
            "median_actions_per_visit", "visits_matched_frac")


_UNIT_AXIS_KEYS = ("unit_recall", "unit_precision", "visits_in_path",
                   "median_actions_per_visit", "visits_matched_frac")


def gen_keys_for(alphabet: str) -> tuple[str, ...]:
    if alphabet_carries(alphabet, "unit"):
        return GEN_KEYS
    return tuple(k for k in GEN_KEYS if k not in _UNIT_AXIS_KEYS)


def load_cells(root: Path = TYPICAL) -> list[dict]:
    cells = []
    for path in sorted(root.glob("*/*/*/metrics.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        meta = data.get("meta", {})
        alphabet, algo, run_id = (path.parent.name, path.parent.parent.name,
                                  path.parent.parent.parent.name)
        for axis, by_path, by_meta in (("run_id", run_id, meta.get("run_id")),
                                       ("algo", algo, meta.get("algo")),
                                       ("alphabet", alphabet, meta.get("alphabet"))):
            if by_meta and by_meta != by_path:
                raise ValueError(
                    f"{path}: {axis} is {by_path!r} by path and {by_meta!r} by meta. A cell's "
                    "lattice address must be one thing — filed under the wrong address it "
                    "pools into the wrong denominator, which nothing downstream can detect.")
        if alphabet not in ALPHABET_NAMES:
            raise ValueError(f"{path}: unknown alphabet {alphabet!r}, expected one of "
                             f"{ALPHABET_NAMES}")
        cells.append({
            "run_id": run_id,
            "algo": algo,
            "alphabet": alphabet,
            "arm": "anon" if "anon" in run_id else "raw",
            "control": SHUFFLED in run_id,
            "dfg_floor": meta.get("dfg_coverage_floor"),
            "n_dropped_by_min_states": meta.get("n_dropped_by_min_states"),
            "clusters": data.get("clusters") or {},
            "aggregate": data.get("aggregate") or {},
            "by_size": data.get("aggregate_by_size") or {},
            "path": str(path if not path.is_absolute() else path.relative_to(ROOT)),
        })
    return cells


def model_vs_medoid(cells: list[dict]) -> dict:
    out = {}
    for alphabet in ALPHABET_NAMES:
        rows = {}
        keys = gen_keys_for(alphabet)
        pool = [c for c in cells if c["alphabet"] == alphabet and not c["control"]]
        medoid_pairs = {k: [] for k in keys}
        model_pairs = {m: {k: [] for k in keys} for m in MODELS}
        for cell in pool:
            for cl in cell["clusters"].values():
                if not isinstance(cl, dict):
                    continue
                w = cl.get("n_traces") or 0
                med = (cl.get("path_reference") or {}).get("medoid_generalization") or {}
                for k in keys:
                    medoid_pairs[k].append((w, med.get(k)))
                for m in MODELS:
                    gen = ((cl.get("models") or {}).get(m) or {}).get("generalization") or {}
                    for k in keys:
                        model_pairs[m][k].append((w, gen.get(k)))
        rows["medoid"] = {k: _wmean(v) for k, v in medoid_pairs.items()}
        for m in MODELS:
            rows[m] = {k: _wmean(v) for k, v in model_pairs[m].items()}
        rows["n_clusters"] = sum(len([c for c in cell["clusters"].values() if isinstance(c, dict)])
                                 for cell in pool)
        out[alphabet] = rows
    return out


def dispersion(cells: list[dict]) -> dict:
    out = {}
    for alphabet in ALPHABET_NAMES:
        vals = {"dispersion": [], "medoid_distance": []}
        for cell in cells:
            if cell["alphabet"] != alphabet or cell["control"]:
                continue
            for cl in cell["clusters"].values():
                if not isinstance(cl, dict):
                    continue
                pr = cl.get("path_reference") or {}
                w = cl.get("n_traces") or 0
                for k in vals:
                    vals[k].append((w, pr.get(k)))
        out[alphabet] = {k: _wmean(v) for k, v in vals.items()}
    return out


def _partition_profile(pool: list[dict], model: str) -> dict:
    top, rec, uns, ef1, glob = [], [], [], [], []
    for _cell, cl, w in _cluster_rows(pool):
        m = (cl.get("models") or {}).get(model) or {}
        t = m.get("top1")
        if not isinstance(t, (int, float)):
            continue
        g = m.get("generalization") or {}
        top.append((w, t))
        rec.append((w, g.get("unit_recall")))
        uns.append((w, g.get("transitions_unseen")))
        ef1.append((w, cl.get("edge_f1")))
        glob.append((w, (cl.get("baseline") or {}).get("top1_global_model")))
    t, r, u = _wmean(top), _wmean(rec), _wmean(uns)
    cov = _round(r * t / (1 + u)) if None not in (r, t, u) else None
    return {"top1": t, "coverage_fidelity": cov, "edge_f1": _wmean(ef1),
            "global_model": _wmean(glob), "n_clusters": len(top)}


def _delta(real, ctrl, key):
    a, b = real.get(key), ctrl.get(key)
    return _round(a - b) if None not in (a, b) else None


def controls(cells: list[dict]) -> dict:
    out = {}
    for alphabet in ALPHABET_NAMES:
        real = [c for c in cells if c["alphabet"] == alphabet and not c["control"]]
        ctrl = [c for c in cells if c["alphabet"] == alphabet and c["control"]]

        def best_top1(pool):
            rows = []
            for cell in pool:
                for cl in cell["clusters"].values():
                    if not isinstance(cl, dict):
                        continue
                    w = cl.get("n_traces") or 0
                    tops = [((cl.get("models") or {}).get(m) or {}).get("top1") for m in MODELS]
                    tops = [t for t in tops if isinstance(t, (int, float))]
                    if not tops:
                        continue
                    b = cl.get("baseline") or {}
                    rows.append((w, max(tops), b.get("top1_successor"), b.get("top1_global_model")))
            return rows

        r_rows, c_rows = best_top1(real), best_top1(ctrl)
        r_best = _wmean([(w, b) for w, b, _, _ in r_rows])
        r_succ = _wmean([(w, s) for w, _, s, _ in r_rows])
        r_glob = _wmean([(w, g) for w, _, _, g in r_rows])
        c_best = _wmean([(w, b) for w, b, _, _ in c_rows])
        c_succ = _wmean([(w, s) for w, _, s, _ in c_rows])
        per_family = {}
        residuals = []
        for model in GEN_MODEL:
            rp = _partition_profile(real, model)
            cp = _partition_profile(ctrl, model)
            v, g = rp["top1"], rp["global_model"]
            if None not in (rp["global_model"], cp["global_model"]):
                residuals.append(rp["global_model"] - cp["global_model"])
            per_family[model] = {
                "per_cluster_top1": v,
                "gain_vs_global": _round(v - g) if None not in (v, g) else None,
                "shuffled_top1": cp["top1"],
                "delta_star_top1": _delta(rp, cp, "top1"),
                "coverage_fidelity": rp["coverage_fidelity"],
                "shuffled_coverage_fidelity": cp["coverage_fidelity"],
                "delta_star_coverage_fidelity": _delta(rp, cp, "coverage_fidelity"),
                "delta_star_adjusted": (
                    _round((rp["top1"] - rp["global_model"]) - (cp["top1"] - cp["global_model"]))
                    if None not in (rp["top1"], rp["global_model"],
                                    cp["top1"], cp["global_model"]) else None),
            }
        by_key = {(c["run_id"], c["algo"]): c for c in cells if c["alphabet"] == alphabet}
        by_clustering = {}
        for (rid, algo), cell in sorted(by_key.items()):
            if SHUFFLED in rid:
                continue
            match = by_key.get((rid + SHUFFLED, algo))
            key = f"{rid}/{algo}"
            if match is None:
                by_clustering[key] = {
                    "delta_star": None,
                    "unmatched_reason": (
                        f"no shape-matched control: cluster-control did not produce "
                        f"{rid}{SHUFFLED}/{algo}. Delta-star is undefined here, because a "
                        "control built from a different clustering has a different cluster "
                        "count and size distribution, and family size alone moves accuracy."),
                }
                continue
            per_model = {}
            for model in GEN_MODEL:
                rp = _partition_profile([cell], model)
                cp = _partition_profile([match], model)
                per_model[model] = {
                    "top1": rp["top1"], "shuffled_top1": cp["top1"],
                    "delta_star_top1": _delta(rp, cp, "top1"),
                    "delta_star_coverage_fidelity": _delta(rp, cp, "coverage_fidelity"),
                }
            by_clustering[key] = {"control": f"{rid}{SHUFFLED}/{algo}",
                                  "delta_star": per_model}

        edge_fidelity = {}
        for key in ("edge_coverage", "edge_usage", "edge_f1"):
            r_e = _wmean([(w, cl.get(key)) for _c, cl, w in _cluster_rows(real)])
            s_e = _wmean([(w, cl.get(key)) for _c, cl, w in _cluster_rows(ctrl)])
            edge_fidelity[key] = {
                "real": r_e, "shuffled": s_e,
                "delta_star": _round(r_e - s_e) if None not in (r_e, s_e) else None}

        out[alphabet] = {
            "per_family_like_for_like": per_family,
            "delta_star_by_clustering": by_clustering,
            "pooled_delta_star_warning": (
                "per_family_like_for_like pools every real clustering against every control. "
                "cluster-control derives its controls from the hdbscan partitions only, so that "
                "pooled figure is shape-matched for hdbscan and confounded for k-means, Leiden "
                "and the parameterisation variants, whose cluster counts and size distributions "
                "differ. Use delta_star_by_clustering, which pairs each clustering with its own "
                "control and reports null where none exists."),
            "edge_fidelity": edge_fidelity,
            "edge_fidelity_note": (
                "edge_* are cluster statistics computed from the unpruned directly-follows "
                "graph, not model outputs, so they take one value per partition and cannot "
                "vary by model family. They are reported here at cell level for that reason."),
            "selected_best_note": ("clustered_best_top1 takes the per-cluster maximum over every "
                                   "model family; the global baseline is a single fixed "
                                   "third-order Markov chain. The comparison is therefore not "
                                   "like-for-like and is reported as a selected-best figure. "
                                   "per_family_like_for_like gives the family-matched gains."),
            "clustered_best_top1": r_best,
            "successor_baseline": r_succ,
            "global_model": r_glob,
            "lift_over_successor": _round(r_best - r_succ) if None not in (r_best, r_succ) else None,
            "lift_over_global_model": _round(r_best - r_glob) if None not in (r_best, r_glob) else None,
            "shuffled_best_top1": c_best,
            "shuffled_successor": c_succ,
            "shuffled_lift_over_successor": _round(c_best - c_succ) if None not in (c_best, c_succ) else None,
            "n_control_cells": len(ctrl),
            "global_baseline_residual": _round(mean(residuals)) if residuals else None,
            "delta_star_note": (
                "delta_star_* is the estimand: the real partition minus its shape-matched "
                "shuffled control. Fitting per family shrinks each model's alphabet, so any "
                "partition with the same size distribution earns a gain for free; "
                "gain_vs_global keeps that raw figure, delta_star_* removes it. "
                "global_baseline_residual should be ~0 -- it scores the same global model on "
                "the same test steps under both partitions, so a non-zero value means the "
                "n_traces weighting is doing work and family imbalance must be reported "
                "alongside the result."),
        }
    return out


def model_count(cells: list[dict]) -> dict:
    trained = sum(
        sum(1 for m in MODELS if isinstance(((cl.get("models") or {}).get(m) or {}).get("top1"), (int, float)))
        for cell in cells for cl in cell["clusters"].values() if isinstance(cl, dict)
    )
    return {"models_trained": trained,
            "cells": len(cells),
            "clusters_evaluated": sum(len([c for c in cell["clusters"].values() if isinstance(c, dict)])
                                      for cell in cells)}


def by_band(cells: list[dict]) -> dict:
    out = {}
    for alphabet in ALPHABET_NAMES:
        bands: dict[str, dict] = {}
        for cell in cells:
            if cell["alphabet"] != alphabet or cell["control"]:
                continue
            for cl in cell["clusters"].values():
                if not isinstance(cl, dict):
                    continue
                band = cl.get("size_band") or "?"
                b = bands.setdefault(band, {"n_clusters": 0, "top1": [], "succ": [], "glob": [],
                                            "unseen": [], "within_25": [], "unit_recall": []})
                b["n_clusters"] += 1
                w = cl.get("n_traces") or 0
                tops = [((cl.get("models") or {}).get(m) or {}).get("top1") for m in MODELS]
                tops = [t for t in tops if isinstance(t, (int, float))]
                if tops:
                    b["top1"].append((w, max(tops)))
                base = cl.get("baseline") or {}
                b["succ"].append((w, base.get("top1_successor")))
                b["glob"].append((w, base.get("top1_global_model")))
                best_m = max(((cl.get("models") or {}).get(m) or {}).get("top1") or 0 for m in MODELS)
                for m in MODELS:
                    mm = (cl.get("models") or {}).get(m) or {}
                    if (mm.get("top1") or 0) == best_m:
                        gen = mm.get("generalization") or {}
                        b["unseen"].append((w, gen.get("transitions_unseen")))
                        b["within_25"].append((w, gen.get("within_25")))
                        b["unit_recall"].append((w, gen.get("unit_recall")))
                        break
        out[alphabet] = {
            name: {
                "n_clusters": b["n_clusters"],
                "top1": _wmean(b["top1"]),
                "successor": _wmean(b["succ"]),
                "global_model": _wmean(b["glob"]),
                "lift_over_successor": (_round(_wmean(b["top1"]) - _wmean(b["succ"]))
                                        if _wmean(b["top1"]) is not None and _wmean(b["succ"]) is not None else None),
                "lift_over_global": (_round(_wmean(b["top1"]) - _wmean(b["glob"]))
                                     if _wmean(b["top1"]) is not None and _wmean(b["glob"]) is not None else None),
                "transitions_unseen": _wmean(b["unseen"]),
                "within_25": _wmean(b["within_25"]),
                "unit_recall": _wmean(b["unit_recall"]),
            } for name, b in bands.items()
        }
    return out


def temporal_holdout() -> dict:
    root = ROOT / "artifacts" / "typical" / "_temporal_holdout"
    if not root.is_dir():
        return {}
    order = [("exp-anon", "full history"), ("exp-anon-cut0.75", "first 75\\%"),
             ("exp-anon-cut0.5", "first 50\\%"), ("exp-anon-cut0.25", "first 25\\%")]
    rows = []
    for run, label in order:
        row = {"features": label}
        for alphabet in ALPHABET_NAMES:
            p = root / f"{run}__hdbscan__{alphabet}.json"
            if not p.is_file():
                continue
            d = json.loads(p.read_text(encoding="utf-8"))
            mk, gl, n, k = [], [], 0, 0
            for cl in (d.get("clusters") or {}).values():
                if not isinstance(cl, dict):
                    continue
                w = cl.get("n_traces") or 0
                k += 1
                n += w
                mk.append((w, ((cl.get("models") or {}).get("markov") or {}).get("top1")))
                gl.append((w, (cl.get("baseline") or {}).get("top1_global_model")))
            m, g = _wmean(mk), _wmean(gl)
            row[alphabet] = {"per_cluster_top1": m, "global_model": g, "n_clusters": k,
                             "n_traces": n,
                             "gain_vs_global": _round(m - g) if None not in (m, g) else None}
        if len(row) > 1:
            rows.append(row)
    matched_path = ROOT / "artifacts" / "stats" / "temporal_holdout_matched.json"
    matched = (json.loads(matched_path.read_text(encoding="utf-8"))
               if matched_path.is_file() else {})
    return {"rows": rows, "algo": "hdbscan", "arm": "exp-anon", "model": "markov3",
            "matched": matched,
            "note": ("Each row clusters on features truncated at a fraction of every case's own "
                     "timeline, then predicts on the full held-out traces. The unmatched rows "
                     "evaluate different populations, so their gradient mostly reflects the "
                     "global baseline moving; the matched block rescores every truncation on the "
                     "cases all four evaluate.")}


def _cluster_rows(cells, *, band=None, lo=None, hi=None):
    for cell in cells:
        for cl in cell["clusters"].values():
            if not isinstance(cl, dict):
                continue
            n = cl.get("n_traces") or 0
            if band and cl.get("size_band") != band:
                continue
            if lo is not None and not (lo <= n < hi):
                continue
            yield cell, cl, n


def combos(cells: list[dict], alphabet: str, band: str | None = None) -> list[dict]:
    pool = [c for c in cells if c["alphabet"] == alphabet and not c["control"]]
    out = []
    for cell in pool:
        for model in GEN_MODEL:
            top, rec, prec, uns, vis, sup = [], [], [], [], [], []
            n_cl = n_tr = 0
            for _, cl, w in _cluster_rows([cell], band=band):
                m = (cl.get("models") or {}).get(model) or {}
                if not isinstance(m.get("top1"), (int, float)):
                    continue
                g = m.get("generalization") or {}
                n_cl += 1
                n_tr += w
                top.append((w, m["top1"]))
                rec.append((w, g.get("unit_recall")))
                prec.append((w, g.get("unit_precision")))
                uns.append((w, g.get("transitions_unseen")))
                vis.append((w, g.get("visits_matched_frac")))
                sup.append((w, g.get("transition_support_mean")))
            t, r, u = _wmean(top), _wmean(rec), _wmean(uns)
            if t is None or u is None:
                continue
            out.append({
                "clustering": f"{cell['run_id']}/{cell['algo']}", "model": model,
                "n_clusters": n_cl, "n_traces": n_tr, "top1": t, "unit_recall": r,
                "unit_precision": _wmean(prec), "transitions_unseen": u,
                "visits_matched_frac": _wmean(vis), "transition_support_mean": _wmean(sup),
                "coverage_fidelity": _round(r * t / (1 + u)) if r is not None else None,
            })
    return sorted(out, key=lambda x: -(x["coverage_fidelity"] or 0))


def model_profile(cells: list[dict], alphabet: str) -> dict:
    pool = [c for c in cells if c["alphabet"] == alphabet and not c["control"]]
    out = {}
    for model in (*GEN_MODEL, "medoid"):
        keys = {k: [] for k in ("top1", "n_units_path", "visits_in_path", "transitions_unseen",
                                "unit_recall", "unit_precision", "visits_matched_frac")}
        for _, cl, w in _cluster_rows(pool):
            if model == "medoid":
                g = (cl.get("path_reference") or {}).get("medoid_generalization") or {}
                m = {}
            else:
                m = (cl.get("models") or {}).get(model) or {}
                g = m.get("generalization") or {}
            if not g:
                continue
            keys["top1"].append((w, m.get("top1")))
            for k in list(keys)[1:]:
                keys[k].append((w, g.get(k)))
        row = {k: _wmean(v) for k, v in keys.items()}
        row["unseen_per_visit_pooled"] = unseen_per_visit(row.get("transitions_unseen"),
                                                          row.get("visits_in_path"))
        out[model] = row
    return out


def size_trend(cells: list[dict], alphabet: str) -> list[dict]:
    pool = [c for c in cells if c["alphabet"] == alphabet and not c["control"]]
    rows = []
    for lo, hi in SIZE_BINS:
        top, rec, uns, w25, glob, tests = [], [], [], [], [], []
        k = 0
        for _, cl, n in _cluster_rows(pool, lo=lo, hi=hi):
            ms = [(v.get("top1"), v) for v in (cl.get("models") or {}).values()
                  if isinstance(v.get("top1"), (int, float))]
            if not ms:
                continue
            k += 1
            best = max(ms, key=lambda x: x[0])
            g = best[1].get("generalization") or {}
            top.append((n, best[0]))
            rec.append((n, g.get("unit_recall")))
            uns.append((n, g.get("transitions_unseen")))
            w25.append((n, g.get("within_25")))
            glob.append((n, (cl.get("baseline") or {}).get("top1_global_model")))
            tests.append(cl.get("n_test") or 0)
        if not k:
            continue
        t, gl = _wmean(top), _wmean(glob)
        rows.append({
            "bin": f"{lo}-{hi if hi < 10 ** 8 else ''}", "n_clusters": k,
            "mean_n_test": round(sum(tests) / len(tests)) if tests else None,
            "top1": t, "global_model": gl,
            "lift_over_global": _round(t - gl) if None not in (t, gl) else None,
            "unit_recall": _wmean(rec), "transitions_unseen": _wmean(uns),
            "within_25": _wmean(w25),
        })
    return rows


def flow_validity(cells: list[dict]) -> dict:
    out = {}
    for alphabet in ALPHABET_NAMES:
        pool = [c for c in cells if c["alphabet"] == alphabet and not c["control"]]
        rows = []
        for model in GEN_MODEL:
            st, wh = [], []
            n = 0
            for _, cl, w in _cluster_rows(pool):
                m = (cl.get("models") or {}).get(model) or {}
                if m.get("flow_validity_step") is None:
                    continue
                n += 1
                st.append((w, m.get("flow_validity_step")))
                wh.append((w, m.get("flow_validity_trace")))
            if n:
                rows.append({"source": model, "step": _wmean(st), "trace": _wmean(wh),
                             "n_clusters": n})
        rs, rw = [], []
        for _, cl, w in _cluster_rows(pool):
            b = cl.get("baseline") or {}
            rs.append((w, b.get("flow_validity_step_real")))
            rw.append((w, b.get("flow_validity_trace_real")))
        real_step, real_trace = _wmean(rs), _wmean(rw)
        if real_step is not None or real_trace is not None:
            rows.append({"source": "real event log", "step": real_step, "trace": real_trace,
                         "n_clusters": None})
        if not rows:
            continue
        out[alphabet] = rows
    return out


def _noninferiority_one(path) -> dict:
    out = json.loads(path.read_text(encoding="utf-8"))
    rows = out.get("results") or []
    failures = sorted((r for r in rows if not r.get("non_inferior_sensitivity")),
                      key=lambda r: r["ci90_one_sided_lower"])
    out["summary"] = {
        "n_comparisons": len(rows),
        "n_non_inferior": sum(1 for r in rows if r.get("non_inferior")),
        "n_non_inferior_sensitivity": sum(1 for r in rows
                                          if r.get("non_inferior_sensitivity")),
        "sensitivity_failures": [
            {"cell": r["cell_a"].split("/")[-1], "model": r["model"],
             "ci90_one_sided_lower": r["ci90_one_sided_lower"]} for r in failures],
    }
    return out


def noninferiority() -> dict:
    out = {}
    for alphabet in ALPHABET_NAMES:
        path = noninferiority_path(alphabet)
        if path.is_file():
            out[alphabet] = _noninferiority_one(path)
    return out
