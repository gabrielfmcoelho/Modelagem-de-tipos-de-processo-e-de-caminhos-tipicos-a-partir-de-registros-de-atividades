# Bukhsh 2021 — ProcessTransformer

**Citation.** Bukhsh, Z. A., Saeed, A., & Dijkman, R. M. (2021). *ProcessTransformer: Predictive Business
Process Monitoring with Transformer Network*. arXiv:2104.00721.
**Link.** https://arxiv.org/abs/2104.00721 · code: https://github.com/Zaharah/processtransformer
**Type.** recent · **Topic.** Transformer for PPM · sequence models

## Why it matters to our work
Direct precedent for our **`TransformerModel`** — a self-attention network for next-activity prediction that, the
authors argue, captures **long-range dependencies** that LSTMs miss on long traces. This is exactly the
hypothesis we test: whether attention better learns the long-range `RECEBIDO↔REMETIDO` pairing. Our honest
finding (attention edges the GRU only on the largest cohort, ties on small ones) is a useful empirical data
point against their general claim, on small administrative cohorts.

## Key takeaways
- ~80%+ next-activity accuracy; attention scores double as **explanations** (relevant to AI & Law's
  explainability concern).
- Motivated by LSTM weakness on lengthy traces — converges with Tax 2017's repetition problem.

## How we cite it
Method (our Transformer arm) and related work; our results provide a small-data counterpoint and an
explainability hook.
