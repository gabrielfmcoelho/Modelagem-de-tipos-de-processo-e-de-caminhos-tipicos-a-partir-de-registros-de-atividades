# `pipeline/core/` — infrastructure and runtime configuration

The foundational layer providing system-wide infrastructure. All other components in `pipeline/` depend on this layer; `core/` has no internal dependencies within the package. This isolation ensures that changes to core infrastructure are isolated and their impact is predictable and traceable.

**Layering exception (documented):** `runner.py` imports `readers/` and `writers/` to select the I/O backend based on stage mode. This does not create a cycle—readers and writers depend on `core` and never on the runner. The runner's orchestration responsibility justifies this localized exception, which is registered in test suite exceptions.

## Modules and Responsibilities

| module | responsibility |
|---|---|
| `config.py` | Environment-driven `Settings` object; single centralized reader for all pipeline configuration. All configuration access must route through this module (no direct `os.getenv` calls elsewhere). Normalizes OpenAI endpoint URLs to end with `/v1` for all downstream consumers |
| `paths.py` | Canonical repository paths: `ROOT` and `ARTIFACTS` directories. This module is the single authoritative source for repository root computation |
| `registry.py`, `_stage_base.py` | Stage registration infrastructure: `@stage` decorator, `StageMeta` dataclass, `RunContext` execution context, phase taxonomy, dependency resolution algorithm |
| `cypher/` | Cypher query template library organized by concern. `SETUP_CONSTRAINTS` (28 queries for graph schema) and `NER_SETUP_CONSTRAINTS` (5 queries for entity layer) are maintained as distinct sets |
| `neo4j_driver.py`, `trino_source.py` | Connection management for Neo4j database and Trino/Iceberg data source |
| `deployment.py` | Institution-identifying string defaults (orgão, sigla) with environment override capability. Defaults are configured to reproduce production parameters exactly |
| `state.py`, `doc_store.py`, `parsed_store.py` | Checkpoint management and document storage abstraction |
| `logging_setup.py`, `console.py` | Output formatting and logging configuration |

## Identity Configuration in `deployment.py`

The two research outputs have inverse identity requirements: the English manuscript (Springer) requires double-blind formatting without author or institutional identification, while the Portuguese manuscript (ABNT/TCC) requires identified author, advisor, and institution. Hardcoding institutional identifiers would prevent the double-blind build. The solution is parameterization with defaults matching production: `PIPELINE_ORGAO_*` environment variables allow override while preserving artifact reproducibility. Setting these variables to redaction tokens enables anonymous runs.

## Neo4j Schema Specification

The Cypher query templates are organized into two constraint sets:

**`SETUP_CONSTRAINTS` (28 queries):** Graph schema definition executed by `precreate` stage
- Node uniqueness constraints on `:Processo`, `:Atividade`, `:Unidade`, `:Documento`, `:Orgao`, `:TipoAcao`, `:GrupoAtividade`
- Property indexes for query optimization
- Vector index for document embeddings

**`NER_SETUP_CONSTRAINTS` (5 queries):** Entity layer schema executed by `ner_load` stage
- Node uniqueness constraints on `:PessoaFisica`, `:PessoaJuridica`, `:CargoFuncao`, `:Legislacao`, `:ContratoEdital`

These sets are intentionally separated: `cypher/__init__.py` both defines module-level names and re-exports from submodules. Submodule re-exports must not shadow `__init__`-defined names. Test `test_no_package_init_is_shadowed_by_its_own_reexports` enforces this invariant.
