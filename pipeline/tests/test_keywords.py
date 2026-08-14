from __future__ import annotations

import pytest

from ..model.keywords import load_vocab, merge_into_vocab, normalize_batch, normalize_keyword, save_vocab, similarity, vocab_prompt_block


def test_unit_paths_collapse_to_the_last_segment():
    assert normalize_keyword("SEAD-PI/GAB/SLC/CADUF") == "caduf"
    assert normalize_keyword("caduf") == "caduf"
    assert normalize_keyword("SEAD-PI/GAB/SLC/CADUF") == normalize_keyword("CADUF")


def test_case_accents_punctuation_and_stopwords_are_normalized():
    assert normalize_keyword("Ata de Registro de Preços") == "ata registro precos"
    assert normalize_keyword("  ATA   DE  REGISTRO,  de PREÇOS! ") == "ata registro precos"
    assert normalize_keyword("Licitação") == normalize_keyword("licitacao")


def test_short_and_empty_terms_are_rejected():
    v: dict[str, int] = {}
    assert merge_into_vocab("", v) is None
    assert merge_into_vocab("de", v) is None
    assert merge_into_vocab("ok", v) is None
    assert v == {}


def test_near_duplicates_fold_into_the_existing_term():
    v: dict[str, int] = {}
    a = merge_into_vocab("ata registro precos", v)
    b = merge_into_vocab("ata registro preco", v)
    assert a == b == "ata registro precos"
    assert v == {"ata registro precos": 2}


def test_distinct_terms_stay_distinct():
    v: dict[str, int] = {}
    merge_into_vocab("ata registro precos", v)
    merge_into_vocab("controle frequencia servidor", v)
    assert len(v) == 2


def test_similarity_is_symmetric_and_bounded():
    assert similarity("abc", "abc") == 1.0
    assert 0.0 <= similarity("licitacao", "aquisicao") <= 1.0
    assert similarity("a", "b") == similarity("b", "a")


def test_normalize_batch_dedupes_within_one_document():
    v: dict[str, int] = {}
    out = normalize_batch(["Ata de Registro de Preços", "ATA DE REGISTRO DE PRECOS",
                           "SEAD-PI/GAB/SLC/CADUF"], v)
    assert out == ["ata registro precos", "caduf"]


def test_vocab_round_trips_and_prompt_block_is_frequency_ordered(tmp_path):
    p = tmp_path / "vocab.json"
    v = {"raro": 1, "comum": 10, "medio": 5}
    save_vocab(v, p)
    assert load_vocab(p) == v
    assert vocab_prompt_block(v).startswith("comum · medio · raro")
    assert vocab_prompt_block({}) == ""
    assert load_vocab(tmp_path / "missing.json") == {}


def test_orgao_names_are_not_keywords():
    v: dict[str, int] = {}
    assert merge_into_vocab("SEAD", v) is None
    assert merge_into_vocab("SEAD-PI", v) is None
    assert merge_into_vocab("Governo do Estado", v) is None
    assert v == {}


def test_sead_variants_do_not_both_survive():
    v: dict[str, int] = {}
    for t in ("SEAD", "SEAD-PI", "sead-pi"):
        merge_into_vocab(t, v)
    assert v == {}


def test_containment_folds_into_the_shorter_term():
    v: dict[str, int] = {}
    a = merge_into_vocab("contracheque", v)
    b = merge_into_vocab("desconto contracheque", v)
    assert a == b == "contracheque"
    assert list(v) == ["contracheque"]


def test_keywords_stage_filters_to_the_study_corpus(tmp_path):
    import numpy as np

    from pipeline.stages.keywords import _load_corpus

    npz = tmp_path / "c.npz"
    np.savez_compressed(npz, protocolos=np.asarray(["A", "B"], dtype=str),
                        features=np.zeros((2, 2), dtype=np.float32))
    assert _load_corpus(npz) == {"A", "B"}

    lab = tmp_path / "labels.json"
    lab.write_text('{"labels": {"X": 1, "Y": -1}}')
    assert _load_corpus(lab) == {"X", "Y"}
    assert _load_corpus(tmp_path / "missing.npz") == set()


def test_stage_source_applies_the_corpus_filter():
    from pathlib import Path
    src = Path("pipeline/stages/keywords.py").read_text(encoding="utf-8")
    assert "if corpus and pf not in corpus:" in src
    assert "corpus_file" in src


def test_protocolo_underscore_and_slash_forms_join():
    from pipeline.stages.keywords import canon_protocolo
    assert canon_protocolo("00002.000002_2025-45") == "00002.000002/2025-45"
    assert canon_protocolo("00002.000002/2025-45") == "00002.000002/2025-45"


def test_corpus_loader_canonicalises_both_sources(tmp_path):
    import numpy as np

    from pipeline.stages.keywords import _load_corpus

    npz = tmp_path / "c.npz"
    np.savez_compressed(npz, protocolos=np.asarray(["00002.1_2025-1"], dtype=str),
                        features=np.zeros((1, 2), dtype=np.float32))
    assert _load_corpus(npz) == {"00002.1/2025-1"}


def test_stage_refuses_a_filter_that_matches_nothing():
    from pathlib import Path
    src = Path("pipeline/stages/keywords.py").read_text(encoding="utf-8")
    assert "matched 0 of" in src
    assert "refusing to silently process nothing" in src


def test_parallel_batches_merge_sequentially_for_reproducibility():
    from pathlib import Path
    src = Path("pipeline/stages/keywords.py").read_text(encoding="utf-8")
    assert "ThreadPoolExecutor" in src
    assert "sorted(results, key=lambda r: r[0])" in src, "merge must be protocolo-ordered"
    assert "block = vocab_prompt_block(vocab, limit=top)" in src, "block frozen per batch"


def test_vocab_prompt_block_respects_the_limit():
    from ..model.keywords import vocab_prompt_block
    v = {f"t{i}": 100 - i for i in range(300)}
    assert len(vocab_prompt_block(v, limit=150).split(" · ")) == 150
    assert vocab_prompt_block(v, limit=10).split(" · ")[0] == "t0"


def test_geographic_and_temporal_terms_are_rejected():
    v: dict[str, int] = {}
    for t in ("Teresina", "exercicio 2025", "ANO 2025", "2025", "exercicio financeiro",
              "Processo Administrativo"):
        assert merge_into_vocab(t, v) is None, t
    assert v == {}


def test_discriminative_terms_still_survive():
    v: dict[str, int] = {}
    for t in ("servidor publico", "suporte tecnico", "ata registro precos"):
        assert merge_into_vocab(t, v) is not None, t
    assert len(v) == 3


def test_two_phase_extraction_is_the_default():
    from pathlib import Path
    src = Path("pipeline/stages/keywords.py").read_text(encoding="utf-8")
    assert "PASSES = 2" in src
    assert "PASS1_BATCH = 10" in src and "PASS1_VOCAB_TOP = 150" in src
    assert "PASS2_BATCH = 30" in src and "PASS2_VOCAB_TOP = 300" in src
    assert "_run_pass(1, p1[0], p1[1], p1[2], force)" in src
    assert "for extra in range(2, passes + 1):" in src


def test_second_pass_reprocesses_and_records_which_pass_won():
    from pathlib import Path
    src = Path("pipeline/stages/keywords.py").read_text(encoding="utf-8")
    assert '_run_pass(extra, p2[0], p2[1], p2[2], True)' in src, 'pass 2 must redo'
    assert '"keywords_pass"' in src
    assert 'if meta.get("keywords") and not redo:' in src


def test_select_k_is_a_pipeline_stage_with_arm_guards():
    from pathlib import Path
    src = Path("pipeline/stages/select_k.py").read_text(encoding="utf-8")
    assert 'name="select-k"' in src
    assert "no features_file was given" in src
    assert "Refusing to select parameters on the wrong arm" in src
    assert "at_grid_edge" in src, "must flag when the optimum sits on a grid boundary"


def test_select_k_is_a_pipeline_stage_with_arm_guards():
    from pathlib import Path
    src = Path("pipeline/stages/select_k.py").read_text(encoding="utf-8")
    assert 'name="select-k"' in src
    assert "no features_file was given" in src
    assert "Refusing to select parameters on the wrong arm" in src
    assert "at_grid_edge" in src, "must flag when the optimum sits on a grid boundary"


def test_select_k_is_registered():
    from pathlib import Path
    assert "select_k" in Path("pipeline/stages/__init__.py").read_text(encoding="utf-8")


def test_keyword_block_is_binary_tfidf_with_a_frequency_floor():
    import numpy as np

    from ..model.processo_features import BlockWeights, ProcessoInput, build_batch_features

    def mk(pf, kws):
        return ProcessoInput(protocolo_formatado=pf, documentos=[], unidades_visitadas=[],
                             unidades_cronologicas=[], atividades_tipo_acao=[], keywords=kws)

    procs = [mk(f"P{i}", ["ata registro precos", "adesao ata"]) for i in range(5)]
    procs.append(mk("P9", ["assunto unico raro"]))
    b = build_batch_features(procs, block_weights=BlockWeights(), keyword_min_df=3)
    assert b.keyword_dim >= 1
    assert "ata_registro_precos" in (b.keyword_vocab or [])
    assert "assunto_unico_raro" not in (b.keyword_vocab or []), "min_df must drop rare terms"


def test_keywords_change_the_feature_hash():
    from ..model.processo_features import ProcessoInput, feature_hash

    def mk(kws):
        return ProcessoInput(protocolo_formatado="P", documentos=[], unidades_visitadas=[],
                             unidades_cronologicas=[], atividades_tipo_acao=[], keywords=kws)

    assert feature_hash(mk(["a b"])) != feature_hash(mk(["c d"]))
    assert feature_hash(mk(["a b"])) != feature_hash(mk(None))
    assert feature_hash(mk(["a b"])) == feature_hash(mk(["a b"]))


def test_empty_extraction_never_overwrites_existing_keywords():
    from pathlib import Path
    src = Path("pipeline/stages/keywords.py").read_text(encoding="utf-8")
    assert "if not raw:" in src and "empty_raw += 1" in src
    assert "if not canon:" in src and "empty_canon += 1" in src
    i_guard = src.index("if not canon:")
    i_write = src.index('meta["keywords"] = canon')
    assert i_guard < i_write, "the guard must precede the write"
    assert '"empty_llm_response"' in src and '"empty_after_normalization"' in src


def test_random_split_is_the_default_and_is_seed_reproducible():
    from ..model.predict import random_split_field
    tw = [(f"2025-{i%12+1:02d}-01", ["A", "B"], f"P{i}") for i in range(100)]
    a_tr, a_te = random_split_field(tw, 2, train_frac=0.7, seed=42)
    b_tr, b_te = random_split_field(tw, 2, train_frac=0.7, seed=42)
    assert a_tr == b_tr and a_te == b_te, "same seed must reproduce"
    assert 60 <= len(a_tr) <= 80 and len(a_tr) + len(a_te) == 100
    assert not (set(a_tr) & set(a_te)), "train and test must be disjoint processos"
    assert set(a_tr) | set(a_te) == {f"P{i}" for i in range(100)}


def test_random_split_ignores_start_date_ordering():
    from ..model.predict import random_split_field, temporal_split_field
    tw = [(f"2025-{i%12+1:02d}-01", ["A", "B"], f"P{i}") for i in range(100)]
    _, rnd_te = random_split_field(tw, 2, train_frac=0.7, seed=42)
    _, tmp_te = temporal_split_field(tw, 2, train_frac=0.7)
    assert set(rnd_te) != set(tmp_te), "random must not reproduce the temporal tail"


def test_evaluate_cluster_records_the_split_it_used():
    from ..model.predict import MarkovModel
    from ..model.typical_eval import ModelSpec, evaluate_cluster
    tw = [(f"2025-01-{i%28+1:02d}", ["GERACAO-PROCEDIMENTO@U", "CONCLUSAO-PROCESSO-UNIDADE@U"],
           f"P{i}") for i in range(40)]
    res = evaluate_cluster(tw, [ModelSpec("markov", lambda: MarkovModel(3))])
    assert res["split"]["mode"] == "random"
    assert res["split"]["train_frac"] == 0.7
    assert res["n_train"] + res["n_test"] == 40
    assert 22 <= res["n_train"] <= 34


def test_naming_prompt_leads_with_cluster_keywords():
    from ..model.clustering import NAMING_SYSTEM_PROMPT, name_cluster

    captured = {}

    def llm(messages):
        captured["user"] = messages[-1]["content"]
        return '{"nome":"X","descricao":"d","marcadores":["a","b","c"]}'

    name_cluster([{"protocolo": "P1", "topic": "t", "summary": "s"}], llm,
                 top_keywords=[("ata registro precos", 9), ("adesao ata", 4)])
    assert "ata registro precos (9x)" in captured["user"]
    assert captured["user"].index("Palavras-chave") < captured["user"].index("Amostra")
    assert "palavras-chave" in NAMING_SYSTEM_PROMPT.lower()


def test_naming_without_keywords_still_works():
    from ..model.clustering import name_cluster
    out = name_cluster([{"protocolo": "P1", "topic": "t"}],
                       lambda m: '{"nome":"X","descricao":"d","marcadores":["a"]}')
    assert out["nome"] == "X"


def test_cluster_top_keywords_counts_by_frequency():
    from pipeline.stages.processo_cluster import cluster_top_keywords
    kw = {"P1": ["ata", "adesao"], "P2": ["ata"], "P3": ["ata", "outro"]}
    top = cluster_top_keywords(["P1", "P2", "P3"], kw, limit=2)
    assert top[0] == ("ata", 3)
    assert len(top) == 2


def test_keywords_persist_outside_the_arm_snapshots(tmp_path):
    from ..model.keywords import load_keywords_store, save_keywords_store
    p = tmp_path / "kw.json"
    assert load_keywords_store(p) == {}
    save_keywords_store({"00002.1/2025-1": ["ata registro precos"]}, p)
    assert load_keywords_store(p) == {"00002.1/2025-1": ["ata registro precos"]}


def test_sidecar_is_saved_incrementally_not_only_at_the_end():
    from pathlib import Path
    src = Path("pipeline/stages/keywords.py").read_text(encoding="utf-8")
    assert src.count("save_keywords_store(store, store_path)") >= 2, \
        "must persist per batch, so a crash does not lose the run"


def test_readers_prefer_the_sidecar_over_metadata():
    from pathlib import Path
    assert "load_keywords_store" in Path("pipeline/stages/processo_embed.py").read_text(encoding="utf-8")
    assert "keywords_by_processo.json" in Path("reports/gen_14_explorer.py").read_text(encoding="utf-8")


def test_path_support_counts_members_within_a_distance_band():
    from ..model.typical_eval import path_support
    seqs = [["a", "b", "c"]] * 8 + [["x", "y", "z"]] * 2
    s = path_support(["a", "b", "c"], seqs, thresholds=(0.25, 0.5))
    assert s["within_25"] == 0.8
    assert s["median_distance"] == 0.0


def test_unit_coverage_reports_recall_and_precision_of_visited_units():
    from ..model.typical_eval import unit_coverage
    seqs = [["A@U1", "B@U2", "C@U3"], ["A@U1", "B@U2"]]
    c = unit_coverage(["A@U1", "B@U2"], seqs)
    assert c["n_units_path"] == 2
    assert c["unit_precision"] == 1.0
    assert 0.5 < c["unit_recall"] <= 1.0


def test_transition_support_flags_invented_transitions():
    from ..model.typical_eval import transition_support
    seqs = [["a", "b", "c"]] * 4
    good = transition_support(["a", "b", "c"], seqs)
    assert good["transitions_unseen"] == 0 and good["transition_support_min"] == 1.0
    bad = transition_support(["a", "z"], seqs)
    assert bad["transitions_unseen"] == 1


def test_step_count_agreement_reports_visits_and_median_actions():
    from ..model.typical_eval import step_count_agreement
    seqs = [["a@U1", "b@U1", "c@U2"], ["a@U1", "b@U1", "d@U2", "e@U2"]]
    g = step_count_agreement(["x@U1", "y@U2"], seqs)
    assert g["visits_in_path"] == 2
    assert g["visits_matched_frac"] == 1.0
    assert g["median_actions_per_visit"] is not None


def test_size_bands_partition_clusters_by_trace_count():
    from ..model.typical_eval import size_band
    assert size_band(30) == "small" and size_band(59) == "small"
    assert size_band(60) == "medium" and size_band(149) == "medium"
    assert size_band(150) == "large" and size_band(5000) == "large"


def test_matrix_aggregates_per_size_band():
    from ..model.typical_eval import evaluate_matrix_by_band
    row = {"top1": 0.6, "top3": 0.8, "suffix_dl": 0.3}
    res = {"a": {"n_traces": 40, "edge_coverage": 1.0, "models": {"markov": row}},
           "b": {"n_traces": 100, "edge_coverage": 1.0, "models": {"markov": row}},
           "c": {"n_traces": 400, "edge_coverage": 1.0, "models": {"markov": row}}}
    bands = evaluate_matrix_by_band(res)
    assert set(bands) == {"small", "medium", "large"}
    assert all(b["n_clusters"] == 1 for b in bands.values())


def test_itinerary_alphabet_is_idempotent():
    from ..model.typical_eval import itinerary_alphabet
    unit = ["GERACAO@U1", "ASSINATURA@U1", "REMETIDO@U2"]
    once = itinerary_alphabet(unit)
    assert once == ["U1", "U2"]
    assert itinerary_alphabet(once) == once, "second decode must not blank the tokens"


def test_unit_coverage_works_on_already_itinerary_traces():
    from ..model.typical_eval import unit_coverage
    seqs = [["U1", "U2", "U3"], ["U1", "U2"]]
    c = unit_coverage(["U1", "U2"], seqs)
    assert c["n_units_path"] == 2
    assert c["unit_precision"] == 1.0
    assert c["unit_recall"] < 1.0, "must not report perfect recall on a partial path"


def test_global_model_control_trains_on_the_pooled_corpus():
    from ..model.typical_eval import global_model_accuracy
    tw = [(f"2025-01-{i%28+1:02d}", ["A", "B", "C"], f"P{i}") for i in range(60)]
    acc = global_model_accuracy(tw, [["A", "B", "C"]])
    assert acc is not None and 0.0 <= acc <= 1.0
    assert global_model_accuracy([], [["A", "B"]]) is None
    assert global_model_accuracy(tw, []) is None


def test_baseline_block_carries_the_global_control():
    from pathlib import Path
    src = Path("pipeline/model/typical_eval.py").read_text(encoding="utf-8")
    assert '"top1_global_model"' in src
    assert "all_traces=all_tws" in Path("pipeline/evidence/typical_path/run_typical_eval.py").read_text(encoding="utf-8")
