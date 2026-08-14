
from __future__ import annotations

from ..model.doc_band import activity_band_score, band, doc_band_score, processo_band_score


def test_band_peaks_at_center_zero_at_edges():
    assert band(0.60) == 1.0
    assert band(0.40) == 0.0
    assert band(0.80) == 0.0
    assert band(0.90) == 0.0
    assert band(0.50) == 0.5
    assert band(None) == 0.0


def test_doc_band_score_median_and_empty():
    assert doc_band_score([0.6, 0.6]) == 1.0
    assert doc_band_score([0.4, 0.6]) == 0.5
    assert doc_band_score([]) is None
    assert doc_band_score([0.95]) == 0.0


def test_doc_band_score_mean_aggregation():
    assert doc_band_score([0.6, 0.5, 0.7], agg="mean") == round((1.0 + 0.5 + 0.5) / 3, 4)


def test_activity_band_score_skips_none():
    assert activity_band_score([0.5, None, 1.0]) == 0.75
    assert activity_band_score([None]) is None
    assert activity_band_score([]) is None


def test_processo_band_score_rank_weighted():
    assert processo_band_score([1.0, 0.0]) == round(3.0 / 4.5, 4)
    assert processo_band_score([]) is None
    assert processo_band_score([None, None]) is None


def test_processo_band_score_none_entries_do_not_consume_rank():
    expected = round((3.0 * 0.8 + 1.5 * 0.4) / 4.5, 4)
    assert processo_band_score([None, 0.8, 0.4]) == expected
