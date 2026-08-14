# `pipeline/writers/` — abstract data persistence interface

I/O abstraction mirror of `readers/`. Stages invoke `ctx.require_writer()` and perform writes; the runner selects the appropriate backend based on declared mode.

| module | backend |
|---|---|
| `base.py` | interface specification and batching contract |
| `neo4j_writer.py` | live Neo4j graph, batch operations, idempotent `MERGE` semantics |
| `json_writer.py` | directory-based JSON serialization (json-emit mode) |

## Idempotency via MERGE Semantics

All Neo4j writes use `MERGE` operations (not `CREATE`), ensuring re-execution converges on identical state without duplication. This property enables:
- Safe stage re-execution: `can_skip_when_done` is reusable
- Failed run resumption: multi-hour loads can recover from interruption

A writer using `CREATE` would violate both properties and break reproducibility.

## Artifact Persistence (Distinct from Graph Writers)

Graph writers persist **reproducible pipeline state**—data rebuilt identically from source at any time. Evidence artifacts stored in `artifacts/` use `evidence/artifact.py` instead, which adds provenance metadata. These are two distinct write pathways:
- **`writers/`:** graph state (reproducible from source)
- **`evidence/artifact.py`:** research findings with provenance (stage ID, timestamp, parameters)

## Import Boundaries

Writers import only from `core/`.
