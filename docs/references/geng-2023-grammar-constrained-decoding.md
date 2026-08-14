# Geng 2023 — Grammar-Constrained Decoding for Structured NLP Tasks

**Citation.** Geng, S., Josifoski, M., Peyrard, M., & West, R. (2023). Grammar-Constrained Decoding for
Structured NLP Tasks without Finetuning. *EMNLP 2023*. arXiv:2305.13971.
**Link.** https://aclanthology.org/2023.emnlp-main.674/ · **Type.** recent · **Topic.** constrained generation

## Why it matters to our work
The NLP-side precedent for our central contribution. Grammar-constrained decoding **masks, at each step, the
tokens that would violate a formal grammar**, guaranteeing structurally-valid output *without retraining* —
which is exactly what `generate_constrained` does with `FlowState.allows` over `tipo@lane` tokens. We can frame
our validity machine as a domain-specific grammar-constrained decoder for administrative process traces.

## Key takeaways
- Inference-time masking of the next-token distribution → outputs *provably* satisfy the grammar.
- No finetuning needed — the model still picks *among the legal options* by its learned probabilities (our exact
  design).

## How we cite it
Method (the formal basis for constrained decoding) and positioning (our Phase-2 "negative result" — richer
tokens don't replace the decode-time guarantee — mirrors this literature's findings).
