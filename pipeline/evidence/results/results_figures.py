from __future__ import annotations
import argparse
import json
from pathlib import Path
from statistics import mean, median
from ...core.paths import ROOT
from ..etl.figures import CORPUS_BIAS, CORPUS_FUNNEL
from ..clustering.figures import ABLATION, CATCH_ALL, COMPARABLE_SPACE, DEFAULT_WEIGHTS, TIPO_CACHE, _agreement, _ari_dropping, _per_processo, _spread_bootstrap, catalogue_sample, catch_all_null, catch_all_share, cluster_counts, common_set_comparison, coverage, index_mechanism, intrinsic_vs_downstream, noise_difficulty, selection_full_coverage, selection_score, selection_sensitivity, taxonomy
from ..typical_path.figures import ALPHABET_NAMES, CONSTRAINT_COST, GEN_KEYS, GEN_MODEL, MODELS, NONINFERIORITY_PATHS, SIZE_BINS, _cluster_rows, by_band, combos, controls, dispersion, flow_validity, load_cells, model_count, model_profile, model_vs_medoid, noninferiority, size_trend, temporal_holdout
from ..shared.blind import _IDENTIFYING, _TRACES, _blind, _unit_acronyms
from ..shared.glossary import METRIC_GLOSSARY
from ..shared.paths import CLUSTERING, MAIN_CELLS, SHUFFLED, TYPICAL
from ..artifact import write_artifact
from ..shared.stats import _round, _scale, _spearman, _spearman_permutation_p, _spearman_power, _wmean


OUT = ROOT / "artifacts" / "stats" / "results_figures.json"


def build() -> dict:
    cells = load_cells()
    if not cells:
        raise FileNotFoundError(
            f"{TYPICAL} holds no <run_id>/<algo>/metrics.json, so there is nothing to aggregate. "
            "`results` reads the typical-path matrix; run `pipeline run matrix` and "
            "`pipeline run typical-cells` first. Aggregating an empty tree produces None where "
            "every figure expects a number, which surfaces much later as an arithmetic error.")
    return {
        "n_cells": len(cells),
        "cells": [{k: c[k] for k in ("run_id", "algo", "alphabet", "arm", "control", "path",
                                     "dfg_floor", "n_dropped_by_min_states")} for c in cells],
        "model_vs_medoid": model_vs_medoid(cells),
        "dispersion": dispersion(cells),
        "controls": controls(cells),
        "by_size_band": by_band(cells),
        "coverage": coverage(cells),
        "model_count": model_count(cells),
        "cluster_counts": cluster_counts(),
        "taxonomy": taxonomy(),
        "catch_all_share": catch_all_share(),
        "catch_all_null": catch_all_null(),
        "temporal_holdout": temporal_holdout(),
        "catalogue_sample": catalogue_sample(selection=selection_full_coverage(cells)),
        "index_mechanism": index_mechanism(cells),
        "selection_full_coverage": selection_full_coverage(cells),
        "constraint_cost": (json.loads(CONSTRAINT_COST.read_text(encoding="utf-8"))
                            if CONSTRAINT_COST.is_file() else {}),
        "noninferiority": noninferiority(),
        "combos": {a: combos(cells, a)[:20] for a in ALPHABET_NAMES},
        "combos_large": {a: combos(cells, a, band="large")[:20] for a in ALPHABET_NAMES},
        "model_profile": {a: model_profile(cells, a) for a in ALPHABET_NAMES},
        "size_trend": {a: size_trend(cells, a) for a in ALPHABET_NAMES},
        "intrinsic_vs_downstream": intrinsic_vs_downstream(cells),
        "common_set": common_set_comparison(cells),
        "noise_difficulty": noise_difficulty(cells),
        "flow_validity": flow_validity(cells),
        "selection": selection_score(cells),
        "selection_all": selection_score(cells, scope="all"),
        "common_set_all": common_set_comparison(cells, "itinerary", "all"),
        "combos_full": {a: combos(cells, a) for a in ALPHABET_NAMES},
        "metric_glossary": [{"metric": m, "family": fam, "direction": d, "definition": t}
                            for m, fam, d, _emits, t in METRIC_GLOSSARY],
        "selection_sensitivity": selection_sensitivity(cells),
        "corpus_bias": (json.loads(CORPUS_BIAS.read_text(encoding="utf-8"))
                        if CORPUS_BIAS.is_file() else {}),
        "corpus_funnel": (json.loads(CORPUS_FUNNEL.read_text(encoding="utf-8"))
                          if CORPUS_FUNNEL.is_file() else {}),
        "ablation": (json.loads(ABLATION.read_text(encoding="utf-8"))
                     if ABLATION.is_file() else {}),
        "catch_all_label": CATCH_ALL,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--print", action="store_true")
    args = ap.parse_args()

    figures = build()
    out = Path(args.out)
    write_artifact(figures, out, stage="results",
                   params={"n_cells": figures["n_cells"]},
                   inputs=[p for p in (CONSTRAINT_COST, CORPUS_BIAS, CORPUS_FUNNEL,
                                       ABLATION, *NONINFERIORITY_PATHS, TIPO_CACHE) if p.is_file()])
    print(f"wrote {out}  ({figures['n_cells']} cells, "
          f"{figures['model_count']['models_trained']} models trained)")
    if args.print:
        print(json.dumps({k: v for k, v in figures.items() if k not in ("cells", "coverage")},
                         ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
