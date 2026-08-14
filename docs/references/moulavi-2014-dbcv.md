# Moulavi 2014 — DBCV (Density-Based Clustering Validation)

**Citation.** Moulavi, D., Jaskowiak, P. A., Campello, R. J. G. B., Zimek, A., & Sander, J. (2014).
Density-Based Clustering Validation. In *SDM 2014*, SIAM, 839–847.
**Link.** https://doi.org/10.1137/1.9781611973440.96 · **Type.** classic (the metric) · **Topic.** cluster validation

## Why it matters to our work
The metric by which we report our clustering quality (**DBCV = 0.556**). It is the *correct* validator for
HDBSCAN because, unlike the silhouette coefficient (which assumes convex, equal-size clusters), DBCV is defined
for **arbitrary-shaped density clusters** — comparing each cluster's internal density to the sparsity of the
valleys between clusters, on [−1, +1]. It is **not** our evidence that the types are real structure — that rests on the shuffled-partition control. DBCV and silhouette were found to track cluster granularity rather than downstream utility (article §6.2).

## Key takeaways
- Density-sparseness (within) vs density-separation (between) via mutual-reachability MSTs.
- Valid for non-convex clusters → the right score to publish for a density-based pipeline.

## How we cite it
Method/evaluation: justification for DBCV over silhouette and the interpretation of our 0.556.
