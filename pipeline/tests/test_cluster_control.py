from __future__ import annotations

import json
from collections import Counter

from pipeline.stages.cluster_control import shuffle_labels


def test_shuffle_preserves_the_size_distribution_exactly():
    labels = {f"P{i}": (i % 5) - 1 for i in range(200)}
    out = shuffle_labels(labels, seed=7)
    assert Counter(out.values()) == Counter(labels.values())
    assert set(out) == set(labels)
    assert out != labels


def test_shuffle_is_deterministic():
    labels = {f"P{i}": i % 9 for i in range(120)}
    assert shuffle_labels(labels, seed=42) == shuffle_labels(labels, seed=42)
    assert shuffle_labels(labels, seed=42) != shuffle_labels(labels, seed=43)


def test_shuffle_reassigns_most_processos():
    labels = {f"P{i}": i % 30 for i in range(900)}
    out = shuffle_labels(labels, seed=1)
    moved = sum(1 for p in labels if labels[p] != out[p])
    assert moved > 0.8 * len(labels)


def test_stage_is_registered():
    import pipeline.stages
    from ..core import registry
    assert "cluster-control" in registry.names()


def test_split_side_is_a_property_of_the_processo_not_of_the_list():
    from ..model.predict import random_split_field
    corpus = [(f"2025-01-{i % 28 + 1:02d}", [f"a{i}"], f"P{i:04d}") for i in range(400)]
    subset = corpus[:120]
    _, test_sub = random_split_field(subset, 2)
    train_all, _ = random_split_field(corpus, 2)
    assert not (set(test_sub) & set(train_all)), (
        "a processo held out for its cluster must never appear in the pooled training set, "
        "otherwise the global-model control is evaluated on its own training data"
    )


def test_split_is_roughly_the_requested_fraction():
    from ..model.predict import random_split_field
    corpus = [(f"2025-01-01", [f"a{i}"], f"P{i:05d}") for i in range(5000)]
    train, test = random_split_field(corpus, 2, train_frac=0.7)
    assert len(train) + len(test) == 5000
    assert 0.68 < len(train) / 5000 < 0.72


def test_split_is_deterministic_across_seeds():
    from ..model.predict import random_split_field
    corpus = [("2025-01-01", [f"a{i}"], f"P{i:04d}") for i in range(300)]
    a = random_split_field(corpus, 2, seed=42)
    assert a == random_split_field(corpus, 2, seed=42)
    assert a != random_split_field(corpus, 2, seed=7)
