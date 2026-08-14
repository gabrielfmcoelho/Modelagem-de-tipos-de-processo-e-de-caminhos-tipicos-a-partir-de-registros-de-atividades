# Cho 2014 — GRU (RNN Encoder–Decoder)

**Citation.** Cho, K., van Merriënboer, B., Gulcehre, C., Bahdanau, D., Bougares, F., Schwenk, H., & Bengio, Y.
(2014). Learning Phrase Representations using RNN Encoder–Decoder for Statistical Machine Translation. *EMNLP
2014*. arXiv:1406.1078.
**Link.** https://arxiv.org/abs/1406.1078 · **Type.** classic · **Topic.** sequence models

## Why it matters to our work
Introduces the **Gated Recurrent Unit** — the exact cell in our default neural predictor
(`predict_lstm.LSTMModel` uses `nn.GRU`). We chose the GRU for its competitive accuracy with fewer parameters,
which matters on our small administrative cohorts (a few hundred traces), where the simpler model often wins.

## Key takeaways
- GRU = LSTM with merged gates, fewer parameters → better on small data (consistent with our results).

## How we cite it
Method: the origin of the GRU cell; justification for a compact recurrent model on small cohorts.
