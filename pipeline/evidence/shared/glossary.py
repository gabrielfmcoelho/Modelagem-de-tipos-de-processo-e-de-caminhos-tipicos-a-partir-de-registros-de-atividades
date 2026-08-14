from __future__ import annotations
import argparse
import json
from pathlib import Path
from statistics import mean, median
from ...core.paths import ROOT


METRIC_GLOSSARY = [
    ("top-1", "downstream", "↑", ("top1",), "Share of held-out steps where the model's first prediction is the true next state."),
    ("top-3", "downstream", "↑", ("top3",), "Share of held-out steps where the true next state is anywhere in the model's first three predictions."),
    ("top-1 (common set)", "downstream", "↑", ("acc_common", "acc_own", "delta", "spread"), "top-1 recomputed only on processos every clustering evaluates, removing the coverage confound."),
    ("successor baseline", "baseline", "↑", ("top1_successor",), "Most-frequent-successor lookup inside the cluster. Floor for 'did the model learn anything'."),
    ("global model", "control", "↑", ("top1_global_model", "global_model"), "One 3rd-order Markov chain trained on the pooled corpus. Answers 'would a single model do as well?'."),
    ("delta-star", "downstream", "↑", ("delta_star_top1", "delta_star_coverage_fidelity", "delta_star_adjusted", "delta_star"), "The estimand: the real partition's score minus the score of its shape-matched shuffled control (same cluster count, same size distribution, same population, membership permuted). Positive only if the partition carries process signal beyond its shape. Computed per model family, so the comparison is like-for-like. delta_star_adjusted additionally subtracts the global baseline under both partitions, cancelling the weighting artefact that global_baseline_residual reports. It is an ADMISSION GATE, not a ranking: delta-star grows with the number of families, because specialising pays more when families are small and the control preserves shape but not what granularity itself buys. Never order partitions of different granularity by it -- use selection_score for that; comparisons at matched k remain valid."),
    ("global baseline residual", "control", "↓", ("global_baseline_residual",), "The pooled global model scored on the same held-out steps under the real and the shuffled partition. Should be ~0 by construction; a non-zero value means the n_traces weighting is doing work and family imbalance must be reported alongside delta-star."),
    ("shuffled partition", "control", "↑", ("shuffled_best_top1", "shuffled_successor", "shuffled_lift_over_successor", "shuffled_top1", "shuffled_coverage_fidelity"), "Same cluster count/sizes/population, membership permuted. Floor for 'is the partition real?'. On its own it is the free gain of partitioning, not a result; its distance from the real arm is delta-star."),
    ("gain vs global", "downstream", "↑", ("gain_vs_global", "lift_over_global", "lift_over_global_model", "lift_over_successor", "top1_minus_markov"), "Per-cluster accuracy minus the baseline's accuracy on the same held-out steps. Measured inside one alphabet against a baseline facing the same vocabulary, so it is the only quantity comparable between representations. It still contains the gain any partition of the same size distribution earns for free, because fitting per family shrinks each model's alphabet — report it beside delta-star, never instead of it."),
    ("suffix distance", "fidelity", "↓", ("suffix_dl", "suffix_length_ratio"), "Normalised Damerau-Levenshtein between the suffix the model generates from a half-prefix and the real suffix. The length ratio says whether a model wins by stopping early."),
    ("suffix distance, constrained", "fidelity", "↓", ("suffix_dl_c",), "The same under constrained decoding, where the flow automaton filters every candidate. Emitted only for alphabets whose states carry an action; on a routing alphabet there is no lifecycle rule to enforce."),
    ("flow validity", "fidelity", "↑", ("flow_validity_step", "flow_validity_trace", "flow_validity_step_real", "flow_validity_trace_real"), "Share of generated steps (and of wholly-legal generated traces) the process lifecycle automaton allows. The _real pair is the same measure on the observed event log, which is the ceiling."),
    ("unit_recall", "coverage", "↑", ("unit_recall",), "Fraction of the units a real case visits that the generated path also visits."),
    ("unit_precision", "coverage", "↑", ("unit_precision",), "Fraction of units in the generated path that real cases actually visit."),
    ("visits_matched_frac", "coverage", "↑", ("visits_matched_frac", "visits_in_path", "n_units_path", "median_actions_per_visit"), "Fraction of a real case's visits matched by the generated path. Captures step-level coverage, not just which units."),
    ("transition_support", "coverage", "↑", ("transition_support_mean", "transition_support_min"), "Mean number of occurrences of each generated transition per cluster member. It counts occurrences, not distinct members, so it may exceed 1 and is not a proportion. The _min variant is the weakest link in the path."),
    ("transitions_unseen", "fidelity", "↓", ("transitions_unseen",), "Transitions in the generated path occurring in no sampled held-out trace of the cluster, against a sample of at most thirty. Fabrication, not variation; the measure overstates it for clusters larger than that sample."),
    ("unseen per visit", "fidelity", "↓", ("unseen_per_visit", "unseen_per_visit_pooled"), "transitions_unseen normalised by path length, so a short path cannot look faithful by generating less. The bare key is per cluster; the _pooled key is the population-level ratio of weighted means, and the two are not interchangeable."),
    ("within_25", "fidelity", "↑", ("within_25", "within_50", "median_distance"), "Share of held-out traces within 0.25 normalised Damerau-Levenshtein of the generated path."),
    ("typical path distance", "fidelity", "↓", ("typical_path_distance", "typical_path_distance_proc", "typical_path_distance_itin"), "Mean normalised Damerau-Levenshtein between the generated typical path and sampled held-out traces. The _proc and _itin variants project onto another alphabet and exist only for cells whose states carry both axes."),
    ("perplexity", "downstream", "↓", ("nll", "perplexity", "oov_rate", "n_steps"), "Exponentiated mean negative log-probability the model assigns to the true next step: the effective number of choices it is still deciding between. oov_rate is the share of steps it gave zero probability and that were floored."),
    ("edge coverage", "fidelity", "↑", ("edge_coverage", "edge_usage", "edge_f1", "n_model_edges", "edge_fidelity"), "Share of held-out transitions present in the cluster's unpruned directly-follows graph; edge_usage is the converse, the share of the graph's edges the held-out traces use. Both are cell statistics computed at floor 0.0, independent of the dfg model's own pruning. edge_fidelity carries the same three measures contrasted against the shuffled control (real/shuffled/delta_star); because they describe the cluster and not a model they take one value per partition and cannot vary by model family."),
    ("dispersion", "context", "—", ("dispersion", "dispersion_proc", "dispersion_itin"), "Mean pairwise distance inside a cluster. Bounds how close any single path can be to all members. The _proc and _itin variants measure the same spread after projecting onto another alphabet, and exist only for cells whose states carry both axes."),
    ("medoid", "baseline", "—", ("medoid_distance", "medoid_distance_proc", "medoid_distance_itin"), "The real trace closest on average to the others. Proximity baseline the generated path must justify itself against."),
    ("DBCV", "partition validity", "↑", ("dbcv",), "Density-based cluster validity. Designed for arbitrary shapes; harsh on centroid partitions."),
    ("silhouette", "partition validity", "↑", ("silhouette",), "Cohesion vs separation. Rewards compact convex clusters — the shape k-means optimises directly."),
    ("Davies-Bouldin", "partition validity", "↓", ("davies_bouldin",), "Mean worst-case ratio of within-cluster scatter to between-cluster separation, in the UMAP-50 cosine space."),
    ("Calinski-Harabasz", "partition validity", "↑", ("calinski_harabasz",), "Ratio of between-cluster to within-cluster dispersion, in the UMAP-50 cosine space."),
    ("cluster separation", "partition validity", "↑", ("mean_ratio", "min_ratio", "n_touching", "n_overlapping"), "Nearest-centroid distance over a cluster's own mean radius, averaged over clusters. Below 1.0 the clusters touch; below 0.7 they overlap."),
    ("Jaccard stability", "partition validity", "↑", ("jaccard_mean", "jaccard_p10", "jaccard_median"), "Bootstrap cluster recovery over 25 subsample refits. Lower bound: UMAP is not refit."),
    ("% evaluated", "coverage", "↑", ("processos_evaluated", "processos_total", "coverage_of_corpus", "share_in_clusters_ge_30", "share_in_clusters_ge_150"), "Share of the corpus inside a cluster that survives the min_traces floor. Captures BOTH discards."),
    ("noise ratio", "coverage", "↓", ("noise_ratio", "noise_ratio_refused", "noise_ratio_before_assignment"), "Share a density method leaves unassigned. noise_ratio is what remains AFTER the default nearest-cluster assignment, so it is zero everywhere and cannot be correlated against; noise_ratio_refused (stored per clustering as noise_ratio_before_assignment) is what density actually refused, and is the variable every abstention claim uses. Zero for k-means and Leiden by construction."),
    ("ARI / NMI vs tipo", "descriptive", "—", ("ari", "nmi", "purity", "majority_baseline", "lift_over_majority", "ari_all", "ari_excl_catch_all"), "Agreement with the declared taxonomy. Reported only; not used as a selection criterion."),
    ("coverage x fidelity", "composite", "↑", ("coverage_fidelity",), "unit_recall x top-1 / (1 + transitions_unseen). An explicit composite used as the outcome variable of the validity-vs-utility correlation and as the sort key of the combos tables, so that a single number trades coverage against fabrication. Its components are always reported separately; it has no independent standing."),
    ("selection score", "composite", "↑", ("score_balanced",), "Min-max scaled combination of common-set accuracy, coverage and silhouette used to elect the deliverable partition; reported under four weightings, and the election must survive all of them."),
    ("selected-best top-1", "downstream", "↑", ("clustered_best_top1",), "Per-cluster maximum over every model family. Not like-for-like against the single-family global baseline; family-matched gains are reported alongside."),
    ("non-inferiority", "control", "↑", ("diff_point", "diff_ci95", "ci90_one_sided_lower", "margin", "sensitivity_margin", "non_inferior", "non_inferior_sensitivity"), "Paired process-level bootstrap of the anonymised arm minus the raw arm, against the pre-registered margin. Pairing is per protocolo within one algorithm; the split is assigned corpus-wide, so both arms score the same cases wherever both clustered them."),
    ("weighting", "context", "—", ("macro", "weighted", "membership_weighted", "unweighted"), "Every aggregate is reported under both weightings: macro/unweighted gives each cluster one vote, weighted/membership_weighted weights by cluster size. A gain that survives only one of them is a property of the weighting, not of the method."),
    ("constrained decoding cost", "control", "—", ("n_decision_steps", "constraint_alters_topk_frac", "constraint_changes_argmax_frac", "unconstrained_argmax_illegal_frac", "no_legal_candidate_frac"), "How often the flow automaton actually changes the ranked candidates, the first prediction, or leaves no legal candidate at all."),
]


NOT_A_PAPER_MEASURE = {
    "n_traces", "n_train", "n_test", "n_clusters", "n_cells", "n_test_sampled",
    "n_train_sampled", "n_processos_with_traces", "n_processos_before_min_states",
    "n_dropped_by_min_states", "n_common", "n_labelled", "n_evaluated", "n_tipos", "n",
    "size_band", "split", "train_frac", "seed", "mode", "dfg_floor", "dfg_coverage_floor",
    "per_trace", "trace", "typical_itinerary", "medoid_itinerary", "medoid_generalization",
    "generalization", "test_protocolos", "p50", "p90", "mean_n_test", "median_size",
    "expected", "present", "missing", "keys", "files",
    "mean", "min", "max", "n_samples", "n_singletons", "space",
    "unidade", "position", "median_actions", "n_matching",
}


def emitted_keys() -> set[str]:
    return {k for _, _, _, emits, _ in METRIC_GLOSSARY for k in emits}


def direction_of(key: str) -> str | None:
    for _, _, arrow, emits, _ in METRIC_GLOSSARY:
        if key in emits:
            return arrow
    return None


def lower_is_better() -> set[str]:
    return {k for _, _, arrow, emits, _ in METRIC_GLOSSARY if arrow == "↓" for k in emits}
