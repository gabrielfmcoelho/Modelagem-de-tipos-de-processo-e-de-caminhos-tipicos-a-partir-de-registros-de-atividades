import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("ab", "pipeline/stages/ablation.py")


def _mod():
    import sys
    sys.path.insert(0, ".")
    import pipeline.stages.ablation as m
    return m


def test_identical_partitions_score_one():
    m = _mod()
    ref = {f"P{i}": i % 5 for i in range(100)}
    r = m.compare_partitions(ref, dict(ref))
    assert r["ari"] == 1.0 and r["nmi"] == 1.0
    assert r["n_compared"] == 100


def test_relabeling_alone_still_scores_one():
    m = _mod()
    ref = {f"P{i}": i % 5 for i in range(500)}
    cut = {f"P{i}": (i * 7 + 3) % 5 for i in range(500)}
    assert m.compare_partitions(ref, cut)["ari"] == 1.0


def test_shuffled_membership_scores_near_zero():
    import random
    m = _mod()
    ref = {f"P{i}": i % 5 for i in range(500)}
    vals = list(ref.values())
    random.Random(0).shuffle(vals)
    cut = dict(zip(sorted(ref), vals))
    assert m.compare_partitions(ref, cut)["ari"] < 0.1


def test_disjoint_processos_raise_rather_than_report_a_bogus_score():
    m = _mod()
    import pytest
    with pytest.raises(RuntimeError):
        m.compare_partitions({"A": 1}, {"B": 1})


def test_only_shared_processos_are_compared():
    m = _mod()
    ref = {f"P{i}": 0 for i in range(10)}
    cut = {f"P{i}": 0 for i in range(5)}
    assert m.compare_partitions(ref, cut)["n_compared"] == 5


def test_noise_is_excluded_from_the_cluster_count():
    m = _mod()
    ref = {"A": -1, "B": 0, "C": 1}
    r = m.compare_partitions(ref, dict(ref))
    assert r["n_clusters_reference"] == 2 and r["noise_reference"] == 1


def test_default_variants_cover_both_ablations_the_reviewers_asked_for():
    m = _mod()
    names = [v.split(":")[0] for v in m.DEFAULT_VARIANTS]
    assert "nokeyword" in names and "notopic" in names
    assert sum(1 for n in names if n.startswith("cut")) == 3
    for v in m.DEFAULT_VARIANTS:
        name, _, spec = v.partition(":")
        assert name and "=" in spec


def test_ablation_does_not_shell_out_to_the_pipeline_cli():
    from pathlib import Path
    src = Path("pipeline/stages/ablation.py").read_text(encoding="utf-8")
    assert "subprocess" not in src, (
        "spawning `pipeline run` from inside a stage deadlocks on the run lock the parent "
        "already holds; sub-stages must be called in-process"
    )
    assert "_substage(" in src
