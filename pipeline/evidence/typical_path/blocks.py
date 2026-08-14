from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from ...core.paths import ROOT
from ..shared.doc import _PENDING, _n, _table
from ..shared.glossary import lower_is_better


from ...model.typical_eval import ALPHABET_NAMES, MODEL_NAMES as _ALL
_DISPLAY_FIRST = ("markov", "gru", "lstm", "transformer", "gnn", "dfg")
MODELS = tuple([m for m in _DISPLAY_FIRST if m in _ALL]
               + [m for m in _ALL if m not in _DISPLAY_FIRST])


LOWER_IS_BETTER = lower_is_better()


def fig_model_vs_medoid(f: dict) -> str:
    parts = []
    for alphabet, block in (f.get("model_vs_medoid") or {}).items():
        metrics = ["within_25", "unit_recall", "unit_precision",
                   "transition_support_mean", "transitions_unseen"]
        rows = []
        for src in ("medoid", *MODELS):
            r = block.get(src) or {}
            rows.append([("**medoid (real trace)**" if src == "medoid" else src)]
                        + [_n(r.get(m)) for m in metrics])
        winners = []
        for m in metrics:
            med = (block.get("medoid") or {}).get(m)
            vals = [((block.get(s) or {}).get(m), s) for s in MODELS
                    if (block.get(s) or {}).get(m) is not None]
            if med is None or not vals:
                continue
            best = min(vals) if m in LOWER_IS_BETTER else max(vals)
            beat = (med < best[0]) if m in LOWER_IS_BETTER else (med > best[0])
            winners.append(f"{m}: **{'medoid' if beat else best[1]}**")
        parts.append(f"**{alphabet} alphabet** ({block.get('n_clusters')} cluster-evaluations)\n\n"
                     + _table(["source", "within_25 ↑", "unit_recall ↑", "unit_precision ↑",
                               "transition_support ↑", "transitions_unseen ↓"], rows)
                     + "\n\nWinner per metric — " + "; ".join(winners) + ".")
    return "\n\n".join(parts) or _PENDING


def fig_controls(f: dict) -> str:
    rows = []
    for alphabet, c in (f.get("controls") or {}).items():
        rows.append([alphabet, _n(c["clustered_best_top1"]), _n(c["successor_baseline"]),
                     _n(c["global_model"]), _n(c["lift_over_successor"]),
                     _n(c["lift_over_global_model"]), _n(c["shuffled_best_top1"]),
                     _n(c["shuffled_lift_over_successor"])])
    return _table(["alphabet", "clustered (best)", "successor baseline", "global model",
                   "lift vs successor", "**lift vs global**", "shuffled partition",
                   "shuffled lift"], rows) if rows else _PENDING


def fig_bands(f: dict) -> str:
    parts = []
    order = ("small", "medium", "large")
    for alphabet, bands in (f.get("by_size_band") or {}).items():
        rows = []
        for name in order:
            b = bands.get(name)
            if not b:
                continue
            rows.append([name, _n(b["n_clusters"]), _n(b["top1"]), _n(b["successor"]),
                         _n(b["global_model"]), _n(b["lift_over_successor"]),
                         _n(b["lift_over_global"]), _n(b["within_25"]),
                         _n(b["unit_recall"]), _n(b["transitions_unseen"])])
        if rows:
            parts.append(f"**{alphabet} alphabet**\n\n" + _table(
                ["band", "clusters", "top-1", "successor", "global", "lift vs succ",
                 "lift vs global", "within_25", "unit_recall", "unseen ↓"], rows))
    return "\n\n".join(parts) or _PENDING


def fig_dispersion(f: dict) -> str:
    parts = []
    for a, d in (f.get("dispersion") or {}).items():
        rows = [[_n(d.get("dispersion")), _n(d.get("medoid_distance"))]]
        parts.append(f"**{a}**\n\n" + _table(["dispersion", "medoid distance"], rows))
    return "\n\n".join(parts) if parts else _PENDING


def fig_scale(f: dict) -> str:
    mc = f.get("model_count")
    if not mc:
        return _PENDING
    return (f"- **{_n(mc['cells'])} matrix cells**, "
            f"**{_n(mc['clusters_evaluated'])} cluster-evaluations**, "
            f"**{_n(mc['models_trained'])} sequence models trained**.")


def _combo_table(rows: list[dict]) -> str:
    return _table(["clustering", "model", "clusters", "traces", "top-1", "unit_recall",
                   "precision", "unseen ↓", "coverage×fidelity"],
                  [[r["clustering"], r["model"], _n(r["n_clusters"]), _n(r["n_traces"]),
                    _n(r["top1"], 3), _n(r["unit_recall"], 3), _n(r["unit_precision"], 3),
                    _n(r["transitions_unseen"], 3), _n(r["coverage_fidelity"], 3)]
                   for r in rows])


def fig_combos(f: dict) -> str:
    parts = []
    for alphabet in ALPHABET_NAMES:
        all_rows = (f.get("combos") or {}).get(alphabet) or []
        big = (f.get("combos_large") or {}).get(alphabet) or []
        if all_rows:
            parts.append(f"**{alphabet} — all cluster sizes**\n\n" + _combo_table(all_rows[:6]))
        if big:
            parts.append(f"**{alphabet} — large clusters only (≥150 traces)**\n\n"
                         + _combo_table(big[:5]))
    return "\n\n".join(parts) or _PENDING


def fig_model_profile(f: dict) -> str:
    parts = []
    for alphabet, prof in (f.get("model_profile") or {}).items():
        rows = []
        for m in (*_DISPLAY_FIRST, "medoid"):
            r = prof.get(m) or {}
            if not r:
                continue
            rows.append([("*medoid (real trace)*" if m == "medoid" else m),
                         _n(r.get("top1"), 3), _n(r.get("n_units_path"), 2),
                         _n(r.get("visits_in_path"), 2), _n(r.get("transitions_unseen"), 3),
                         _n(r.get("unseen_per_visit_pooled"), 4), _n(r.get("unit_recall"), 3),
                         _n(r.get("visits_matched_frac"), 3)])
        parts.append(f"**{alphabet}**\n\n" + _table(
            ["model", "top-1", "units in path", "visits", "unseen ↓", "unseen/visit ↓",
             "unit_recall ↑", "visits matched ↑"], rows))
    return "\n\n".join(parts) or _PENDING


def fig_size_trend(f: dict) -> str:
    parts = []
    for alphabet, rows in (f.get("size_trend") or {}).items():
        if not rows:
            continue
        parts.append(f"**{alphabet}**\n\n" + _table(
            ["cluster size", "clusters", "mean test n", "top-1", "vs global model",
             "unit_recall", "unseen ↓", "within_25"],
            [[r["bin"], _n(r["n_clusters"]), _n(r["mean_n_test"]), _n(r["top1"], 3),
              _n(r["lift_over_global"], 4), _n(r["unit_recall"], 3),
              _n(r["transitions_unseen"], 3), _n(r["within_25"], 3)] for r in rows]))
    return "\n\n".join(parts) or _PENDING


def fig_combos_full(f: dict) -> str:
    parts = []
    for alphabet in ALPHABET_NAMES:
        rows = (f.get("combos_full") or {}).get(alphabet) or []
        if not rows:
            continue
        rows = sorted(rows, key=lambda r: (r["clustering"], -(r["coverage_fidelity"] or 0)))
        parts.append(f"**{alphabet}** — every clustering × every model ({len(rows)} rows)\n\n"
                     + _table(["clustering", "model", "clusters", "traces", "top-1",
                               "unit_recall", "unit_precision", "visits_matched",
                               "transition_support", "unseen ↓", "coverage×fidelity"],
                              [[r["clustering"], r["model"], _n(r["n_clusters"]),
                                _n(r["n_traces"]), _n(r["top1"], 3), _n(r["unit_recall"], 3),
                                _n(r["unit_precision"], 3), _n(r["visits_matched_frac"], 3),
                                _n(r["transition_support_mean"], 3),
                                _n(r["transitions_unseen"], 3),
                                _n(r["coverage_fidelity"], 3)] for r in rows]))
    return "\n\n".join(parts) or _PENDING


def fig_flow_validity(f: dict) -> str:
    fv = f.get("flow_validity") or {}
    if not fv:
        return _PENDING
    parts = []
    for alphabet, rows in fv.items():
        parts.append(f"**{alphabet} alphabet**\n\n" + _table(
            ["source", "valid steps ↑", "fully-valid traces ↑", "cluster-evaluations"],
            [[("*" + r["source"] + "*" if r["source"] == "real event log" else r["source"]),
              _n(r["step"], 4), _n(r["trace"], 4), _n(r["n_clusters"]) if r["n_clusters"] else "—"]
             for r in rows]))
    return "\n\n".join(parts)


def fig_noninferiority(f: dict) -> str:
    per_alphabet = f.get("noninferiority") or {}
    blocks = [_fig_noninferiority_one(a, per_alphabet[a])
              for a in ALPHABET_NAMES if per_alphabet.get(a)]
    return "\n\n".join(blocks) if blocks else _PENDING


def _fig_noninferiority_one(alphabet: str, ni: dict) -> str:
    results = ni.get("results") or []
    if not results:
        return ""
    meta = ni.get("meta") or {}
    rows = [[r["cell_a"].split("/")[-1], r["model"], _n(r["point_a"], 4), _n(r["point_b"], 4),
             _n(r["diff_point"], 4),
             f"[{_n(r['diff_ci95'][0], 4)}, {_n(r['diff_ci95'][1], 4)}]",
             _n(r["ci90_one_sided_lower"], 4), _n(r["n_paired"]),
             "yes" if r["non_inferior"] else "**NO**",
             "yes" if r["non_inferior_sensitivity"] else "**NO**"]
            for r in results]
    body = (f"**Alphabet: {alphabet}.** The margin is pre-registered per alphabet and the "
            "vocabularies differ in size, so a verdict here says nothing about another "
            "alphabet; these are never pooled.\n\n"
            + _table(["clustering", "model", "raw", "anon", "diff (anon-raw)", "95% CI",
                      "one-sided 90% lower", "n paired", f"non-inf (δ={meta.get('margin')})",
                      f"sensitivity (δ={meta.get('sensitivity_margin')})"], rows))
    failed = [r for r in results if not r["non_inferior"]]
    sens_failed = sorted((r for r in results if not r["non_inferior_sensitivity"]),
                         key=lambda r: r["ci90_one_sided_lower"])
    names = ", ".join(f"{r['model']} on {r['cell_a'].split('/')[-1]} "
                      f"({_n(r['ci90_one_sided_lower'], 4)})" for r in sens_failed)
    return body + (
        f"\n\nPaired case-level bootstrap, {_n(meta.get('replicates'))} replicates. "
        f"Non-inferiority is declared when the one-sided 90% lower bound on the "
        f"anonymised-minus-raw difference exceeds $-\\delta$. Margins were fixed before "
        f"the comparison was run (`docs/research/non-inferiority-preregistration.md`). "
        f"At the pre-registered $\\delta = {meta.get('margin')}$, "
        f"**{len(results) - len(failed)} of {len(results)}** comparisons clear it"
        + (f", **{len(failed)} do not**. " if failed else ". ")
        + (f"At the tighter sensitivity margin $\\delta = {meta.get('sensitivity_margin')}$ "
           f"the result is **{len(results) - len(sens_failed)} of {len(results)}**: "
           f"{names} fall below the threshold. They fail narrowly, and only under a margin "
           f"half the pre-registered one, but they fail."
           if sens_failed else
           f"All {len(results)} also clear the tighter sensitivity margin "
           f"$\\delta = {meta.get('sensitivity_margin')}$.")
        + " Anonymisation is applied before clustering because the governing instrument "
          "requires it; this measures what that costs, not whether to do it.")
