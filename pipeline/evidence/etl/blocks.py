from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from ...core.paths import ROOT
from ..shared.doc import _n, _table


def fig_corpus_bias(f: dict) -> str:
    cb = f.get("corpus_bias") or {}
    if not cb.get("months"):
        return "_Not yet computed — run `pipeline run corpus-bias`._"
    rows = [[m["month"], _n(m["observed"]), _n(m["days_available"]),
             _n(m["median_lifetime"], 0), _n(m["max_lifetime"], 0),
             f"{100 * m['estimated_excluded_frac']:.1f}%", _n(m["estimated_true_n"])]
            for m in cb["months"]]
    tot = (f"\n\n**Observed {_n(cb['observed_total'])}; estimated true "
           f"{_n(cb['estimated_true_total'])}; missing ≈ **{_n(cb['estimated_missing'])} "
           f"({100 * cb['estimated_missing_frac']:.1f}%)**. "
           f"{cb.get('caveat', '')}")
    return _table(["birth month", "observed", "days available", "median lifetime",
                   "max lifetime", "est. excluded", "est. true n"], rows) + tot
