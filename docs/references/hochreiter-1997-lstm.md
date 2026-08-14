# Hochreiter & Schmidhuber 1997 — Long Short-Term Memory

**Citation.** Hochreiter, S., & Schmidhuber, J. (1997). Long Short-Term Memory. *Neural Computation*, 9(8),
1735–1780.
**Link.** https://doi.org/10.1162/neco.1997.9.8.1735 · **Type.** classic · **Topic.** sequence models

## Why it matters to our work
The architecture underneath every deep-PPM predictor we and the literature use. The gating that lets an RNN
carry information across long gaps is what (in principle) lets a trace model remember a far-back REMETIDO when
it later sees a RECEBIDO — the long-range dependency at the heart of our validity problem.

## Key takeaways
- Constant-error carousel / gates solve the vanishing-gradient problem of vanilla RNNs.

## How we cite it
Background for the GRU/LSTM family; the canonical origin citation for our recurrent predictor.
