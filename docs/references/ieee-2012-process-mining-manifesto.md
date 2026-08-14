# IEEE Task Force 2012 — Process Mining Manifesto

**Citation.** van der Aalst, W. et al. (IEEE Task Force on Process Mining) (2012). *Process Mining Manifesto*.
In *BPM 2011 Workshops*, LNBIP 99, Springer, 169–194.
**Link.** https://doi.org/10.1007/978-3-642-28108-2_19 · **Type.** classic (position paper) · **Topic.** process-mining foundations

## Why it matters to our work
The community's statement of guiding principles and challenges. It explicitly names **event-log quality**,
**concept drift**, **representational bias**, and **cross-organizational mining** — the exact pragmatic issues we
confront in a real government log (missing/parsed documents, open vs concluded cases, unit-sigla granularity).

## Key takeaways
- Six guiding principles (e.g. "log quality matters", "models should be treated as purposeful abstractions").
- Eleven challenges — several of which our methodological choices directly address (e.g. balancing model
  simplicity vs accuracy → our `coverage_floor` / `lane_depth` decisions).

## How we cite it
Methodology / threats-to-validity: to motivate our log-cleaning, the concluded-only filter, and the explicit
discussion of representational choices (lane granularity).
