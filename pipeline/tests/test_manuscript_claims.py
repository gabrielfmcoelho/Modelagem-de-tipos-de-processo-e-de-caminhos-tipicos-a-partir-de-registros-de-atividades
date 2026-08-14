from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FIGURES = ROOT / "artifacts" / "stats" / "results_figures.json"
SECTIONS = ROOT / "article" / "latex" / "sections"
SECTIONS_PT = ROOT / "article" / "latex-ptbr" / "sections"


def _dig(data, path: str):
    cur = data
    for part in path.split("."):
        if isinstance(cur, list):
            cur = cur[int(part)]
        else:
            cur = cur[part]
    return cur


ANCHOR_WINDOW = 200
CAVEAT_WINDOW = 400

CLAIMS = [
    ("corpus_funnel.n_opening_documents_parsed", "12{,}259",
     "ran over every case opened in the year"),
    ("corpus_funnel.n_generated", "12{,}621", None),
    ("controls.unit.clustered_best_top1", "0.726",
     "reduces best next-step accuracy from"),
    ("controls.unit.shuffled_best_top1", "0.494",
     "reduces best next-step accuracy from"),
    ("controls.unit.global_model", "0.713",
     "single global third-order Markov chain"),
    ("controls.unit.per_family_like_for_like.markov.gain_vs_global", "0.004",
     "against the same chain fitted globally, gains"),
    ("controls.itinerary.per_family_like_for_like.markov.gain_vs_global", "0.035",
     "against the same chain fitted globally, gains"),
    ("controls.itinerary.clustered_best_top1", "0.672",
     "reduces best next-step accuracy from"),
    ("catch_all_null.single_class_contrast.1.ari_all", "0.128", "agreement is"),
    ("catch_all_null.single_class_contrast.1.ari_excl_catch_all", "0.246",
     "without the catch-all"),
    ("catch_all_null.single_class_contrast.1.ari_excl_rank2", "0.107", None),
    ("temporal_holdout.matched.n_common_cases", "637", "cases all four evaluate"),
    ("temporal_holdout.matched.rows.0.gain_vs_global", "0.0380", None),
    ("temporal_holdout.matched.rows.3.gain_vs_global", "0.0310", None),
    ("index_mechanism.robustness.partial_silhouette_vs_coverage_given_median_size", "0.125",
     "partial correlation between silhouette and coverage"),
    ("index_mechanism.robustness.subsets.drop_consensus.silhouette_vs_median_size", "0.92",
     "dropping the consensus partitions gives"),
    ("index_mechanism.robustness.subsets.kmeans_only.silhouette_vs_median_size", "0.83",
     "the six centroid clusterings alone"),
    ("index_mechanism.robustness.configuration_level_silhouette_vs_median_size", "0.77",
     "on the six configuration-level points"),
    ("index_mechanism.robustness.configuration_level_p_exact", "0.10",
     "on the six configuration-level points"),
    ("temporal_holdout.rows.0.itinerary.gain_vs_global", "0.0381", None),
    ("temporal_holdout.rows.3.itinerary.gain_vs_global", "0.0145", None),
    ("common_set_all.spread", "0.0079", "puts the spread at"),
    ("common_set_all.spread_bootstrap.ci95.1", "0.0139", None),
    ("common_set_all.spread_bootstrap.upper90_one_sided", "0.0124", None),
    ("intrinsic_vs_downstream.permutation.noise_ratio_refused.p_permutation", "0.059", None),
    ("intrinsic_vs_downstream.permutation.dbcv.rho", "0.36", "for DBCV"),
    ("intrinsic_vs_downstream.permutation.silhouette.rho", "0.35", "for silhouette"),
    ("intrinsic_vs_downstream.permutation.davies_bouldin.rho", "-0.48", "Davies--Bouldin"),
    ("index_mechanism.all_clusterings.silhouette_vs_noise_ratio", "0.61",
     "with the share of cases discarded as noise"),
    ("index_mechanism.all_clusterings.noise_ratio_vs_own_top1", "0.68",
     "raises the score on the partition's own evaluated set"),
    ("index_mechanism.full_coverage.silhouette_vs_median_size", "0.87",
     "Silhouette tracks granularity almost deterministically"),
    ("index_mechanism.full_coverage.silhouette_vs_n_clusters", "-0.84",
     "Silhouette tracks granularity almost deterministically"),
    ("index_mechanism.full_coverage.silhouette_vs_coverage", "0.84",
     "Silhouette also correlates with coverage at"),
    ("index_mechanism.full_coverage.silhouette_vs_common_top1", "0.35",
     "silhouette correlates with accuracy at"),
    ("index_mechanism.within_size_band.small.silhouette_vs_top1", "-0.10", None),
    ("index_mechanism.within_size_band.large.silhouette_vs_top1", "-0.12", None),
    ("selection_full_coverage.rows.0.share_in_clusters_ge_150", "52.9", None),
    ("model_count.models_trained", "8{,}985", None),
    ("constraint_cost.n_decision_steps", "69{,}012", None),
    ("catalogue_sample.rows.0.top1", "0.974", None),
    ("catalogue_sample.rows.0.n_cases", "325", None),
    ("catalogue_sample.rows.3.top1", "0.522", None),
    ("catalogue_sample.rows.3.n_cases", "261", None),
    ("catalogue_sample.rows.7.top1", "0.424", None),
    ("catalogue_sample.rows.2.unit_recall", "0.917", None),
    ("noninferiority.unit.summary.n_comparisons", "20",
     "model-by-clustering comparisons"),
    ("noninferiority.unit.summary.n_non_inferior_sensitivity", "17", "17 of 20"),
    ("noninferiority.unit.summary.sensitivity_failures.0.ci90_one_sided_lower", "-0.0072",
     "one-sided 90"),
    ("noninferiority.unit.summary.sensitivity_failures.2.ci90_one_sided_lower", "-0.0059",
     "one-sided 90"),
    ("noninferiority.unit.meta.replicates", "2{,}000", "paired bootstrap with"),
    ("taxonomy.exp-anon/hdbscan.all.ari", "0.202", "the agreement is modest"),
    ("catch_all_share.share_concluded_pct", "30.5", "concluded cases"),
    ("catch_all_share.share_analysed_pct", "30.2", "of the 5{,}243 analysed"),
    ("catch_all_share.n_concluded", "5{,}445", "concluded cases"),
    ("taxonomy.exp-anon/hdbscan.no_catch_all.ari", "0.352",
     "remove that one label and agreement rises to"),
]

RANGE_CLAIMS = [
    ("catch_all_null.rows", "z", 7.3, 17.2, "7.3", "17.2"),
]

MUST_BE_NEGATIVE = {
    "intrinsic_vs_downstream.permutation.davies_bouldin.rho",
    "index_mechanism.full_coverage.silhouette_vs_n_clusters",
    "index_mechanism.within_size_band.small.silhouette_vs_top1",
    "index_mechanism.within_size_band.large.silhouette_vs_top1",
}

MUST_BE_POSITIVE = {
    "index_mechanism.full_coverage.silhouette_vs_median_size",
    "index_mechanism.all_clusterings.silhouette_vs_noise_ratio",
}


CLAIMS_PT = [
    ("corpus_funnel.n_generated", "12.621", "é por isso dado na íntegra:"),
    ("corpus_funnel.n_corpus_protocolos", "5.445", "nasceram na Secretaria durante o ano;"),
    ("corpus_funnel.n_opening_documents_parsed", "5.243", "carregam documento inicial legível"),
    ("corpus_funnel.n_conclusion_event_logged_same_year", "7.920",
     "descrição do andamento. A segunda registra"),
    ("corpus_funnel.n_not_concluded_same_year", "4.701", "conclusões dentro do ano, contra os"),
    ("catch_all_share.n_concluded", "5.445", "dos 5.445 processos concluídos"),
    ("catch_all_share.share_concluded_pct", "30,5", "toda espécie e se aplica a"),
    ("model_count.clusters_evaluated", "4.323", "de modelo: 84 células de avaliação,"),
    ("model_count.models_trained", "25.938", "é exigência do estudo, que treinou"),
    ("controls.unit.global_baseline_residual", "0,0179", "e deveria ser nulo --- vale"),
    ("controls.itinerary.global_baseline_residual", "0,0149", "o resíduo do alfabeto é"),
    ("controls.unit.per_family_like_for_like.markov.gain_vs_global", "0,0004",
     "tipo sobre um modelo global ---"),
    ("controls.itinerary.per_family_like_for_like.markov.gain_vs_global", "0,0097",
     "um modelo global --- 0,0004 e"),
    ("controls.procedure.per_family_like_for_like.markov.gain_vs_global", "0,1091",
     "interpretável. A cadeia de Markov ganha"),
    ("controls.procedure.per_family_like_for_like.gru.gain_vs_global", "0,131",
     "famílias sequenciais ganham de 0,109 a"),
    ("common_set_all.spread", "0,0055", "separa os catorze agrupamentos candidatos por"),
    ("selection_full_coverage.rows.0.coverage", "0,751", "tem 60 tipos e cobertura de"),
    ("selection_full_coverage.rows.0.n_clusters", "60", "a eleger. O catálogo entregue tem"),
    ("taxonomy.exp-anon/hdbscan.no_catch_all.ari", "0,283", "genérica a eleva para 0,230 a"),
]


RETRACTED_PT = {
    "0,818": "the coassoc-space DBCV that produced the retracted best-index/worst-path claim",
    "0,981": "the coassoc-space silhouette from the same retracted claim",
}

CAVEAT_REQUIRED_PT = {
    "0,013": ("0,004",
              "0,013 is the SELECTED-BEST action gain (0,726 - 0,713). It is a legitimate "
              "figure, but stating it without the family-matched 0,004 nearby is the "
              "retracted claim: part of that gain is per-cluster selection over every model "
              "families, not partitioning."),
}


@pytest.fixture(scope="module")
def figures():
    if not FIGURES.is_file():
        pytest.skip("results_figures.json not built")
    return json.loads(FIGURES.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manuscript():
    if not SECTIONS.is_dir():
        pytest.skip("manuscript sections not present")
    raw = "\n".join(p.read_text(encoding="utf-8") for p in sorted(SECTIONS.glob("*.tex")))
    return " ".join(raw.split())


def _renderings(value) -> set[str]:
    if isinstance(value, int):
        return {f"{value:,}".replace(",", "{,}"), str(value)}
    out = set()
    for places in range(1, 5):
        out.add(f"{value:.{places}f}")
        out.add(f"{abs(value):.{places}f}")
    for places in range(0, 3):
        out.add(f"{value * 100:.{places}f}")
        out.add(f"{abs(value) * 100:.{places}f}")
    return out


@pytest.mark.parametrize("path", sorted(MUST_BE_NEGATIVE | MUST_BE_POSITIVE))
def test_registered_signs_have_not_flipped(figures, path):
    actual = _dig(figures, path)
    if path in MUST_BE_NEGATIVE:
        assert actual < 0, (
            f"{path} is now {actual}; the manuscript states it as a loss or a negative "
            "correlation. A sign flip changes the claim, not just the magnitude.")
    else:
        assert actual > 0, (
            f"{path} is now {actual}; the manuscript states it as a gain or a positive "
            "correlation. A sign flip changes the claim, not just the magnitude.")


def _near(manuscript: str, rendered: str, anchor: str, window: int = ANCHOR_WINDOW) -> bool:
    spots = [i for i in range(len(manuscript))
             if manuscript.startswith(rendered, i)]
    starts = [i for i in range(len(manuscript))
              if manuscript.startswith(anchor, i)]
    return any(abs(s - a) <= window for s in spots for a in starts)


@pytest.mark.parametrize("path,rendered,anchor", CLAIMS, ids=[c[0] for c in CLAIMS])
def test_manuscript_prose_matches_artifacts(figures, manuscript, path, rendered, anchor):
    actual = _dig(figures, path)
    assert rendered in _renderings(actual), (
        f"{path}: the artifact is {actual}, which does not round to the {rendered!r} this "
        "table expects. The evidence base changed; update the manuscript and this table.")
    assert rendered in manuscript, (
        f"{path} = {rendered} is not present anywhere in the manuscript prose. "
        "Either the prose drifted from the artifacts or the claim is no longer made.")
    if anchor is not None:
        assert anchor in manuscript, (
            f"{path}: the anchor {anchor!r} is gone from the prose. {rendered} still appears "
            "elsewhere, so the bare presence check would have passed while the sentence that "
            "actually makes this claim was deleted or rewritten.")
        assert _near(manuscript, rendered, anchor), (
            f"{path}: {rendered} appears in the manuscript but never within {ANCHOR_WINDOW} "
            f"characters of {anchor!r}. The number survives somewhere else in the paper while "
            "the sentence that states this claim no longer carries it.")


@pytest.mark.parametrize("path,field,lo,hi,lo_text,hi_text", RANGE_CLAIMS,
                         ids=[c[0] for c in RANGE_CLAIMS])
def test_manuscript_ranges_match_artifacts(figures, manuscript, path, field, lo, hi,
                                           lo_text, hi_text):
    values = [r[field] for r in _dig(figures, path)]
    assert min(values) == pytest.approx(lo, abs=0.05), (
        f"{path}.{field}: artifact minimum is {min(values)}, prose says {lo_text}")
    assert max(values) == pytest.approx(hi, abs=0.05), (
        f"{path}.{field}: artifact maximum is {max(values)}, prose says {hi_text}")
    for text in (lo_text, hi_text):
        assert text in manuscript, f"{path}.{field}: bound {text} absent from the prose"


def _renderings_pt(value) -> set[str]:
    if isinstance(value, int):
        return {f"{value:,}".replace(",", "."), str(value)}
    return {r.replace(".", ",") for r in _renderings(value)}


@pytest.fixture(scope="module")
def manuscript_pt():
    if not SECTIONS_PT.is_dir():
        pytest.skip("pt-BR manuscript not present")
    raw = "\n".join(p.read_text(encoding="utf-8") for p in sorted(SECTIONS_PT.glob("*.tex")))
    return " ".join(raw.split())


@pytest.mark.parametrize("path,rendered,anchor", CLAIMS_PT, ids=[c[0] for c in CLAIMS_PT])
def test_ptbr_prose_matches_artifacts(figures, manuscript_pt, path, rendered, anchor):
    assert anchor in manuscript_pt, (
        f"{path}: the anchor {anchor!r} is gone from the pt-BR prose. The sentence that "
        "makes this claim was deleted or rewritten; update CLAIMS_PT to what the manuscript "
        "now says, or drop the claim.")
    assert rendered in _renderings_pt(_dig(figures, path)), (
        f"{path}: the artifact no longer renders as {rendered!r}; the registered figure is "
        "stale against the evidence base.")
    expected = _renderings_pt(_dig(figures, path))
    assert any(_near(manuscript_pt, r, anchor) for r in expected), (
        f"{path}: the pt-BR manuscript states the sentence anchored on {anchor!r}, but none of "
        f"the artifact renderings {sorted(expected)} appears within {ANCHOR_WINDOW} characters "
        "of it. The translation carries a different number than the evidence base.")


def test_ptbr_register_is_not_vacuous(manuscript_pt):
    matched = [p for p, _r, a in CLAIMS_PT if a in manuscript_pt]
    if len(manuscript_pt) < 4000:
        pytest.skip("pt-BR manuscript is still a stub; nothing to anchor against yet")
    assert matched, (
        f"the pt-BR manuscript is {len(manuscript_pt)} characters -- real content -- but not one "
        f"of the {len(CLAIMS_PT)} pt-BR anchors matches, so every claim check above skipped. "
        "Either the anchors drifted from the translation or the register is theatre. "
        "Fix the anchors in CLAIMS_PT; do not delete this test.")


@pytest.mark.parametrize("value,pair", sorted(CAVEAT_REQUIRED_PT.items()))
def test_ptbr_selected_best_figure_always_carries_its_caveat(manuscript_pt, value, pair):
    caveat, why = pair
    if value not in manuscript_pt:
        pytest.skip("figure not used in the pt-BR manuscript")
    assert _near(manuscript_pt, value, caveat, CAVEAT_WINDOW), (
        f"{value} appears in the pt-BR manuscript without {caveat} within {CAVEAT_WINDOW} "
        f"characters. {why}")


@pytest.mark.parametrize("value,why", sorted(RETRACTED_PT.items()))
def test_ptbr_prose_does_not_reassert_a_retracted_figure(manuscript_pt, value, why):
    assert value not in manuscript_pt, (
        f"the pt-BR manuscript contains {value}, which is {why}. This is the exact drift that "
        "docs/paper/abstract-ptbr.md suffered while it sat outside the register.")


def test_noninferiority_verdicts_still_match_the_prose(figures, manuscript):
    s = _dig(figures, "noninferiority.unit.summary")
    assert s["n_non_inferior"] == s["n_comparisons"], (
        f"only {s['n_non_inferior']} of {s['n_comparisons']} comparisons are non-inferior at "
        "the pre-registered margin; the manuscript states that all of them are.")
    assert len(s["sensitivity_failures"]) == 3, (
        f"{len(s['sensitivity_failures'])} comparisons now fail the sensitivity margin; the "
        "manuscript names exactly three and identifies them by model.")
    named = {f["model"] for f in s["sensitivity_failures"]}
    assert named == {"gru", "lstm", "transformer"}, (
        f"the sensitivity failures are now {sorted(named)}; the manuscript names GRU, LSTM and "
        "Transformer. Reporting a different set as though it were the same would be the "
        "selective reporting this section exists to avoid.")


def test_catch_all_null_has_no_draw_reaching_the_observed_value(figures, manuscript):
    rows = _dig(figures, "catch_all_null.rows")
    if not rows:
        pytest.skip("catch-all null not built")
    worst = max(r["n_null_at_or_above_observed"] for r in rows)
    assert worst == 0, (
        f"{worst} null draw(s) now reach the observed ARI; the manuscript claims none do.")
    assert "no null draw reaches the observed" in manuscript
