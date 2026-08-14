
from __future__ import annotations

import numpy as np

from ..model.processo_features import ALGO_VERSION, TIPO_ACAO_DIM, BatchFeatures, BlockWeights, FeatureWeights, ProcessoInput, _bigram_tokens, _dedup_consecutive, build_batch_features, feature_hash, reduce_with_umap, semantic_embedding, tipo_acao_histogram, topic_embedding, unidade_bigram_text, unidade_unigram_text


def _proc(protocolo, docs=None, unidades=None, cronologia=None, acoes=None, topic_emb=None):
    return ProcessoInput(
        protocolo_formatado=protocolo,
        documentos=docs or [],
        unidades_visitadas=unidades or [],
        unidades_cronologicas=cronologia or [],
        atividades_tipo_acao=acoes or [],
        first_doc_topic_embedding=list(topic_emb) if topic_emb is not None else None,
    )


def _doc(numero, embedding, topic=None, summary=None):
    d = {"numero": numero, "embedding": list(embedding), "embedding_hash": f"h-{numero}"}
    if topic is not None:
        d["topic"] = topic
    if summary is not None:
        d["summary"] = summary
    return d


def test_semantic_first_doc_only_uses_first_doc():
    p = _proc("P1", docs=[
        _doc("d1", [1.0, 0.0]),
        _doc("d2", [0.0, 1.0]),
        _doc("d3", [0.0, 1.0]),
    ])
    fd = semantic_embedding(p)
    assert np.isclose(fd[0], 1.0) and np.isclose(fd[1], 0.0)
    mean = semantic_embedding(p, first_doc_only=False)
    assert mean[1] > 0.0


def test_first_doc_weighted_more_than_followups():
    p = _proc("P1", docs=[
        _doc("d1", [1.0, 0.0]),
        _doc("d2", [0.0, 1.0]),
        _doc("d3", [0.0, 1.0]),
        _doc("d4", [0.0, 1.0]),
    ])
    weighted = semantic_embedding(p, first_doc_only=False)
    unweighted = semantic_embedding(p, FeatureWeights(
        first_doc_weight=1.0, early_doc_weight=1.0, default_doc_weight=1.0,
    ), first_doc_only=False)
    assert weighted[0] > unweighted[0]


def test_single_doc_returns_normalized_embedding():
    p = _proc("P1", docs=[_doc("d1", [3.0, 4.0])])
    emb = semantic_embedding(p)
    assert np.isclose(emb[0], 0.6, atol=1e-6)
    assert np.isclose(emb[1], 0.8, atol=1e-6)


def test_no_docs_returns_empty_zero():
    p = _proc("P1", docs=[])
    emb = semantic_embedding(p)
    assert emb.size == 0


def test_doc_with_dim_mismatch_is_skipped():
    p = _proc("P1", docs=[
        _doc("d1", [1.0, 0.0]),
        _doc("d2", [1.0, 0.0, 0.0]),
    ])
    emb = semantic_embedding(p, first_doc_only=False)
    assert emb.shape == (2,)


def test_custom_weights_change_aggregation():
    p = _proc("P1", docs=[
        _doc("d1", [1.0, 0.0]),
        _doc("d2", [0.0, 1.0]),
    ])
    eq_w = FeatureWeights(first_doc_weight=1.0, early_doc_weight=1.0, default_doc_weight=1.0)
    biased = FeatureWeights(first_doc_weight=10.0, early_doc_weight=1.0, default_doc_weight=1.0)
    eq = semantic_embedding(p, eq_w, first_doc_only=False)
    bs = semantic_embedding(p, biased, first_doc_only=False)
    assert bs[0] > eq[0]


def test_topic_embedding_normalizes():
    p = _proc("P1", topic_emb=[3.0, 4.0])
    t = topic_embedding(p)
    assert np.isclose(t[0], 0.6, atol=1e-6) and np.isclose(t[1], 0.8, atol=1e-6)


def test_topic_embedding_absent_returns_empty():
    p = _proc("P1")
    assert topic_embedding(p).size == 0


def test_tipo_acao_histogram_normalizes_to_one():
    p = _proc("P1", acoes=["GERACAO-PROCEDIMENTO", "PROCESSO-RECEBIDO-UNIDADE",
                            "PROCESSO-RECEBIDO-UNIDADE", "GERACAO-DOCUMENTO"])
    h = tipo_acao_histogram(p)
    assert h.shape == (TIPO_ACAO_DIM,)
    assert np.isclose(h.sum(), 1.0)


def test_tipo_acao_unknown_falls_to_outros():
    p = _proc("P1", acoes=["TOTALMENTE-INVENTADO"])
    h = tipo_acao_histogram(p)
    assert np.isclose(h.sum(), 1.0)
    assert np.isclose(h[-1], 1.0)


def test_tipo_acao_empty_returns_zero_vector():
    p = _proc("P1", acoes=[])
    h = tipo_acao_histogram(p)
    assert h.sum() == 0.0


def test_unigram_text_dedupes_visited_units():
    p = _proc("P1", unidades=["A", "B", "A", "C"])
    txt = unidade_unigram_text(p)
    parts = txt.split()
    assert sorted(parts) == sorted(["A", "B", "C"])


def test_bigram_text_uses_chronological_dedup():
    p = _proc("P1", cronologia=["A", "A", "B", "B", "B", "C", "A"])
    txt = unidade_bigram_text(p)
    assert txt == "A__B B__C C__A"


def test_bigram_text_empty_when_no_transitions():
    p = _proc("P1", cronologia=["A", "A", "A"])
    assert unidade_bigram_text(p) == ""


def test_dedup_consecutive_helper():
    assert _dedup_consecutive(["A", "A", "B", "B", "B", "C"]) == ["A", "B", "C"]
    assert _dedup_consecutive([]) == []


def test_bigram_tokens_helper():
    assert _bigram_tokens(["A", "B", "C"]) == ["A__B", "B__C"]
    assert _bigram_tokens(["A"]) == []


def test_feature_hash_deterministic():
    p = _proc("P1",
              docs=[_doc("d1", [1.0])],
              unidades=["A", "B"],
              cronologia=["A", "B"],
              acoes=["GERACAO-PROCEDIMENTO"])
    h1 = feature_hash(p)
    h2 = feature_hash(p)
    assert h1 == h2


def test_feature_hash_changes_when_doc_changes():
    p1 = _proc("P1", docs=[_doc("d1", [1.0])])
    p2 = _proc("P1", docs=[_doc("d2", [1.0])])
    assert feature_hash(p1) != feature_hash(p2)


def test_feature_hash_changes_when_units_change():
    p1 = _proc("P1", unidades=["A"])
    p2 = _proc("P1", unidades=["A", "B"])
    assert feature_hash(p1) != feature_hash(p2)


def test_feature_hash_changes_when_weights_change():
    p = _proc("P1", docs=[_doc("d1", [1.0])])
    h1 = feature_hash(p, FeatureWeights(first_doc_weight=3.0))
    h2 = feature_hash(p, FeatureWeights(first_doc_weight=5.0))
    assert h1 != h2


def test_feature_hash_changes_when_any_block_weight_changes():
    p = _proc("P1", docs=[_doc("d1", [1.0])])
    base = feature_hash(p, block_weights=BlockWeights())
    for field in ("semantic", "topic", "unigram", "bigram", "tipo_acao", "keyword"):
        ablated = feature_hash(p, block_weights=BlockWeights(**{field: 0.0}))
        assert ablated != base, f"{field} is not covered by the feature stamp"


def test_feature_hash_is_unchanged_by_default_block_weights():
    p = _proc("P1", docs=[_doc("d1", [1.0])])
    assert feature_hash(p) == feature_hash(p, block_weights=BlockWeights())


def test_feature_hash_changes_when_algo_version_changes():
    p = _proc("P1", docs=[_doc("d1", [1.0])])
    h1 = feature_hash(p, algo_version="1.0")
    h2 = feature_hash(p, algo_version="2.0")
    assert h1 != h2


def test_feature_hash_independent_of_unit_order_unigram():
    p1 = _proc("P1", unidades=["A", "B", "C"])
    p2 = _proc("P1", unidades=["C", "B", "A"])
    assert feature_hash(p1) == feature_hash(p2)


def test_feature_hash_changes_when_first_doc_topic_changes():
    p1 = _proc("P1", docs=[_doc("d1", [1.0], topic="licitação", summary="s")])
    p2 = _proc("P1", docs=[_doc("d1", [1.0], topic="contrato", summary="s")])
    assert feature_hash(p1) != feature_hash(p2)


def test_feature_hash_changes_when_first_doc_only_flips():
    p = _proc("P1", docs=[_doc("d1", [1.0])])
    assert feature_hash(p, first_doc_only=True) != feature_hash(p, first_doc_only=False)


def test_feature_hash_changes_when_block_weights_change():
    p = _proc("P1", docs=[_doc("d1", [1.0])])
    h1 = feature_hash(p, block_weights=BlockWeights(topic=1.0))
    h2 = feature_hash(p, block_weights=BlockWeights(topic=0.0))
    assert h1 != h2


def _make_batch(n: int) -> list[ProcessoInput]:
    out: list[ProcessoInput] = []
    for i in range(n):
        out.append(_proc(
            f"P{i}",
            docs=[_doc(f"d-{i}-1", [1.0 if i % 2 == 0 else 0.0,
                                    0.0 if i % 2 == 0 else 1.0,
                                    0.5])],
            unidades=["UA", "UB"] if i % 2 == 0 else ["UC", "UD"],
            cronologia=["UA", "UB"] if i % 2 == 0 else ["UC", "UD"],
            acoes=["GERACAO-PROCEDIMENTO", "PROCESSO-RECEBIDO-UNIDADE"],
        ))
    return out


def test_build_batch_features_shape_consistency():
    procs = _make_batch(6)
    batch = build_batch_features(procs)
    assert isinstance(batch, BatchFeatures)
    assert batch.raw.shape[0] == 6
    expected_cols = (
        batch.semantic_dim + batch.topic_dim
        + batch.unigram_dim + batch.bigram_dim + batch.tipo_acao_dim
    )
    assert batch.raw.shape[1] == expected_cols


def test_build_batch_features_with_no_docs_works():
    procs = [_proc("P1", unidades=["A"], cronologia=["A"])]
    batch = build_batch_features(procs)
    assert batch.semantic_dim == 0
    assert batch.topic_dim == 0
    assert batch.raw.shape == (
        1, batch.semantic_dim + batch.topic_dim
        + batch.unigram_dim + batch.bigram_dim + batch.tipo_acao_dim
    )


def test_build_batch_features_includes_topic_block():
    procs = [
        _proc("P0", docs=[_doc("d0", [1.0, 0.0])], unidades=["UA"], cronologia=["UA"],
              acoes=["GERACAO-PROCEDIMENTO"], topic_emb=[1.0, 0.0, 0.0, 0.0]),
        _proc("P1", docs=[_doc("d1", [0.0, 1.0])], unidades=["UB"], cronologia=["UB"],
              acoes=["GERACAO-PROCEDIMENTO"], topic_emb=[0.0, 1.0, 0.0, 0.0]),
    ]
    batch = build_batch_features(procs)
    assert batch.semantic_dim == 2
    assert batch.topic_dim == 4
    assert batch.raw.shape[1] == (
        batch.semantic_dim + batch.topic_dim
        + batch.unigram_dim + batch.bigram_dim + batch.tipo_acao_dim
    )
    topic_cols = batch.raw[:, batch.semantic_dim:batch.semantic_dim + batch.topic_dim]
    assert np.any(topic_cols != 0.0)


def test_block_weights_zero_topic_zeroes_topic_columns():
    procs = [
        _proc("P0", docs=[_doc("d0", [1.0, 0.0])], unidades=["UA"], cronologia=["UA"],
              acoes=["GERACAO-PROCEDIMENTO"], topic_emb=[1.0, 0.0]),
        _proc("P1", docs=[_doc("d1", [0.0, 1.0])], unidades=["UB"], cronologia=["UB"],
              acoes=["GERACAO-PROCEDIMENTO"], topic_emb=[0.0, 1.0]),
    ]
    batch = build_batch_features(procs, block_weights=BlockWeights(topic=0.0))
    topic_cols = batch.raw[:, batch.semantic_dim:batch.semantic_dim + batch.topic_dim]
    assert batch.topic_dim == 2
    assert np.allclose(topic_cols, 0.0)


def test_reduce_with_umap_handles_tiny_batch():
    procs = _make_batch(6)
    batch = build_batch_features(procs)
    reduced = reduce_with_umap(batch, n_components=3, n_neighbors=3, random_state=42)
    assert reduced.shape == (6, 3)


def test_reduce_with_umap_empty_returns_empty():
    batch = BatchFeatures(protocolos=[], raw=np.zeros((0, 10), dtype=np.float32),
                          semantic_dim=0, unigram_dim=0, bigram_dim=0, tipo_acao_dim=10)
    reduced = reduce_with_umap(batch, n_components=5)
    assert reduced.shape == (0, 5)


def test_algo_version_constant_present():
    assert isinstance(ALGO_VERSION, str)
    assert len(ALGO_VERSION) > 0


def test_apply_cutoff_keeps_only_the_prefix_of_both_sequences():
    from ..model.processo_features import apply_cutoff
    events = [{"u": "U1", "ts": "2025-01-01"}, {"u": "U2", "ts": "2025-06-01"},
              {"u": "U3", "ts": "2025-12-01"}]
    acts = [{"t": "A", "ts": "2025-01-01"}, {"t": "B", "ts": "2025-06-01"},
            {"t": "C", "ts": "2025-12-01"}]
    ev, ac = apply_cutoff(events, acts, 0.5)
    assert [e["u"] for e in ev] == ["U1", "U2"]
    assert [a["t"] for a in ac] == ["A", "B"]


def test_apply_cutoff_is_identity_at_full_coverage():
    from ..model.processo_features import apply_cutoff
    events = [{"u": "U1", "ts": "2025-01-01"}, {"u": "U2", "ts": "2025-06-01"}]
    acts = [{"t": "A", "ts": "2025-01-01"}]
    ev, ac = apply_cutoff(events, acts, 1.0)
    assert ev is events and ac is acts


def test_apply_cutoff_survives_missing_timestamps():
    from ..model.processo_features import apply_cutoff
    ev, ac = apply_cutoff([{"u": "U1"}], [{"t": "A"}], 0.5)
    assert len(ev) == 1 and len(ac) == 1


def test_feature_hash_separates_cutoff_configurations():
    from ..model.processo_features import feature_hash
    p = _proc("00002.000001/2025-11", unidades=["U1", "U2"], acoes=["A", "B"])
    full = feature_hash(p)
    assert feature_hash(p, cutoff_frac=1.0) == full
    assert feature_hash(p, cutoff_frac=0.5) != full
    assert feature_hash(p, cutoff_frac=0.5) != feature_hash(p, cutoff_frac=0.7)
