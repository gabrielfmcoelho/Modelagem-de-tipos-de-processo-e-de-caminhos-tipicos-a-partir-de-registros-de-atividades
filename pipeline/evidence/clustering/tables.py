from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from ...core.paths import ROOT
from ..shared.tex import esc, num, table


def t_intrinsic_rows(f):
    iv = f.get("intrinsic_vs_downstream") or {}
    rows = iv.get("rows") or []
    if not rows:
        return ""
    body = [[esc(r["clustering"]), num(r["downstream"]), num(r["dbcv"]), num(r["silhouette"]),
             num(r["davies_bouldin"]), num(r["noise_ratio"]), num(r["n_clusters"], 0),
             num(r["median_size"], 0)] for r in rows]
    note = ("One row per clustering, all in the same reduced embedding. The correlations of "
            "Table~\\ref{tab:intrinsic} are computed over these columns. Noise ratio is the share "
            "of cases the algorithm leaves unassigned; the density methods are the only ones for "
            "which it is non-zero.")
    return table(
        "Internal validity indices and downstream quality, per clustering.",
        "tab:intrinsic-rows", "lrrrrrrr",
        ["clustering", "downstream", "DBCV", "Silhouette", "Davies--Bouldin",
         "noise", "clusters", "median size"], body, note)


def t_intrinsic(f):
    iv = f.get("intrinsic_vs_downstream") or {}
    label = {"dbcv": "DBCV", "silhouette": "Silhouette",
             "davies_bouldin": "Davies--Bouldin", "calinski_harabasz": "Calinski--Harabasz",
             "noise_ratio": "Noise ratio", "noise_ratio_refused": "Noise ratio (refused)",
             "n_clusters": "Number of clusters", "median_size": "Median cluster size"}
    rows = [[label.get(k, esc(k)), num(v.get("rho")), num(v.get("p_permutation"))]
            for k, v in (iv.get("permutation") or {}).items() if v.get("rho") is not None]
    note = (f"Spearman rank correlation with downstream quality across "
            f"{iv.get('n_clusterings')} clusterings; permutation test with "
            f"{num(iv.get('n_permutations'))} draws. The downstream measure spans "
            f"{num(iv.get('downstream_spread'))} "
            f"({100 * (iv.get('downstream_relative_spread') or 0):.0f}\\% relative).")
    return table("Internal validity indices against downstream utility.",
                 "tab:intrinsic", "lrr", ["index", "$\\rho$", "$p$"], rows, note)


def t_ablation(f):
    ab = f.get("ablation") or {}
    label = {"cut0.75": "History truncated at 75\\%", "cut0.5": "History truncated at 50\\%",
             "cut0.25": "History truncated at 25\\%", "nokeyword": "Keyword block removed",
             "notopic": "Topic block removed"}
    rows = [[label.get(v["variant"], esc(v["variant"])), num(v["ari"]), num(v["nmi"]),
             num(v["n_clusters_cut"])] for v in (ab.get("variants") or [])]
    ref = ab.get("reference") or {}
    note = (f"Each variant rebuilds the features under one change and re-clusters; agreement is "
            f"measured against the full-history partition "
            f"({num(ref.get('n_clusters'))} clusters over {num(ref.get('n_processos'))} cases).")
    return table("Feature-block and temporal-dependency ablations.",
                 "tab:ablation", "lrrr", ["variant", "ARI", "NMI", "clusters"], rows, note)


def t_index_mechanism(f):
    im = f.get("index_mechanism") or {}
    if not im:
        return ""
    a, fc = im.get("all_clusterings") or {}, im.get("full_coverage") or {}
    rows = [
        ["Silhouette vs.\\ share of cases discarded as noise",
         f"all {im['n_all']}", num(a.get("silhouette_vs_noise_ratio"))],
        ["Share discarded vs.\\ accuracy on the partition's own set",
         f"all {im['n_all']}", num(a.get("noise_ratio_vs_own_top1"))],
        ["Silhouette vs.\\ median cluster size",
         f"full-cov.\\ {im['n_full_coverage']}", num(fc.get("silhouette_vs_median_size"))],
        ["Silhouette vs.\\ number of clusters",
         f"full-cov.\\ {im['n_full_coverage']}", num(fc.get("silhouette_vs_n_clusters"))],
        ["Number of clusters vs.\\ coverage",
         f"full-cov.\\ {im['n_full_coverage']}", num(fc.get("n_clusters_vs_coverage"))],
        ["Silhouette vs.\\ coverage",
         f"full-cov.\\ {im['n_full_coverage']}", num(fc.get("silhouette_vs_coverage"))],
        ["\\textbf{Silhouette vs.\\ common-set accuracy}",
         f"full-cov.\\ {im['n_full_coverage']}",
         f"\\textbf{{{num(fc.get('silhouette_vs_common_top1'))}}}"],
        ["\\textbf{DBCV vs.\\ common-set accuracy}",
         f"full-cov.\\ {im['n_full_coverage']}",
         f"\\textbf{{{num(fc.get('dbcv_vs_common_top1'))}}}"],
    ]
    n_full = im.get("n_full_coverage")
    for band, b in (im.get("within_size_band") or {}).items():
        rows.append([f"Silhouette vs.\\ accuracy, {esc(band)} clusters only "
                     f"(mean top-1 {num(b['mean_top1'])})",
                     f"{b['n_clusters']} clusters, {n_full} values", num(b["silhouette_vs_top1"])])
    return table("What the validity indices actually track.", "tab:index-mechanism",
                 "lll", ["relation", "population", "$\\rho$"], rows, im.get("note", ""),
                 small=True)


def t_selection_full_coverage(f):
    sf = f.get("selection_full_coverage") or {}
    rows = [[esc(r["cell"]), num(r["acc_common"], 4), num(r["coverage"], 3),
             num(r["silhouette"], 3), num(r["median_size"], 0), num(r["n_clusters"], 0),
             num(r.get("share_in_clusters_ge_150"), 3),
             f"\\textbf{{{num(r['score_balanced'], 3)}}}"] for r in (sf.get("rows") or [])]
    if not rows:
        return ""
    note = sf.get("note", "")
    if sf.get("unanimous"):
        note += (" The same candidate wins under all four weightings, including one that "
                 "ignores the validity indices entirely.")
    alpha = sf.get("alphabet") or "itinerary"
    note += (" ``in clusters $\\ge$150'' is the share of cases the partition places in clusters "
             "large enough for the low-fabrication band of "
             f"Table~\\ref{{tab:size-trend-{alpha}}}.")
    return table("Choosing a deliverable among the clusterings, scored on the "
                 f"{alpha} alphabet alone.",
                 "tab:selection", "lrrrrrrr",
                 ["clustering", "common t-1", "coverage", "silh.", "med.\\ size",
                  "clusters", "in clusters $\\ge$150", "score"], rows, note, small=True)


def t_catalogue(f):
    cs = f.get("catalogue_sample") or {}
    rows = [[esc(r["name"]), num(r["n_cases"], 0), num(r["n_evaluated"], 0),
             num(r["top1"], 3), num(r["unit_recall"], 3)] for r in (cs.get("rows") or [])]
    if not rows:
        return ""
    return table("Illustrative catalogue entries, largest and smallest evaluated types.",
                 "tab:catalogue", "p{0.42\\textwidth}rrrr",
                 ["process type (generated name)", "cases", "eval.", "top-1", "unit rec."],
                 rows, cs.get("note", ""), small=True)


def t_catch_all_null(f):
    cn = f.get("catch_all_null") or {}
    rows = [[esc(r["cell"]), num(r["ari_all"], 4), num(r["ari_excl_catch_all"], 4),
             f"{num(r['null_mean'], 4)} $\\pm$ {num(r['null_sd'], 4)}", num(r["null_max"], 4),
             f"{num(r['n_null_at_or_above_observed'], 0)}/{num(r['null_draws'], 0)}",
             num(r["z"], 1)] for r in (cn.get("rows") or [])]
    if not rows:
        return ""
    note = ("Null: drop a randomly chosen set of whole declared classes totalling within "
            f"{num((cn.get('tolerance') or 0) * 100, 0)}\\% of the catch-all's size, and rescore. "
            "Removing random classes of the same size lowers agreement; removing the catch-all "
            "raises it. No null draw reaches the observed value for any clustering.")
    return table("The catch-all class against a same-size random-class null.",
                 "tab:catch-all-null", "lrrrrrr",
                 ["clustering", "ARI all", "ARI excl.", "null mean", "null max",
                  "$\\geq$ obs.", "$z$"], rows, note)


def t_common_set(f):
    cs = f.get("common_set_all") or f.get("common_set") or {}
    rows = [[esc(r["cell"]), num(r["n_own"], 0), num(r["acc_own"], 4),
             f"\\textbf{{{num(r['acc_common'], 4)}}}", num(r["delta"], 4)]
            for r in (cs.get("rows") or [])]
    note = (f"All clusterings rescored on the {num(cs.get('n_common'))} cases every one of them "
            f"evaluates. Spread on the common set: \\textbf{{{num(cs.get('spread'), 4)}}}.")
    return table("Clustering comparison on a common set of cases.",
                 "tab:common-set", "lrrrr",
                 ["clustering", "own $n$", "own set", "common set", "$\\Delta$"],
                 rows, note, small=True)


def t_taxonomy(f):
    tax = f.get("taxonomy") or {}
    rows = []
    for k in sorted(tax):
        if k.split("/")[0] not in ("exp-raw", "exp-anon"):
            continue
        for scope, lbl in (("all", "all"), ("no_catch_all", "excl.\\ catch-all")):
            a = tax[k].get(scope) or {}
            if a:
                rows.append([esc(k), lbl, num(a["n"], 0), num(a["majority_baseline"]),
                             num(a["purity"]), num(a["nmi"]), num(a["ari"])])
    return table("Agreement between the emergent partition and the declared taxonomy.",
                 "tab:taxonomy", "llrrrrr",
                 ["clustering", "scope", "$n$", "majority", "purity", "NMI", "ARI"],
                 rows, small=True)
