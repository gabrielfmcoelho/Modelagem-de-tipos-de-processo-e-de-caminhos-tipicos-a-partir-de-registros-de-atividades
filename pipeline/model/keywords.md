# Keywords — Incrementally Constructed Controlled Vocabulary

**Research Question:** What domain terminology does the corpus use to self-describe without manual curation by the researcher?

**Implementation:** `pipeline/model/keywords.py` (normalization and merging logic) + `pipeline/stages/keywords.py` (LLM extraction passes). Produces the **sixth feature block** for `processo-embed` stage.

## Rationale

Other semantic feature blocks generate dense, non-interpretable embeddings (document embeddings, topic/summary embeddings). The keyword block serves two purposes:
1. **Interpretability:** Discovered clusters must be human-readable; keywords provide the semantic bridge from vector space to natural language cluster descriptions
2. **Sparsity and interpretability signal:** Keyword features provide sparse, human-interpretable signals complementing dense embeddings

The vocabulary is **incremental and controlled:** LLM proposes candidate terms per document; each proposed term either merges into an existing vocabulary term or enters as new. The vocabulary is never predefined; it grows from corpus-derived proposals.

## Term Admission and Merging

**Normalization (`normalize_keyword`):**
- Lowercase conversion
- Diacritic removal (NFD normalization via `strip_accents`)
- Punctuation removal except `/` and `-`
- Whitespace collapsing
- Unit path collapsing via `collapse_unit_path` (e.g., reducing unit hierarchies)
- Year-like pattern filtering via `_YEARISH` regex (removes isolated years like `2025`, `exercicio 2024`)

**Vocabulary filtering:**
- `STOPWORDS`: Standard language stopwords
- `ORGAO_TERMS`: Administration-identifying terms (e.g., unit names, orgão descriptors) that appear in nearly all processes, providing no discriminative signal. Retaining these would create a constant axis in the feature space.

**Similarity-based merging (`merge_into_vocab`):**
- Compares normalized term against existing vocabulary terms via **character bigram similarity** (Dice coefficient on `_bigrams`)
- Threshold decision: if similarity > 0.9, term merges into existing term; if ≤ 0.9, enters as new term
- Example: threshold determines whether `"licitacao pregao"` and `"licitacao pregoes"` are one term or two
- Exposed as `--flag merge_threshold` parameter

## Hyperparameters

| parameter | default | effect |
|---|---|---|
| `merge_threshold` | `0.9` | Character bigram similarity threshold for term merging |
| `passes` | `PASSES` (constant) | Number of LLM extraction passes over corpus |
| `vocab_top` | `PASS1_VOCAB_TOP` (constant) | Size of current vocabulary provided to LLM in prompt |
| `workers`, `batch` | Per-pass defaults | Parallelism and batch size for LLM invocation |
| `force` | `false` | Force reprocessing of documents already annotated |

**Two-pass design rationale:** First pass extracts terms while building vocabulary from initially empty state; early documents are annotated against sparse vocabulary. Second pass re-annotates all documents against the final, complete vocabulary, ensuring consistent annotation.

## Outputs

| file | content | format |
|---|---|---|
| `artifacts/cache/keyword_vocab.json` | Canonical term → document frequency mapping | JSON dict |
| `artifacts/cache/keywords_by_processo.json` | Process ID (protocolo) → canonical term list | JSON dict |

Both outputs are stamped by the `keywords` stage using `write_sidecar`, not by the model module. This respects layer boundaries: `model/` does not import `evidence/artifact` (the stamper module).

## Determinism Classification

**Non-deterministic (LLM component):** Term proposals are LLM-generated and non-deterministic. 

**Deterministic given fixed terms (normalization and merging):** Normalization and merging are deterministic given:
- Fixed set of LLM-proposed terms
- Fixed arrival order

**Order dependency:** Order matters because vocabulary grows during construction; the first of two similar terms becomes canonical. This is an order-of-arrival dependency, not merely content-based, necessitating vocabulary persistence as an artifact rather than reconstruction per run.

## Known Limitations

**Lexical similarity (character bigrams):** Merging operates on character-level bigram Dice similarity, not semantic similarity.

**Morphological normalization:** Fuses morphological variants (`contrato`/`contratos`) by string similarity.

**Missed synonyms:** Fails to fuse semantically equivalent terms with distinct orthography (e.g., `servidor` vs. `funcionario`). Semantic embeddings would address this limitation, but embedding-based merging was not evaluated in this study.

**Short-term collision risk:** Very short terms may merge incorrectly due to small bigram sets producing coincidental high similarity. No mitigation was implemented.
