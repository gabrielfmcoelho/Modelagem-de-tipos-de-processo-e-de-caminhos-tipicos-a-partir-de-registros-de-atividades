---
type: architecture
title: Execution Modes and Graph I/O
description: The four execution modes, how each binds a GraphWriter and GraphReader pair, the NDJSON capture-and-replay format that lets graph stages run without a live Neo4j, and the retry and batching behaviour of the direct writer.
tags: [execution-modes, graph-io, neo4j, ndjson, replay, writers, readers]
verified:
  - by: openwiki/0.5.0
    at: 2026-09-10T12:46:32.229Z
sources:
  - id: openwiki-source-f201f1be48b48643ec061fae
    resource: repo://pipeline/core/_stage_base.py
  - id: openwiki-source-06e8517972e186f4e0b541f1
    resource: repo://pipeline/core/neo4j_driver.py
  - id: openwiki-source-3d20aa9e6ace8985f48b41af
    resource: repo://pipeline/core/runner.py
  - id: openwiki-source-0ed7c8e70a10ec8979c2c1f0
    resource: repo://pipeline/readers/base.py
  - id: openwiki-source-b732ae4e3b2770fcdef69ce6
    resource: repo://pipeline/readers/json_reader.py
  - id: openwiki-source-6b89638ab252d9465b7f1529
    resource: repo://pipeline/readers/neo4j_reader.py
  - id: openwiki-source-cdb019941578375ce2095a00
    resource: repo://pipeline/writers/json_writer.py
  - id: openwiki-source-8b0b328f8c80e2de788e64e4
    resource: repo://pipeline/writers/neo4j_writer.py
generated: { by: "claude-code", at: "2026-09-10T12:46:32.229Z" }
---

# Execution Modes and Graph I/O

Graph-touching stages never talk to Neo4j directly. They are handed a
`GraphWriter` and a `GraphReader` on their `RunContext`, and the *mode* of the
run decides which concrete implementations those are. This indirection is the
reason the graph half of the pipeline can be exercised, diffed and tested with no
database present at all.

## The mode axis

`Mode` is a closed set of four values declared in
`pipeline/core/_stage_base.py`:

| Mode | Writer | Reader | Typical use |
|---|---|---|---|
| `neo4j` | `DirectNeo4jWriter` | `Neo4jReader` | Normal operation against a live database |
| `json-emit` | `JsonFileWriter` | `Neo4jReader` (best effort) | Capture graph mutations to disk for inspection or replay |
| `json-replay` | `JsonFileWriter` or `DirectNeo4jWriter` | `JsonFileReader` | Re-run downstream stages from a captured emit |
| `fs` | none | none | Stages that only read and write the filesystem |

Each stage declares the modes it supports in `StageMeta.modes`.

### How a mode is chosen

`pick_mode` applies a fixed precedence: an explicit `mode` flag wins; otherwise a
configured read directory selects `json-replay`; otherwise a configured emit
directory selects `json-emit`; otherwise the default is `neo4j`. Both the read
and emit directories may come from settings or from per-run flags, with the flag
consulted first.

The chosen mode is then a *preference*, not a mandate. For each stage the runner
calls `_resolved_mode_for`, which returns the chosen mode when the stage declares
it and otherwise **falls back to the stage's first declared mode**. A single run
can therefore execute different stages in different modes — an `fs`-only
evidence stage will run in `fs` even when the run was launched as `neo4j`. Only a
stage declaring no modes at all is a hard error, raising
`IncompatibleModeError`.

### Where the I/O lives in the run

`_io_for` is a context manager, and the runner enters it **inside the stage
loop**, once per stage, rather than once per run. Each stage therefore receives a
freshly built driver, writer and reader that are torn down before the next stage
begins. The `finally` block closes writer, reader and driver in that order, each
inside its own `try/except`, so a failure closing one cannot prevent the others
from being released.

Ownership is tracked explicitly: `own_driver` records whether `_io_for` built the
driver, and only a driver it built is closed. Credential failures are handled
asymmetrically by design — in `neo4j` mode a `ConfigError` becomes an
`IncompatibleModeError` explaining that the mode needs credentials, while in the
JSON modes it is caught and logged at info level, leaving the corresponding side
absent. A stage that then needs the missing side gets an actionable message from
`RunContext.require_writer`, `require_reader` or `require_driver`, each of which
names the flag that would have provided it.

## The writer contract

`GraphWriter` exposes three mutation primitives plus phase hooks:

- `write_nodes(label, key_fields, rows, *, phase, props=None)`
- `write_edges(rel_type, from_label, from_key, to_label, to_key, rows, *, phase, props=None)`
- `execute_template(name, cypher, params, *, phase)`

`open_phase` and `close_phase` default to no-ops, so an implementation opts into
phase awareness only if it has something to do with it.

Both concrete writers share two validation invariants: `write_nodes` rejects an
empty `key_fields`, and `write_edges` rejects an empty `from_key` or `to_key`,
each raising `WriterError`. Both also return `0` and write nothing for an empty
row set, so callers need not guard.

One behaviour deserves care. When `props` is `None`, both writers infer the
property list from **the first row only** — every key of `data[0]` that is not a
key field. Rows in a batch are expected to be homogeneous; a field present only
in later rows is silently dropped. Callers that build heterogeneous rows should
pass `props` explicitly.

### Direct Neo4j writer

`DirectNeo4jWriter` compiles each call into a parameterised Cypher statement and
runs it in slices of `batch_size`. Node writes become
`UNWIND $rows AS r / MERGE (n:Label {key…}) / SET …` and edge writes become
`UNWIND $rows AS r / MATCH (a…) / MATCH (b…) / MERGE (a)-[rel:TYPE]->(b) / SET …`.
Because the primitive is `MERGE` on the key fields rather than `CREATE`, re-running a
stage against a populated database updates rather than duplicates — which is what
makes the whole pipeline safe to resume.

Every statement goes through `run_with_retry`, which catches Neo4j
`TransientError` — the class that carries deadlocks — and retries up to twenty
times with exponential backoff plus random jitter, capped at ten seconds per
wait. Concurrent `MERGE` on shared `Unidade` nodes is the expected source of
those deadlocks, and the jitter is what keeps retrying writers from
resynchronising.

Note that the edge key mappings are read as `row_field -> node_property`: the
mapping key names the field in the incoming row, the value names the property on
the matched node.

### JSON file writer

`JsonFileWriter` captures the same three primitives as newline-delimited JSON
under `nodes/`, `edges/` and `templates/`, one shard per label, relationship type
or template name. Shard file names are derived by `_to_shard_name`, which splits
camel-case boundaries, lowercases, and replaces any remaining non
`[a-z0-9_]` character with an underscore — so `DO_PROCESSO` and a
`ProcessoMetadados` label both yield safe filenames.

Alongside the shards it maintains `manifest.json` carrying a schema version,
start and completion timestamps, in-progress and completed phase lists, and
per-label, per-relationship and per-template counts. The manifest is rewritten on
every phase transition and on close, so an interrupted emit still describes how
far it got.

Durability and concurrency are handled explicitly: a single `Lock` guards handle
creation, writes and manifest updates; file handles are opened in append mode and
cached per path; and `close_phase` flushes and `fsync`s every open handle before
recording the phase as completed. `OSError` from `fsync` is tolerated, which
keeps the writer usable on filesystems that do not support it.

## The reader contract

`GraphReader` is deliberately narrow — `count_processos` and
`iter_processo_batches` — and both implementations yield the same value type,
`ProcessoTimeline`, pairing a `protocolo_formatado` with a list of activity
dictionaries. That shared shape is the contract that makes replay meaningful.

`Neo4jReader` paginates with `SKIP`/`LIMIT` over processes ordered by
`protocolo_formatado`, collecting each process's activities through
`DO_PROCESSO` and `EXECUTADO_PELA_UNIDADE`, with the sending unit matched
optionally so activities without one are retained rather than dropped. Activities
are ordered inside the query by `(pf, data_hora, source_id)`.

`CohortNeo4jReader` subclasses it and overrides both methods with cohort-scoped
queries that traverse `MEMBRO_DA_COORTE`, so downstream stages can consume a
cohort through exactly the reader interface they already use.

`JsonFileReader` reconstructs the same timelines from disk — but only from
`templates/load_atividades.ndjson`, not from the `nodes/` and `edges/` shards.
The template capture records the parameter rows of the activity-loading
statement, and the reader regroups those rows by process. A missing template file
raises `ReaderError` naming the file and the command that produces it, rather
than yielding an empty result that would look like an empty database.

The reader sorts each process's activities by `(data_hora, source_id)` and
returns processes in sorted protocol order, deliberately reproducing the
ordering the Cypher query imposes. Timelines are loaded once and cached in
memory, and `close` drops the cache.

## Why this matters

The combination gives the repository a capture-and-replay loop: run the ingest
stages once against Neo4j with `--emit-json`, then re-run every downstream stage
from that directory with `--read-json`, deterministically and offline. It is what
lets the graph-consuming tests execute in CI without a database, and it makes a
change in downstream behaviour attributable to the code rather than to a drifting
database.

## Related pages

- [Stage DAG and Registry](stage-dag-and-registry.md)
- [Ingest and Knowledge Graph Construction](../workflows/ingest-and-graph-build.md)
- [Test Strategy and Repository Invariants](../testing/test-strategy.md)
