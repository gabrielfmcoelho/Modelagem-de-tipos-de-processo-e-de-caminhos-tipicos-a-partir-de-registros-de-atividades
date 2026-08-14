from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from ...core.paths import ROOT
from ..shared.tex import esc, num, table


from ...model.typical_eval import ALPHABET_NAMES, MODEL_NAMES as _ALL
_DISPLAY_FIRST = ("markov", "gru", "lstm", "transformer", "gnn", "dfg")
MODELS = tuple([m for m in _DISPLAY_FIRST if m in _ALL]
               + [m for m in _ALL if m not in _DISPLAY_FIRST])
ALPHABET_LABEL = {"unit": "action-by-unit", "itinerary": "routing", "procedure": "action"}


DELTA_STAR_NOTE = (
    "$\\Delta^{*}$ is the estimand: the real partition minus its shape-matched shuffled control, "
    "which has the same cluster count, the same size distribution and the same population, with "
    "membership permuted. Fitting one model per family changes what that model sees, so a "
    "partition of this shape moves accuracy on its own; only the excess over the control is "
    "attributable to the grouping. $\\Delta^{*}$ adjusted additionally subtracts the pooled "
    "global model under both partitions, cancelling a small weighting artefact. $\\Delta^{*}$ "
    "coverage applies the same contrast to unit recall $\\times$ top-1 $/(1+$transitions "
    "unseen$)$. $\\Delta^{*}$ is an admission gate, not a ranking: it grows with the number of "
    "families, because specialising pays more when families are small, so partitions of "
    "different granularity must not be ordered by it. Alphabets are never tabulated together.")


CONTROLS_NOTE = (
    "``selected best'' takes the per-cluster maximum over every model family, so its gain over a "
    "single-family global baseline is not like-for-like; the $\\Delta$ columns hold the family "
    "fixed. $\\Delta$ still contains whatever a partition of this size distribution earns on its "
    "own, which is why the shuffled column is reported beside it and the partition's own "
    "contribution is separated into its own table. edge-F1 is the harmonic mean of "
    "directly-follows edge coverage and edge usage; it is a cluster statistic rather than a "
    "model output, so it takes one value per partition and cannot vary by model family. Every "
    "number is measured inside one alphabet, against a baseline facing the same vocabulary; "
    "alphabets are never tabulated together, because accuracies over vocabularies of different "
    "size are not the same quantity.")


def t_delta_star(f):
    note = DELTA_STAR_NOTE
    parts = []
    for alpha in ALPHABET_NAMES:
        c = (f.get("controls") or {}).get(alpha)
        if not c:
            continue
        pf = c.get("per_family_like_for_like") or {}
        has_cov = any((pf.get(m) or {}).get("delta_star_coverage_fidelity") is not None
                      for m in MODELS)
        rows = []
        for model in MODELS:
            v = pf.get(model)
            if not v:
                continue
            rows.append([model, num(v.get("per_cluster_top1")), num(v.get("shuffled_top1")),
                         f"\\textbf{{{num(v.get('delta_star_top1'))}}}",
                         num(v.get("delta_star_adjusted"))]
                        + ([num(v.get("delta_star_coverage_fidelity"))] if has_cov else []))
        if not rows:
            continue
        head = ["family", "top-1 real", "top-1 shuffled", "$\\Delta^{*}$ top-1",
                "$\\Delta^{*}$ adjusted"] + (["$\\Delta^{*}$ coverage"] if has_cov else [])
        parts.append(table(
            "Contribution of the partition itself, "
            f"{ALPHABET_LABEL.get(alpha, alpha)} alphabet.",
            f"tab:delta-star-{alpha}", "l" + "r" * (len(head) - 1), head, rows, note))
    return "\n".join(parts)


def t_controls(f):
    note = CONTROLS_NOTE
    parts = []
    for alpha in ALPHABET_NAMES:
        c = (f.get("controls") or {}).get(alpha)
        if not c:
            continue
        pf = c.get("per_family_like_for_like") or {}
        mkv = pf.get("markov") or {}
        mk = mkv.get("gain_vs_global")
        best_family = max((v.get("gain_vs_global") for v in pf.values()
                           if v.get("gain_vs_global") is not None), default=None)
        ef = (c.get("edge_fidelity") or {}).get("edge_f1") or {}
        rows = [[num(c["clustered_best_top1"]), num(c["successor_baseline"]),
                 num(c["global_model"]), num(c["shuffled_best_top1"]),
                 f"\\textbf{{{num(mk)}}}", num(best_family),
                 num(ef.get("real")), num(ef.get("shuffled")), num(ef.get("delta_star"))]]
        parts.append(table(
            f"Next-step accuracy against three baselines, {ALPHABET_LABEL.get(alpha, alpha)} "
            "alphabet.",
            f"tab:controls-{alpha}", "rrrrrrrrr",
            ["sel.\\ best", "successor", "global", "shuffled",
             "$\\Delta$ fixed family", "$\\Delta$ best family",
             "edge-F1", "edge-F1 shuffled", "$\\Delta^{*}$ edge-F1"], rows, note))
    return "\n".join(parts)


def t_temporal_holdout(f):
    th = f.get("temporal_holdout") or {}
    matched = {r["features"].replace("%", "\\%"): r
               for r in ((th.get("matched") or {}).get("rows") or [])}
    rows = []
    for r in (th.get("rows") or []):
        it = r.get("itinerary") or {}
        m = matched.get(r["features"]) or {}
        rows.append([r["features"], num(it.get("n_clusters"), 0),
                     num(it.get("per_cluster_top1"), 4), num(it.get("global_model"), 4),
                     num(it.get("gain_vs_global"), 4),
                     f"\\textbf{{{num(m.get('gain_vs_global'), 4)}}}"])
    if not rows:
        return ""
    n_common = (th.get("matched") or {}).get("n_common_cases")
    note = th.get("note", "")
    if n_common:
        note += (f" The final column rescores every truncation on the {num(n_common, 0)} cases "
                 "all four evaluate, which is the comparison the unmatched column cannot make.")
    return table("Downstream gain when the partition sees only part of each case's history.",
                 "tab:temporal-holdout", "lrrrrr",
                 ["clustering features", "clusters", "per-cluster", "global",
                  "gain (as evaluated)", "gain (matched)"], rows, note)


def t_flow(f):
    rows = []
    for r in (f.get("flow_validity") or {}).get("unit", []):
        name = ("\\emph{real event log}" if r["source"] == "real event log" else esc(r["source"]))
        rows.append([name, num(r["step"], 4), num(r["trace"], 4)])
    return table("Rule compliance of unconstrained generation, against the event log itself.",
                 "tab:flow", "lrr", ["source", "valid steps", "fully valid traces"], rows,
                 "Constrained decoding is valid by construction and is not tabulated.")


def t_size_trend(f):
    st = f.get("size_trend") or {}
    parts = []
    for alpha in ALPHABET_NAMES:
        src = st.get(alpha) or []
        if not src:
            continue
        has_unit = any(r.get("unit_recall") is not None for r in src)
        rows = [[esc(r["bin"]), num(r["n_clusters"], 0), num(r["top1"]),
                 num(r["lift_over_global"], 4)]
                + ([num(r["unit_recall"])] if has_unit else [])
                + [num(r["transitions_unseen"])] for r in src]
        head = (["cases in cluster", "clusters", "top-1", "gain vs global"]
                + (["unit recall"] if has_unit else []) + ["unseen"])
        parts.append(table(
            f"Path quality by cluster size, {ALPHABET_LABEL.get(alpha, alpha)} alphabet.",
            f"tab:size-trend-{alpha}", "l" + "r" * (len(head) - 1), head, rows,
            "Gain is measured band by band against a global model of the same family. "
            "Clusters below thirty traces are not evaluated."))
    return "\n".join(parts)


def t_combos_full(f):
    parts = []
    for alphabet in ALPHABET_NAMES:
        rows = sorted((f.get("combos_full") or {}).get(alphabet) or [],
                      key=lambda r: (r["clustering"], -(r["coverage_fidelity"] or 0)))
        if not rows:
            continue
        has_unit = any(r.get("unit_recall") is not None for r in rows)
        body = [[esc(r["clustering"]), esc(r["model"]), num(r["n_clusters"], 0), num(r["top1"])]
                + ([num(r["unit_recall"]), num(r["unit_precision"])] if has_unit else [])
                + [num(r["transitions_unseen"])] for r in rows]
        head = (["clustering", "family", "clusters", "top-1"]
                + (["recall", "precision"] if has_unit else []) + ["unseen"])
        parts.append(table(
            f"Complete results grid, {ALPHABET_LABEL.get(alphabet, alphabet)} alphabet.",
            f"tab:combos-{alphabet}", "ll" + "r" * (len(head) - 2), head, body, long=True))
    return "\n".join(parts)
