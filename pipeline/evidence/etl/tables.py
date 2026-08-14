from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from ...core.paths import ROOT
from ..shared.tex import esc, num, table


def t_corpus_bias(f):
    cb = f.get("corpus_bias") or {}
    rows = [[esc(m["month"]), num(m["observed"], 0), num(m["days_available"], 0),
             num(m["median_lifetime"], 0), num(m["max_lifetime"], 0),
             f"{100 * m['estimated_excluded_frac']:.1f}\\%"]
            for m in (cb.get("months") or [])]
    note = (f"Observed {num(cb.get('observed_total'))}; estimated true "
            f"{num(cb.get('estimated_true_total'))}; estimated missing "
            f"\\textbf{{{num(cb.get('estimated_missing'))}}} "
            f"({100 * (cb.get('estimated_missing_frac') or 0):.1f}\\%). Lower bound: the "
            f"reference month is itself truncated.")
    return table("Right-censoring by opening month.", "tab:corpus-bias", "lrrrrr",
                 ["month", "observed", "days available", "median life", "max life",
                  "est.\\ excluded"], rows, note, small=True)
