from __future__ import annotations

from statistics import mean

ROUND_TO = 4


def _numeric(values):
    return [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]


def macro_mean(values):
    vals = _numeric(values)
    return round(mean(vals), ROUND_TO) if vals else None


def weighted_mean(pairs):
    pairs = [(w, v) for w, v in pairs
             if isinstance(v, (int, float)) and not isinstance(v, bool)]
    total = sum(w for w, _ in pairs)
    return round(sum(w * v for w, v in pairs) / total, ROUND_TO) if total else None


def both_means(pairs):
    return {"macro": macro_mean([v for _, v in pairs]), "weighted": weighted_mean(pairs)}
