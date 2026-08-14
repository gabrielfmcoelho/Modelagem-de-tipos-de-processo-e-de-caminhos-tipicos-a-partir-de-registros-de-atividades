# Günther & van der Aalst 2007 — Fuzzy Mining (spaghetti / unstructured processes)

**Citation.** Günther, C. W., & van der Aalst, W. M. P. (2007). Fuzzy Mining – Adaptive Process Simplification
Based on Multi-Perspective Metrics. In *BPM 2007*, LNCS 4714, Springer, 328–343.
**Link.** https://doi.org/10.1007/978-3-540-75183-0_24 · **Type.** classic · **Topic.** unstructured process mining

## Why it matters to our work — the *messy, unstandardized SEI*
**The canonical reference for our problem's hardest feature.** The current Piauí-government SEI is *dirty and
unstandardized*: even similar processes differ, and there is **no strong enforcement** of document types, unit
routing, or when a unit concludes. Günther & van der Aalst named exactly this: *"real-life processes turn out to
be less structured than people tend to believe"*, and naïve discovery yields **"spaghetti-like" models** that
show every detail without separating signal from noise.

Their answer — *adaptive simplification*: keep significant, correlated behavior and abstract away the rest, like a
**roadmap** choosing a faithful level of detail — is the principle behind our **`coverage_floor`** (keep the
generic highways most cases take) and our **clustering-then-model-each-family** strategy (turn one spaghetti log
into many homogeneous, readable timelines). It justifies why we do **not** present a single global model.

## Key takeaways
- Unstructured processes ⇒ spaghetti models; simplify by significance/correlation metrics ("roadmap" abstraction).

## How we cite it
Problem statement (unstandardized SEI), and method/justification for our simplification + per-cluster modeling.
