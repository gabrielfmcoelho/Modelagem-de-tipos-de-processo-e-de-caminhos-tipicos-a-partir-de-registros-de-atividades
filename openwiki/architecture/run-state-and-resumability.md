---
type: architecture
title: Run State, Skipping and the Stage Ledger
description: How the pipeline checkpoints and resumes work — the state directory layout, completion semantics, PID-based run locking, the narrow argument comparison that invalidates a skip, and the per-stage ledger and run history it writes.
tags: [resumability, checkpoints, state, locking, ledger, provenance, operations]
verified:
  - by: openwiki/0.5.0
    at: 2026-09-10T12:46:32.229Z
sources:
  - id: openwiki-source-b498553cb46a9af94bacbf41
    resource: repo://pipeline/apps/status.py
  - id: openwiki-source-f201f1be48b48643ec061fae
    resource: repo://pipeline/core/_stage_base.py
  - id: openwiki-source-3d20aa9e6ace8985f48b41af
    resource: repo://pipeline/core/runner.py
  - id: openwiki-source-20a810d2a9c7fd96d3710141
    resource: repo://pipeline/core/state.py
  - id: openwiki-source-3fbc1af210db71014a7f2080
    resource: repo://pipeline/tests/test_status.py
generated: { by: "claude-code", at: "2026-09-10T12:46:32.229Z" }
---

# Run State, Skipping and the Stage Ledger

A full run of this pipeline spans hours: it downloads tens of thousands of
documents, embeds them, and fits models. It is expected to be interrupted. The
resumability machinery is therefore not an optimisation but a working
assumption — every stage checkpoints, and a re-invocation continues where the
last one stopped.

Two distinct records are written, and confusing them is the usual source of
error:

| Record | Location | Purpose | Lifetime |
|---|---|---|---|
| **Checkpoint** | `.pipeline-state/stages/<stage>.json` | Decides whether a stage may be skipped | Control state — deleting it re-runs the stage |
| **Ledger entry** | `artifacts/runs/<stage>.json` | Describes what the stage did, for audit | Evidence — regenerated, never consulted for control |

## The state directory

`StateDir` owns three paths under a root that defaults to `./.pipeline-state`
and is overridable per run:

- `stages/<name>.json` — one `StageRecord` per stage;
- `runs.jsonl` — append-only run history;
- `lock` — the single-writer guard.

### Completion semantics

`StageRecord.is_complete` is true only when `completed_at` is set **and**
`failed_at` is not. A record therefore encodes three distinguishable states —
never run (no file), running or failed, and done — which is what the status view
renders. Each attempt constructs a fresh `StageRecord`, so a later success
overwrites a prior failure rather than leaving both markers set.

Writes are atomic: `write_stage` serialises to a `.tmp` sibling and then
`replace`s it onto the target path. An interruption during a write cannot leave a
truncated checkpoint that would be misread on the next run.

Reads are forgiving in a specific direction. `read_stage` returns `None` on
invalid JSON, and `all_records` skips entries that fail to decode or that carry
fields the dataclass does not accept. A corrupted checkpoint therefore causes the
stage to **re-run**, never to crash the pipeline — the safe direction for a
control record.

### Run locking

`try_lock` implements a PID-based single-writer guard with stale-lock recovery.
If no lock file exists it is created with the current PID. If one exists, the
recorded PID is probed with signal 0: a live process means the lock is held and
`try_lock` returns `False`, causing `run_stages` to raise with the lock path and
instructions. A dead PID — or a lock file that cannot be parsed at all — is
treated as stale and taken over.

The runner acquires the lock before executing anything and releases it in the
`finally` that also appends the run history, including on the early return taken
by a dry resolution.

> Two ceilings are worth knowing. The guard is single-host: it compares PIDs on
> the local machine, so it does not coordinate runs across containers sharing a
> mounted state directory. And PID reuse can in principle make a stale lock look
> live, in which case the operator removes it by hand as the error message
> suggests.

## When a stage is skipped

The skip decision is a conjunction, and every term matters:

```
record exists
  AND record.is_complete
  AND stage.meta.can_skip_when_done
  AND NOT force
  AND stage name NOT IN force_stage
  AND args_compatible(record.args, flags)
```

`can_skip_when_done` lets a stage opt out of caching permanently — appropriate
for maintenance and audit stages whose whole purpose is to re-examine current
state. `--force` clears the whole plan; `--force-stage` clears one stage while
leaving its dependencies cached.

The last term is the subtle one. `args_compatible` does **not** compare the flag
dictionaries wholesale. It compares only a fixed tuple of corpus-defining keys —
`from_date`, `to_date`, `limit`, `from`, `to`, `orgao` — and treats missing keys
as `None` on both sides. The rationale is that these are the flags that change
*which data* a stage consumed; changing them must invalidate the checkpoint.

The consequence is equally important: **any other flag change does not
invalidate a skip.** Re-running with a different `--chunk-size`, a different
`--flag k=v`, or different model settings will silently reuse the existing
checkpoint. When such a flag genuinely changes the output, the operator must pass
`--force-stage` explicitly.

## What a completed stage records

On success the runner stamps `completed_at`, then pulls the stage's own summary
out of the shared per-run cache using a naming convention: the key
`<stage_name_with_underscores>_summary`. A stage reports metrics by writing that
key into `ctx.cache`; anything it does not write simply yields an empty summary.
The runner adds `duration_seconds` and persists the record.

That same `shared_cache` dictionary is created once per run and passed to every
stage's `RunContext`, so it doubles as a cross-stage memo — `ctx.cached(key,
factory)` computes a value at most once per run, which is how expensive loaded
models and corpora are shared between consecutive stages.

On failure the runner stamps `failed_at` and `error`, stores the formatted
traceback in the summary, writes the record and the ledger entry, and then
**re-raises**. A failing stage aborts the plan; subsequent stages do not run.
Because the failure is checkpointed before the re-raise, the next invocation sees
a non-complete record and retries that stage.

## The stage ledger

For both outcomes, `_write_stage_ledger` writes `artifacts/runs/<stage>.json`
describing the execution. Beyond timings, mode, status and flags, it carries
three things that come from elsewhere in the system:

- **Registry metadata** — the stage's `phase`, its `question`, and its
  `deterministic` declaration are copied from `StageMeta`, so an auditor reads a
  stage's determinism claim off the same source the code registered.
- **Outputs** — drained from the process-wide write buffer that artifact writing
  populates via `record_write`, each with its path and byte size.
- **Inputs** — collected from those same write records and deduplicated by path,
  preserving first-seen order.

The buffer itself, `_WRITES`, is module-global and guarded by a lock;
`drain_writes` returns and clears it, so each ledger entry captures the writes
recorded since the previous drain.

Ledger writing is best-effort: an `OSError` is caught and logged as a warning.
An unwritable `artifacts/` directory degrades the audit trail but does not fail
the run.

## Run history

The `finally` block of `run_stages` appends one JSON line to `runs.jsonl` for
every invocation — start and end timestamps, wall duration, the resolved stage
list, the preferred mode, the force settings, and the per-stage outcome map. It
is appended for failed and interrupted runs too, since it lives in `finally`,
which makes the history a complete record of attempts rather than only of
successes.

## Inspecting state

`pipeline status` renders three tables. The checkpoint table iterates the
**registry**, not the state directory, so stages that have never run appear
explicitly rather than being absent. Each row shows the three-state status, the
relevant timestamp, the mode, and the summary with the traceback filtered out.

The filesystem table uses a `-1` sentinel from `_safe_count` for a directory that
does not exist and renders it as a dash, keeping "not there" visually distinct
from "there and empty" — a distinction pinned by
`pipeline/tests/test_status.py`. The Neo4j table degrades in two steps: missing
credentials produce no table and a configuration hint, while a configured but
unreachable database produces a table whose title says `UNREACHABLE` and whose
body carries the error.

## Related pages

- [Stage DAG and Registry](stage-dag-and-registry.md)
- [Artifact Provenance and Audit](../concepts/artifact-provenance-and-audit.md)
- [CLI Surface and Operating the Pipeline](../operations/cli-and-runbook.md)
