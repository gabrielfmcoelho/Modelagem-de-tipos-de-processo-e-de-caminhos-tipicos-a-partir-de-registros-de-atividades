
from __future__ import annotations

import json

import numpy as np
import pytest

from ..model.clustering import NOISE_LABEL, ClusterResult, _disambiguate_names, _format_sample, build_catalog, category_id, cluster_macro, cluster_micro_within, compute_dbcv, dedupe_macro_labels, fit, name_all_clusters, name_cluster


def test_fit_hdbscan_finds_multiple_clusters():
    _, feat = _three_clusters_synthetic()
    res = fit(feat, "hdbscan", min_cluster_size=10)
    assert isinstance(res, ClusterResult)
    assert res.algo == "hdbscan"
    assert len(set(int(x) for x in res.labels) - {NOISE_LABEL}) >= 2


def test_fit_kmeans_k3_is_three_clusters_and_deterministic():
    _, feat = _three_clusters_synthetic()
    r1 = fit(feat, "kmeans", k=3)
    r2 = fit(feat, "kmeans", k=3)
    assert len(set(int(x) for x in r1.labels)) == 3
    assert (r1.labels == r2.labels).all()
    assert (r1.strengths == 1.0).all()


def test_fit_kmeans_requires_explicit_k():
    _, feat = _three_clusters_synthetic()
    with pytest.raises(ValueError):
        fit(feat, "kmeans")


def test_fit_leiden_finds_clusters_and_is_deterministic():
    pytest.importorskip("igraph")
    pytest.importorskip("leidenalg")
    _, feat = _three_clusters_synthetic()
    r1 = fit(feat, "leiden")
    r2 = fit(feat, "leiden")
    assert len(set(int(x) for x in r1.labels) - {NOISE_LABEL}) >= 2
    assert (r1.labels == r2.labels).all()


def test_fit_unknown_algo_raises_listing_available():
    _, feat = _three_clusters_synthetic()
    with pytest.raises(ValueError, match="hdbscan"):
        fit(feat, "does-not-exist")


def _three_clusters_synthetic(rng_seed: int = 0) -> tuple[list[str], np.ndarray]:
    rng = np.random.default_rng(rng_seed)
    a = rng.normal(loc=[0, 0], scale=0.05, size=(20, 2))
    b = rng.normal(loc=[5, 0], scale=0.05, size=(20, 2))
    c = rng.normal(loc=[0, 5], scale=0.05, size=(20, 2))
    feat = np.vstack([a, b, c]).astype(np.float32)
    pf = [f"P{i}" for i in range(60)]
    return pf, feat


def test_macro_finds_three_separable_clusters():
    _, feat = _three_clusters_synthetic()
    labels, strengths = cluster_macro(feat, min_cluster_size=10)
    unique = set(int(x) for x in labels) - {NOISE_LABEL}
    assert len(unique) == 3
    assert (strengths > 0).sum() >= 50


def test_dbcv_positive_for_well_separated_clusters():
    _, feat = _three_clusters_synthetic()
    labels, _ = cluster_macro(feat, min_cluster_size=10)
    score = compute_dbcv(feat, labels)
    assert score is not None
    assert -1.0 <= score <= 1.0
    assert score > 0.0


def test_dbcv_none_when_fewer_than_two_clusters():
    feat = np.random.default_rng(0).normal(scale=0.05, size=(30, 2)).astype(np.float64)
    labels = np.zeros(30, dtype=int)
    assert compute_dbcv(feat, labels) is None


def test_dedupe_merges_overlapping_clusters_keeps_separated_ones():
    rng = np.random.default_rng(0)
    a = rng.normal(loc=[1, 1], scale=0.01, size=(30, 2))
    b = rng.normal(loc=[1, 1], scale=0.01, size=(20, 2))
    c = rng.normal(loc=[5, 5], scale=0.01, size=(15, 2))
    feat = np.vstack([a, b, c]).astype(np.float64)
    macro = np.array([0] * 30 + [1] * 20 + [2] * 15)
    out = dedupe_macro_labels(feat, macro, threshold=1.0)
    assert len(set(int(x) for x in out)) == 2
    assert (out == 0).sum() == 50
    assert (out == 2).sum() == 15


def test_disambiguate_names_handles_shared_marcador():
    out = {
        "a": {"nome": "Adesão", "marcadores": ["Licitação: Consulta"]},
        "b": {"nome": "Adesão", "marcadores": ["Licitação: Consulta"]},
        "c": {"nome": "Adesão", "marcadores": ["Licitação: Consulta"]},
    }
    _disambiguate_names(out, ["a", "b", "c"])
    names = [out[k]["nome"] for k in ("a", "b", "c")]
    assert len(set(names)) == 3
    assert out["a"]["nome"] == "Adesão"


def test_dedupe_threshold_zero_is_noop():
    feat = np.random.default_rng(0).normal(size=(20, 2)).astype(np.float64)
    macro = np.array([0] * 10 + [1] * 10)
    out = dedupe_macro_labels(feat, macro, threshold=0.0)
    assert (out == macro).all()


def test_dedupe_preserves_noise_label():
    feat = np.random.default_rng(0).normal(size=(12, 2)).astype(np.float64)
    macro = np.array([0] * 5 + [1] * 5 + [NOISE_LABEL] * 2)
    out = dedupe_macro_labels(feat, macro, threshold=0.99)
    assert (out[-2:] == NOISE_LABEL).all()


def test_macro_marks_isolated_points_as_noise():
    rng = np.random.default_rng(0)
    cluster = rng.normal(loc=[0, 0], scale=0.05, size=(20, 2))
    isolated = np.array([[10.0, 10.0]])
    feat = np.vstack([cluster, isolated]).astype(np.float32)
    labels, _ = cluster_macro(feat, min_cluster_size=10)
    assert labels[-1] == NOISE_LABEL


def test_macro_handles_too_few_points():
    feat = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
    labels, strengths = cluster_macro(feat, min_cluster_size=10)
    assert (labels == NOISE_LABEL).all()
    assert (strengths == 0).all()


def test_micro_rescues_outlier_subgroups_into_named_clusters():
    rng = np.random.default_rng(0)
    grp_a = rng.normal(loc=[0, 0], scale=0.1, size=(5, 2))
    grp_b = rng.normal(loc=[10, 10], scale=0.1, size=(5, 2))
    grp_c = rng.normal(loc=[-10, 10], scale=0.1, size=(5, 2))
    feat = np.vstack([grp_a, grp_b, grp_c]).astype(np.float32)

    macro_labels = np.full(15, NOISE_LABEL, dtype=int)

    micro_labels, _, reclassificada = cluster_micro_within(
        feat, macro_labels, min_cluster_size=3,
    )
    found_clusters = set(int(x) for x in micro_labels) - {NOISE_LABEL}
    assert len(found_clusters) >= 2
    for i in range(15):
        if micro_labels[i] != NOISE_LABEL:
            assert reclassificada[i] is np.True_ or bool(reclassificada[i])


def test_micro_does_not_mark_macro_members_as_reclassificada():
    rng = np.random.default_rng(0)
    feat = rng.normal(loc=[0, 0], scale=0.3, size=(30, 2)).astype(np.float32)
    macro_labels = np.zeros(30, dtype=int)

    _, _, reclassificada = cluster_micro_within(feat, macro_labels, min_cluster_size=3)
    assert not reclassificada.any()


def test_build_catalog_groups_assignments_correctly():
    pf, feat = _three_clusters_synthetic()
    macro_labels, macro_str = cluster_macro(feat, min_cluster_size=10)
    micro_labels, micro_str, reclass = cluster_micro_within(
        feat, macro_labels, min_cluster_size=5,
    )
    catalog = build_catalog(
        run_id="test-run",
        protocolos=pf,
        features=feat,
        macro_labels=macro_labels,
        macro_strengths=macro_str,
        micro_labels=micro_labels,
        micro_strengths=micro_str,
        reclassificada=reclass,
    )
    assert catalog.run_id == "test-run"
    assert len(catalog.assignments) == len(pf)
    assert len(catalog.macro_clusters) == 3
    assert catalog.macro_clusters[0].centroid.shape == (2,)
    desc = catalog.macro_clusters[0]
    member_strengths = [macro_str[i] for i in desc.sample_ranks]
    assert member_strengths == sorted(member_strengths, reverse=True)


def test_catalog_skips_noise_clusters():
    pf = [f"P{i}" for i in range(5)]
    feat = np.array([[0, 0]] * 5, dtype=np.float32)
    macro_labels = np.array([0, 0, 0, 0, NOISE_LABEL], dtype=int)
    macro_str = np.array([0.9, 0.9, 0.9, 0.9, 0.0])
    micro_labels = np.array([NOISE_LABEL] * 5, dtype=int)
    micro_str = np.zeros(5)
    reclass = np.zeros(5, dtype=bool)

    catalog = build_catalog("r", pf, feat, macro_labels, macro_str,
                             micro_labels, micro_str, reclass)
    assert len(catalog.macro_clusters) == 1
    assert catalog.macro_clusters[0].macro_label == 0


def _stub_llm_returning(payload: dict):
    raw = json.dumps(payload)
    return lambda messages: raw


def test_format_sample_uses_content_and_never_the_declared_sei_type():
    s = {"protocolo": "P1", "tipo_procedimento": "Licitação: Pregão Eletrônico",
         "topic": "Aquisição de material de informática",
         "summary": "Pedido de compra de notebooks.",
         "top_unidades": ["SEAD-PI/SLC"], "top_tipos_acao": ["GERACAO-DOCUMENTO"]}
    out = _format_sample(s)
    assert "tipo SEI" not in out
    assert "Licitação: Pregão Eletrônico" not in out
    assert "Aquisição de material de informática" in out
    assert "Pedido de compra de notebooks." in out


def test_format_sample_falls_back_to_resumo_key():
    out = _format_sample({"protocolo": "P1", "resumo": "texto antigo"})
    assert "texto antigo" in out


def test_disambiguate_names_breaks_collisions():
    out = {
        "a": {"nome": "Solicitação de Pessoal", "marcadores": ["contratação", "estágio"]},
        "b": {"nome": "Solicitação de Pessoal", "marcadores": ["diárias", "viagem"]},
        "c": {"nome": "Licitação", "marcadores": []},
    }
    _disambiguate_names(out, ["a", "b", "c"])
    names = {out[k]["nome"] for k in out}
    assert len(names) == 3
    assert out["a"]["nome"] == "Solicitação de Pessoal"
    assert out["b"]["nome"] == "Solicitação de Pessoal — diárias"


def test_name_cluster_with_sub_names_requests_umbrella():
    captured: dict = {}

    def llm(messages):
        captured["user"] = messages[1]["content"]
        return '{"nome":"Atas de Registro de Preços","descricao":"d","marcadores":["a"]}'

    res = name_cluster([{"protocolo": "P1", "resumo": "x"}], llm,
                       sub_names=["Adesão a Ata", "Reequilíbrio de Ata"])
    assert "AGRUPA as seguintes subcategorias" in captured["user"]
    assert "Adesão a Ata" in captured["user"] and "Reequilíbrio de Ata" in captured["user"]
    assert res["nome"] == "Atas de Registro de Preços"


def test_name_cluster_contrastive_includes_own_and_sibling_profiles():
    captured: dict = {}

    def llm(messages):
        captured["user"] = messages[1]["content"]
        return '{"nome":"Adesão consulta rápida","descricao":"d","marcadores":["curto"]}'

    res = name_cluster(
        [{"protocolo": "P1", "resumo": "x"}], llm,
        profile="23 processos, porte curto (~42 atividades), tipo predominante: Licitação: Consulta",
        sibling_profiles=["67 processos, porte longo (~312 atividades), tipo predominante: Documento Oficial"],
    )
    assert "Perfil quantitativo deste subgrupo" in captured["user"]
    assert "porte curto" in captured["user"]
    assert "COEXISTE com outros grupos" in captured["user"]
    assert "porte longo" in captured["user"]
    assert res["nome"] == "Adesão consulta rápida"


def test_name_all_clusters_macro_receives_micro_context():
    import json as _j
    pf, feat = _three_clusters_synthetic()
    macro_labels, macro_str = cluster_macro(feat, min_cluster_size=10)
    micro_labels, micro_str, reclass = cluster_micro_within(feat, macro_labels, min_cluster_size=5)
    catalog = build_catalog("test-run", pf, feat, macro_labels, macro_str,
                             micro_labels, micro_str, reclass)
    prompts: list[str] = []

    def loader(protocolos):
        return [{"protocolo": p, "resumo": f"r {p}"} for p in protocolos]

    def llm(messages):
        prompts.append(messages[1]["content"])
        return _j.dumps({"nome": "SubName", "descricao": "d", "marcadores": ["m"]})

    name_all_clusters(catalog, loader, llm, samples_per_cluster=3)
    if any(catalog.micro_clusters):
        assert any("AGRUPA as seguintes subcategorias" in p for p in prompts)


def test_name_all_clusters_renames_colliding_macros():
    import json as _j
    pf, feat = _three_clusters_synthetic()
    ml, ms = cluster_macro(feat, min_cluster_size=10)
    mi, mis, recl = cluster_micro_within(feat, ml, min_cluster_size=5)
    catalog = build_catalog("trun", pf, feat, ml, ms, mi, mis, recl)
    macro_labels = sorted({int(x) for x in ml} - {NOISE_LABEL})
    macro_profiles = {category_id("trun", "macro", L): f"profile-of-macro-{L}" for L in macro_labels}

    prompts: list[str] = []

    def loader(ps):
        return [{"protocolo": p, "resumo": "x"} for p in ps]

    def llm(messages):
        prompts.append(messages[1]["content"])
        return _j.dumps({"nome": "MesmoNome", "descricao": "d", "marcadores": ["m"]})

    names = name_all_clusters(catalog, loader, llm, samples_per_cluster=3, macro_profiles=macro_profiles)
    assert any("profile-of-macro-" in p and "COEXISTE com outros grupos" in p for p in prompts)
    macro_names = [names[category_id("trun", "macro", L)]["nome"] for L in macro_labels]
    assert len(set(macro_names)) == len(macro_names)


def test_name_cluster_parses_valid_json():
    samples = [{"protocolo": "P1", "resumo": "Pedido de licitação..."}]
    result = name_cluster(samples, _stub_llm_returning({
        "nome": "Contratação direta",
        "descricao": "Aquisição sem licitação prévia.",
        "marcadores": ["Lei 8.666", "Inexigibilidade", "JURIDICO"],
    }))
    assert result["nome"] == "Contratação direta"
    assert len(result["marcadores"]) == 3


def test_name_cluster_falls_back_on_invalid_json():
    samples = [{"protocolo": "P1", "resumo": "x"}]

    def bad(messages):
        return "not valid json"

    result = name_cluster(samples, bad)
    assert result["nome"] == "Cluster sem nome"
    assert result["marcadores"] == []


def test_name_cluster_falls_back_on_llm_exception():
    def boom(messages):
        raise RuntimeError("api down")
    result = name_cluster([{"protocolo": "P1", "resumo": "x"}], boom)
    assert result["nome"] == "Cluster sem nome"


def test_name_cluster_truncates_long_fields():
    huge = {
        "nome": "x" * 500,
        "descricao": "y" * 5000,
        "marcadores": [f"m{i}" for i in range(20)],
    }
    result = name_cluster([{"protocolo": "P1"}], _stub_llm_returning(huge))
    assert len(result["nome"]) <= 120
    assert len(result["descricao"]) <= 500
    assert len(result["marcadores"]) <= 5


def test_name_all_clusters_uses_loader_and_naming():
    pf, feat = _three_clusters_synthetic()
    macro_labels, macro_str = cluster_macro(feat, min_cluster_size=10)
    micro_labels, micro_str, reclass = cluster_micro_within(
        feat, macro_labels, min_cluster_size=5,
    )
    catalog = build_catalog("test-run", pf, feat, macro_labels, macro_str,
                             micro_labels, micro_str, reclass)

    loader_called: list[list[str]] = []

    def loader(protocolos):
        loader_called.append(list(protocolos))
        return [{"protocolo": p, "resumo": f"resumo {p}"} for p in protocolos]

    llm = _stub_llm_returning({
        "nome": "Categoria X",
        "descricao": "descrição",
        "marcadores": ["a", "b", "c"],
    })
    names = name_all_clusters(catalog, loader, llm, samples_per_cluster=3)
    assert len(names) >= 3
    for sample_set in loader_called:
        assert len(sample_set) <= 3


def test_name_all_clusters_parallel_matches_sequential():
    import threading
    pf, feat = _three_clusters_synthetic()
    macro_labels, macro_str = cluster_macro(feat, min_cluster_size=10)
    micro_labels, micro_str, reclass = cluster_micro_within(feat, macro_labels, min_cluster_size=5)
    catalog = build_catalog("test-run", pf, feat, macro_labels, macro_str,
                             micro_labels, micro_str, reclass)

    seen_threads: set[int] = set()

    def loader(protocolos):
        return [{"protocolo": p, "resumo": f"r {p}"} for p in protocolos]

    def llm(messages):
        seen_threads.add(threading.get_ident())
        import json as _j
        return _j.dumps({"nome": "Cat", "descricao": "d", "marcadores": ["a", "b", "c"]})

    seq = name_all_clusters(catalog, loader, llm, samples_per_cluster=3, workers=1)
    par = name_all_clusters(catalog, loader, llm, samples_per_cluster=3, workers=4)
    assert set(seq.keys()) == set(par.keys())
    assert len(seen_threads) >= 2


def test_category_id_is_deterministic_and_includes_parent():
    a = category_id("run-1", "macro", 5)
    assert a == "run-1|macro|5"
    b = category_id("run-1", "micro", 2, parent_label=5)
    assert b == "run-1|micro|5|2"
    assert category_id("run-1", "macro", 5) == a
