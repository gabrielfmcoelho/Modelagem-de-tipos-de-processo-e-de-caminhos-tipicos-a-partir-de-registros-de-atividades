# `pipeline/` — the research execution package

The implementation of the AI pipeline process mining study. A single Typer CLI entry point (`python -m pipeline`), a unified stage registry, and a deterministic execution DAG. The registry is authoritative; [`docs/architecture/stage-registry.md`](../docs/architecture/stage-registry.md) is generated from it.

## Architectural Organization

The package follows two organizing principles:

1. **Layering (directories):** Strict import hierarchy defining data dependencies and reusability
   - `core/` ← everything else
   - `model/` ← stages, evidence, readers/writers
   - `readers/`, `writers/` ← stages
   - `stages/` ← evidence, apps
   - `evidence/` ← apps
   - `apps/` ← nothing

2. **Phases (execution order):** The logical sequence in which the pipeline executes
   ```
   ingest → graph → documents → features → clustering → typical-path → evidence → delivery
   ```
   Phases are tracked in `StageMeta.phase` and generated in phase-ordered views. Architectural layers and phases are intentionally orthogonal; forcing alignment would violate the separation of concerns.

## Architectural Layers

| package | responsibility | imports allowed |
|---|---|---|
| [`core/`](core/core.md) | Infrastructure: configuration, registry, Neo4j driver, paths, Cypher templates | none within `pipeline/` |
| [`model/`](model/model.md) | Algorithms and metrics: clustering, feature engineering, typical path extraction, evaluation | `core/` only |
| [`readers/`, `writers/`](readers/readers.md) | I/O abstraction for both Neo4j and JSON backends | `core/` only |
| [`stages/`](stages/stages.md) | Pipeline stages: 47 registered execution steps, each orchestrating a single research question | `core/`, `model/`, `readers/`, `writers/`, `evidence.artifact` |
| [`evidence/`](evidence/evidence.md) | Evidence synthesis: transforms frozen artifacts into numeric results for manuscripts | `core/`, `model/` (+ local imports to `stages` for registry resolution) |
| [`apps/`](apps/apps.md) | CLI interface: Typer entry points for `run`, `list`, `status`, `interactive` | all layers |

**Layering inversion (localized):** `evidence.artifact` performs local imports of `pipeline.stages` within functions to resolve stage metadata during artifact stamping. This is the single accepted inversion; it is local rather than module-level to avoid genuine cyclic imports.

## Architectural Invariants (Enforced)

The following constraints are verified by automated test suite and are necessary for reproducibility:

| Invariant | Verification |
|---|---|
| Code carries meaning through naming and structure; all explanatory prose resides in `.md` documentation | `test_no_comments_or_docstrings` |
| Repository root is accessed only via `core.paths.ROOT`; no module computes it independently | `test_no_module_computes_its_own_repo_root` |
| External scripts correctly anchor the repository root at appropriate depth | `test_scripts_outside_the_package_anchor_the_repo_root_correctly` |
| Package imports are complete and the stage registry is fully populated | `test_the_package_imports_and_the_registry_is_complete` |
| Every executable module containing `main()` includes `__main__` guard for `python -m` invocation | `test_every_module_with_a_main_can_be_run_with_dash_m` |
| Package `__init__.py` re-exports do not shadow names from submodules | `test_no_package_init_is_shadowed_by_its_own_reexports` |
| Every registered stage declares an explicit phase | `test_no_stage_defaults_its_phase_silently` |
| Every registered stage appears in reference documentation | `test_every_registered_stage_appears_in_the_reference_docs` |
| Every architectural package provides documentation (`.md`) | `test_every_architectural_package_explains_itself` |
| Deployable package contains no copyleft dependencies | `test_no_copyleft_dependency_reaches_the_deployable_package` |
| Test suite does not write into real `artifacts/` tree | `conftest.artifacts_stay_read_only` |
| Every artifact file declares its producing stage in provenance metadata | `pipeline run artifact-audit --flag strict=true` |
