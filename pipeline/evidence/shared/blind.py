from __future__ import annotations
import argparse
import json
from pathlib import Path
from statistics import mean, median
from ...core.paths import ROOT


_IDENTIFYING = ("sead", "piau", "teresina")


_TRACES = ROOT / "artifacts" / "traces" / "protocol_traces.json.gz"


def _unit_acronyms() -> set[str]:
    if not _TRACES.is_file():
        raise FileNotFoundError(
            f"{_TRACES} is missing. It is the only source of the unit acronyms that _blind() "
            "replaces with [unit] in the catalogue table, so without it the blind manuscript "
            "would be built with those acronyms intact and nothing would report it. Run "
            "`pipeline run export-traces` before `results`.")
    import gzip
    import re
    raw = json.loads(gzip.open(_TRACES, "rt", encoding="utf-8").read())
    out = set()
    for rec in (raw.get("traces") or raw).values():
        for state in (rec.get("states") or []):
            _, _, lane = state.partition("@")
            for seg in re.split(r"[/\-]", lane):
                seg = seg.strip()
                if len(seg) >= 3 and seg.isalpha() and seg.isupper():
                    out.add(seg)
    return out


def _blind(text: str, acronyms: set[str] | None = None) -> str:
    low = (text or "").lower()
    if any(t in low for t in _IDENTIFYING):
        return "[redacted for double-blind review]"
    if acronyms:
        import re
        tokens = set(re.findall(r"\b[A-Z]{3,}\b", text or ""))
        if tokens & acronyms:
            return re.sub(r"\b[A-Z]{3,}\b",
                          lambda m: "[unit]" if m.group() in acronyms else m.group(), text)
    return text
