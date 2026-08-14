# Chen 2024 — BGE M3-Embedding

**Citation.** Chen, J., Xiao, S., Zhang, P., Luo, K., Lian, D., & Liu, Z. (2024). *BGE M3-Embedding:
Multi-Lingual, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation*.
arXiv:2402.03216.
**Link.** https://arxiv.org/abs/2402.03216 · **Type.** recent · **Topic.** document embeddings

## Why it matters to our work
The **actual embedding model** we run (`BAAI/bge-m3`, 1024-d) to embed the 12,259 parsed SEI documents. Its
**multilingual** capability matters because our corpus is **Portuguese** administrative text — a setting where
English-only embedders underperform. The first-doc bge-m3 vector is the strongest block of our clustering
features.

## Key takeaways
- Multilingual, multi-granularity (sentence→document) dense embeddings, 1024-d.
- Strong on retrieval/semantic-similarity across languages incl. pt-BR.

## How we cite it
Method: the document encoder for cluster features (reproducibility — exact model + dimension).
