# Camargo 2019 — Learning Accurate LSTM Models of Business Processes

**Citation.** Camargo, M., Dumas, M., & González-Rojas, O. (2019). Learning Accurate LSTM Models of Business
Processes. In *BPM 2019*, LNCS 11675, Springer, 286–302.
**Link.** https://doi.org/10.1007/978-3-030-26619-6_19 · **Type.** recent · **Topic.** PPM · generative process models

## Why it matters to our work
Moves from *prediction* to **generation** — using the trained LSTM to roll out whole traces and a *generative*
model of the process, evaluating the realism of the generated sequences. This is precisely our `gen_08`/`gen_11`
agenda (generate a representative timeline, compare to the real). Their pre/post-processing for sequence realism
parallels our medoid + validity machinery.

## Key takeaways
- Shared categorical embeddings + scaling improve LSTM trace generation.
- Treats generated traces as artifacts to be assessed for fidelity — our exact stance.

## How we cite it
Related work for **generative** PPM and trace-realism evaluation; precedent for using a predictor to generate
representative journeys.
