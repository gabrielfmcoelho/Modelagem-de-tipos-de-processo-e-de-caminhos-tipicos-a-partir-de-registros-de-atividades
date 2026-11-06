---
type: concept
title: Artifact Provenance and Audit
description: The contract every generated artifact must satisfy — a stamped metadata envelope naming its producing stage, hashed inputs, captured library versions and commit — and the audit stage that enforces it across the artifact tree.
tags: [provenance, artifacts, reproducibility, audit, evidence, hashing]
verified:
  - by: openwiki/0.5.0
    at: 2026-09-10T12:46:32.229Z
sources:
  - id: openwiki-source-8ea91a6e8c06e8ccb6acb256
    resource: repo://docs/research/artifact-contract.md
  - id: openwiki-source-5c37c55bce570f82e4400c63
    resource: repo://pipeline/evidence/artifact.py
  - id: openwiki-source-843018027c6123422c340353
    resource: repo://pipeline/evidence/etl/export_traces.py
  - id: openwiki-source-fd9f36ca1d1ed68b1a4e3524
    resource: repo://pipeline/evidence/typical_path/run_typical_eval.py
  - id: openwiki-source-a56788520d39116a4b4812b6
    resource: repo://pipeline/stages/artifact_audit.py
  - id: openwiki-source-8a8028221080f02daea7e2e0
    resource: repo://pipeline/stages/cluster_eval.py
  - id: openwiki-source-d24e90308282cb21e387469a
    resource: repo://pipeline/stages/results.py
generated: { by: "claude-code", at: "2026-09-10T12:46:32.229Z" }
---

# Artifact Provenance and Audit

This repository is the reproducible artifact of a study, so an output file is not
merely data: it is evidence that some stage answered some question at some
commit, from some inputs. The provenance machinery makes that claim machine-
checkable rather than a matter of trust.

The governing direction, stated in `docs/research/artifact-contract.md`, is that
**an artifact answers a question and the text interprets the artifact, never the
reverse**. The contract exists because that direction was once violated:
an artifact reporting four measurements was found with no producer anywhere in
the repository, and the numbers it carried happened to be exactly the ones the
argument wanted. Everything below is the mechanism that makes a recurrence
detectable.

## The metadata envelope

`build_meta` in `pipeline/evidence/artifact.py` assembles the envelope stamped
onto every artifact:

| Field | Source |
|---|---|
| `stage` | The registered stage name passed by the caller |
| `question` | Copied from that stage's `StageMeta.question` |
| `deterministic`, `nondeterminism` | Copied from the same `StageMeta` |
| `generated_at` | UTC timestamp |
| `commit` | `git rev-parse HEAD`, or `null` |
| `params` | Caller-supplied parameters that change the output |
| `inputs` | Repository-relative path and SHA-256 for each input |
| `versions` | Versions of the tracked scientific libraries |

The first entry is enforced, not merely conventional. `build_meta` looks the
stage up in the registry and raises `ValueError` when it is absent, with a
message stating the reason: an artifact must name its producing stage so that its
question and its determinism can be *read off the registry rather than guessed*.
It is therefore impossible to stamp an artifact with an invented producer, which
is the precise failure the contract was written against.

Three helpers make the envelope robust rather than brittle:

- `_versions` probes a fixed tuple of tracked distributions — `numpy`,
  `scikit-learn`, `hdbscan`, `umap-learn`, `igraph`, `leidenalg`, `torch`,
  `neo4j` — and silently omits any that are not installed, so the envelope
  records what was actually present rather than failing.
- `_commit` shells out with a five-second timeout and `check=False`, returning
  `None` on any failure. An artifact generated outside a git checkout is stamped
  with a null commit instead of erroring.
- `_rel` renders paths relative to the repository root and falls back to the
  absolute string for paths outside it, so recorded paths are portable.

`digest` streams SHA-256 in one-mebibyte chunks and returns `None` for anything
that is not a file, which keeps hashing large model or embedding artifacts
memory-bounded.

## Two stamping shapes

The format of an artifact decides how it is stamped.

**JSON artifacts carry the envelope inline.** `write_artifact` merges
`{"_meta": meta, **payload}`, creates parent directories, and writes indented
UTF-8 JSON. Passing `force=False` makes it refuse to overwrite an existing file
with `FileExistsError`, the mechanism for freezing an artifact that must not be
clobbered.

**Binary artifacts get a sidecar.** `write_sidecar` writes
`<name>.meta.json` next to the target, containing the envelope plus `describes`,
`sha256` and `bytes`. It enforces an ordering invariant: the target must already
exist, and a missing one raises `FileNotFoundError` explaining that the sidecar
records the digest of the bytes actually on disk. Write first, stamp second —
a sidecar can never describe a file that was never written.

Both paths call `record_write`, which pushes the path, size and declared inputs
into the process-wide write buffer that the stage ledger drains. Stamping an
artifact is therefore also what makes it appear in the run's audit trail.

The stamper is used broadly rather than in one corner: roughly seventeen stage
modules and eight evidence modules call `write_artifact` or `write_sidecar`,
which is what allows the audit to expect provenance everywhere.

## Auditing without re-running

`inputs_match` reads an artifact's envelope, re-digests each recorded input at
its repository-relative path, and returns the paths whose hashes no longer
agree. This answers "is this artifact still consistent with the files it was
built from?" without recomputing the artifact — the property that makes `inputs`
worth recording at all.

## The audit stage

`artifact-audit` walks the artifact tree and demands provenance from every file.

It declares `can_skip_when_done=False`, so it never reuses a checkpoint: an
audit's entire purpose is to re-examine current state, and a cached pass would be
worthless. Its root defaults to `artifacts/` and is overridable with
`--flag root=…`.

Candidate selection excludes three things: anything under a `_backup` directory,
files with `.log`, `.tgz` or `.tar` suffixes, and the `.meta.json` sidecars
themselves — a sidecar is provenance, not an artifact needing its own.

A file counts as stamped if a sidecar exists for it, or — for `.json` files only
— if it parses as a dictionary containing the `_meta` key. JSON that fails to
parse is reported as unstamped with the exception type as the reason, so a
corrupt artifact is surfaced rather than skipped. For stamped JSON the audit
additionally runs `inputs_match` and records any drift.

Results are reported in two registers. The stage always writes a summary of
stamped, unstamped and drifted counts into the shared cache under
`artifact_audit_summary`, logs the totals, and warns about the first twenty
unstamped files and every drifted one. With `--flag strict=true`, any unstamped
or drifted artifact instead raises `RuntimeError` — the form used in CI and
before a release, where the message points back at the contract document.

The two registers matter operationally: the default reporting mode lets an
operator see the state of a partially regenerated tree, while strict mode is the
gate that keeps an unprovenanced number from reaching a manuscript.

## Related pages

- [Run State, Skipping and the Stage Ledger](../architecture/run-state-and-resumability.md)
- [Evidence Composition and Manuscript Delivery](../workflows/evidence-and-manuscript-delivery.md)
- [Experiment Arms and Run Identifiers](experiment-arms-and-run-ids.md)
