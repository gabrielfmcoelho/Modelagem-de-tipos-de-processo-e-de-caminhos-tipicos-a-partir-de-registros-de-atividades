#!/usr/bin/env python

from __future__ import annotations

import argparse
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import Doc

HEAVY = ["gen_08_comparison", "gen_09_richtokens", "gen_10_tuning", "gen_11_stitching"]


_FAILED: list[str] = []


def _run(modname: str) -> None:
    try:
        importlib.import_module(modname).main()
        print(f"  ✓ {modname}")
    except Exception as e:
        print(f"  ✗ {modname} failed: {type(e).__name__}: {e}")
        _FAILED.append(f"{modname} ({type(e).__name__})")


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate reports + index")
    ap.add_argument("--skip-datalake", action="store_true", help="skip report ① (needs Trino/VPN)")
    ap.add_argument("--heavy", action="store_true", help="also run the GPU timeline reports (gen_08–11)")
    args = ap.parse_args()

    _run("gen_02_dataset")
    _run("gen_13_matrix")
    _run("gen_14_explorer")
    if not args.skip_datalake:
        _run("gen_01_datalake")
    if args.heavy:
        for m in HEAVY:
            _run(m)

    idx = Doc(
        "Reports — SEAD-PI / 2025 SEI process-mining study",
        "_Generated artifacts for the TCC. Light reports + this index: `python reports/gen_all.py`; "
        "the GPU timeline reports run individually (`docs/research/models-and-reports.md`) or with `--heavy`. "
        "Charts under [`charts/`](charts/)._",
    )
    idx.h2("Data & clustering")
    idx.table(
        ["report", "content"],
        [["[① Datalake source](01-datalake-schema.md)", "table schema, peculiarities, raw→graph mapping"],
         ["[② Dataset & pipeline](02-dataset-overview.md)", "corpus profile, per-stage lineage, flow health"],
         ["[⑭ Cluster & experiment explorer](explorer.html)", "único dashboard interativo — clusters de todo algoritmo (nomeados), timelines por modelo, qualidade do clustering, glossários e página de algoritmos (HTML)"]],
    )
    idx.h2("Timeline algorithms (GPU)")
    idx.table(
        ["report", "content"],
        [["[⑧ Algorithm comparison](08-comparison.md)", "Real × GRU-chrono × Transformer × GRU-flow × Markov, per cluster (md, --heavy)"],
         ["[⑨ Rich-token + Phase-3 ablations](09-phase2-richtokens.md)", "do richer tokens / aux-loss / RL help the model *learn* validity?"],
         ["[⑩ Hyperparameter tuning](10-tuning.md)", "train/val/test sweep — top-1 + generation validity"],
         ["[⑪ Branch-stitching](11-stitching.md)", "`generate_full`: structural validity vs length"],
         ["[⑬ Clustering × modelo matrix](13-matrix.md)", "raw/anon × hdbscan/kmeans/leiden + consensus × per-cluster next-step models (from `pipeline/run_typical_eval.py` artifacts)"]],
    )
    idx.h2("See also")
    idx.p("- [`docs/research/models-and-reports.md`](../../docs/research/models-and-reports.md) — models, report generators & how-to-run\n"
          "- [`docs/architecture/algorithms.md`](../../docs/architecture/algorithms.md) — clustering method, coverage, DBCV\n"
          "- [`docs/README.md`](../../docs/README.md) — the experiment & context")
    idx.write("00-index.md")
    print("wrote reports/out/00-index.md")
    if _FAILED:
        print(f"FAILED ({len(_FAILED)}): " + "; ".join(_FAILED))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
