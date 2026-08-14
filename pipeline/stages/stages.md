# `pipeline/stages/` — pipeline execution steps

47 registered stages implementing the complete research pipeline. Each stage module declares `StageMeta` and implements `def run(ctx: RunContext) -> None`. This uniformity of interface enables the runner to resolve dependencies, orchestrate execution, manage checkpoints, and report progress without knowledge of individual stage implementation.

## Stage Registration Format

```python
@stage(StageMeta(
    name="cluster-eval",
    phase="clustering",
    question="Que particao cada algoritmo produz, e com que validade interna?",
    deterministic="conditional",
    nondeterminism="UMAP e HDBSCAN fixados pelo seed registrado em params",
    type="op",
    depends_on=("processo-embed",),
    modes=("neo4j",),
))
def run(ctx: RunContext) -> None:
    ...
```

**Field semantics:**
- **`question`:** Research question this stage addresses. Copied into artifact metadata during stamping so stored files declare their purpose
- **`deterministic` / `nondeterminism`:** Reproducibility classification. `"conditional"` means reproducible given the random seed recorded in `_meta.params`
- **`phase`:** Logical phase for ordering in generated views. Default is `"operations"`; only stages `clean`, `resumo`, `graph-health`, `artifact-audit` use non-standard phases

## Stage Responsibilities and Boundaries

Each stage performs orchestration only; algorithms and I/O logic reside in their designated layers:
- **Algorithms:** `model/` (tests independently, reusable across stages)
- **Persistence:** `readers/` / `writers/` (abstract backend selection)
- **Stage logic:** Read configuration flags → invoke algorithm → hand result to writer → stamp artifact

Module size indicates misplaced logic: a stage exceeding ~200 lines typically indicates algorithmic code that should migrate to `model/`.

## Three rules with teeth

- **A module-level path constant is part of the test surface.** A stage that names an output
  path as a module constant must let a test redirect it. `conftest.artifacts_stay_read_only`
  fails any session that writes into the real `artifacts/` tree.
- **`main()` requires a `__main__` guard.** `matrix` and `typical-cells` spawn stage modules as
  subprocesses; without the guard the module imports, does nothing, and exits 0 — a subprocess
  caller reads that as success. `test_every_module_with_a_main_can_be_run_with_dash_m` enforces it.
- **Evidence stages run with `--no-deps`.** `results` declares `depends_on=("cluster-eval",)`;
  the flag keeps the runner from walking the chain back to `download`, which hits the network.
