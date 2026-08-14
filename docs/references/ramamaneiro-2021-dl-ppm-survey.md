# Rama-Maneiro 2021/2023 — Deep Learning for Predictive Process Monitoring: Review and Benchmark

**Citation.** Rama-Maneiro, E., Vidal, J. C., & Lama, M. (2023). Deep Learning for Predictive Business Process
Monitoring: Review and Benchmark. *IEEE Transactions on Services Computing*, 16(1), 739–756 (online 2021).
**Link.** https://doi.org/10.1109/TSC.2021.3139807 · **Type.** recent (survey + benchmark) · **Topic.** PPM

## Why it matters to our work
The systematic review + reproducible benchmark of deep-learning PPM (10 approaches × 12 logs). It positions our
choices (LSTM/Transformer, next-activity + suffix metrics) within the state of the art and supplies the
**standard evaluation protocol** (temporal split, top-1/top-3, suffix distance) we follow in `gen_08`/`gen_10`.

## Key takeaways
- No single architecture dominates across logs — **dataset matters** (echoes our finding that the Transformer
  beats the GRU only on the largest cohort).
- Establishes the metrics and the train/test discipline we adopt.

## How we cite it
Related work (situating our models) and methodology (evaluation protocol + the "no universal winner" caveat).
