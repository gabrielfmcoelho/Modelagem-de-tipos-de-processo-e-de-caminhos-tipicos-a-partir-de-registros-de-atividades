# McInnes 2018 — UMAP

**Citation.** McInnes, L., Healy, J., & Melville, J. (2018). *UMAP: Uniform Manifold Approximation and
Projection for Dimension Reduction*. arXiv:1802.03426. (Software: *JOSS* 3(29), 861.)
**Link.** https://arxiv.org/abs/1802.03426 · **Type.** recent (widely used) · **Topic.** dimensionality reduction

## Why it matters to our work
The dimensionality reducer in `processo-embed`: our composite per-processo feature vector (first-doc embedding +
topic + unit-flow TF-IDF + tipo-ação histogram, ~3.6k-dim) is projected to **50-d** with UMAP before HDBSCAN.
UMAP preserves local + some global structure better than PCA/t-SNE for downstream density clustering, which is
why the HDBSCAN step finds well-separated categories.

## Key takeaways
- Manifold-learning embedding; standard preprocessing for HDBSCAN (the UMAP+HDBSCAN pipeline).

## How we cite it
Method: the feature-reduction step of our clustering pipeline.
