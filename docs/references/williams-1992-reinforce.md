# Williams 1992 — REINFORCE (policy-gradient RL)

**Citation.** Williams, R. J. (1992). Simple statistical gradient-following algorithms for connectionist
reinforcement learning. *Machine Learning*, 8(3–4), 229–256.
**Link.** https://doi.org/10.1007/BF00992696 · **Type.** classic · **Topic.** reinforcement learning · generation

## Why it matters to our work
The algorithm behind our **Phase-3 conformance-reward fine-tuning** (`predict_lstm.fit_rl`): we sample traces,
reward each by its `validity_score`, and update the policy with a baseline-subtracted REINFORCE gradient —
training the generator to *prefer* structurally-valid traces rather than only masking at decode time. Our honest
finding (RL is high-variance — it helped some handoffs but hurt some pairing) is consistent with REINFORCE's
known variance, which the baseline only partly tames.

## Key takeaways
- Likelihood-ratio (score-function) gradient estimator; baseline for variance reduction — the exact recipe we use.

## How we cite it
Method (the RL arm of our learn-validity ablation) and the variance caveat in our results.
