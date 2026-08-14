# Reimers & Gurevych 2019 — Sentence-BERT

**Citation.** Reimers, N., & Gurevych, I. (2019). Sentence-BERT: Sentence Embeddings using Siamese
BERT-Networks. *EMNLP 2019*. arXiv:1908.10084.
**Link.** https://arxiv.org/abs/1908.10084 · **Type.** recent · **Topic.** document embeddings

## Why it matters to our work
Establishes the **sentence/document embedding** paradigm we use to turn each SEI document's text into a vector
for clustering features. Our embedder (BGE-M3) is a multilingual successor in this lineage; SBERT is the
canonical citation for "dense semantic embeddings of text via transformer encoders, comparable by cosine".

## Key takeaways
- Siamese fine-tuning → embeddings where cosine similarity ≈ semantic similarity (the property our first-doc
  semantic block relies on).

## How we cite it
Method/background for the document-embedding feature block of clustering.
