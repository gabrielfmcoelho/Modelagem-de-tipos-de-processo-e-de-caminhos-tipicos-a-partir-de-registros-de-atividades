from __future__ import annotations

from ..evidence.typical_path import paired_bootstrap as pb


def _arm(rate: float, n: int = 400, steps: int = 10):
    hits = round(rate * steps)
    return {f"p{i:04d}": (hits, steps) for i in range(n)}


def test_identical_arms_give_a_difference_interval_containing_zero():
    a = _arm(0.70)
    res = pb.paired_bootstrap(a, dict(a), n=400, seed=1)
    d = res["difference_b_minus_a"]
    assert d["point"] == 0.0
    assert d["ci95"][0] <= 0.0 <= d["ci95"][1]
    assert res["n_shared_processes"] == 400


def test_a_clearly_better_arm_gives_an_interval_excluding_zero():
    a, b = _arm(0.50), _arm(0.90)
    res = pb.paired_bootstrap(a, b, n=400, seed=1)
    d = res["difference_b_minus_a"]
    assert d["point"] > 0.35
    assert d["ci95"][0] > 0.0


def test_only_shared_protocolos_are_compared():
    a = _arm(0.70, n=100)
    b = _arm(0.70, n=100)
    b["extra-not-in-a"] = (10, 10)
    del a["p0000"]
    res = pb.paired_bootstrap(a, b, n=100, seed=1)
    assert res["n_shared_processes"] == 99


def test_per_process_reads_aligned_records_and_skips_empty_traces():
    cell = {
        "clusters": {
            "c1": {
                "test_protocolos": ["pA", "pB", "pC"],
                "models": {"gru": {"per_trace": [[3, 4, 5], [0, 1, 2], [0, 0, 0]]}},
            }
        }
    }
    top1 = pb.per_process(cell, "gru", 1)
    top3 = pb.per_process(cell, "gru", 3)
    assert top1 == {"pA": (3, 5), "pB": (0, 2)}
    assert top3 == {"pA": (4, 5), "pB": (1, 2)}


def test_misaligned_records_are_rejected_rather_than_silently_paired():
    cell = {
        "clusters": {
            "c1": {
                "test_protocolos": ["pA", "pB"],
                "models": {"gru": {"per_trace": [[1, 1, 2]]}},
            }
        }
    }
    try:
        pb.per_process(cell, "gru", 1)
    except SystemExit:
        return
    raise AssertionError("misaligned per-trace records must raise")
