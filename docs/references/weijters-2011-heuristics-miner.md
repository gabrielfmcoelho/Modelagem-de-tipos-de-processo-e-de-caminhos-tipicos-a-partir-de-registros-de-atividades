# Weijters & Ribeiro 2011 — Flexible Heuristics Miner (noise-tolerant discovery)

**Citation.** Weijters, A. J. M. M., & Ribeiro, J. T. S. (2011). Flexible Heuristics Miner (FHM). In *IEEE
Symposium on Computational Intelligence and Data Mining (CIDM) 2011*, 310–317. (Orig.: Weijters, van der Aalst &
de Medeiros, *Process Mining with the HeuristicsMiner Algorithm*, TU/e WP 166, 2006.)
**Link.** https://doi.org/10.1109/CIDM.2011.5949453 · **Type.** classic · **Topic.** noise-tolerant process discovery

## Why it matters to our work
Heuristics Miner is the **noise-tolerant** discovery algorithm: it uses *frequency-based* dependency measures so
that **infrequent / exceptional behavior does not corrupt the model** — essential when, as in the Piauí SEI,
there is no enforcement and the log is full of one-off deviations. Our frequency/coverage thresholds
(`coverage_floor`, Markov back-off, the top-K constrained candidates) are in the same spirit: trust the
well-supported transitions, discount the rare noise.

## Key takeaways
- Dependency/frequency heuristics → robust control-flow from noisy logs; handles incompleteness.

## How we cite it
Related work for noise-tolerant discovery; justification for our frequency-based pruning under a noisy log.
