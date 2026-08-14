from __future__ import annotations

import pytest

from pipeline.stages.corpus_bias import days_available, estimate_censoring


def test_days_available_shrinks_through_the_year():
    assert days_available("2025-01", "2026-01-01") == 365
    assert days_available("2025-12", "2026-01-01") == 31
    assert days_available("2025-07", "2026-01-01") == 184


def test_uncensored_corpus_reports_no_missing_processos():
    rows = [(f"2025-{m:02d}", 3.0) for m in range(1, 13) for _ in range(50)]
    out = estimate_censoring(rows, "2026-01-01", "2025-01")
    assert out["estimated_missing"] == 0
    assert all(m["estimated_excluded_frac"] == 0.0 for m in out["months"])


def test_long_reference_durations_imply_late_months_are_censored():
    rows = [("2025-01", float(d)) for d in range(1, 366)]
    rows += [("2025-12", 5.0)] * 100
    out = estimate_censoring(rows, "2026-01-01", "2025-01")
    dec = [m for m in out["months"] if m["month"] == "2025-12"][0]
    assert dec["estimated_excluded_frac"] > 0.8, (
        "with a reference distribution spanning the year, a December birth can only be "
        "observed if it concludes within 31 days"
    )
    assert dec["estimated_true_n"] > dec["observed"]


def test_missing_reference_month_raises_rather_than_guessing():
    with pytest.raises(RuntimeError):
        estimate_censoring([("2025-06", 10.0)], "2026-01-01", "2025-01")


def test_estimate_is_reported_as_a_lower_bound_total():
    rows = [("2025-01", float(d)) for d in range(1, 300)]
    rows += [("2025-11", 5.0)] * 60
    out = estimate_censoring(rows, "2026-01-01", "2025-01")
    assert out["estimated_true_total"] >= out["observed_total"]
    assert 0.0 <= out["estimated_missing_frac"] < 1.0
