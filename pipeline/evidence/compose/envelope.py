from __future__ import annotations

from pathlib import Path

from ...core.paths import ROOT
from ...model.typical_eval import ALPHABET_NAMES
from ..artifact import write_artifact

NO_ALPHABET = "none"

POPULATIONS = {
    "all-labelled": "every cluster the cell evaluated, with no cross-cell restriction",
    "non-control": "every non-shuffled cell; the shuffled controls are excluded",
    "main-cells": ("the main sweep: shuffled controls and ablation variants both excluded, so an\n                   arm or model difference is not confounded with a deliberately degraded run"),
    "shared-across-cells": ("only the protocolos every cell in `members` evaluated, so the "
                            "comparison is over one population rather than several"),
    "size-band": "clusters whose trace count falls in the named band",
    "corpus": "the analysed corpus, before any clustering",
}


class IncompleteAggregate(RuntimeError):
    pass


def members_block(expected, present, allow_missing: bool = False, files=()) -> dict:
    expected = sorted(set(expected))
    present = sorted(set(present))
    missing = sorted(set(expected) - set(present))
    if missing and not allow_missing:
        raise IncompleteAggregate(
            f"aggregate covers {len(present)} of {len(expected)} members; missing {missing}. "
            "An aggregate is over all of its level or it declares the omission explicitly — "
            "a silently shorter denominator is how a skipped GPU cell becomes a headline number.")
    block = {"expected": len(expected), "present": len(present), "missing": missing,
             "keys": present}
    if files:
        block["files"] = sorted({str(f) for f in files})
    return block


def population_block(name: str, n_cases: int | None = None, definition: str = "") -> dict:
    if name not in POPULATIONS and not definition:
        raise ValueError(
            f"population {name!r} is not one of {sorted(POPULATIONS)} and carries no definition. "
            "Name and define the case set — the population is the most consequential choice in "
            "any comparison here and must not live in a key name.")
    return {"name": name, "n_cases": n_cases,
            "definition": definition or POPULATIONS[name]}


def compose(scope: dict, population: dict, members: dict, results: dict) -> dict:
    return {"scope": scope, "population": population, "members": members, "results": results}


def write_composed(payload: dict, path: Path, *, stage: str, params: dict | None = None,
                   inputs=()) -> Path:
    for key in ("scope", "population", "members", "results"):
        if key not in payload:
            raise ValueError(
                f"composed artifact {path} lacks {key!r}. Every composed artifact states the "
                "lattice point it occupies, the population it covers and the members it "
                "aggregated; without them it cannot be compared with anything.")
    scope = payload["scope"]
    alphabet = scope.get("alphabet")
    if alphabet not in (*ALPHABET_NAMES, NO_ALPHABET):
        raise ValueError(
            f"composed artifact {path} declares alphabet {alphabet!r}. Every composed artifact "
            f"fixes one of {ALPHABET_NAMES}, or {NO_ALPHABET!r} when it reads no trace at all. "
            "The alphabets encode different things over different populations, so each gets "
            "its own matrix of arm x algorithm x model.")
    if "alphabet" in (scope.get("aggregated_over") or ()):
        raise ValueError(
            f"composed artifact {path} aggregates over 'alphabet'. That is the one axis this "
            "study never averages: a unit cell and an itinerary cell do not evaluate the same "
            "cases, and the pooled number carries no mark of it. Emit one artifact per "
            "alphabet instead.")
    pop = payload["population"]
    if pop.get("name") == "shared-across-cells" and pop.get("n_cases") == 0:
        raise ValueError(
            f"composed artifact {path} declares a shared population of zero cases. Every "
            "summary built on it comes out None, which reads as 'not yet run' rather than as "
            "a failure — and the usual cause is intersecting cells whose populations were "
            "never meant to overlap.")
    merged = dict(params or {})
    merged.update({k: v for k, v in scope.items() if isinstance(v, (str, bool))})
    member_files = [ROOT / f for f in (payload["members"].get("files") or ())]
    return write_artifact(payload, path, stage=stage, params=merged,
                          inputs=[*inputs, *member_files])
