# Vaswani 2017 — Attention Is All You Need

**Citation.** Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., Kaiser, Ł., &
Polosukhin, I. (2017). Attention Is All You Need. *NeurIPS 2017*. arXiv:1706.03762.
**Link.** https://arxiv.org/abs/1706.03762 · **Type.** classic · **Topic.** sequence models · attention

## Why it matters to our work
The Transformer architecture our `TransformerModel` implements (token + positional embeddings → encoder →
linear head). The motivation we test directly: self-attention reaches **arbitrary-distance dependencies** in one
hop, which should help the long-range RECEBIDO↔REMETIDO pairing better than a recurrent state.

## Key takeaways
- Self-attention replaces recurrence; positional encodings inject order; attention weights are inspectable
  (explainability).

## How we cite it
Method (our Transformer arm) and the long-range-dependency hypothesis we evaluate.
