# Campello 2013 — HDBSCAN (Hierarchical Density-Based Clustering)

**Citation.** Campello, R. J. G. B., Moulavi, D., & Sander, J. (2013). Density-Based Clustering Based on
Hierarchical Density Estimates. In *PAKDD 2013*, LNCS 7819, Springer, 160–172. (Extended: Campello, Moulavi,
Zimek, Sander, *ACM TKDD* 10(1), 2015.)
**Link.** https://doi.org/10.1007/978-3-642-37456-2_14 · **Type.** classic (the algorithm) · **Topic.** density clustering

## Why it matters to our work
The clustering algorithm behind the density-based arm of the catalogue (`processo-cluster`); it yields 64 types on the raw arm. (An earlier note here said *182 macro + 346 micro* — that is the superseded run.) HDBSCAN's
defining property is the one we leaned on when explaining coverage: it **labels low-density points as noise**
rather than forcing every processo into a cluster (unlike k-means) — which is why our macro coverage is 82% (97%
any-level) with a principled 3% outlier set, and why the categories are clean.

## Key takeaways
- Builds the full hierarchy of DBSCAN* clusterings; extracts a stable flat clustering of **varying density**.
- Explicit **noise** label = honest outliers — a feature we defend, not a defect.

## How we cite it
Method (clustering algorithm) and the density-based / noise-handling argument in our results discussion.
