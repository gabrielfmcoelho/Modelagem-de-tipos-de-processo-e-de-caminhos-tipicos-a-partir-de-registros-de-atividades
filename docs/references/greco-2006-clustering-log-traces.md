# Greco 2006 — Discovering Expressive Process Models by Clustering Log Traces

**Citation.** Greco, G., Guzzo, A., Pontieri, L., & Saccà, D. (2006). Discovering Expressive Process Models by
Clustering Log Traces. *IEEE Transactions on Knowledge and Data Engineering*, 18(8), 1010–1027.
**Link.** https://doi.org/10.1109/TKDE.2006.123 · **Type.** classic · **Topic.** trace clustering

## Why it matters to our work
The origin of the idea that motivates our cluster→cohort design: a heterogeneous log is best understood by
**partitioning traces into homogeneous groups and modeling each separately** — instead of forcing one tangled
model over everything. Greco et al. map traces to feature vectors (n-grams) and cluster — the conceptual
ancestor of our per-processo feature vectors + HDBSCAN.

## Key takeaways
- Clustering log traces yields simpler, more *expressive* per-group models — our justification for analyzing
  each top cluster's timeline separately rather than the whole log.

## How we cite it
Related work: the foundational argument for trace clustering as a precondition to good process models.
