# `pipeline/apps/` — command-line interface layer

The CLI entry point for user interaction. Four Typer sub-applications implement commands accessible via `python -m pipeline`. This is the only layer permitted to import all other layers, because nothing in the codebase imports from `apps/`.

| module | command | function |
|---|---|---|
| `list.py` | `pipeline list` | Print stage registry; fastest validation of package health |
| `run.py` | `pipeline run <stage>` | Dependency resolution, mode selection, stage execution |
| `status.py` | `pipeline status` | Report execution checkpoints and run state |
| `interactive.py` | Interactive mode | Questionary-based stage picker for users unfamiliar with stage names |

## Import Scope

`apps/` resides within the `pipeline/` package, so relative imports use `..` to reach package root (not `...`, which would escape the package and raise `ImportError`). No other modules import from `apps/`, so this layer is not loaded by the test suite except when explicitly invoked via `python -m pipeline list` during verification.

## Responsibilities

No algorithmic or orchestration logic belongs in `apps/`. Each sub-app:
1. Parses command-line arguments
2. Calls `core.runner` or appropriate stage function
3. Formats and returns output

Any computational logic found in this layer indicates code that should migrate to `model/` or be wrapped as a stage.
