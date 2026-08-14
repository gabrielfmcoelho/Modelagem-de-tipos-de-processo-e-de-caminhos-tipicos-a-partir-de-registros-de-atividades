# Tax 2017 — Predictive Business Process Monitoring with LSTM Neural Networks

**Citation.** Tax, N., Verenich, I., La Rosa, M., & Dumas, M. (2017). Predictive Business Process Monitoring
with LSTM Neural Networks. In *CAiSE 2017*, LNCS 10253, Springer, 477–492.
**Link.** https://doi.org/10.1007/978-3-319-59536-8_30 · code: https://github.com/verenich/ProcessSequencePrediction
**Type.** classic (the seminal deep-PPM paper) · **Topic.** predictive process monitoring · sequence models

## Why it matters to our work
This is the **method our predictor is built on**: an LSTM over `tipo@lane` state traces predicting the next
activity, the suffix, and remaining time. We re-implement its core (`predict_lstm.LSTMModel`) and adopt its
evaluation (next-step accuracy + suffix Damerau-Levenshtein distance).

**Crucially**, Tax et al. report that *"LSTMs have problems with logs that contain repeated activities, causing
the model to predict overly long sequences of the same activity"* — the **exact degenerate-generation failure
we observed** (a 689-step trace) and **fixed with constrained decoding**. This paper is therefore both our
baseline *and* the named motivation for our contribution.

## Key takeaways
- One-hot/embedding state encoding → LSTM → next-activity + time; suffix by autoregressive roll-out.
- Acknowledged failure mode: repetition / over-long suffixes — i.e. **no structural validity guarantee**.

## How we cite it
Method (our predictor) **and** problem statement (the motivation for `FlowState`-constrained generation). The
sharpest single citation in the paper.
