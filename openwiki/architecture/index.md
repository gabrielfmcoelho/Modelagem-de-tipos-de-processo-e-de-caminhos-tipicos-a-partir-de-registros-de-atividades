# Files

- [Configuration and Deployment Seams](configuration-and-deployment-seams.md) - How the pipeline resolves settings from environment, .env and CLI flags, how missing credentials become typed configuration errors, how compute devices are chosen, and how institutional identity is kept out of the source tree.
- [Execution Modes and Graph I/O](execution-modes-and-graph-io.md) - The four execution modes, how each binds a GraphWriter and GraphReader pair, the NDJSON capture-and-replay format that lets graph stages run without a live Neo4j, and the retry and batching behaviour of the direct writer.
- [Run State, Skipping and the Stage Ledger](run-state-and-resumability.md) - How the pipeline checkpoints and resumes work — the state directory layout, completion semantics, PID-based run locking, the narrow argument comparison that invalidates a skip, and the per-stage ledger and run history it writes.
- [Stage DAG and Registry](stage-dag-and-registry.md) - How stages register themselves by decorator, what StageMeta declares, how dependency resolution orders and validates a plan, the nine research phases, and how the runner drives a resolved plan.
