from __future__ import annotations

import json
from pathlib import Path

from ...core.paths import ARTIFACTS
from ..shared.paths import CLUSTERING, TYPICAL
from .envelope import NO_ALPHABET, compose, members_block, population_block
from .lattice import ALPHABETS, MODELS, cell_key, coord_of_cell, main_cells, parse_run_id
from .metrics import best_model_per_cluster, model_rows, summarise_clusters, summarise_model

BY_MODEL = TYPICAL / "_by_model"
BY_ALPHABET = TYPICAL / "_by_alphabet"


def _cells_for(cells, **fixed):
    out = []
    for c in cells:
        co = coord_of_cell(c)
        if all(getattr(co, k) == v for k, v in fixed.items()):
            out.append(c)
    return out


def _clustering_metrics(run_id: str, algo: str) -> dict:
    p = CLUSTERING / run_id / algo / "metrics.json"
    if not p.is_file():
        return {}
    d = json.loads(p.read_text(encoding="utf-8"))
    return {k: d.get(k) for k in ("dbcv", "silhouette", "n_clusters", "noise_ratio", "coverage")}


def _labels(run_id: str, algo: str) -> dict:
    p = CLUSTERING / run_id / algo / "labels.json"
    if not p.is_file():
        return {}
    d = json.loads(p.read_text(encoding="utf-8"))
    return d.get("labels") or {}


def arm_summary(arm: str, cells: list[dict]) -> tuple[Path, dict]:
    mine = _cells_for(cells, arm=arm)
    combos = sorted({(c["run_id"], c["algo"]) for c in mine})
    rows = []
    for run_id, algo in combos:
        co = parse_run_id(run_id)
        rows.append({"run_id": run_id, "param": co.param, "algo": algo,
                     "control": co.control, "ablation": co.ablation,
                     "clustering": _clustering_metrics(run_id, algo)})
    payload = compose(
        scope={"level": "L1", "arm": arm, "alphabet": NO_ALPHABET},
        population=population_block("all-labelled"),
        members=members_block([f"{r}/{a}" for r, a in combos],
                              [f"{r}/{a}" for r, a in combos]),
        results={"n_clusterings": len(rows), "clusterings": rows},
    )
    return CLUSTERING / f"exp-{arm}" / "arm_summary.json", payload


def arm_path_summary(arm: str, alphabet: str, cells: list[dict]) -> tuple[Path, dict]:
    mine = _cells_for(main_cells(cells), arm=arm, alphabet=alphabet)
    keys = [cell_key(c) for c in mine]
    by_algo, by_model_out = {}, {}
    for algo in sorted({c["algo"] for c in mine}):
        by_algo[algo] = summarise_clusters(_cells_for(mine, algo=algo))
    rows = model_rows(mine)
    for name in MODELS:
        by_model_out[name] = summarise_model(rows.get(name, []))
    payload = compose(
        scope={"level": "L1", "arm": arm, "alphabet": alphabet},
        population=population_block("main-cells"),
        members=members_block(keys, keys, files=[c["path"] for c in mine]),
        results={"n_cells": len(mine), "by_algorithm": by_algo, "by_model": by_model_out,
                 "best_model_per_cluster": best_model_per_cluster(mine)},
    )
    return TYPICAL / f"exp-{arm}" / alphabet / "arm_path_summary.json", payload


def _ari_nmi(a: dict, b: dict) -> dict:
    common = sorted(set(a) & set(b))
    if len(common) < 2:
        return {"n_common": len(common), "ari": None, "nmi": None}
    from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
    la = [str(a[k]) for k in common]
    lb = [str(b[k]) for k in common]
    return {"n_common": len(common),
            "ari": round(float(adjusted_rand_score(la, lb)), 4),
            "nmi": round(float(normalized_mutual_info_score(la, lb)), 4)}


def agreement(run_id: str, algo: str, siblings: list[tuple[str, str]]) -> tuple[Path, dict]:
    mine = _labels(run_id, algo)
    pairs = {}
    for other_run, other_algo in siblings:
        if (other_run, other_algo) == (run_id, algo):
            continue
        pairs[f"{other_run}/{other_algo}"] = _ari_nmi(mine, _labels(other_run, other_algo))
    co = coord_of_cell({"run_id": run_id, "algo": algo, "alphabet": NO_ALPHABET})
    keys = [f"{r}/{a}" for r, a in siblings if (r, a) != (run_id, algo)]
    payload = compose(
        scope={**co.scope("L2"), "alphabet": NO_ALPHABET},
        population=population_block(
            "shared-across-cells", n_cases=len(mine),
            definition="each pair is scored on the protocolos both clusterings label"),
        members=members_block(keys, sorted(pairs)),
        results={"n_labelled": len(mine), "vs": pairs},
    )
    return CLUSTERING / run_id / algo / "agreement.json", payload


def by_model(model: str, alphabet: str, cells: list[dict]) -> tuple[Path, dict]:
    pool = [c for c in main_cells(cells) if c["alphabet"] == alphabet]
    keys = [cell_key(c) for c in pool]
    rows = model_rows(pool).get(model, [])
    per_cell = {}
    for c in pool:
        r = model_rows([c]).get(model, [])
        per_cell[cell_key(c)] = summarise_model(r)
    payload = compose(
        scope={"level": "L4", "model": model, "alphabet": alphabet},
        population=population_block("main-cells"),
        members=members_block(keys, keys, files=[c["path"] for c in pool]),
        results={
            "overall": summarise_model(rows),
            "per_cell": per_cell,
            "by_arm": {arm: summarise_model(model_rows(
                _cells_for(pool, arm=arm)).get(model, [])) for arm in ("raw", "anon")},
        },
    )
    return BY_MODEL / alphabet / f"{model}.json", payload


def by_alphabet(alphabet: str, cells: list[dict]) -> tuple[Path, dict]:
    pool = [c for c in main_cells(cells) if c["alphabet"] == alphabet]
    keys = [cell_key(c) for c in pool]
    rows = model_rows(pool)
    payload = compose(
        scope={"level": "L4", "alphabet": alphabet},
        population=population_block("main-cells"),
        members=members_block(keys, keys, files=[c["path"] for c in pool]),
        results={
            "n_cells": len(pool),
            "clusters": summarise_clusters(pool),
            "by_model": {m: summarise_model(rows.get(m, [])) for m in MODELS},
            "best_model_per_cluster": best_model_per_cluster(pool),
            "by_arm": {arm: summarise_clusters(_cells_for(pool, arm=arm))
                       for arm in ("raw", "anon")},
        },
    )
    return BY_ALPHABET / f"{alphabet}.json", payload


def clusters_index(cell: dict) -> tuple[Path, dict]:
    co = coord_of_cell(cell)
    entries = {}
    for cid, rec in (cell.get("clusters") or {}).items():
        if not isinstance(rec, dict):
            continue
        models = {n: m.get("top1") for n, m in (rec.get("models") or {}).items()
                  if isinstance(m, dict) and "skipped" not in m}
        entries[cid] = {
            "n_traces": rec.get("n_traces"),
            "n_test": rec.get("n_test"),
            "edge_f1": rec.get("edge_f1"),
            "edge_coverage": rec.get("edge_coverage"),
            "baseline": rec.get("baseline") or {},
            "top1_by_model": models,
            "best_model": (max(models, key=lambda k: models[k])
                           if any(v is not None for v in models.values()) else None),
            "typical_itinerary_len": len((rec.get("path_reference") or {}).get(
                "medoid_itinerary") or []),
        }
    payload = compose(
        scope=co.scope("L5"),
        population=population_block("all-labelled", n_cases=len(entries)),
        members=members_block(sorted(entries), sorted(entries), files=[cell["path"]]),
        results={"n_clusters": len(entries), "clusters": entries},
    )
    return (TYPICAL / cell["run_id"] / cell["algo"] / cell["alphabet"] / "clusters_index.json",
            payload)


def stats_path(name: str) -> Path:
    return ARTIFACTS / "stats" / name
