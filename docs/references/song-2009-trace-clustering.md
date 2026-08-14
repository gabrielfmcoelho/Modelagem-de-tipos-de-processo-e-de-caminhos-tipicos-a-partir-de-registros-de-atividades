# Song 2009 — Trace Clustering in Process Mining

**Citation.** Song, M., Günther, C. W., & van der Aalst, W. M. P. (2009). Trace Clustering in Process Mining.
In *BPM 2008 Workshops*, LNBIP 17, Springer, 109–120.
**Link.** https://doi.org/10.1007/978-3-642-00328-8_11 · **Type.** classic · **Topic.** trace clustering · process variants

## Why it matters to our work
Defines **trace profiles** — characterizing each case by features (activities, transitions, performers, data)
to drive clustering. Our per-processo `cluster_features` (first-doc embedding + topic + unit-flow TF-IDF +
tipo-ação histogram) is a modern, embedding-augmented instance of exactly this idea, and our goal — splitting a
diverse log into homogeneous subsets ("variants") — is the goal stated here.

## Key takeaways
- Profile families (activity / transition / performer / data) → distance → clustering.
- Trace clustering exposes **process variants**; the term/framing we use for our emergent process types.

## How we cite it
Method (our feature-vector + clustering design) and terminology (variants / cohorts).
