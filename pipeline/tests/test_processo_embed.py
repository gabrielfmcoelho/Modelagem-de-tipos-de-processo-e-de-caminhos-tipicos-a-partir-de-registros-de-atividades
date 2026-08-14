
from __future__ import annotations

import numpy as np
import pytest

from ..model import processo_features as pf
from pipeline.stages import processo_embed as pe


class _FakeEmbedder:
    model_name = "fake"
    dimension = 3

    def embed_batch(self, texts):
        return [[float(len(t)), 0.0, 0.0] for t in texts]


def _proc(proto, docs):
    return pf.ProcessoInput(
        protocolo_formatado=proto,
        documentos=docs,
        unidades_visitadas=[],
        unidades_cronologicas=[],
        atividades_tipo_acao=[],
    )


def test_attach_first_doc_topic_embeddings(monkeypatch, tmp_path):
    monkeypatch.setattr(pe, "build_embedder", lambda settings=None, **k: _FakeEmbedder())
    pending = [
        _proc("P0", [{"numero": "d0", "embedding": [1.0], "topic": "licitação", "summary": "x"}]),
        _proc("P1", [{"numero": "d1", "embedding": [1.0]}]),
    ]
    n = pe._attach_first_doc_topic_embeddings(pending, None, tmp_path / "tc.npz")
    assert n == 1
    assert pending[0].first_doc_topic_embedding is not None
    assert len(pending[0].first_doc_topic_embedding) == 3
    assert pending[1].first_doc_topic_embedding is None


def test_attach_topic_embeddings_uses_first_doc_only(monkeypatch, tmp_path):
    captured = {}

    class _Capture(_FakeEmbedder):
        def embed_batch(self, texts):
            captured["texts"] = list(texts)
            return super().embed_batch(texts)

    monkeypatch.setattr(pe, "build_embedder", lambda settings=None, **k: _Capture())
    pending = [_proc("P0", [
        {"numero": "d0", "embedding": [1.0], "topic": "primeiro", "summary": "abre"},
        {"numero": "d1", "embedding": [1.0], "topic": "segundo", "summary": "depois"},
    ])]
    pe._attach_first_doc_topic_embeddings(pending, None, tmp_path / "tc.npz")
    assert captured["texts"] == ["primeiro. abre"]


def test_attach_topic_embeddings_handles_embedder_failure(monkeypatch, tmp_path):
    def _boom(settings=None, **k):
        raise RuntimeError("no embedder")

    monkeypatch.setattr(pe, "build_embedder", _boom)
    pending = [_proc("P0", [{"numero": "d0", "embedding": [1.0], "topic": "t", "summary": "s"}])]
    n = pe._attach_first_doc_topic_embeddings(pending, None, tmp_path / "tc.npz")
    assert n == 0
    assert pending[0].first_doc_topic_embedding is None


def test_export_features_npz_matches_freeze_schema(tmp_path):
    path = tmp_path / "sub" / "exp.npz"
    features = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]], dtype=np.float64)
    pe._export_features_npz(path, ["P0", "P1"], features, digest="abc123", text_variant="raw")
    data = np.load(path)
    assert sorted(data.files) == ["digest", "features", "protocolos", "text_variant"]
    assert str(data["digest"]) == "abc123"
    assert str(data["text_variant"]) == "raw"
    assert data["protocolos"].dtype.kind == "U"
    assert list(data["protocolos"]) == ["P0", "P1"]
    assert data["features"].dtype == np.float32
    assert data["features"].shape == (2, 3)
    np.testing.assert_allclose(data["features"], features, rtol=1e-6)


def test_stage_reads_exactly_the_keys_the_clustering_query_returns():
    from pathlib import Path

    from ..core.cypher import LIST_PROCESSOS_FOR_CLUSTERING_CYPHER as query
    from pipeline.stages import processo_embed as stage

    src = Path(stage.__file__).read_text(encoding="utf-8")
    for key in ("atividades_raw", "unidade_events_raw", "unidades_visitadas",
                "documentos_raw", "cluster_features_hash"):
        assert f"AS {key}" in query, f"{key} not returned by the clustering query"
        assert f'"{key}"' in src, f"{key} not read by the processo-embed stage"


def test_clustering_query_carries_timestamps_for_the_cutoff():
    from ..core.cypher import LIST_PROCESSOS_FOR_CLUSTERING_CYPHER as query
    assert "a.data_hora" in query
    assert "ts: a2.data_hora" in query


def test_clustering_query_is_defined_once():
    from pathlib import Path

    from ..core import cypher

    pkg = Path(cypher.__file__).parent
    total = sum(p.read_text(encoding="utf-8").count("\nLIST_PROCESSOS_FOR_CLUSTERING_CYPHER = ")
                for p in pkg.glob("*.py"))
    assert total == 1


def test_embedded_documentos_keeps_only_docs_with_embeddings_in_first_seen_order():
    docs = [
        {"numero": "d2", "embedding": [1.0], "first_seen": "2025-03-01"},
        {"numero": "d0", "embedding": None, "first_seen": "2025-01-01"},
        {"numero": "d1", "embedding": [2.0], "first_seen": "2025-02-01"},
    ]
    out = pe._embedded_documentos(docs)
    assert [d["numero"] for d in out] == ["d1", "d2"]


def test_processo_without_any_embedded_document_yields_empty_corpus_entry():
    assert pe._embedded_documentos([]) == []
    assert pe._embedded_documentos([{"numero": "d0", "embedding": None}]) == []


def test_every_cluster_feature_property_written_is_also_cleared():
    import re

    from ..core.cypher import CLEAR_PROCESSO_CLUSTER_FEATURES_CYPHER as clear
    from ..core.cypher import LOAD_PROCESSO_CLUSTER_FEATURES_CYPHER as load

    written = set(re.findall(r"p\.(cluster_features\w*)\s*=", load))
    removed = set(re.findall(r"p\.(cluster_features\w*)", clear))
    assert written, "load template sets no cluster_features properties"
    assert written <= removed, f"not cleared on discard: {sorted(written - removed)}"


def test_stage_discards_processos_without_documents_and_clears_their_features():
    from pathlib import Path

    from pipeline.stages import processo_embed as stage

    src = Path(stage.__file__).read_text(encoding="utf-8")
    assert "sem_documento.append(pf)" in src
    assert "CLEAR_PROCESSO_CLUSTER_FEATURES_CYPHER" in src
    assert "discarded_sem_documento" in src


def test_feature_digest_is_order_independent_and_content_sensitive():
    pairs = [("P1", "h1"), ("P2", "h2")]
    assert pe.feature_digest(pairs) == pe.feature_digest(reversed(pairs))
    assert pe.feature_digest(pairs) != pe.feature_digest([("P1", "h1"), ("P2", "hX")])
    assert pe.feature_digest(pairs) != pe.feature_digest([("P1", "h1")])


def test_resolve_text_variant_prefers_explicit_then_embed_state(tmp_path):
    import json
    assert pe.resolve_text_variant("anon") == "anon"
    (tmp_path / "embed.json").write_text(json.dumps({"args": {"text_variant": "raw"}}))
    assert pe.resolve_text_variant(None, tmp_path) == "raw"
    assert pe.resolve_text_variant(None, tmp_path / "nope") == "unknown"


def test_cluster_eval_rejects_features_built_from_the_other_arm(tmp_path):
    import numpy as np

    from pipeline.stages.cluster_eval import _ARM_VARIANT, _load_features_from_npz

    path = tmp_path / "f.npz"
    pe._export_features_npz(path, ["P0", "P1"], np.zeros((2, 3)),
                            digest="d", text_variant="anon")
    _, _, stamp = _load_features_from_npz(str(path))
    assert stamp["text_variant"] == "anon"
    assert _ARM_VARIANT["exp-raw"] == "raw" and _ARM_VARIANT["exp-anon"] == "anon"
    assert stamp["text_variant"] != _ARM_VARIANT["exp-raw"]


def test_topic_cache_round_trips_and_is_keyed_by_model_and_text(tmp_path):
    path = tmp_path / "tc.npz"
    assert pe.load_topic_cache(path) == {}
    cache = {pe.topic_key("abc", "m1"): [0.1, 0.2], pe.topic_key("abc", "m2"): [0.3, 0.4]}
    assert len(cache) == 2
    pe.save_topic_cache(cache, path)
    back = pe.load_topic_cache(path)
    assert set(back) == set(cache)
    assert back[pe.topic_key("abc", "m1")] == pytest.approx([0.1, 0.2])


def test_topic_embeddings_are_cached_so_a_second_run_calls_no_api(tmp_path, monkeypatch):
    calls = []

    class _Counting(_FakeEmbedder):
        def embed_batch(self, texts):
            calls.append(list(texts))
            return super().embed_batch(texts)

    monkeypatch.setattr(pe, "build_embedder", lambda settings=None, **k: _Counting())
    path = tmp_path / "tc.npz"
    mk = lambda: [_proc("P0", [{"numero": "d", "embedding": [1.0], "topic": "t", "summary": "s"}])]

    first = mk()
    assert pe._attach_first_doc_topic_embeddings(first, None, path) == 1
    assert len(calls) == 1

    second = mk()
    assert pe._attach_first_doc_topic_embeddings(second, None, path) == 1
    assert len(calls) == 1, "second run must hit the cache, not the API"
    assert second[0].first_doc_topic_embedding == first[0].first_doc_topic_embedding


def test_topic_embeddings_use_fixed_size_batches():
    from pathlib import Path
    src = Path("pipeline/stages/processo_embed.py").read_text(encoding="utf-8")
    assert "TOPIC_BATCH" in src
    assert "range(0, len(missing), TOPIC_BATCH)" in src


def test_processo_cluster_also_refuses_ambient_features_for_an_arm():
    from pathlib import Path
    src = Path("pipeline/stages/processo_cluster.py").read_text(encoding="utf-8")
    assert "names the {arm!r} arm" in src
    assert "Refusing to produce a mislabelled catalog" in src
    assert "_load_features_from_npz" in src


def test_naming_does_not_use_the_declared_sei_type():
    from pathlib import Path

    from ..model.clustering import NAMING_SYSTEM_PROMPT, _format_sample

    assert "tipo_procedimento" not in NAMING_SYSTEM_PROMPT
    assert "tipo SEI" not in NAMING_SYSTEM_PROMPT
    assert "NÃO use a classificação oficial do SEI" in NAMING_SYSTEM_PROMPT
    rendered = _format_sample({"protocolo": "P1", "tipo_procedimento": "Documento Oficial",
                               "topic": "t", "summary": "s"})
    assert "Documento Oficial" not in rendered
    assert "tipo SEI" not in rendered
    src = Path("pipeline/model/clustering/naming.py").read_text(encoding="utf-8")
    assert "tipo SEI: {p['tipo_procedimento']}" not in src


def test_processo_cluster_exports_catalog_artifacts_itself():
    from pathlib import Path
    src = Path("pipeline/stages/processo_cluster.py").read_text(encoding="utf-8")
    assert "_export_catalog_artifacts(driver, run_id" in src
    assert "cluster_catalog.json" in src and "names.json" in src
    assert "catalog_artifacts" in src


def test_doc_embedding_cache_round_trips(tmp_path):
    from pipeline.stages import embed as em
    path = tmp_path / "dc.npz"
    assert em.load_doc_cache(path) == {}
    cache = {em._hash_for("abc", "m"): [0.1, 0.2, 0.3]}
    em.save_doc_cache(cache, path)
    back = em.load_doc_cache(path)
    assert set(back) == set(cache)
    assert back[em._hash_for("abc", "m")] == pytest.approx([0.1, 0.2, 0.3])


def test_doc_hash_is_model_and_text_scoped():
    from pipeline.stages import embed as em
    assert em._hash_for("a", "m1") != em._hash_for("a", "m2")
    assert em._hash_for("a", "m1") != em._hash_for("b", "m1")
    assert em._hash_for("a", "m1") == em._hash_for("a", "m1")


def test_embed_serves_pending_docs_from_the_disk_cache():
    from pathlib import Path
    src = Path("pipeline/stages/embed.py").read_text(encoding="utf-8")
    assert "load_doc_cache()" in src
    assert "h not in doc_cache" in src
    assert "vectors = [doc_cache[h] for _, _, h in batch]" in src
    assert "save_doc_cache(doc_cache)" in src
