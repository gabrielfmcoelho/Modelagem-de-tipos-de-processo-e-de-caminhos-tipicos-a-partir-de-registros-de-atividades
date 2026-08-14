import pytest

from ..model.cluster_catalog import aggregate_catalog


def test_aggregate_catalog_basic():
    labels = {
        "p1": {"macro": "r|macro|1", "micro": "r|micro|1|1"},
        "p2": {"macro": "r|macro|1", "micro": "r|micro|1|1"},
        "p3": {"macro": "r|macro|1", "micro": "r|micro|1|2"},
        "p4": {"macro": "r|macro|2", "micro": None},
        "p5": {"macro": -1, "micro": None},
    }
    attrs = {
        "p1": {"open_units": 0, "tipo": "Pagamento"},
        "p2": {"open_units": 2, "tipo": "Pagamento"},
        "p3": {"open_units": 0, "tipo": "Ferias"},
        "p4": {"open_units": 0, "tipo": "Pagamento"},
    }
    cat = aggregate_catalog(labels, attrs)
    assert set(cat) == {"r|macro|1", "r|macro|2"}
    assert cat["r|macro|1"] == {"n": 3, "concl": 2, "micro": 2,
                                "tipos": [{"tipo": "Pagamento", "n": 2}, {"tipo": "Ferias", "n": 1}]}
    assert cat["r|macro|2"]["n"] == 1
    assert cat["r|macro|2"]["micro"] == 0
    assert cat["r|macro|2"]["concl"] == 1


def test_aggregate_catalog_missing_attrs_default_open():
    labels = {"a": {"macro": "m|1", "micro": None}}
    cat = aggregate_catalog(labels, {})
    assert cat["m|1"] == {"n": 1, "concl": 0, "micro": 0, "tipos": []}


def test_coassociation_inner_product_is_the_agreement_rate():
    import numpy as np

    from ..model.clustering.consensus.consensus_model import coassociation, onehot

    algos = ["a", "b", "c"]
    protos = ["p0", "p1", "p2", "p3"]
    lm = {"a": {"p0": 1, "p1": 1, "p2": 2, "p3": -1},
          "b": {"p0": 5, "p1": 5, "p2": 7, "p3": -1},
          "c": {"p0": -1, "p1": 3, "p2": 3, "p3": -1}}
    x, _ = coassociation(lm, algos, protos)
    raw = np.hstack([onehot(lm[a], protos) for a in algos])
    for i in range(len(protos)):
        for j in range(len(protos)):
            assert float(x[i] @ x[j]) == pytest.approx(float(raw[i] @ raw[j]) / len(algos)), (
                "the co-association embedding must satisfy the property the method is named "
                "for: the inner product of two rows is the fraction of algorithms that put the "
                "two cases together. Row-wise L2 normalisation breaks this whenever one case is "
                "noise somewhere, inflating its similarity by sqrt(n/(n-1)).")


def test_a_case_that_is_noise_everywhere_has_no_similarity_to_anything():
    from ..model.clustering.consensus.consensus_model import coassociation

    algos = ["a", "b"]
    protos = ["p0", "p1"]
    lm = {"a": {"p0": 1, "p1": -1}, "b": {"p0": 2, "p1": -1}}
    x, _ = coassociation(lm, algos, protos)
    assert float(x[1] @ x[1]) == 0.0
    assert float(x[0] @ x[1]) == 0.0
