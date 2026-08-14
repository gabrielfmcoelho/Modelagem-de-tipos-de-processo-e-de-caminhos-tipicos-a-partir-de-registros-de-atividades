
from __future__ import annotations

from statistics import mean, median

DEFAULT_BAND_CENTER = 0.60
DEFAULT_BAND_HALFWIDTH = 0.20

_FIRST_DOC_WEIGHT = 3.0
_EARLY_DOC_WEIGHT = 1.5
_EARLY_DOC_UNTIL_RANK = 3
_DEFAULT_DOC_WEIGHT = 1.0


def band(
    score: float | None,
    center: float = DEFAULT_BAND_CENTER,
    halfwidth: float = DEFAULT_BAND_HALFWIDTH,
) -> float:
    if score is None or halfwidth <= 0:
        return 0.0
    return round(max(0.0, 1.0 - abs(score - center) / halfwidth), 6)


def doc_band_score(
    scores,
    *,
    center: float = DEFAULT_BAND_CENTER,
    halfwidth: float = DEFAULT_BAND_HALFWIDTH,
    agg: str = "median",
) -> float | None:
    bands = [band(s, center, halfwidth) for s in scores if s is not None]
    if not bands:
        return None
    value = mean(bands) if agg == "mean" else median(bands)
    return round(value, 4)


def _doc_weight(rank_one_based: int) -> float:
    if rank_one_based == 1:
        return _FIRST_DOC_WEIGHT
    if rank_one_based <= _EARLY_DOC_UNTIL_RANK:
        return _EARLY_DOC_WEIGHT
    return _DEFAULT_DOC_WEIGHT


def activity_band_score(doc_bands) -> float | None:
    vals = [b for b in doc_bands if b is not None]
    return round(mean(vals), 4) if vals else None


def processo_band_score(ordered_band_scores) -> float | None:
    num = den = 0.0
    for i, b in enumerate((b for b in ordered_band_scores if b is not None), start=1):
        w = _doc_weight(i)
        num += w * b
        den += w
    return round(num / den, 4) if den > 0 else None
