---
type: workflow
title: Ingest and Knowledge Graph Construction
description: How the SEI activity log is read from Trino/Iceberg and projected into Neo4j — the corpus-defining query, two injection-safety idioms, dimension pre-creation before the parallel load, chunked bulk loading, and the derived timeline, residence and status structure.
tags: [ingest, trino, iceberg, neo4j, etl, graph, sql-safety, bulk-load]
verified:
  - by: openwiki/0.5.0
    at: 2026-09-10T12:46:32.229Z
sources:
  - id: openwiki-source-061bbeaba44f5ca4efeb6031
    resource: repo://pipeline/core/cypher/__init__.py
  - id: openwiki-source-191eec18d828bfb00f7e31cc
    resource: repo://pipeline/core/cypher/precreate.py
  - id: openwiki-source-06e8517972e186f4e0b541f1
    resource: repo://pipeline/core/neo4j_driver.py
  - id: openwiki-source-ca449014b7efe7f8ff4bf294
    resource: repo://pipeline/core/sql.py
  - id: openwiki-source-0083042fa9b747e6669ca716
    resource: repo://pipeline/core/trino_source.py
  - id: openwiki-source-18f93105b4227f05663cc949
    resource: repo://pipeline/model/embedding.py
  - id: openwiki-source-5c25a073962181c7c4c0bded
    resource: repo://pipeline/stages/atividades.py
  - id: openwiki-source-f24926314a8c66463f629b82
    resource: repo://pipeline/stages/permanencia.py
  - id: openwiki-source-669ba4e22a3ab74e4247db53
    resource: repo://pipeline/stages/precreate.py
  - id: openwiki-source-3a3b58b4787d6b09f50c01ea
    resource: repo://pipeline/stages/situacao.py
  - id: openwiki-source-584281858c7967f0a6d1de1c
    resource: repo://pipeline/stages/timeline.py
  - id: openwiki-source-3baaed0a0df63c1b35dfbf19
    resource: repo://pipeline/tests/test_atividades_chunk.py
  - id: openwiki-source-3ae1ded4663c58056f0ad9a7
    resource: repo://pipeline/tests/test_trino_source.py
  - id: openwiki-source-cdb019941578375ce2095a00
    resource: repo://pipeline/writers/json_writer.py
generated: { by: "claude-code", at: "2026-09-10T12:46:32.229Z" }
---

# Ingest and Knowledge Graph Construction

The study's raw material is an event log: one row per activity recorded against
an administrative process. This workflow reads that log out of the datalake and
projects it into a property graph, then derives the sequence, residence and
status structure that everything downstream depends on.

## The source

Activities are read from a Trino catalog over Iceberg tables, principally
`sei_atividades`, joined against `sei_unidades` for unit descriptions and — for
status filtering — a gold-layer process metadata table.

`pipeline/core/sql.py` holds the query templates as named constants with
`{placeholder}` slots for the filter fragments, keeping SQL text out of the stage
logic.

### What defines the corpus

A process enters the study through one specific predicate: it has an activity
whose description matches the process-generation pattern. That single `LIKE`
clause is the corpus boundary — the study covers processes *born* in the window,
not processes merely active in it. Date, agency and status filters narrow that
set further; the status filter does so through a subquery against the gold
metadata table rather than by joining.

### Two injection-safety idioms

Filters are built two different ways, and the difference is deliberate.

**Parameterised fragments.** `build_date_filter`, `build_orgao_filter` and
`build_status_filter` return a SQL fragment containing `?` placeholders together
with a list of parameter values, to be passed to the driver separately. Date
bounds are normalised so a bare date is padded to midnight, and a full timestamp
is preserved as given.

**Validated literals.** Some fragments must be embedded directly into composed
SQL, where a placeholder cannot travel. Those go through `_safe_ts`, which
matches the value against a strict date-or-timestamp pattern and **raises
`ValueError` naming the offending value** when it does not conform. Validation
substitutes for parameterisation exactly where parameterisation is unavailable.

For lists of process identifiers, `sql_quote_list` escapes embedded single quotes
by doubling them and returns the literal `NULL` for an empty list — so an empty
selection produces a query that matches nothing rather than a syntax error. All
three behaviours are pinned by tests.

## Pre-creating the dimensions

`precreate` runs first and creates the schema and the dimension nodes — agencies,
units, action types and their groups, users, processes and procedure types —
before any parallel loading begins.

The ordering is not cosmetic. The activity load runs concurrently and `MERGE`s
edges against those dimension nodes; having many workers `MERGE` the same shared
`Unidade` or `TipoAcao` simultaneously is the classic source of Neo4j deadlocks.
Creating them once, serially, up front removes that contention.

The schema itself is one list of roughly thirty statements: uniqueness
constraints for every keyed label, lookup indexes on the properties that
downstream queries filter by, relationship-property indexes, and a **vector index
on document embeddings pinned at 1024 dimensions with cosine similarity** — so
the embedding dimension is a schema-level commitment, not just a model default.

> This constraint list is the subject of one of the repository's invariant tests.
> A package `__init__` once re-exported a different list under the same name,
> causing `precreate` to create the five entity constraints instead of the full
> schema; a meta-test now fails on that shadowing pattern.

## The bulk load

`atividades` is the heavy stage — tens of minutes for a million activities.

Work is partitioned **by process**, not by row: process identifiers are grouped
into chunks (two hundred by default) and dispatched to a thread pool. Each worker
opens its own Trino connection, fetches its chunk with an `IN` list, transforms
the rows, and writes them through the graph writer in batches, closing the
connection in a `finally`.

Chunking by process is what makes the sequence numbering correct. Each activity
receives a per-process ordinal assigned as rows are consumed, and the fetch query
orders by process then timestamp — so the ordinal is chronological. Because every
activity of a process lands in the same chunk, that counter never has to be
reconciled across workers.

Failure is contained rather than fatal: an exception in one chunk is logged with
its traceback and counted, and the remaining chunks continue. The stage reports
how many chunks failed, so a partially loaded run is visible rather than silently
short.

The loader also surfaces classification gaps. Activity descriptions that fall
into the catch-all action type are sampled — a bounded number of distinct
descriptions, truncated — and reported, so an unrecognised description pattern
appears as a finding instead of quietly becoming `OUTROS`.

`atividades` declares `deterministic='conditional'`, with the recorded reason
that the lakehouse is under active curation and the result is fixed only for a
given snapshot. That is an honest statement about a mutable upstream source
rather than a claim the pipeline cannot keep.

## Derived graph structure

Three stages read the loaded activities back and write derived structure. All
three depend on `atividades`, all three declare `deterministic=True`, and all
three support `json-replay` in addition to the live modes — which is what lets
them be re-run and compared offline against a captured emit.

- **`timeline`** builds the sequential edges between consecutive activities of a
  process, tracking unit transitions.
- **`permanencia`** computes residence cycles — how long a process stays in each
  unit and agency between entry and conclusion.
- **`situacao`** derives open-versus-concluded status per process, unit and
  agency, soft-depending on `permanencia` because the cycles it produces sharpen
  the result without being required for it.

Each obtains its reader and writer through the `require_*` accessors, so an
incompatible mode produces an actionable message rather than a null dereference,
and each wraps its work in a named writer phase opened and closed in a
`try/finally`. Those phase names are what appear in the NDJSON emit manifest,
making a capture directory self-describing.

## Testing without a datalake

The chunk loader is exercised against a fake Trino connection and cursor that
record an event trace. The test asserts the full sequence — execute, fetch,
cursor close, connection close — alongside the rows written, so both the
transformation and the resource handling are verified with neither Trino nor
Neo4j present.

## Related pages

- [Execution Modes and Graph I/O](../architecture/execution-modes-and-graph-io.md)
- [Document Acquisition and Parsing](document-acquisition-and-parsing.md)
- [Typical Path Discovery and Evaluation](typical-path-discovery.md)
