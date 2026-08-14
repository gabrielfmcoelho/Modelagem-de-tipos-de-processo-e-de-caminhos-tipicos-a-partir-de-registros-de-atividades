from __future__ import annotations
import argparse
import json
from statistics import median as _median
from pathlib import Path
from statistics import mean, median
from ...core.paths import ROOT
from ..shared.blind import _blind, _unit_acronyms
from ..shared.paths import CLUSTERING, MAIN_CELLS, SHUFFLED, TYPICAL
from ..shared.stats import _round, _scale, _spearman, _spearman_permutation_p, _spearman_power, unseen_per_visit
from ..typical_path.figures import combos, controls


COMPARABLE_SPACE = "umap50-cosine"


ABLATION = ROOT / "artifacts" / "stats" / "ablation.json"


TIPO_CACHE = ROOT / "artifacts" / "cache" / "tipo_procedimento.json"


def _load_tipos() -> dict:
    if not TIPO_CACHE.is_file():
        raise FileNotFoundError(
            f"{TIPO_CACHE} is missing. It is the declared SEI taxonomy every agreement figure "
            "is scored against, so without it tab:taxonomy and tab:catch-all-null would render "
            "empty and nothing would say so. Run `pipeline run cluster-eval` to write it.")
    d = json.loads(TIPO_CACHE.read_text(encoding="utf-8"))
    return d.get("tipos", d)


CATCH_ALL = "Documento Oficial: Ofício, Memorando, Portaria, Edital, Instrução Normativa e outros"


def coverage(cells: list[dict]) -> list[dict]:
    rows = []
    for cell in cells:
        if cell["control"]:
            continue
        labels_path = CLUSTERING / cell["run_id"] / cell["algo"] / "labels.json"
        total = noise = None
        if labels_path.is_file():
            labels = json.loads(labels_path.read_text(encoding="utf-8"))["labels"]
            total = len(labels)
            noise = sum(1 for v in labels.values() if v == -1)
        clusters = [c for c in cell["clusters"].values() if isinstance(c, dict)]
        rows.append({
            "cell": f"{cell['run_id']}/{cell['algo']}",
            "alphabet": cell["alphabet"],
            "clusters_evaluated": len(clusters),
            "clusters_total": len(set(json.loads(labels_path.read_text(encoding="utf-8"))["labels"].values()) - {-1})
                              if labels_path.is_file() else None,
            "processos_evaluated": sum(c.get("n_traces") or 0 for c in clusters),
            "processos_total": total,
            "noise": noise,
        })
    return rows


def cluster_counts() -> dict:
    out = {}
    for labels_path in sorted(CLUSTERING.glob("*/*/labels.json")):
        run_id, algo = labels_path.parent.parent.name, labels_path.parent.name
        labels = json.loads(labels_path.read_text(encoding="utf-8"))["labels"]
        sizes = {}
        for v in labels.values():
            sizes[v] = sizes.get(v, 0) + 1
        real = {k: v for k, v in sizes.items() if k != -1}
        out[f"{run_id}/{algo}"] = {
            "n_processos": len(labels),
            "n_clusters": len(real),
            "noise": sizes.get(-1, 0),
            "singletons": sum(1 for v in real.values() if v == 1),
            "median_size": median(sorted(real.values())) if real else None,
            "above_30": sum(1 for v in real.values() if v >= 30),
        }
    return out


def _agreement(labels: dict[str, int], tipos: dict[str, str], *, drop=None) -> dict:
    from collections import Counter, defaultdict
    from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

    dropped = set() if drop is None else ({drop} if isinstance(drop, str) else set(drop))
    pairs = [(c, tipos[p]) for p, c in labels.items()
             if c != -1 and p in tipos and tipos[p] not in dropped]
    if not pairs:
        return {}
    by_cluster = defaultdict(Counter)
    for c, t in pairs:
        by_cluster[c][t] += 1
    purity = sum(cnt.most_common(1)[0][1] for cnt in by_cluster.values()) / len(pairs)
    majority = Counter(t for _, t in pairs).most_common(1)[0][1] / len(pairs)
    cl = [c for c, _ in pairs]
    tl = [t for _, t in pairs]
    return {
        "n": len(pairs),
        "n_tipos": len(set(tl)),
        "majority_baseline": _round(majority),
        "purity": _round(purity),
        "lift_over_majority": _round(purity - majority),
        "nmi": _round(float(normalized_mutual_info_score(tl, cl))),
        "ari": _round(float(adjusted_rand_score(tl, cl))),
    }


def taxonomy() -> dict:
    tipos = _load_tipos()
    out = {}
    for labels_path in sorted(CLUSTERING.glob("*/*/labels.json")):
        run_id, algo = labels_path.parent.parent.name, labels_path.parent.name
        if SHUFFLED in run_id:
            continue
        labels = json.loads(labels_path.read_text(encoding="utf-8"))["labels"]
        if not set(labels) & set(tipos):
            raise ValueError(
                f"{TIPO_CACHE} shares no protocolo with {run_id}/{algo} ({len(tipos)} reference "
                f"entries against {len(labels)} labelled cases). The reference is not for this "
                "corpus — most likely it was overwritten by a test fixture. Regenerate it with "
                "`pipeline run cluster-eval`; scoring against it would silently render "
                "tab:taxonomy and tab:catch-all-null empty.")
        out[f"{run_id}/{algo}"] = {
            "all": _agreement(labels, tipos),
            "no_catch_all": _agreement(labels, tipos, drop=CATCH_ALL),
        }
    return out


def catch_all_share() -> dict:
    tipos = _load_tipos()
    n_concluded = len(tipos)
    n_ca_concluded = sum(1 for v in tipos.values() if v == CATCH_ALL)

    best = None
    for labels_path in sorted(CLUSTERING.glob("*/*/labels.json")):
        if SHUFFLED in labels_path.parent.parent.name:
            continue
        keys = set(json.loads(labels_path.read_text(encoding="utf-8"))["labels"])
        if best is None or len(keys) > len(best[1]):
            best = (f"{labels_path.parent.parent.name}/{labels_path.parent.name}", keys)
    if best is None:
        return {}

    cell, analysed = best
    n_ca_analysed = sum(1 for k in analysed if tipos.get(k) == CATCH_ALL)
    return {
        "label": CATCH_ALL,
        "n_concluded": n_concluded,
        "n_catch_all_concluded": n_ca_concluded,
        "share_concluded_pct": _round(100 * n_ca_concluded / n_concluded, 2),
        "analysed_from": cell,
        "n_analysed": len(analysed),
        "n_catch_all_analysed": n_ca_analysed,
        "share_analysed_pct": _round(100 * n_ca_analysed / len(analysed), 2),
        "deterministic": True,
        "note": ("A count over a declared data field, not a model output: no clustering, "
                 "sampling or seeded step enters it. The analysed denominator is the "
                 "largest non-control label set, which is every full-coverage clustering "
                 "and is itself fixed by the feature matrix. Both shares therefore "
                 "reproduce exactly. The two denominators differ and the two figures are "
                 "not interchangeable: one is of the concluded population, the other of "
                 "the population actually analysed."),
    }


def _ari_dropping(labels: dict[str, int], tipos: dict[str, str], dropped: set) -> float | None:
    from sklearn.metrics import adjusted_rand_score
    cl, tl = [], []
    for p, c in labels.items():
        if c == -1 or p not in tipos:
            continue
        t = tipos[p]
        if t in dropped:
            continue
        cl.append(c)
        tl.append(t)
    return float(adjusted_rand_score(tl, cl)) if cl else None


def catch_all_null(n_draws: int = 1000, seed: int = 42, tol: float = 0.10) -> dict:
    import random as _random
    from collections import Counter
    tipos = _load_tipos()
    rows = []
    for cell in MAIN_CELLS:
        run_id, algo = cell.split("/")
        lp = CLUSTERING / run_id / algo / "labels.json"
        if not lp.is_file():
            continue
        labels = json.loads(lp.read_text(encoding="utf-8"))["labels"]
        counts = Counter(tipos[p] for p, c in labels.items()
                         if c != -1 and p in tipos)
        target = counts.get(CATCH_ALL)
        if not target:
            continue
        base = _ari_dropping(labels, tipos, set())
        observed = _ari_dropping(labels, tipos, {CATCH_ALL})
        others = [t for t in counts if t != CATCH_ALL]
        rng = _random.Random(seed)
        null, sizes = [], []
        lo, hi = target * (1 - tol), target * (1 + tol)
        for _ in range(n_draws):
            rng.shuffle(others)
            picked, total = set(), 0
            for t in others:
                if total >= lo:
                    break
                picked.add(t)
                total += counts[t]
            if lo <= total <= hi:
                v = _ari_dropping(labels, tipos, picked)
                if v is not None:
                    null.append(v)
                    sizes.append(len(picked))
        if not null:
            continue
        mu = mean(null)
        sd = (sum((v - mu) ** 2 for v in null) / max(1, len(null) - 1)) ** 0.5
        rows.append({
            "cell": cell, "n_catch_all": target, "ari_all": _round(base),
            "ari_excl_catch_all": _round(observed),
            "median_classes_per_draw": _round(_median(sizes)) if sizes else None,
            "null_draws": len(null), "null_mean": _round(mu), "null_sd": _round(sd),
            "null_max": _round(max(null)),
            "n_null_at_or_above_observed": sum(1 for v in null if v >= observed),
            "z": _round((observed - mu) / sd) if sd else None,
        })
    contrast = []
    for cell in MAIN_CELLS:
        run_id, algo = cell.split("/")
        lp = CLUSTERING / run_id / algo / "labels.json"
        if not lp.is_file():
            continue
        labels = json.loads(lp.read_text(encoding="utf-8"))["labels"]
        counts = Counter(tipos[p] for p, c in labels.items() if c != -1 and p in tipos)
        biggest = [t for t, _ in counts.most_common() if t != CATCH_ALL][:3]
        entry = {"cell": cell, "ari_all": _round(_ari_dropping(labels, tipos, set())),
                 "ari_excl_catch_all": _round(_ari_dropping(labels, tipos, {CATCH_ALL}))}
        for rank, t in enumerate(biggest, start=2):
            entry[f"ari_excl_rank{rank}"] = _round(_ari_dropping(labels, tipos, {t}))
            entry[f"n_rank{rank}"] = counts[t]
        contrast.append(entry)
    return {"tolerance": tol, "requested_draws": n_draws, "rows": rows,
            "single_class_contrast": contrast,
            "contrast_note": ("Dropping the catch-all raises agreement; dropping any of the next "
                              "three largest declared classes individually lowers it. The "
                              "size-matched null cannot separate 'a large class' from 'this "
                              "class' because no other single class approaches the catch-all's "
                              "size; this contrast can.")}


def catalogue_sample(run_id: str = "exp-raw", algo: str = "hdbscan", n_large: int = 6,
                     n_small: int = 4, *, selection: dict | None = None,
                     family: str = "gru") -> dict:
    if selection and selection.get("winners"):
        winner = selection["winners"].get("balanced")
        if winner and "/" in winner:
            run_id, algo = winner.split("/", 1)
    names_path = CLUSTERING / run_id / algo / "names.json"
    metrics_path = TYPICAL / run_id / algo / "itinerary" / "metrics.json"
    if not (names_path.is_file() and metrics_path.is_file()):
        return {}
    names = json.loads(names_path.read_text(encoding="utf-8")).get("names") or {}
    clusters = json.loads(metrics_path.read_text(encoding="utf-8")).get("clusters") or {}
    acronyms = _unit_acronyms()
    by_id = {}
    for key, meta in names.items():
        cid = key.rsplit("|", 1)[-1]
        cl = clusters.get(cid)
        if not isinstance(cl, dict):
            continue
        g = ((cl.get("models") or {}).get(family) or {}).get("generalization") or {}
        vis = g.get("visits_in_path")
        unseen = g.get("transitions_unseen")
        by_id[cid] = {
            "name": _blind(meta.get("nome") or "", acronyms),
            "n_cases": meta.get("n_members"),
            "n_evaluated": cl.get("n_traces"),
            "size_band": cl.get("size_band"),
            "top1": ((cl.get("models") or {}).get(family) or {}).get("top1"),
            "unit_recall": g.get("unit_recall"),
            "visits_in_path": vis,
            "unseen_per_visit": unseen_per_visit(unseen, vis),
        }
    ranked = sorted((r for r in by_id.values() if r["n_evaluated"]),
                    key=lambda r: -(r["n_evaluated"] or 0))
    picked = ranked[:n_large] + ranked[-n_small:] if len(ranked) > n_large + n_small else ranked
    return {"family": family,
        "run_id": run_id, "algo": algo, "n_named": len(names),
            "n_shown": len(picked), "rows": picked,
            "note": ("Illustrative entries from the catalogue, largest and smallest evaluated "
                     "types. Names are generated (Section 4.7) and unvalidated; measures are "
                     "for the GRU path on the routing alphabet, the family that gains most on "
                     "routing (Section 4.8).")}


def index_mechanism(cells: list[dict], alphabet: str = "itinerary") -> dict:
    from statistics import median as _median
    iv = intrinsic_vs_downstream(cells, alphabet)
    rows = iv.get("rows") or []
    cs = {r["cell"]: r for r in (common_set_comparison(cells, alphabet, scope="all")
                                 .get("rows") or [])}
    cov = {}
    for c in coverage(cells):
        if c["alphabet"] == alphabet and c.get("processos_total"):
            cov[c["cell"]] = c["processos_evaluated"] / c["processos_total"]
    full = [r for r in rows if r["clustering"] in cs]
    if len(full) < 4:
        return {}

    def rho(xs, ys):
        return _spearman(xs, ys)

    sil = [r["silhouette"] for r in full]
    out = {
        "n_all": len(rows), "n_full_coverage": len(full), "alphabet": alphabet,
        "noise_ratio_reading": (
            "noise_ratio is 0 for every clustering because HDBSCAN noise is assigned to the "
            "nearest cluster by default, so a correlation against it is undefined. These two "
            "measures therefore use noise_ratio_refused — what density would have left "
            "unassigned, preserved in each clustering's params as "
            "noise_ratio_before_assignment. That is the variable the claim was always about: "
            "how much a partition abstains, not what survived a policy choice."),
        "all_clusterings": {
            "silhouette_vs_noise_ratio": rho([r["silhouette"] for r in rows],
                                             [r["noise_ratio_refused"] for r in rows]),
            "noise_ratio_vs_own_top1": rho([r["noise_ratio_refused"] for r in rows],
                                           [cs[r["clustering"]]["acc_own"] for r in rows
                                            if r["clustering"] in cs]
                                           if all(r["clustering"] in cs for r in rows) else []),
        },
        "full_coverage": {
            "silhouette_vs_median_size": rho(sil, [r["median_size"] for r in full]),
            "silhouette_vs_n_clusters": rho(sil, [r["n_clusters"] for r in full]),
            "silhouette_vs_coverage": rho(sil, [cov.get(r["clustering"]) for r in full]),
            "silhouette_vs_common_top1": rho(sil, [cs[r["clustering"]]["acc_common"]
                                                   for r in full]),
            "dbcv_vs_common_top1": rho([r["dbcv"] for r in full],
                                       [cs[r["clustering"]]["acc_common"] for r in full]),
            "n_clusters_vs_coverage": rho([r["n_clusters"] for r in full],
                                          [cov.get(r["clustering"]) for r in full]),
        },
    }

    bands = {}
    full_names = {r["clustering"] for r in full}
    per = {"small": [], "medium": [], "large": []}
    for cell in cells:
        name = f"{cell['run_id']}/{cell['algo']}"
        if cell["alphabet"] != alphabet or cell["control"] or name not in full_names:
            continue
        s = next((r["silhouette"] for r in full if r["clustering"] == name), None)
        for cl in cell["clusters"].values():
            if not isinstance(cl, dict):
                continue
            t = ((cl.get("models") or {}).get("markov") or {}).get("top1")
            band = cl.get("size_band")
            if isinstance(t, (int, float)) and band in per and s is not None:
                per[band].append((cl.get("n_traces") or 0, t, s))
    for band, vals in per.items():
        if len(vals) < 8:
            continue
        bands[band] = {
            "n_clusters": len(vals),
            "median_size": int(_median([v[0] for v in vals])),
            "mean_top1": _round(mean([v[1] for v in vals])),
            "silhouette_vs_top1": rho([v[2] for v in vals], [v[1] for v in vals]),
        }
    out["within_size_band"] = bands

    def _rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            mid = (i + j) / 2 + 1
            for k2 in range(i, j + 1):
                r[order[k2]] = mid
            i = j + 1
        return r

    def _pearson(a, b):
        ma, mb = mean(a), mean(b)
        num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
        den = ((sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) ** 0.5)
        return num / den if den else None

    sil_r = _rank(sil)
    cov_r = _rank([cov.get(r["clustering"]) for r in full])
    siz_r = _rank([r["median_size"] for r in full])
    acc_r = _rank([cs[r["clustering"]]["acc_common"] for r in full])
    r_sc, r_ss, r_cs = _pearson(sil_r, cov_r), _pearson(sil_r, siz_r), _pearson(cov_r, siz_r)
    partial = ((r_sc - r_ss * r_cs) / (((1 - r_ss ** 2) * (1 - r_cs ** 2)) ** 0.5)
               if None not in (r_sc, r_ss, r_cs) else None)

    subsets = {}
    for label, drop in (("drop_leiden", "leiden"), ("kmeans_only", None)):
        sub = ([r for r in full if drop not in r["clustering"]] if drop
               else [r for r in full if "kmeans" in r["clustering"]])
        if len(sub) >= 4:
            subsets[label] = {
                "n": len(sub),
                "silhouette_vs_median_size": rho([r["silhouette"] for r in sub],
                                                 [r["median_size"] for r in sub]),
            }

    import random as _random
    rng = _random.Random(42)
    pairs = {}
    for r in full:
        key = r["clustering"].replace("exp-raw", "").replace("exp-anon", "")
        pairs.setdefault(key, []).append(r)
    groups = list(pairs.values())
    diffs = []
    for _ in range(5000):
        draw = [x for _ in groups for x in rng.choice(groups)]
        if len({r["clustering"] for r in draw}) < 4:
            continue
        s = [r["silhouette"] for r in draw]
        c = rho(s, [cov.get(r["clustering"]) for r in draw])
        a = rho(s, [cs[r["clustering"]]["acc_common"] for r in draw])
        if c is not None and a is not None:
            diffs.append(c - a)
    diffs.sort()

    cfg_sil = [mean([r["silhouette"] for r in g]) for g in groups]
    cfg_siz = [mean([float(r["median_size"]) for r in g]) for g in groups]
    cfg_rho = rho(cfg_sil, cfg_siz)
    cfg_p = None
    if cfg_rho is not None:
        from itertools import permutations
        perms = list(permutations(range(len(cfg_siz))))
        hits = sum(1 for p in perms
                   if abs(rho(cfg_sil, [cfg_siz[i] for i in p]) or 0) >= abs(cfg_rho) - 1e-12)
        cfg_p = hits / len(perms)

    out["robustness"] = {
        "partial_silhouette_vs_coverage_given_median_size": _round(partial),
        "subsets": subsets,
        "n_configurations": len(groups),
        "configuration_level_silhouette_vs_median_size": _round(cfg_rho),
        "configuration_level_p_exact": _round(cfg_p),
        "rho_difference_coverage_minus_accuracy": _round(
            (rho(sil, [cov.get(r["clustering"]) for r in full]) or 0)
            - (rho(sil, [cs[r["clustering"]]["acc_common"] for r in full]) or 0)),
        "rho_difference_ci95": ([_round(diffs[int(0.025 * len(diffs))]),
                                 _round(diffs[int(0.975 * len(diffs))])] if diffs else None),
        "n_bootstrap": len(diffs),
    }
    out["note"] = ("Granularity is the relationship that survives scrutiny at this sample size. "
                   "The coverage rows are largely a restatement of it (partial correlation given "
                   "median cluster size is small), and the difference between the coverage and "
                   "accuracy correlations is not resolvable here -- its bootstrap interval over "
                   "configurations includes zero. The band rows carry only as many distinct "
                   "silhouette values as there are partitions, not as many as there are "
                   "clusters, so they are far weaker evidence than their cluster counts suggest.")
    return out


def selection_full_coverage(cells: list[dict], alphabet: str = "itinerary") -> dict:
    iv = intrinsic_vs_downstream(cells, alphabet)
    cs = {r["cell"]: r for r in (common_set_comparison(cells, alphabet, scope="all")
                                 .get("rows") or [])}
    cov = {}
    for c in coverage(cells):
        if c["alphabet"] == alphabet and c.get("processos_total"):
            cov[c["cell"]] = c["processos_evaluated"] / c["processos_total"]
    full = [r for r in (iv.get("rows") or [])
            if r["clustering"] in cs and r["clustering"] in cov]
    if len(full) < 4:
        return {}

    def scale(vals):
        lo, hi = min(vals), max(vals)
        return [(v - lo) / (hi - lo) if hi > lo else 0.5 for v in vals]

    acc = [cs[r["clustering"]]["acc_common"] for r in full]
    cvg = [cov[r["clustering"]] for r in full]
    sil = [r["silhouette"] for r in full]
    msz = [r["median_size"] for r in full]
    s = {"acc": scale(acc), "cov": scale(cvg), "sil": scale(sil), "msz": scale(msz)}
    schemes = {
        "accuracy+coverage": (0.5, 0.5, 0.0, 0.0),
        "balanced": (0.4, 0.3, 0.15, 0.15),
        "coverage-first": (0.3, 0.5, 0.1, 0.1),
        "quality-weighted": (0.3, 0.3, 0.3, 0.1),
    }
    rows = []
    for i, r in enumerate(full):
        entry = {"cell": r["clustering"], "acc_common": _round(acc[i]),
                 "coverage": _round(cvg[i]), "silhouette": _round(sil[i]),
                 "median_size": msz[i], "n_clusters": r["n_clusters"]}
        for name, (wa, wc, ws, wm) in schemes.items():
            entry[f"score_{name}"] = _round(
                wa * s["acc"][i] + wc * s["cov"][i] + ws * s["sil"][i] + wm * s["msz"][i])
        rows.append(entry)
    winners = {name: max(rows, key=lambda e: e[f"score_{name}"])["cell"] for name in schemes}
    from collections import Counter
    for entry in rows:
        run_id, algo = entry["cell"].split("/", 1)
        lp = CLUSTERING / run_id / algo / "labels.json"
        if not lp.is_file():
            continue
        counts = Counter(json.loads(lp.read_text(encoding="utf-8"))["labels"].values())
        total = sum(counts.values())
        for thr in (30, 150):
            share = sum(v for v in counts.values() if v >= thr)
            entry[f"share_in_clusters_ge_{thr}"] = _round(share / total) if total else None
    rows.sort(key=lambda e: -e["score_balanced"])
    return {"alphabet": alphabet, "n_candidates": len(rows), "schemes": schemes,
            "rows": rows, "winners": winners,
            "unanimous": len(set(winners.values())) == 1,
            "note": (f"Every clustering is a candidate: no coverage filter is applied, because "
                     f"assigning density noise to the nearest cluster already closed the discard "
                     f"channel upstream. Features are min--max scaled across candidates; accuracy "
                     f"is scored on the common set. Scored on the {alphabet!r} alphabet alone --- "
                     f"the alphabets are never pooled, so the deliverable is selected on one of "
                     f"them and that choice is a scoping decision, not a property of the data.")}


def intrinsic_vs_downstream(cells: list[dict], alphabet: str = "itinerary") -> dict:
    pool = [c for c in cells if c["alphabet"] == alphabet and not c["control"]]
    rows = []
    for cell in pool:
        mp = CLUSTERING / cell["run_id"] / cell["algo"] / "metrics.json"
        if not mp.is_file():
            continue
        cm = json.loads(mp.read_text(encoding="utf-8"))
        best = max((c["coverage_fidelity"] or 0)
                   for c in combos([cell], alphabet)) if cell["clusters"] else None
        if not best:
            continue
        src = cm.get("internal_comparable") or cm
        if src.get("space") != COMPARABLE_SPACE:
            raise RuntimeError(
                f"intrinsic_vs_downstream: {cell['run_id']}/{cell['algo']} reports internal "
                f"indices in space {src.get('space')!r}, not {COMPARABLE_SPACE!r}. Validity "
                "indices from different metric spaces are not comparable and must not be "
                "pooled into one correlation. Re-run the stage that produced this clustering "
                "so it writes an 'internal_comparable' block.")
        rows.append({
            "clustering": f"{cell['run_id']}/{cell['algo']}", "downstream": best,
            "dbcv": src.get("dbcv"), "silhouette": src.get("silhouette"),
            "davies_bouldin": src.get("davies_bouldin"),
            "calinski_harabasz": src.get("calinski_harabasz"),
            "noise_ratio": src.get("noise_ratio"), "n_clusters": src.get("n_clusters"),
            "noise_ratio_refused": float(
                ((cm.get("meta") or {}).get("params") or {})
                .get("noise_ratio_before_assignment") or 0.0),
            "median_size": (cm.get("size_stats") or {}).get("p50"),
        })
    down = [r["downstream"] for r in rows]
    keys = ("dbcv", "silhouette", "davies_bouldin", "calinski_harabasz",
            "noise_ratio", "noise_ratio_refused", "n_clusters", "median_size")
    corr = {k: _spearman([r[k] for r in rows], down) for k in keys}
    perm = {}
    for k in keys:
        rho, pval = _spearman_permutation_p([r[k] for r in rows], down)
        perm[k] = {"rho": rho, "p_permutation": pval}
    ds = [d for d in down if isinstance(d, (int, float))]
    return {"alphabet": alphabet, "n_clusterings": len(rows),
            "rows": sorted(rows, key=lambda r: -r["downstream"]), "spearman": corr,
            "permutation": perm, "n_permutations": 20000,
            "power": _spearman_power(len(rows)),
            "min_p": _round(min((v.get("p_permutation") or 1.0) for v in perm.values())),
            "n_indices_tested": len(perm),
            "downstream_metric": "unit_recall x top1 / (1 + transitions_unseen)",
            "downstream_spread": _round(max(ds) - min(ds)) if ds else None,
            "downstream_relative_spread": (_round((max(ds) - min(ds)) / min(ds)) if ds else None)}


def _per_processo(cell) -> dict:
    out = {}
    for cl in cell["clusters"].values():
        if not isinstance(cl, dict):
            continue
        protos = cl.get("test_protocolos") or []
        best = bname = None
        for name, m in (cl.get("models") or {}).items():
            t = m.get("top1")
            if isinstance(t, (int, float)) and (best is None or t > best):
                best, bname = t, name
        rows = ((cl.get("models") or {}).get(bname) or {}).get("per_trace")
        if not rows or len(rows) != len(protos):
            continue
        for pf, r in zip(protos, rows):
            if r[2]:
                out[pf] = (r[0], r[2])
    return out


def common_set_comparison(cells: list[dict], alphabet: str = "itinerary",
                          scope: str = "main") -> dict:
    keep = set(MAIN_CELLS) if scope == "main" else None
    pool = {f"{c['run_id']}/{c['algo']}": c for c in cells
            if c["alphabet"] == alphabet and not c["control"]
            and (keep is None or f"{c['run_id']}/{c['algo']}" in keep)}
    if len(pool) < 2:
        return {}
    pp = {k: _per_processo(c) for k, c in pool.items()}
    common = set.intersection(*(set(v) for v in pp.values()))

    def acc(d, keys):
        h = sum(d[k][0] for k in keys if k in d)
        t = sum(d[k][1] for k in keys if k in d)
        return _round(h / t) if t else None

    rows = [{"cell": k, "n_own": len(v), "acc_own": acc(v, v.keys()),
             "acc_common": acc(v, common)} for k, v in pp.items()]
    for r in rows:
        r["delta"] = (_round(r["acc_common"] - r["acc_own"])
                      if None not in (r["acc_common"], r["acc_own"]) else None)
    rows.sort(key=lambda r: -(r["acc_common"] or 0))
    accs = [r["acc_common"] for r in rows if r["acc_common"] is not None]
    return {"alphabet": alphabet, "scope": scope, "n_common": len(common), "rows": rows,
            "n_clusterings": len(pool),
            "spread": _round(max(accs) - min(accs)) if accs else None,
            "spread_bootstrap": _spread_bootstrap(pp, common)}


def _spread_bootstrap(pp: dict, common: set, n_boot: int = 2000, seed: int = 42) -> dict:
    import numpy as np
    keys = sorted(common)
    cells = sorted(pp)
    if len(keys) < 2 or len(cells) < 2:
        return {}
    hits = np.array([[pp[c].get(k, (0, 0))[0] for k in keys] for c in cells], dtype=float)
    tot = np.array([[pp[c].get(k, (0, 0))[1] for k in keys] for c in cells], dtype=float)
    rng = np.random.default_rng(seed)
    spreads = []
    for _ in range(n_boot):
        col = rng.integers(0, len(keys), size=len(keys))
        h, t = hits[:, col].sum(axis=1), tot[:, col].sum(axis=1)
        a = h[t > 0] / t[t > 0]
        if a.size >= 2:
            spreads.append(float(a.max() - a.min()))
    if not spreads:
        return {}
    arr = np.sort(np.array(spreads))
    return {"n_boot": n_boot,
            "ci95": [_round(float(np.percentile(arr, 2.5))),
                     _round(float(np.percentile(arr, 97.5)))],
            "upper90_one_sided": _round(float(np.percentile(arr, 90))),
            "upper95_one_sided": _round(float(np.percentile(arr, 95)))}


def noise_difficulty(cells: list[dict], alphabet: str = "itinerary") -> list[dict]:
    out = []
    for arm in ("exp-raw", "exp-anon"):
        lp = CLUSTERING / arm / "hdbscan" / "labels.json"
        if not lp.is_file():
            continue
        labels = json.loads(lp.read_text(encoding="utf-8"))["labels"]
        noise = {p for p, v in labels.items() if v == -1}
        if not noise:
            continue
        for algo in ("kmeans", "leiden"):
            cell = next((c for c in cells if c["run_id"] == arm and c["algo"] == algo
                         and c["alphabet"] == alphabet and not c["control"]), None)
            if cell is None:
                continue
            d = _per_processo(cell)
            inside, outside = noise & set(d), set(d) - noise
            def acc(keys):
                h = sum(d[k][0] for k in keys)
                t = sum(d[k][1] for k in keys)
                return _round(h / t) if t else None
            a_in, a_out = acc(inside), acc(outside)
            out.append({"arm": arm, "algo": algo, "n_hdbscan_noise": len(noise),
                        "n_noise_evaluated": len(inside), "acc_on_noise": a_in,
                        "n_rest": len(outside), "acc_on_rest": a_out,
                        "gap": _round(a_in - a_out) if None not in (a_in, a_out) else None})
    return out


DEFAULT_WEIGHTS = {"downstream": 0.5, "coverage": 0.3, "quality": 0.2}


def selection_score(cells: list[dict], weights: dict | None = None,
                    alphabet: str = "itinerary", scope: str = "main") -> dict:
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    cs = common_set_comparison(cells, alphabet, scope)
    acc = {r["cell"]: r["acc_common"] for r in (cs.get("rows") or [])}
    if not acc:
        return {}
    ctrl = (controls(cells).get(alphabet) or {})
    floor = ctrl.get("shuffled_best_top1")
    if floor is None:
        floor = 0.0
    cov_rows = [r for r in coverage(cells) if r["alphabet"] == alphabet]
    cov = {r["cell"]: (r["processos_evaluated"] / r["processos_total"]
                       if r["processos_total"] else None) for r in cov_rows}
    n_eval = {r["cell"]: r["clusters_evaluated"] for r in cov_rows}

    rows = []
    for cell_id in acc:
        run_id, algo = cell_id.split("/")
        mp = CLUSTERING / run_id / algo / "metrics.json"
        cm = json.loads(mp.read_text(encoding="utf-8")) if mp.is_file() else {}
        src = cm.get("internal_comparable") or cm
        if cm and src.get("space") != COMPARABLE_SPACE:
            raise RuntimeError(
                f"selection_score: {run_id}/{algo} reports internal indices in space "
                f"{src.get('space')!r}, not {COMPARABLE_SPACE!r}. The selection criterion "
                "ranks clusterings by a quality term built from DBCV and silhouette; indices "
                "from a different metric space inflate that term and can hand the selection to "
                "the wrong clustering. Re-run the stage so it writes 'internal_comparable'.")
        dbcv, sil = src.get("dbcv"), src.get("silhouette")
        q = None
        if isinstance(dbcv, (int, float)) and isinstance(sil, (int, float)):
            q = _round((_scale(dbcv, -1.0, 1.0) + _scale(sil, -1.0, 1.0)) / 2)
        d = _scale(acc[cell_id], floor, 1.0)
        c = _scale(cov.get(cell_id), 0.0, 1.0)
        parts = [(w["downstream"], d), (w["coverage"], c), (w["quality"], q)]
        rows.append({
            "cell": cell_id, "acc_common": acc[cell_id], "coverage": _round(cov.get(cell_id)),
            "dbcv": dbcv, "silhouette": sil, "noise_ratio": cm.get("noise_ratio"),
            "n_clusters_evaluated": n_eval.get(cell_id),
            "s_downstream": d, "s_coverage": c, "s_quality": q,
            "score": _round(sum(wt * v for wt, v in parts if v is not None)),
        })
    rows.sort(key=lambda r: -(r["score"] or 0))
    return {"weights": w, "alphabet": alphabet, "scope": scope,
            "n_clusterings": cs.get("n_clusterings"), "n_common": cs.get("n_common"),
            "downstream_floor": floor, "rows": rows,
            "scales": {"downstream": f"[{floor} shuffled-partition floor, 1.0]",
                       "coverage": "[0, 1] fraction of corpus evaluated after min_traces",
                       "quality": "mean of DBCV and silhouette, each mapped from [-1,1] to [0,1]"}}


def selection_sensitivity(cells: list[dict]) -> list[dict]:
    schemes = {
        "balanced (0.5/0.3/0.2)": {"downstream": 0.5, "coverage": 0.3, "quality": 0.2},
        "downstream-first (0.7/0.2/0.1)": {"downstream": 0.7, "coverage": 0.2, "quality": 0.1},
        "coverage-first (0.3/0.5/0.2)": {"downstream": 0.3, "coverage": 0.5, "quality": 0.2},
        "quality-first (0.2/0.2/0.6)": {"downstream": 0.2, "coverage": 0.2, "quality": 0.6},
        "equal thirds": {"downstream": 1/3, "coverage": 1/3, "quality": 1/3},
    }
    out = []
    for name, w in schemes.items():
        sc = selection_score(cells, w)
        rows = sc.get("rows") or []
        out.append({"scheme": name, "winner": rows[0]["cell"] if rows else None,
                    "score": rows[0]["score"] if rows else None,
                    "runner_up": rows[1]["cell"] if len(rows) > 1 else None})
    return out
