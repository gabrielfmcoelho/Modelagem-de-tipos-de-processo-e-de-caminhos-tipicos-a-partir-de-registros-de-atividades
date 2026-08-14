# Evermann 2017 — Predicting Process Behaviour Using Deep Learning

**Citation.** Evermann, J., Rehse, J.-R., & Fettke, P. (2017). Predicting process behaviour using deep learning.
*Decision Support Systems*, 100, 129–140.
**Link.** https://doi.org/10.1016/j.dss.2017.04.003 · **Type.** classic (contemporary to Tax) · **Topic.** PPM · sequence models

## Why it matters to our work
The other foundational 2017 deep-PPM paper — an RNN/LSTM over activity sequences with **embedding-based**
encoding (rather than one-hot), which is the encoding family our `_TorchSeqModel` uses. Together with Tax 2017
it establishes that recurrent nets are the default neural baseline for next-activity prediction, which our
Markov-vs-GRU-vs-Transformer comparison extends.

## Key takeaways
- Word-embedding analogy for activities; RNN language-model view of traces — the conceptual basis for treating a
  trace as a "sentence" of `tipo@lane` tokens.

## How we cite it
Related work / baseline framing for the neural predictor.
