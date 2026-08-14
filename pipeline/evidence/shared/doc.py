from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from ...core.paths import ROOT


_PENDING = "_Not yet computed — regenerate with `pipeline run results`._"


def _n(v, nd=4):
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.{nd}f}".rstrip("0").rstrip(".") if nd > 0 else f"{v:.0f}"
    return f"{v:,}" if isinstance(v, int) else str(v)


def _table(header: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(header) + " |",
           "|" + "|".join(["---"] * len(header)) + "|"]
    out += ["| " + " | ".join(rows_i) + " |" for rows_i in rows]
    return "\n".join(out)


def fig_glossary(f: dict) -> str:
    rows = f.get("metric_glossary") or []
    if not rows:
        return _PENDING
    return _table(["metric", "family", "better", "definition"],
                  [[f"`{r['metric']}`", r["family"], r["direction"], r["definition"]]
                   for r in rows])
