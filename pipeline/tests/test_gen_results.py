import json

from pipeline.evidence.results import results_doc as gr

FIG = {
  "model_count": {"cells": 40, "clusters_evaluated": 1000, "models_trained": 5000},
  "cluster_counts": {"exp-anon/hdbscan": {"n_processos": 5243, "n_clusters": 62, "noise": 800,
                                          "singletons": 0, "median_size": 40, "above_30": 50}},
  "model_vs_medoid": {"unit": {"n_clusters": 800,
      "medoid": {"within_25": 0.31, "unit_recall": 0.78, "unit_precision": 0.76,
                 "transition_support_mean": 0.73, "transitions_unseen": 1.88},
      "markov": {"within_25": 0.28, "unit_recall": 0.70, "unit_precision": 0.77,
                 "transition_support_mean": 0.66, "transitions_unseen": 3.53},
      "gru": {}, "lstm": {}, "transformer": {}, "dfg": {}}},
  "controls": {"unit": {"clustered_best_top1": 0.70, "successor_baseline": 0.63,
                        "global_model": 0.68, "lift_over_successor": 0.07,
                        "lift_over_global_model": 0.02, "shuffled_best_top1": 0.66,
                        "shuffled_successor": 0.62, "shuffled_lift_over_successor": 0.04}},
  "by_size_band": {"unit": {"large": {"n_clusters": 20, "top1": 0.74, "successor": 0.65,
                                      "global_model": 0.70, "lift_over_successor": 0.09,
                                      "lift_over_global": 0.04, "within_25": 0.37,
                                      "unit_recall": 0.8, "transitions_unseen": 1.91}}},
  "dispersion": {"unit": {"dispersion": 0.15, "dispersion_proc": 0.15, "dispersion_itin": 0.07,
                          "medoid_distance": 0.08, "medoid_distance_itin": 0.04}},
  "coverage": [{"cell": "exp-anon/hdbscan", "alphabet": "unit", "clusters_evaluated": 50,
                "clusters_total": 62, "processos_evaluated": 4000, "processos_total": 5243,
                "noise": 800}],
}


def test_every_block_renders_without_error():
    for name, fn in gr.BLOCKS.items():
        assert isinstance(fn(FIG), str) and fn(FIG).strip()


def test_render_replaces_only_inside_markers():
    doc = "prose before\n\n<!-- fig:scale -->\nSTALE\n<!-- /fig:scale -->\n\nprose after\n"
    out, filled = gr.render(doc, FIG)
    assert filled == ["scale"]
    assert "STALE" not in out
    assert "prose before" in out and "prose after" in out
    assert "5,000 sequence models trained" in out


def test_render_is_idempotent():
    doc = "<!-- fig:scale -->\nx\n<!-- /fig:scale -->\n"
    once, _ = gr.render(doc, FIG)
    twice, _ = gr.render(once, FIG)
    assert once == twice


def test_medoid_winner_is_computed_not_assumed():
    out = gr.fig_model_vs_medoid(FIG)
    assert "within_25: **medoid**" in out
    assert "unit_precision: **markov**" in out
    assert "transitions_unseen: **medoid**" in out


def test_missing_markers_are_reported_not_silently_skipped():
    doc = "<!-- fig:scale -->\nx\n<!-- /fig:scale -->\n"
    _, filled = gr.render(doc, FIG)
    assert set(gr.BLOCKS) - set(filled)


def test_render_fills_an_empty_marker_pair():
    doc = "<!-- fig:scale -->\n<!-- /fig:scale -->\n"
    out, filled = gr.render(doc, FIG)
    assert filled == ["scale"], "adjacent markers with no body must still be filled"
    assert "5,000 sequence models trained" in out


def test_render_of_an_empty_pair_is_idempotent():
    doc = "<!-- fig:scale -->\n<!-- /fig:scale -->\n"
    once, _ = gr.render(doc, FIG)
    assert gr.render(once, FIG)[0] == once


def test_check_fails_when_markers_are_absent(tmp_path, capsys, monkeypatch):
    figures = tmp_path / "f.json"
    figures.write_text(json.dumps(FIG), encoding="utf-8")
    doc = tmp_path / "d.md"
    doc.write_text("no markers at all\n", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["gen_results.py", "--check",
                                     "--figures", str(figures), "--doc", str(doc)])
    assert gr.main() == 1, "a check that finds no markers must fail, not pass vacuously"


def test_no_block_ever_renders_empty_on_missing_data():
    for name, fn in gr.BLOCKS.items():
        out = fn({})
        assert out and out.strip(), f"block {name} rendered empty for missing data"
