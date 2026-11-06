---
type: architecture
title: Stage DAG and Registry
description: How stages register themselves by decorator, what StageMeta declares, how dependency resolution orders and validates a plan, the nine research phases, and how the runner drives a resolved plan.
tags: [stage-registry, dag, topological-sort, pipeline, orchestration, phases]
verified:
  - by: openwiki/0.5.0
    at: 2026-09-10T12:46:32.229Z
sources:
  - id: openwiki-source-d01648e7869f87d45b2226f0
    resource: repo://pipeline/app.py
  - id: openwiki-source-921c192327e2f98033066a7a
    resource: repo://pipeline/apps/list.py
  - id: openwiki-source-f201f1be48b48643ec061fae
    resource: repo://pipeline/core/_stage_base.py
  - id: openwiki-source-f78e643a8b1eac6859e6a07b
    resource: repo://pipeline/core/registry.py
  - id: openwiki-source-3d20aa9e6ace8985f48b41af
    resource: repo://pipeline/core/runner.py
  - id: openwiki-source-5c37c55bce570f82e4400c63
    resource: repo://pipeline/evidence/artifact.py
  - id: openwiki-source-f8a01b05a1aa75534536509b
    resource: repo://pipeline/evidence/stage_doc.py
  - id: openwiki-source-b4a64d200c21c76aee2a0067
    resource: repo://pipeline/stages/__init__.py
  - id: openwiki-source-bbac6e3d793c89810e95443c
    resource: repo://pipeline/stages/_bootstrap.py
  - id: openwiki-source-3dab3019deaab997ed09d50b
    resource: repo://pipeline/stages/processo_embed.py
  - id: openwiki-source-3c6a5bfbf4a5f6f8d99988b8
    resource: repo://pipeline/tests/test_registry.py
  - id: openwiki-source-05ccef8d4cf1698187f20464
    resource: repo://pyproject.toml
generated: { by: "claude-code", at: "2026-09-10T12:46:32.229Z" }
---

# Stage DAG and Registry

The pipeline is a set of independently declared stages joined by declared
dependencies. Nothing hand-orders them: a caller names the stages it wants and
the registry computes the order, pulls in what is missing, and refuses cycles.
This is the backbone every other page hangs from.

## Registration by decorator

A stage is a function taking a `RunContext` and returning `None`, decorated with
`@stage(StageMeta(...))`. The decorator inserts a `StageDef` — metadata plus
function — into the module-global `_REGISTRY` keyed by stage name, and returns
the function unchanged so it remains directly callable.

Registering a name twice is a hard error. The decorator raises `RuntimeError`
naming the function that already holds the name, which turns an accidental
collision between two stage modules into an import-time failure rather than a
silent shadowing.

Because registration is an import side effect, the registry is populated by
importing `pipeline.stages`, whose `__init__.py` imports every stage module for
exactly that reason. `pipeline/app.py` in turn imports the package. Both files
carry a `ruff` per-file `F401` exemption in `pyproject.toml`, which is how the
project records that these apparently unused imports are load-bearing.

The registry also exposes `clear()`, which exists so tests can swap in an
isolated registry — `pipeline/tests/test_registry.py` saves the real one,
clears, registers fixtures, and restores in a `finally`.

## What StageMeta declares

`StageMeta` is a frozen dataclass, so a registered stage's metadata cannot be
mutated after registration.

| Field | Meaning |
|---|---|
| `name` | Registry key and CLI identifier |
| `description` | One-line summary shown by `pipeline list` |
| `type` | `bootstrap`, `core`, `enrich` or `op` — grouping for display |
| `phase` | One of the nine research phases |
| `depends_on` | Hard dependencies; resolved and executed first |
| `soft_depends_on` | Advisory dependencies; warned about, never enforced |
| `modes` | Execution modes the stage supports |
| `can_skip_when_done` | Whether a completed checkpoint permits skipping |
| `estimated_duration` | Free-text operator hint |
| `question` | The research question the stage answers |
| `deterministic` / `nondeterminism` | Reproducibility declaration and its reason |

The last two fields are unusual for a pipeline framework and are central here.
`deterministic` may be a boolean or a string, and `nondeterminism` records *why*
a stage is not reproducible. Both are copied verbatim into the stage ledger and
into every artifact's provenance envelope, so a downstream auditor reads a
stage's reproducibility claim from the same declaration the code registered
rather than from prose that can drift.

### The nine phases

`Phase` is a closed literal ordered by `PHASE_ORDER`: `ingest`, `graph`,
`documents`, `features`, `clustering`, `typical-path`, `evidence`, `delivery`,
`operations`. `PHASE_QUESTION` maps each to the research question that phase
answers, written in Portuguese — a convention that runs through the repository,
where code identifiers are English but the research-facing descriptions,
questions and stage summaries are in the language of the study.

The phase taxonomy is not merely decorative grouping: `pipeline/evidence/stage_doc.py`
walks `PHASE_ORDER` and `PHASE_QUESTION` to generate the stage documentation from
the live registry, so the documented phase structure cannot fall out of step with
the registered stages.

## Resolution

`resolve(names, include_deps=True)` returns an ordered list of `StageDef`.

It validates first and traverses second: **every** requested name is checked
against the registry up front, so an unknown stage raises `StageNotFoundError`
before any partial plan is built. It then runs a three-colour depth-first search
— white unvisited, grey on the current path, black finished — appending each node
in post-order. Encountering a grey node means the path has re-entered itself, and
`CyclicDependencyError` is raised naming that stage. Black nodes return
immediately, so a diamond dependency is visited once and appears once.

`include_deps=False` (the `--no-deps` flag) changes only which edges are
followed: a dependency is still visited if it is itself among the requested
names. The consequence, pinned by test, is that `--no-deps` with several stages
still orders those stages topologically relative to one another — it suppresses
*pulling in* absent dependencies, not ordering.

### Soft dependencies

`soft_depends_on` expresses "this stage produces better output if that one has
run", not a requirement. `soft_dep_warnings` compares each selected stage's soft
dependencies against the selected set and returns the missing pairs; the runner
logs each as a warning before execution begins. Soft dependencies never affect
ordering and never fail a run.

The distinction carries real meaning in the DAG. `processo-embed`, for example,
hard-depends only on `embed` while soft-depending on `permanencia`, `atividades`
and `evaluate` — it can produce a feature vector from document embeddings alone,
but a richer one when the graph-derived signals exist.

### An unused seam

`check_mode` is defined in the registry to return the stages incompatible with a
given mode, but nothing calls it. The runner takes a different approach —
per-stage fallback in `_resolved_mode_for` — so plans are never rejected wholesale
for mode incompatibility. The helper is available should a pre-flight validation
be wanted.

## Macro stages

`etl` and `etl-full` are registered stages whose functions do nothing but
`return None`. Their entire content is `depends_on`: `etl` names the five graph
stages, and `etl-full` names `etl` plus the document, entity, embedding and
clustering stages.

This is composition through the dependency graph rather than through function
calls, and it has a useful property — a macro cannot drift from what it claims to
run, because "running the macro" *is* resolving its dependencies. It also means
macros participate normally in checkpointing, mode resolution and the ledger.

`etl-full` additionally declares `deterministic=False` with the reason
`"inclui etapas de LLM (parse, evaluate, naming)"`, so the non-reproducibility of
the full pipeline is stated where the composition is defined.

## From plan to execution

`run_stages` resolves the plan, picks a mode, emits soft-dependency warnings,
takes the run lock, and iterates. For each stage it consults the checkpoint,
resolves the stage's actual mode, builds the I/O for that mode, constructs a
`RunContext`, and calls the stage function.

`RunContext` is the whole surface a stage sees: settings, its resolved mode, the
flag dictionary, the state directory, the shared per-run cache, the writer,
reader and driver for its mode, and a progress handle. The `require_*` accessors
convert an absent writer, reader or driver into an error naming the flag that
would have supplied it, and `cached` memoises an expensive value for the rest of
the run.

Progress is reported through a `StageProgress` abstraction whose default
implementation is a no-op, with `_RichProgress` adapting it onto a Rich progress
bar. A stage calls `set_total` and `advance` without knowing whether anything is
rendering.

## Inspecting the DAG

- `pipeline list` tabulates every registered stage grouped by type, showing
  dependencies, supported modes and descriptions.
- `pipeline graph [stages…]` prints the resolved topological order; with no
  arguments it resolves every non-`bootstrap` stage, which renders the whole DAG.
- `pipeline run … --dry-resolve` prints the plan annotated with each stage's
  checkpoint status and the mode it would actually run in, without executing.

## Related pages

- [Execution Modes and Graph I/O](execution-modes-and-graph-io.md)
- [Run State, Skipping and the Stage Ledger](run-state-and-resumability.md)
- [CLI Surface and Operating the Pipeline](../operations/cli-and-runbook.md)
