# `pipeline/readers/` — abstract data access interface

I/O abstraction layer enabling stages to read data without knowledge of the underlying storage backend. Three modules implement this abstraction:

| module | backend |
|---|---|
| `base.py` | interface specification (abstract base class) |
| `neo4j_reader.py` | live Neo4j graph via bolt protocol |
| `json_reader.py` | directory-based JSON replay mode |

## Purpose and Rationale

The runner selects the appropriate reader based on stage mode declaration: `modes=("neo4j", "json-emit", "json-replay")`. Without this abstraction, every stage would require internal mode branching, causing JSON modes to drift and become unmaintainable. JSON modes enable pipeline execution in environments without Neo4j access.

Trace export workflow demonstrates the abstraction value: `export-traces` reads from live Neo4j once and freezes results into `artifacts/traces/`. Subsequent typical-path phase stages read from this frozen artifact using JSON reader, enabling database-free execution.

## Import and Type Boundaries

Readers import only from `core/`. Return types are strictly untyped or basic Python types (dict, list): never model objects or driver handles. Callers requiring direct database access must request it from `RunContext`.
