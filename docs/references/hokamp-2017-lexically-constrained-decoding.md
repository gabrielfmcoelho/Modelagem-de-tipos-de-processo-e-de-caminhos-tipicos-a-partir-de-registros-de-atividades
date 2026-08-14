# Hokamp & Liu 2017 — Lexically Constrained Decoding (Grid Beam Search)

**Citation.** Hokamp, C., & Liu, Q. (2017). Lexically Constrained Decoding for Sequence Generation Using Grid
Beam Search. *ACL 2017*. arXiv:1704.07138.
**Link.** https://arxiv.org/abs/1704.07138 · **Type.** classic (constrained-decoding origin) · **Topic.** constrained generation

## Why it matters to our work
An early, widely-cited demonstration that you can **enforce hard constraints at decode time** on a neural
sequence model, steering generation without changing the trained weights. It establishes the general technique
our `generate_constrained` / `generate_full` specialize to process-flow rules, and predates the LLM-era
grammar-constrained work (Geng 2023).

## Key takeaways
- Constraints applied during search, not training — the inference-time-control paradigm.

## How we cite it
Related work: the lineage of constrained decoding our method belongs to.
