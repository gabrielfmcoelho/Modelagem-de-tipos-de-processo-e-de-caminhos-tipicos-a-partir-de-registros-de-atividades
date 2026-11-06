---
type: testing
title: Test Strategy and Repository Invariants
description: How the suite is organised — driver doubles and round-trip tests that keep graph code offline, the guard protecting real evidence from fixture writes, and the meta-tests that enforce layering, licensing, naming and manuscript-to-artifact invariants.
tags: [testing, pytest, invariants, fixtures, layering, meta-tests, regression]
verified:
  - by: openwiki/0.5.0
    at: 2026-09-10T12:46:32.229Z
sources:
  - id: openwiki-source-f78e643a8b1eac6859e6a07b
    resource: repo://pipeline/core/registry.py
  - id: openwiki-source-d4faaa19ab6e2db4936586ec
    resource: repo://pipeline/tests/conftest.py
  - id: openwiki-source-138f3ebf41679fe4b65da019
    resource: repo://pipeline/tests/test_json_reader.py
  - id: openwiki-source-dcbf3a60cc0a5ee5dc6f9b36
    resource: repo://pipeline/tests/test_manuscript_claims.py
  - id: openwiki-source-abf14fc3d5eccbeb9b3ce09c
    resource: repo://pipeline/tests/test_neo4j_writer.py
  - id: openwiki-source-6981a9528fa786708564ab18
    resource: repo://pipeline/tests/test_no_comments.py
  - id: openwiki-source-3c6a5bfbf4a5f6f8d99988b8
    resource: repo://pipeline/tests/test_registry.py
  - id: openwiki-source-05ccef8d4cf1698187f20464
    resource: repo://pyproject.toml
generated: { by: "claude-code", at: "2026-09-10T12:46:32.229Z" }
---

# Test Strategy and Repository Invariants

The suite has two halves that look nothing alike. One is ordinary unit testing of
parsers, models and stages. The other is a body of **meta-tests that assert
properties of the repository itself** — its layering, its licensing, its naming,
and the correspondence between generated numbers and manuscript prose. The second
half is where most of this repository's testing effort actually lives.

`pyproject.toml` sets `testpaths = ["pipeline/tests", "reports/tests"]` with
`-q`. There are on the order of seventy test modules under `pipeline/tests`.

## Protecting the evidence

The most consequential fixture is in `conftest.py` and runs for every session
automatically. `artifacts_stay_read_only` snapshots the modification time and
size of every file under `artifacts/` before the session, snapshots again after,
and fails if anything was added, removed or changed.

Its message explains why it exists: a module-level path constant once escaped
monkeypatching and a test overwrote real evidence with fixture data. The message
also states the remedy — patch the constant in the test — and instructs
explicitly that the guard must not be relaxed.

This is the testing counterpart of the provenance contract. Artifacts are
evidence for a published study; a test run must not be able to silently rewrite
them.

## Keeping graph tests offline

Two techniques let the graph layer be tested without Neo4j.

**Driver doubles.** `test_neo4j_writer.py` defines a `_RecordingDriver` whose
sessions simply append `(cypher, params)` to a list. Because
`DirectNeo4jWriter` builds its Cypher as strings and passes rows as parameters,
the test can assert on the *exact statement generated* — that a node write
produces `MERGE (n:Orgao {sigla: r.sigla})` under `UNWIND $rows AS r`, that no
`SET` clause appears when there are no properties, and that the parameters are
the rows verbatim. This pins the writer's contract, including the MERGE-not-
CREATE choice that makes re-runs idempotent.

**Round trips.** `test_json_reader.py` exercises the capture-and-replay contract
end to end in a temporary directory: rows are written through `JsonFileWriter`
and read back through `JsonFileReader`, verifying that the reader reconstructs
per-process timelines in the ordering the Cypher query would have produced —
including that out-of-order input rows are sorted correctly.

**Registry isolation.** Tests that need to register stages swap the module-global
registry: save the real dictionary, clear it, yield, and restore in a `finally`.
This is what `registry.clear()` exists for.

## The invariant suite

`pipeline/tests/test_no_comments.py` is misleadingly named. Its first test does
enforce the repository's comment policy, but the file continues for several
hundred more lines asserting structural properties of the codebase. Each
assertion message names the concrete incident that motivated it.

### Code shape

- **No comments or docstrings** anywhere under `pipeline`, `reports`, `scripts`
  and `article/figures`, with shebangs and encoding declarations preserved. It
  works by tokenising for `COMMENT` tokens and walking the AST for leading string
  expressions in modules, classes and functions, and is parametrised per file so
  a failure names the offending path.
- **No module derives its own repository root.** Every module is imported and
  checked for a `ROOT` or `_ROOT` attribute that is not the actual repository
  root, with a known third-party allowlist so a missing optional dependency skips
  rather than fails. The fix it demands is importing `ROOT` from
  `pipeline.core.paths`.
- **Scripts outside the package must anchor the root correctly.** Scripts cannot
  import `pipeline.core.paths` without side effects, so their
  `Path(__file__).resolve().parent…` chains are checked *statically*: the test
  walks the AST computing how many levels each assignment climbs and compares it
  to the file's actual depth. Getting this wrong means reading and writing
  outside the repository.
- **Every module defining `main()` must have a `__main__` guard**, because
  without one `python -m <module>` imports the module and exits zero having done
  nothing — which a subprocess caller reads as success.
- **String literals naming a module must resolve**, since such references are
  invisible to import checking and fail only when the line executes.

### Architecture

- **Every architectural package carries a note** named after itself explaining
  why it exists and what it may import; the layering rule is only enforceable if
  it is written next to the code it constrains.
- **The layering rule is machine-checked.** `core` may import only `core`;
  `model` and `io` may import `core`; `evidence` may import `core`, `model` and
  `io`; `stages` may import everything below; `apps` may import anything. Imports
  are resolved from the AST, including relative ones. Two inversions are
  recorded as explicit exceptions *with their rationale in the code*:
  `evidence → stages`, because the provenance stamper must resolve the registry
  and registration happens by import side effect, so the import is function-local
  to avoid a cycle; and `core → io`, because the runner selects reader and writer
  from a stage's mode — noted as orchestration sitting in the plumbing layer and
  flagged for relocation rather than silently accepted.
- **No stage may silently default its phase.** Any stage left in the default
  `operations` phase fails unless it is one of the four genuinely operational
  stages, because a mis-phased stage disappears from the generated phase view.
- **The package must import and the registry must be complete** — at least
  forty-seven stages with no duplicate names. This catches breakage that neither
  compilation nor static name resolution would find.

### Licensing

`pm4py` is AGPL. The suite asserts that nothing inside the deployable `pipeline`
package imports it: it is confined to `scripts/conformance_pm4py.py` and reached
by subprocess **precisely so its licence does not attach to the pipeline**. An
import inside the package would defeat that containment, so it is a test failure
rather than a review comment.

### Documentation coupling

- **Every registered stage must appear** in three named reference documents, so
  no stage is discoverable only by reading the registry.
- **Live documentation must not name a Python file that moved.** Markdown under
  `docs/` is scanned for module paths that no longer exist, with two exemptions:
  historical directories, and any paragraph that says `deleted in commit` —
  naming a dead module is acceptable as long as the document says when it died.

### Registry completeness

Two tests guard against partial reimplementation of a registry.

The first checks that every downstream model list — in the figure, table, block,
lattice and non-inferiority modules — covers `MODEL_NAMES`. Its message records
the failure it prevents: when `gnn` was added, cells carried its metrics while
every table and figure silently ignored them.

The second is more general. It scans every string tuple, list, set and
comma-separated literal in the codebase and fails any that contains two or more
members of a registry without containing all of them. Extra entries are fine;
*coverage* is what is checked. Three partial enumerations are legitimate and
appear in an exception table, each with a written justification — for instance
that one alphabet is a base rather than a projection and so has no transform
function. The message notes that the previous version of this guard enumerated
the seven lists it knew about, which is exactly why the eighth went unnoticed.

## Binding the manuscript to the artifacts

`test_manuscript_claims.py` is the last link in the provenance chain. It asserts
that the numbers printed in the manuscripts still match the generated figures
artifact.

`CLAIMS` is a table of triples: a dotted path into `results_figures.json`, the
exact rendering expected in the LaTeX source, and an optional anchor phrase that
must appear near it. `CLAIMS_PT` repeats this for the Portuguese manuscript with
comma decimal separators — the two builds carry different renderings of the same
underlying values, and both are checked.

Three further mechanisms go beyond value matching:

- **Sign guards.** Paths registered as must-be-negative or must-be-positive fail
  when a correlation flips sign, since the prose describes a direction, not just
  a magnitude.
- **Retraction guards.** Specific numbers from retracted claims are forbidden
  from reappearing in the text, each annotated with what it used to assert.
- **Caveat requirements.** A number that is legitimate but misleading in
  isolation must appear near its companion figure. The recorded case is a gain
  that is real but partly attributable to per-cluster model selection rather than
  to partitioning; stating it without the family-matched figure nearby *is* the
  retracted claim.

`_renderings` accounts for how a float may legitimately appear in prose,
generating the value at several decimal precisions, as a percentage, and in
absolute value.

Both fixtures are module-scoped and **skip rather than fail** when the figures
artifact or the manuscript sections are absent, so the suite remains runnable in
a checkout that has not been through a full pipeline run.

## Related pages

- [Execution Modes and Graph I/O](../architecture/execution-modes-and-graph-io.md)
- [Stage DAG and Registry](../architecture/stage-dag-and-registry.md)
- [Artifact Provenance and Audit](../concepts/artifact-provenance-and-audit.md)
