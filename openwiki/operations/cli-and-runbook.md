---
type: operations
title: CLI Surface and Operating the Pipeline
description: The Typer command surface — run, list, graph, status and the interactive wizard — the flags that control selection, forcing and modes, the maintenance stages, and container and GPU execution.
tags: [cli, operations, runbook, typer, docker, gpu, maintenance]
verified:
  - by: openwiki/0.5.0
    at: 2026-09-10T12:46:32.229Z
sources:
  - id: openwiki-source-b79fbbd921df689b4bbdc82f
    resource: repo://docker-compose.yml
  - id: openwiki-source-bb1ebe868e35e9e500714501
    resource: repo://Dockerfile
  - id: openwiki-source-c81cc42d569c1153134d495b
    resource: repo://docs/operations/gpu-acceleration.md
  - id: openwiki-source-3e4b669dbed1b8e66f161a5c
    resource: repo://pipeline/__main__.py
  - id: openwiki-source-d01648e7869f87d45b2226f0
    resource: repo://pipeline/app.py
  - id: openwiki-source-5261539b2038cd02baa29e51
    resource: repo://pipeline/apps/interactive.py
  - id: openwiki-source-957449a1f9c87853515e83b2
    resource: repo://pipeline/apps/run.py
  - id: openwiki-source-3d20aa9e6ace8985f48b41af
    resource: repo://pipeline/core/runner.py
  - id: openwiki-source-1fc4108dd6acd4bbaea4f5c2
    resource: repo://pipeline/stages/clean.py
  - id: openwiki-source-c47e336616b1b5261680687f
    resource: repo://pipeline/stages/graph_health.py
  - id: openwiki-source-c1089d915617e9dde125c0f7
    resource: repo://pipeline/stages/ner_extract.py
  - id: openwiki-source-3120143f5f08fe3158b3395b
    resource: repo://pipeline/stages/resumo.py
  - id: openwiki-source-05ccef8d4cf1698187f20464
    resource: repo://pyproject.toml
generated: { by: "claude-code", at: "2026-09-10T12:46:32.229Z" }
---

# CLI Surface and Operating the Pipeline

Everything the pipeline does is reachable through one Typer application. This
page covers the operator's view: how commands are assembled, what the flags mean,
how to inspect state before committing to a long run, and how the maintenance
stages behave.

## The application

`pipeline/app.py` builds the Typer app and four sub-applications register
commands onto it: `interactive`, `run`, `list` and `status`. Two entry points
reach the same object — the `pipeline` console script declared in
`pyproject.toml`, and `python -m pipeline` via `pipeline/__main__.py`.

The app is created with `no_args_is_help=False`, which is deliberate: the
interactive module registers a Typer callback with `invoke_without_command=True`,
so an invocation with no subcommand falls through to the wizard rather than
printing help.

Note that the app's help string interpolates `ORGAO_SIGLA` from the deployment
constants, so even the CLI banner honours the institution seam.

## `pipeline run`

The main command. It takes one or more stage names and resolves dependencies
topologically before executing.

| Flag | Effect |
|---|---|
| `--mode` | Force `neo4j`, `json-emit`, `json-replay` or `fs` |
| `--emit-dir` / `--read-dir` | NDJSON capture and replay directories |
| `--from` / `--to` | Date window for the event log |
| `--limit`, `--workers`, `--batch-size`, `--chunk-size` | Volume and parallelism |
| `--force` | Re-run every selected stage, ignoring checkpoints |
| `--force-stage` | Re-run one stage (repeatable), leaving others cached |
| `--no-deps` | Run only the named stages, without pulling dependencies in |
| `--state-dir` | Point at a different checkpoint directory |
| `--dry-resolve` | Print the plan and exit without executing |
| `--flag KEY=VALUE` | Stage-specific flag, repeatable |

`--flag` is the extension point for everything stage-specific. It is parsed by
`_parse_flag`, which rejects a value without `=` as a `typer.BadParameter`
rather than silently ignoring it. The parsed pairs are merged into the same flag
dictionary that carries the standard options, which is how a stage reads both
kinds uniformly from `ctx.flags`.

Two failures are translated into clean operator errors rather than tracebacks:
an unknown stage name prints the name and points at `pipeline list`, and a mode
incompatibility prints the underlying message. Both exit with status 2.

### Before a long run

`--dry-resolve` is the safety check. It resolves the plan, then prints each stage
with its checkpoint status and **the mode it would actually run in** — which may
differ from the requested mode per stage — and returns without executing or
holding the lock.

## `pipeline list` and `pipeline graph`

`list` tabulates every registered stage sorted by type (`bootstrap`, `core`,
`enrich`, `op`) then name, showing dependencies, supported modes and
descriptions.

`graph` prints the resolved topological order for the stages named; with no
arguments it resolves every non-`bootstrap` stage, rendering the full DAG in
execution order with each stage's dependencies annotated.

## `pipeline status`

A read-only three-part view: filesystem counts for the download, parsed
document, NER and emit directories; live Neo4j node and relationship counts by
label; and the checkpoint table for every registered stage.

It degrades rather than failing. Absent Neo4j credentials produce a hint instead
of a table, an unreachable database produces a table marked `UNREACHABLE`
carrying the error, and a missing directory renders as a dash rather than a zero.

## The interactive wizard

Running `pipeline` with no subcommand starts a `questionary` wizard that walks an
operator through building a run. It is more than a menu — it applies three checks
that a hand-typed command would not.

First, stage choices are annotated from the state directory, so each option
carries `✓ done` or `✗ failed` with the date.

Second, after selection it resolves the plan and reports which stages were
**auto-added as dependencies**, so the operator sees the true scope before
confirming.

Third — and this is the wizard's only genuinely distinct piece of logic —
`_common_modes_for` intersects the supported modes of every stage in the resolved
plan and offers only modes all of them share. When the intersection is empty it
refuses and asks the operator to narrow the selection. This is stricter than
`pipeline run`, which would instead fall each stage back to its own first
declared mode.

The wizard prompts for a date window and worker count only when the plan contains
a stage that consumes them (`precreate`, `atividades` or `etl`), prints the
numbered plan with each stage's estimated duration, and requires an explicit
confirmation before running.

## Maintenance stages

Three `operations`-phase stages exist for running the system rather than
producing evidence. All three declare `can_skip_when_done=False`, since a cached
answer about current state would be worthless.

**`clean`** destroys graph state. In JSON modes it removes the emit directory
tree. In `neo4j` mode it deletes relationships in batches of five thousand and
nodes in batches of ten thousand, looping until a batch comes back empty, then
drops every constraint and every non-`LOOKUP` index. Batching is what keeps the
deletion of a multi-million-element graph inside transaction limits, and
`LOOKUP` indexes are excluded because Neo4j maintains those itself.

`clean` also keeps a standalone `main()` with its own argument parser. That path
— and only that path — prompts for interactive confirmation before deleting,
requiring a literal `y` unless `--force` is passed. **Invoked as a stage through
`pipeline run clean`, there is no confirmation prompt**; the stage function
deletes immediately.

**`graph-health`** is a read-only connectivity report identifying isolated nodes
by type. It soft-depends on `timeline`, since the flow edges it inspects are what
that stage builds.

**`resumo`** prints a statistical summary of the loaded graph. It supports all
three data modes, with a reduced set of statistics available from a JSON emit
directory rather than a live database.

## Containers

`docker-compose.yml` defines two services. `neo4j` runs Neo4j 5 with the APOC
plugin, a healthcheck on the HTTP port, and named volumes for data, logs and
plugins. Its heap and page-cache sizes are set explicitly and commented with the
load they were sized for — the bulk activity load — together with guidance to
lower them on smaller hosts and never to exceed host memory.

The `pipeline` service is behind a `runner` profile, so `docker compose up` does
not start it; it is invoked per command with `docker compose run --rm pipeline
run <stage>`. It waits for the database to be *healthy* rather than merely
started, overrides `NEO4J_URI` to the compose network name, and bind-mounts the
artifact directories plus the source tree for development.

The image installs `poppler-utils` for PDF rasterisation and `build-essential`
for packages that fall back to source builds, copies requirements before source
so the dependency layer is cached across code changes, and sets
`python -m pipeline` as its entrypoint with `--help` as the default command.

## GPU execution

Two stages benefit from an accelerator: `embed`, but only on its local
sentence-transformers path — the default remote embeddings backend does no local
compute, and the local path is forced with `--flag embedder=local` — and
`ner-extract`, which runs GLiNER2. Both resolve their device through
`pipeline/core/devices.py` at load time, so no separate GPU configuration is
needed beyond `PIPELINE_DEVICE` and `PIPELINE_DTYPE`.

`ner-extract` does not trust the load-time device placement: it verifies the
model's parameters actually landed on the selected device and falls back to an
explicit move, then to CPU, if they did not.

## Related pages

- [Stage DAG and Registry](../architecture/stage-dag-and-registry.md)
- [Run State, Skipping and the Stage Ledger](../architecture/run-state-and-resumability.md)
- [Configuration and Deployment Seams](../architecture/configuration-and-deployment-seams.md)
