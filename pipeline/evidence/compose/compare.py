from __future__ import annotations

from pathlib import Path

from .envelope import compose, members_block, population_block
from .lattice import ALGOS, MODELS, cell_key, coord_of_cell, main_cells
from .levels import _cells_for, stats_path
from .metrics import best_model_per_cluster, model_rows, summarise_clusters, summarise_model


def _delta(a, b):
    return round(a - b, 4) if isinstance(a, (int, float)) and isinstance(b, (int, float)) else None


def compare_arms(cells: list[dict], alphabet: str) -> tuple[Path, dict]:
    pool = [c for c in main_cells(cells) if c["alphabet"] == alphabet]
    keys = [cell_key(c) for c in pool]
    per_arm = {}
    for arm in ("raw", "anon"):
        sub = _cells_for(pool, arm=arm)
        per_arm[arm] = {"n_cells": len(sub), "clusters": summarise_clusters(sub),
                        "by_model": {m: summarise_model(model_rows(sub).get(m, []))
                                     for m in MODELS}}
    deltas = {}
    for m in MODELS:
        r = per_arm["raw"]["by_model"].get(m, {}).get("membership_weighted", {}).get("top1")
        a = per_arm["anon"]["by_model"].get(m, {}).get("membership_weighted", {}).get("top1")
        deltas[m] = {"raw_top1": r, "anon_top1": a, "anon_minus_raw": _delta(a, r),
                     "raw_n_clusters": per_arm["raw"]["clusters"].get("n_clusters"),
                     "anon_n_clusters": per_arm["anon"]["clusters"].get("n_clusters"),
                     "raw_n_traces": per_arm["raw"]["clusters"].get("n_traces"),
                     "anon_n_traces": per_arm["anon"]["clusters"].get("n_traces")}
    payload = compose(
        scope={"level": "L0", "alphabet": alphabet,
               "aggregated_over": ["param", "algo", "model"]},
        population=population_block(
            "main-cells",
            definition="each arm over the cases its own clusterings evaluated. The two are not "
                       "restricted to a common set: that intersection keeps only the cases both "
                       "arms clustered alike, which is where anonymisation cost the least. Every "
                       "accuracy carries its denominators instead. The paired raw-vs-anon test "
                       "is the noninferiority stage, which pairs per protocolo within one "
                       "algorithm"),
        members=members_block(keys, keys, files=[c["path"] for c in pool]),
        results={"per_arm": per_arm, "anonymisation_cost_top1": deltas},
    )
    return stats_path(alphabet) / "compare_arms.json", payload


def population_accounting() -> dict:
    import json

    from ...core.paths import ARTIFACTS
    idx = ARTIFACTS / "traces" / "index.json"
    if not idx.is_file():
        return {"available": False,
                "reason": f"{idx} absent; run export-traces to record per-cell coverage"}
    data = json.loads(idx.read_text(encoding="utf-8"))
    rows = {}
    for cell in data.get("cells", []):
        key = f"{cell['run_id']}/{cell['algo']}"
        labelled = cell.get("processos_labelled") or 0
        kept = cell.get("processos_kept") or 0
        rows[key] = {
            "processos_unlabelled": cell.get("processos_unlabelled"),
            "processos_below_floor": cell.get("processos_below_floor"),
            "processos_kept": kept,
            "coverage_of_corpus": cell.get("coverage_of_corpus"),
            "lost_to_noise": cell.get("processos_unlabelled"),
            "lost_to_min_traces": (labelled - kept) if labelled else None,
        }
    covs = [r["coverage_of_corpus"] for r in rows.values()
            if isinstance(r["coverage_of_corpus"], (int, float))]
    return {
        "available": True,
        "per_cell": rows,
        "coverage_spread": (round(max(covs) - min(covs), 4) if covs else None),
        "reading": ("two filters shrink the evaluated population and they are not symmetric "
                    "across methods. Density clustering emits noise (label -1) which is dropped "
                    "entirely, so only that family loses cases this way; the min_traces floor "
                    "then drops whole small clusters, which costs a fine-grained partition more "
                    "than a coarse one. A top-1 difference between two algorithms is therefore "
                    "not a scalar comparison: `coverage_of_corpus` here is the other half of "
                    "the result, and a method that scores higher over fewer cases has not won. "
                    "Restricting both to their common cases was tried and removed — the "
                    "intersection keeps only the cases every method clustered alike, which is "
                    "a sample selected on the very outcome being compared."),
    }


def compare_algorithms(cells: list[dict], alphabet: str) -> tuple[Path, dict]:
    pool = [c for c in main_cells(cells) if c["alphabet"] == alphabet]
    keys = [cell_key(c) for c in pool]
    per_algo = {}
    for algo in ALGOS:
        sub = [c for c in pool if c["algo"] == algo]
        if not sub:
            continue
        rows_all = model_rows(sub)
        per_algo[algo] = {
            "n_cells": len(sub),
            "clusters": summarise_clusters(sub),
            "by_model": {m: summarise_model(rows_all.get(m, [])) for m in MODELS},
        }
    payload = compose(
        scope={"level": "L0", "alphabet": alphabet,
               "aggregated_over": ["arm", "param", "model"]},
        population=population_block(
            "main-cells",
            definition="each algorithm over the cases it clustered into a cluster large enough "
                       "to evaluate. Algorithms differ in coverage as well as in accuracy, so "
                       "n_clusters and n_traces sit beside every number: a higher accuracy over "
                       "a smaller share of the corpus is not a better result, it is a different "
                       "point on the same trade-off"),
        members=members_block(keys, keys, files=[c["path"] for c in pool]),
        results={"per_algorithm": per_algo,
                 "population_accounting": population_accounting()},
    )
    return stats_path(alphabet) / "compare_algorithms.json", payload


def compare_models(cells: list[dict], alphabet: str) -> tuple[Path, dict]:
    pool = [c for c in main_cells(cells) if c["alphabet"] == alphabet]
    keys = [cell_key(c) for c in pool]
    rows_all = model_rows(pool)
    per_model = {}
    for m in MODELS:
        s = summarise_model(rows_all.get(m, []))
        per_model[m] = {
            "all_cells": s,
            "n_clusters": s.get("n_clusters"),
            "cells_evaluated": len({r["cell"] for r in rows_all.get(m, [])}),
        }
    base_top1 = per_model.get("markov", {}).get("all_cells", {}) \
                         .get("membership_weighted", {}).get("top1")
    vs_markov = {m: _delta(per_model[m]["all_cells"]
                           .get("membership_weighted", {}).get("top1"), base_top1)
                 for m in MODELS if m != "markov"}
    payload = compose(
        scope={"level": "L0", "alphabet": alphabet,
               "aggregated_over": ["arm", "param", "algo"]},
        population=population_block(
            "main-cells",
            definition="every model over every cell of this alphabet. A model that was skipped "
                       "on some cells covers fewer clusters, so cells_evaluated and n_clusters "
                       "are reported per model: a model is not better for having been scored on "
                       "less"),
        members=members_block(keys, keys, files=[c["path"] for c in pool]),
        results={"per_model": per_model,
                 "top1_minus_markov": vs_markov,
                 "best_model_per_cluster": best_model_per_cluster(pool)},
    )
    return stats_path(alphabet) / "compare_models.json", payload


def compare_populations(cells: list[dict], alphabet: str) -> tuple[Path, dict]:
    pool = [c for c in main_cells(cells) if c["alphabet"] == alphabet]
    controls = [c for c in cells
                if coord_of_cell(c).control and c["alphabet"] == alphabet]
    keys = [cell_key(c) for c in pool]

    def _view(rows):
        out = {}
        for m in MODELS:
            s = summarise_model(rows.get(m, []))
            out[m] = {
                "top1_membership_weighted": s.get("membership_weighted", {}).get("top1"),
                "top1_unweighted": s.get("unweighted", {}).get("top1"),
                "baseline_global_model": s.get("baselines", {}).get("top1_global_model"),
                "baseline_successor": s.get("baselines", {}).get("top1_successor"),
                "gain_vs_global_model": s.get("gain_vs_global_model"),
                "gain_vs_successor": s.get("gain_vs_successor"),
                "n_clusters": s.get("n_clusters"),
            }
        return out

    views = {"all-labelled": _view(model_rows(pool))}
    if controls:
        views["shuffled-control"] = _view(model_rows(controls))
    payload = compose(
        scope={"level": "L0", "alphabet": alphabet,
               "aggregated_over": ["arm", "param", "algo", "model"]},
        population=population_block(
            "main-cells",
            definition="the real partition beside its shuffled control under both weightings, "
                       "so a gain that survives only one of them is visible instead of "
                       "arguable"),
        members=members_block(keys, keys, files=[c["path"] for c in pool]),
        results={"views": views,
                 "n_control_cells": len(controls),
                 "reading": "a gain that changes sign between weightings is a property of the "
                            "baseline and the population, not of the method"},
    )
    return stats_path(alphabet) / "compare_populations.json", payload


def ablation_cells(cells: list[dict]) -> list[tuple[Path, dict]]:
    out = []
    for cell in cells:
        co = coord_of_cell(cell)
        if not co.ablation:
            continue
        base = [c for c in cells
                if coord_of_cell(c).arm == co.arm and coord_of_cell(c).param == "base"
                and c["algo"] == cell["algo"] and c["alphabet"] == cell["alphabet"]]
        rows = model_rows([cell])
        base_rows = model_rows(base) if base else {}
        deltas = {}
        for m in MODELS:
            v = summarise_model(rows.get(m, [])).get("membership_weighted", {}).get("top1")
            b = summarise_model(base_rows.get(m, [])).get("membership_weighted", {}).get("top1")
            deltas[m] = {"ablated_top1": v, "base_top1": b, "delta": _delta(v, b)}
        payload = compose(
            scope=co.scope("L3"),
            population=population_block(
                "all-labelled",
                definition="the ablated cell against the base cell of the same arm, algorithm "
                           "and alphabet"),
            members=members_block([cell_key(cell)] + [cell_key(c) for c in base],
                                  [cell_key(cell)] + [cell_key(c) for c in base],
                                  allow_missing=True),
            results={"clusters": summarise_clusters([cell]),
                     "vs_base_top1": deltas,
                     "base_present": bool(base)},
        )
        name = f"{cell['algo']}-{cell['alphabet']}.json"
        out.append((stats_path("ablation") / f"exp-{co.arm}" / co.param / name, payload))
    return out
