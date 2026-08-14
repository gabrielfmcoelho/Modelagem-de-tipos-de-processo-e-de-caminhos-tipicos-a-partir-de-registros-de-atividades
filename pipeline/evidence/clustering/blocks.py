from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from ...core.paths import ROOT
from ..shared.doc import _PENDING, _n, _table


def fig_cluster_counts(f: dict) -> str:
    cc = f.get("cluster_counts") or {}
    keys = [k for k in sorted(cc) if "shuffled" not in k]
    rows = [[k, _n(cc[k]["n_processos"]), _n(cc[k]["n_clusters"]), _n(cc[k]["noise"]),
             _n(cc[k]["singletons"]), _n(cc[k]["median_size"], 0), _n(cc[k]["above_30"])]
            for k in keys]
    return _table(["clustering", "processos", "clusters", "noise", "singletons",
                   "median size", "clusters ≥30"], rows) if rows else _PENDING


def fig_coverage(f: dict) -> str:
    rows = []
    for r in (f.get("coverage") or []):
        if r["alphabet"] != "unit":
            continue
        pct = (f"{100 * r['processos_evaluated'] / r['processos_total']:.1f}%"
               if r["processos_total"] else "—")
        rows.append([r["cell"], f"{r['clusters_evaluated']}/{r['clusters_total']}",
                     _n(r["processos_evaluated"]), pct, _n(r["noise"])])
    return _table(["cell", "clusters kept/total", "processos evaluated", "% of corpus",
                   "noise"], rows) if rows else _PENDING


def fig_taxonomy(f: dict) -> str:
    tax = f.get("taxonomy") or {}
    keys = [k for k in sorted(tax) if k.split("/")[0] in ("exp-raw", "exp-anon")]
    if not keys:
        return _PENDING
    rows = []
    for k in keys:
        for scope, label in (("all", "all"), ("no_catch_all", "no catch-all")):
            a = tax[k].get(scope) or {}
            if not a:
                continue
            rows.append([k, label, _n(a["n"]), _n(a["n_tipos"]), _n(a["majority_baseline"], 3),
                         _n(a["purity"], 3), _n(a["lift_over_majority"], 3),
                         _n(a["nmi"], 3), _n(a["ari"], 3)])
    body = _table(["clustering", "scope", "n", "tipos", "majority", "purity",
                   "lift", "NMI", "ARI"], rows)
    return body + (f"\n\nCatch-all label excluded in the second row of each pair: "
                   f"*{f.get('catch_all_label', '')}*.")


def fig_ablation(f: dict) -> str:
    ab = f.get("ablation") or {}
    variants = ab.get("variants") or []
    if not variants:
        return "_Ablation not yet run._"
    ref = ab.get("reference") or {}
    label = {"cut0.75": "features cut at 75% of each timeline",
             "cut0.5": "features cut at 50%",
             "cut0.25": "features cut at 25%",
             "nokeyword": "keyword block removed",
             "notopic": "topic block removed"}
    rows = [[label.get(v["variant"], v["variant"]), f"`{v['flag']}`", _n(v["ari"], 4),
             _n(v["nmi"], 4), _n(v["n_clusters_cut"]), _n(v["noise_cut"])]
            for v in variants]
    return (f"Reference partition: **{ref.get('run_id')}/{ref.get('algo')}**, "
            f"{_n(ref.get('n_processos'))} processos, {_n(ref.get('n_clusters'))} clusters. "
            f"Each row re-derives the features under one change, re-clusters, and scores the "
            f"resulting partition against the reference.\n\n"
            + _table(["variant", "flag", "ARI vs full", "NMI", "clusters", "noise"], rows))


def fig_intrinsic(f: dict) -> str:
    iv = f.get("intrinsic_vs_downstream") or {}
    rows = iv.get("rows") or []
    if not rows:
        return "_Not yet computed._"
    tbl = _table(["clustering", "downstream (itin)", "DBCV", "silhouette", "Davies-Bouldin",
                  "noise", "clusters", "median size"],
                 [[r["clustering"], _n(r["downstream"], 3), _n(r["dbcv"], 3),
                   _n(r["silhouette"], 3), _n(r["davies_bouldin"], 3),
                   _n(r["noise_ratio"], 3), _n(r["n_clusters"]), _n(r["median_size"], 0)]
                  for r in rows])
    perm = iv.get("permutation") or {}
    label = {"dbcv": "DBCV", "silhouette": "silhouette",
             "davies_bouldin": "Davies-Bouldin (lower better)",
             "calinski_harabasz": "Calinski-Harabasz", "noise_ratio": "noise ratio",
             "n_clusters": "n_clusters", "median_size": "median cluster size"}
    ctbl = _table(["intrinsic index", "Spearman ρ", f"permutation p ({_n(iv.get('n_permutations'))} draws)"],
                  [[label.get(k, k), _n(v.get("rho"), 3), _n(v.get("p_permutation"), 4)]
                   for k, v in perm.items()])
    return (tbl + f"\n\nDownstream metric: `{iv.get('downstream_metric')}`, spread "
            f"{_n(iv.get('downstream_spread'), 4)} across the {iv.get('n_clusterings')} "
            f"clusterings (**{100 * (iv.get('downstream_relative_spread') or 0):.0f}% relative**) "
            f"— it is not a flat metric.\n\n" + ctbl)


def fig_common_set(f: dict) -> str:
    cs = f.get("common_set") or {}
    rows = cs.get("rows") or []
    if not rows:
        return _PENDING
    tbl = _table(["clustering", "processos on its own set", "top-1 (own set)",
                  "top-1 (common set)", "delta"],
                 [[r["cell"], _n(r["n_own"]), _n(r["acc_own"], 4),
                   f"**{_n(r['acc_common'], 4)}**", _n(r["delta"], 4)] for r in rows])
    return (f"All eight scored on the **{_n(cs.get('n_common'))} processos every one of them "
            f"evaluates** ({cs.get('alphabet')} alphabet, best model per cluster).\n\n" + tbl
            + f"\n\nSpread across all eight on the common set: **{_n(cs.get('spread'), 4)}**"
            + _spread_interval(f))


def fig_noise_difficulty(f: dict) -> str:
    rows = f.get("noise_difficulty") or []
    if not rows:
        return ("_Não mensurável sob a política vigente: o ruído da família de densidade é "
                "atribuído ao grupo mais próximo por omissão, de modo que nenhuma partição "
                "avaliada deixa processos sem rótulo e não existe o conjunto de casos recusados "
                "cuja dificuldade esta medida compararia. A fração que a densidade recusaria "
                "antes da atribuição continua registrada por agrupamento._")
    return _table(["arm", "algorithm", "n of HDBSCAN-noise it evaluates", "top-1 on those",
                   "top-1 on the rest", "gap"],
                  [[r["arm"], r["algo"], _n(r["n_noise_evaluated"]), _n(r["acc_on_noise"], 4),
                    _n(r["acc_on_rest"], 4), _n(r["gap"], 4)] for r in rows])


def _downstream_spread(f: dict, n_clusterings=None):
    variants = [f.get("common_set_all") or {}, f.get("common_set") or {}]
    for cs in variants:
        if n_clusterings and cs.get("n_clusterings") == n_clusterings:
            return cs.get("spread")
    for cs in variants:
        if isinstance(cs.get("spread"), (int, float)):
            return cs["spread"]
    return None


def _spread_interval(f: dict) -> str:
    csa = f.get("common_set_all") or {}
    boot = csa.get("spread_bootstrap") or {}
    ci = boot.get("ci95")
    if not (csa.get("spread") and ci):
        return "."
    return (f"; across all {_n(csa.get('n_clusterings'))} it is "
            f"**{_n(csa['spread'], 4)}**, with a case-level bootstrap 95% CI of "
            f"**[{_n(ci[0], 4)}, {_n(ci[1], 4)}]** \u2014 too wide to support an equivalence "
            "claim.")


def fig_selection(f: dict) -> str:
    sel = f.get("selection_all") or f.get("selection") or {}
    rows = sel.get("rows") or []
    if not rows:
        return _PENDING
    w = sel.get("weights") or {}
    tbl = _table(["clustering", "**score**", f"downstream ×{w.get('downstream')}",
                  f"coverage ×{w.get('coverage')}", f"quality ×{w.get('quality')}",
                  "top-1 (common)", "% evaluated", "DBCV", "silhouette", "clusters"],
                 [[r["cell"], f"**{_n(r['score'], 3)}**", _n(r["s_downstream"], 3),
                   _n(r["s_coverage"], 3), _n(r["s_quality"], 3), _n(r["acc_common"], 4),
                   f"{100 * (r['coverage'] or 0):.1f}%", _n(r["dbcv"], 3),
                   _n(r["silhouette"], 3), _n(r["n_clusters_evaluated"])] for r in rows])
    sc = sel.get("scales") or {}
    scales = "\n".join(f"- **{k}** — {v}" for k, v in sc.items())
    sens = f.get("selection_sensitivity") or []
    stbl = _table(["weighting", "winner", "score", "runner-up"],
                  [[r["scheme"], r["winner"] or "—", _n(r["score"], 3), r["runner_up"] or "—"]
                   for r in sens])
    return (f"All **{_n(sel.get('n_clusterings'))}** clusterings, scored on the "
            f"**{_n(sel.get('n_common'))}** processos every one of them evaluates.\n\n"
            + tbl + "\n\nEach component is mapped to [0,1] on an **absolute** scale, never "
            "min-max across candidates — min-max would inflate the downstream dimension, whose "
            f"true spread is only {_n(_downstream_spread(f, sel.get(chr(39)+chr(110)+chr(95)+chr(99)+chr(108)+chr(117)+chr(115)+chr(116)+chr(101)+chr(114)+chr(105)+chr(110)+chr(103)+chr(115)+chr(39))), 4)}, into a full range and "
            "manufacture a decisive winner out of noise.\n\n" + scales +
            "\n\n**Sensitivity to the weighting:**\n\n" + stbl)


def fig_index_mechanism(f: dict) -> str:
    im = f.get("index_mechanism") or {}
    fc, rb = im.get("full_coverage") or {}, im.get("robustness") or {}
    if not fc:
        return _PENDING
    lead = _table(["relationship", "Spearman ρ"],
                  [["silhouette ~ median cluster size", _n(fc.get("silhouette_vs_median_size"), 4)],
                   ["silhouette ~ number of clusters", _n(fc.get("silhouette_vs_n_clusters"), 4)],
                   ["silhouette ~ coverage", _n(fc.get("silhouette_vs_coverage"), 4)],
                   ["silhouette ~ downstream accuracy (common set)",
                    _n(fc.get("silhouette_vs_common_top1"), 4)],
                   ["DBCV ~ downstream accuracy (common set)",
                    _n(fc.get("dbcv_vs_common_top1"), 4)]])
    subs = _table(["subset", "n", "silhouette ~ median size"],
                  [[k.replace("_", " "), _n(v["n"]), _n(v["silhouette_vs_median_size"], 4)]
                   for k, v in (rb.get("subsets") or {}).items()]
                  + [["configuration level (raw/anon averaged)",
                      _n(rb.get("n_configurations")),
                      f"{_n(rb.get('configuration_level_silhouette_vs_median_size'), 4)} "
                      f"(exact p = {_n(rb.get('configuration_level_p_exact'), 4)})"]])
    ci = rb.get("rho_difference_ci95") or [None, None]
    return (
        f"Computed on the **{_n(im.get('n_full_coverage'))} clusterings that assign every "
        f"case**, so the noise-masking confound is closed by construction "
        f"(all {_n(im.get('n_all'))}: silhouette ~ noise ratio = "
        f"{_n((im.get('all_clusterings') or {}).get('silhouette_vs_noise_ratio'), 4)}).\n\n"
        + lead + "\n\n" + subs
        + f"\n\nPartial correlation of silhouette with coverage, given median cluster size: "
          f"**{_n(rb.get('partial_silhouette_vs_coverage_given_median_size'), 4)}** — the "
          f"coverage row is largely a restatement of the granularity one. The coverage-minus-"
          f"accuracy difference in ρ is {_n(rb.get('rho_difference_coverage_minus_accuracy'), 4)} "
          f"with a bootstrap 95% interval of [{_n(ci[0], 4)}, {_n(ci[1], 4)}] over "
          f"{_n(rb.get('n_configurations'))} configurations — **it includes zero**, so the "
          f"indices cannot be said to track coverage rather than accuracy at this sample size.\n\n"
        + "> Granularity is what survives. Note that the twelve vary $k$ and resolution **by "
          "design**, so granularity is the variable the parameter sweep manipulates; at the "
          "configuration level the association does not clear significance. The manuscript "
          "states this caveat alongside the finding.")
