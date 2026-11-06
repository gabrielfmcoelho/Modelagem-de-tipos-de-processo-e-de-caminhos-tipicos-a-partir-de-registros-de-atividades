---
type: architecture
title: Configuration and Deployment Seams
description: How the pipeline resolves settings from environment, .env and CLI flags, how missing credentials become typed configuration errors, how compute devices are chosen, and how institutional identity is kept out of the source tree.
tags: [configuration, environment, settings, credentials, device-selection, logging, deployment]
verified:
  - by: openwiki/0.5.0
    at: 2026-09-10T12:46:32.229Z
sources:
  - id: openwiki-source-d01648e7869f87d45b2226f0
    resource: repo://pipeline/app.py
  - id: openwiki-source-6e6efa1569f158fcdb678ef0
    resource: repo://pipeline/cli.py
  - id: openwiki-source-f201f1be48b48643ec061fae
    resource: repo://pipeline/core/_stage_base.py
  - id: openwiki-source-48d95fe3c5349c7e8ddc5727
    resource: repo://pipeline/core/config.py
  - id: openwiki-source-e11e72a8c66d72b8e11942d6
    resource: repo://pipeline/core/deployment.py
  - id: openwiki-source-7bfe419686ac3f2b0c64e1bc
    resource: repo://pipeline/core/devices.py
  - id: openwiki-source-bd68d8abdd7fcacae3ed2a51
    resource: repo://pipeline/core/logging_setup.py
  - id: openwiki-source-a90a70f370e79cd9de6d8fa6
    resource: repo://pipeline/core/paths.py
  - id: openwiki-source-3d20aa9e6ace8985f48b41af
    resource: repo://pipeline/core/runner.py
  - id: openwiki-source-ddc6ed0513aeed7a9e6e19d2
    resource: repo://pipeline/model/clustering/naming.py
  - id: openwiki-source-5119786ae49ee1eb43ab9e47
    resource: repo://pipeline/model/ner_llm.py
  - id: openwiki-source-dee5c2604c055c2a84117aad
    resource: repo://pipeline/model/ner/gliner.py
  - id: openwiki-source-06dcba1fa45b42b13041ff4c
    resource: repo://pipeline/model/parsing/pdf.py
  - id: openwiki-source-c74ea9440855dff9efd97e77
    resource: repo://pipeline/tests/test_config.py
  - id: openwiki-source-487afceefc5aa503f28006d3
    resource: repo://pipeline/tests/test_devices.py
generated: { by: "claude-code", at: "2026-09-10T12:46:32.229Z" }
---

# Configuration and Deployment Seams

Every stage receives its configuration through a single frozen-by-convention object,
`Settings`, carried on the `RunContext`. Nothing in the pipeline reads `os.getenv`
at the point of use for connection or model configuration; the environment is
sampled once, layered with command-line overrides, and passed down. This page
describes that resolution chain, the failure semantics around missing
credentials, the device-selection policy, and the separate seam that keeps the
name of the administration out of the code.

## Responsibility split

| Module | Owns |
|---|---|
| `pipeline/core/config.py` | `Settings`, environment resolution, `overlay`, `require_*` preconditions |
| `pipeline/cli.py` | Mapping argparse/Typer flags onto an overlay |
| `pipeline/core/devices.py` | Compute device and dtype selection, autocast |
| `pipeline/core/logging_setup.py` | Idempotent Rich logging installation |
| `pipeline/core/paths.py` | Repository-anchored directory constants |
| `pipeline/core/deployment.py` | Institution identity, read from `PIPELINE_ORGAO_*` |

## Resolution chain

Configuration is resolved in three ordered steps, each strictly narrower than the
last.

1. **`.env` discovery.** `Settings.from_env` first calls `_ensure_dotenv_loaded`,
   which probes `Path.cwd() / ".env"` and then the repository root `.env`,
   loading the **first** one it finds and stopping. The load uses
   `override=False`, so a variable already present in the real environment wins
   over the file. A module-level `_LOADED_DOTENV` guard makes this a
   once-per-process operation, so repeated `Settings.from_env()` calls in a long
   run do not re-read the file. When `python-dotenv` is not installed the import
   falls back to a no-op stub rather than failing, which keeps the package
   importable in minimal environments.

2. **Environment read.** Each field is read through `_env`, which treats an unset
   variable **and an empty string** as absent and returns the dataclass default.
   This matters operationally: a `.env` line such as `TRINO_HOST=` behaves
   exactly like an omitted line rather than configuring an empty host. `_env`
   also performs the `int`, `float` and `bool` casts; the boolean vocabulary here
   is `{"1", "true", "yes", "on"}`.

   > Note a deliberate asymmetry: stage-level flag parsing uses a *different*
   > predicate, `truthy` in `pipeline/core/_stage_base.py`, whose vocabulary also
   > accepts `y` and the Portuguese `sim`. Environment booleans and `--flag`
   > booleans are therefore not parsed by the same rules.

3. **Overlay.** `resolve_settings` in `pipeline/cli.py` builds the base settings
   from the environment and then applies `Settings.overlay` with the standard
   command-line options. `overlay` has two behaviours that make this safe:
   it **skips `None` values**, so an unsupplied flag cannot blank out a value
   that came from the environment; and it routes any key that is not a declared
   field into the `extra` dictionary instead of raising, which lets callers pass
   ad-hoc values through without widening the dataclass.

`__post_init__` normalises one field: `openai_base_url` is stripped of a trailing
slash and given a `/v1` suffix when it lacks one, so callers may configure the
host with or without the version segment.

## Credentials as preconditions, not surprises

`Settings` does not validate itself on construction. Instead it exposes explicit
preconditions that a consumer calls when it is about to need a backend:

- `require_neo4j()` raises `ConfigError` when `neo4j_password` is unset, naming
  the environment variable and the three ways to supply it.
- `require_trino()` collects **all** missing fields of `trino_host`,
  `trino_user`, `trino_password` and reports them in one message, rather than
  failing on the first.

This deferral is what allows a stage that only touches the filesystem to run in a
process with no database credentials at all. The runner converts the failure into
a mode error: when `_io_for` builds the `neo4j` mode and `build_driver` raises
`ConfigError`, it is re-raised as `IncompatibleModeError` with the original
attached, so the operator sees "this mode needs credentials" rather than a bare
connection failure. In the JSON modes the same `ConfigError` is caught and merely
logged, because a reader or writer may legitimately be absent in those modes.

## Device and dtype selection

`select_device` implements a *degrade, do not fail* policy. An explicit
`cpu` short-circuits immediately. An explicit `cuda`, `xpu` or `mps` that turns
out to be unavailable logs a warning and returns `cpu` — the run continues
slowly rather than aborting. The default `auto` probes in a fixed preference
order: CUDA, then XPU, then MPS, then CPU.

Availability probing is itself defensive: `_torch` raises a `RuntimeError`
carrying install instructions when `torch` is absent, and each `_*_available`
helper catches that and reports `False`. The pipeline therefore reports "no
accelerator" rather than "torch missing" when the dependency is not installed,
and `device_summary` degrades to `device=cpu (torch not installed)`.

`select_dtype` maps a small vocabulary of aliases (`bf16`/`bfloat16`,
`fp16`/`float16`/`half`, `fp32`/`float32`/`full`) onto torch dtypes and falls
back to `bfloat16` with a warning on an unrecognised value. `autocast_for` is a
context manager that yields without entering autocast in two cases: when the
device is not `cuda` or `xpu`, and when the configured dtype is full precision.
Callers can therefore wrap model code unconditionally.

## Institutional identity seam

`pipeline/core/deployment.py` holds every reference to the administration the
pipeline was built for as an environment-overridable constant —
`ORGAO_SIGLA`, `ORGAO_GOVERNO`, `ORGAO_DOMINIO`, example addresses and sibling
agency lists — each defaulting to the original deployment but readable from a
`PIPELINE_ORGAO_*` variable.

This is not cosmetic. The constants are consumed across roughly twenty modules,
concentrated in the places where institution-specific strings would otherwise be
hard-coded into model behaviour: NER prompt exemplars
(`pipeline/model/ner/gliner.py`, `pipeline/model/ner_llm.py`), document parsers
that strip agency boilerplate (`pipeline/model/parsing/*`), cluster naming
(`pipeline/model/clustering/naming.py`) and the CLI help text itself. Redeploying
the pipeline for a different administration is therefore a configuration change
at this seam, not a code edit — which is also what keeps the prompt exemplars
consistent with the anonymisation policy applied to documents.

## Logging and paths

`configure_logging` is idempotent by construction: it installs a `RichHandler`
only when the root logger does not already carry one, and when it does install,
it first removes every pre-existing root handler. The result is a single
consistent handler regardless of how many entry points call it — the CLI apps
call it once per invocation, while `pipeline/stages/parse.py` and
`pipeline/stages/resumo.py` also call it at import time to obtain a module
logger.

`pipeline/core/paths.py` anchors `ROOT` to the package location
(`parents[2]` of the module file), not to the working directory, and derives
`ARTIFACTS`, `ARTICLE` and `DOCS` from it. Artifact paths are consequently stable
no matter where the pipeline is invoked from — a property the provenance stamper
relies on when it records repository-relative paths.

## Verifying behaviour

`pipeline/tests/test_config.py` pins the overlay contract (None ignored, unknown
keys to `extra`) and both `require_*` error messages.
`pipeline/tests/test_devices.py` pins the precedence rule that an explicit
argument beats `PIPELINE_DEVICE`, and that each unavailable accelerator degrades
to CPU with a warning.

## Related pages

- [CLI Surface and Operating the Pipeline](../operations/cli-and-runbook.md)
- [Ingest and Knowledge Graph Construction](../workflows/ingest-and-graph-build.md)
- [Anonymization and Entity Extraction](../workflows/anonymization-and-entity-extraction.md)
