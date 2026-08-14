# `pipeline/evidence/` — results synthesis and validation

The evidence layer transforms frozen artifacts into research findings. **No Neo4j access:** all evidence stages read from stamped artifacts and produce numeric results, figures, tables, and `RESULTS.md`.

This separation from `stages/` enables auditability: the entire evidence layer executes on any machine in seconds without database access and produces bit-identical output on replay. Verification command: `pipeline run results --flag check=true`.

## Module Responsibilities

| module | responsibility |
|---|---|
| `artifact.py` | **Provenance stamping:** `write_artifact` (JSON), `write_sidecar` (.gz/.npz), `build_meta`, `inputs_match` |
| `etl/` | Corpus flow analysis (funnel), trace freezing, corpus-bias verification |
| `clustering/` | Taxonomy agreement verification, selection score computation, k-sweep analysis, cluster catalog |
| `typical_path/` | Cells extraction, control computation, shared population analysis, temporal hold-out evaluation, constraint cost |
| `results/` | **Authoritative numeric source:** `results_figures.py` produces `results_figures.json`; `results_tex.py` and `results_doc.py` generate LaTeX tables and `RESULTS.md` |
| `shared/` | Shared utilities: double-blind anonymization, glossary, statistical aggregation, paths |
| `stage_doc.py` | Registry-to-markdown rendering for documentation generation |

## Verification Contracts

The evidence layer enforces four invariants:

1. **Single authoritative numeric source:** `results_figures.json` is the only permitted origin for all paper figures; every number in manuscripts must trace to a path in this file
2. **Generated tables only:** Hand-edited `.tex` table files are forbidden; tables are generated from `results_figures.json` exclusively
3. **Bidirectional consistency checking:** `test_manuscript_claims.py` verifies agreement:
   - Prose claim → artifact must exist and match
   - Artifact change → prose must reflect change
4. **Registered and translated numbers:** Any numeric claim in running prose must appear in the results register in both Portuguese and English

## Import Boundaries and Layering Exception

`evidence/` imports from `core/` and `model/`. For artifact stamping, `evidence/artifact.py` performs local (function-level) imports of `stages` to resolve stage metadata. This is the single accepted layering inversion: registration occurs via side effects, making module-level import impossible without creating a genuine cycle. Do not extend this exception to other modules.

## Fail-Fast Error Semantics

Evidence computations use fail-fast semantics: missing or mismatched inputs raise errors with context (filename, value counts) rather than returning empty or zero values. Example: `taxonomy()` validates cluster labels against `artifacts/cache/tipo_procedimento.json`; when no matching protocolo exists, it raises an error naming the file and reporting mismatched counts. An empty result would appear as a valid table with zero rows, misleadingly suggesting a finding. This convention applies uniformly across all evidence aggregations.
