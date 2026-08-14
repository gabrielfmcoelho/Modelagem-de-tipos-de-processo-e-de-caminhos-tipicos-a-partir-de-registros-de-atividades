# `pipeline/model/` — scientific algorithms and analysis methods

Every algorithm referenced in research claims resides in this layer. **Strict constraints:** no I/O operations, no Neo4j calls, no CLI logic. Each function operates on data and returns data, enabling testable unit behavior without external dependencies. This isolation allows verification of reproducibility: `cluster-audit` can refit all 19 clusterings from stamped feature matrices and recover identical labels.

For verification of what the study actually implemented, this layer is authoritative. `stages/` only provides orchestration; the computational logic and decision-making reside here.

## Map

| area | modules | card |
|---|---|---|
| clustering | `clustering/` — `_dispatch.py` (`fit`), `catalog.py`, `naming.py`, and one folder per algorithm | one `.md` per algorithm |
| typical path | `typical_path/` — `_torch_base.py` plus one folder per model | one `.md` per model, plus [`alphabets.md`](typical_path/alphabets.md) and [`protocolo-de-avaliacao.md`](typical_path/protocolo-de-avaliacao.md) |
| evaluation | `typical_eval.py` (the harness), `predict.py` (split + next-step scoring), `aggregate.py` | [`typical_path/protocolo-de-avaliacao.md`](typical_path/protocolo-de-avaliacao.md) |
| features | `processo_features.py`, `cluster_metrics.py` | — |
| documents | `parsing/`, `ner/`, `anonymize.py`, `classifier.py`, `embedding.py`, `keywords.py` | `parsing/parsing.md` |
| graph analysis | `timeline.py`, `dfg.py`, `gcn.py`, `comum_graph.py`, `link_score.py`, `cohort.py` | — |

**`aggregate.py` contains critical aggregation logic:** Functions `macro_mean`, `weighted_mean`, and `both_means` are the **sole authoritative definitions** for aggregating per-cluster metrics into per-cell numbers. The evidence layer imports and uses these functions (re-exported as `_wmean` in `evidence/shared/stats.py`). This centralized definition prevents the prior risk of divergent implementations across the codebase. Layering permits `evidence` → `model` imports but not reverse; this ensures single source of truth.

## Model Cards as Method Documentation

Every registered algorithm is accompanied by a `.md` model card residing adjacent to its code. Model cards are essential method documentation, not supplementary: they state the research question the algorithm addresses, its complete hyperparameter specification, and its determinism classification. Reproducibility depends on this information as fundamentally as on the algorithm itself.

**Determinism classification:**
- Clustering algorithms (HDBSCAN, Leiden, KMeans, consensus): seeded, deterministic on replay
- Neural models (GRU, LSTM, Transformer): non-deterministic, trained on GPU with floating-point variability

**Card completeness requirements:**
1. Every hyperparameter table claims completeness; every constructor argument must appear, including default values set to zero
2. Every card documents which hyperparameters the operational harness actually uses. Example: `aux_lambda > 0` and `fit_rl` are implemented and tested but `typical_eval.py` invokes models only with `epochs` parameter, so those values do not appear in any manuscript figure. Cards explicitly state this.

## Import Boundaries

`model/` imports only from `core/`. It does not import from `stages/`, `evidence/`, `readers/`, or `writers/`. This isolation enforces that algorithms remain stateless and composable:
- Input data is passed as function arguments
- Computed results are returned to the caller
- Persistence is the caller's responsibility
