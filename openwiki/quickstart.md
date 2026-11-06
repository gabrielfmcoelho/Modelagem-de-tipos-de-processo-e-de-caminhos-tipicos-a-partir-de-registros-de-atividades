---
type: quickstart
title: Quickstart and Task Routing
description: What this repository is, how to install and run it, the two force levels that are easy to conflate, and a map from the kind of change you are making to the wiki page that covers it.
tags: [quickstart, onboarding, setup, routing, cli]
verified:
  - by: openwiki/0.5.0
    at: 2026-09-10T12:46:32.229Z
sources:
  - id: openwiki-source-a2371d6362e5db4bc834ad03
    resource: repo://CLAUDE.md
  - id: openwiki-source-66381fd16098d228f5875787
    resource: repo://docs/operations/runbook.md
  - id: openwiki-source-3e4b669dbed1b8e66f161a5c
    resource: repo://pipeline/__main__.py
  - id: openwiki-source-f201f1be48b48643ec061fae
    resource: repo://pipeline/core/_stage_base.py
  - id: openwiki-source-48d95fe3c5349c7e8ddc5727
    resource: repo://pipeline/core/config.py
  - id: openwiki-source-fba8db829ee9ed8d365c15b5
    resource: repo://pipeline/stages/anonymize.py
  - id: openwiki-source-5c25a073962181c7c4c0bded
    resource: repo://pipeline/stages/atividades.py
  - id: openwiki-source-87b3bf677f3cb053a67e43d8
    resource: repo://pipeline/stages/matrix.py
  - id: openwiki-source-d4faaa19ab6e2db4936586ec
    resource: repo://pipeline/tests/conftest.py
  - id: openwiki-source-dcbf3a60cc0a5ee5dc6f9b36
    resource: repo://pipeline/tests/test_manuscript_claims.py
  - id: openwiki-source-6981a9528fa786708564ab18
    resource: repo://pipeline/tests/test_no_comments.py
  - id: openwiki-source-05ccef8d4cf1698187f20464
    resource: repo://pyproject.toml
  - id: openwiki-source-23775c3de52f3ab95a13cb8b
    resource: repo://README.md
generated: { by: "claude-code", at: "2026-09-10T12:46:32.229Z" }
---

# Quickstart and Task Routing

## What this repository is

A pipeline that turns the activity log of a state administration's electronic
process system into a Neo4j knowledge graph, discovers process families by
unsupervised clustering, and distils a typical path for each family.

It is the reproducible artifact of an undergraduate thesis, and it produces **two
write-ups of the same study with opposite identity requirements** — a
double-blind English submission and an identified Portuguese thesis. Both draw
their numbers from one generated evidence artifact. Never edit one manuscript to
match the other.

That research framing explains design choices that would otherwise look
excessive: every artifact carries provenance naming the stage that produced it,
every stage declares whether it is reproducible, and a test suite asserts that
the numbers printed in the manuscripts still match the generated evidence.

## Prerequisites

- Python 3.11 or later
- Docker and Docker Compose
- Access to the Trino/Iceberg datalake that holds the activity log
- An API key for the OpenAI-compatible endpoint used for vision parsing and LLM
  features
- 16 GB of RAM or more; a GPU is optional but recommended for the embedding and
  entity-extraction stages

## Install and run

```bash
pip install -r requirements.txt

# Configure credentials — see the note below
$EDITOR .env

docker compose up -d neo4j        # http://localhost:7474

python -m pipeline list           # every registered stage
python -m pipeline run etl        # build the knowledge graph
```

> **Setup trap.** `README.md` instructs `cp .env.template .env`, but no
> `.env.template` file exists in the repository. Create `.env` directly. The
> variables that matter are the `NEO4J_*`, `TRINO_*`, `SEI_*` and `OPENAI_*`
> groups; the authoritative list of every setting and its default is the
> `Settings` dataclass in `pipeline/core/config.py`, and
> `docs/operations/deployment.md` describes them in prose.

Use the project's own virtual environment rather than a neighbouring one — the
scientific dependencies (`hdbscan`, `umap-learn`, `leidenalg`, `neo4j`) are not
present in every environment on a shared machine.

## The two force levels

This is the single most conflated thing in the repository, and worth
internalising before a long run.

| Level | Flag | What it busts |
|---|---|---|
| Runner | `--force`, `--force-stage NAME` | The stage completion record under `.pipeline-state/stages/` |
| Stage-internal | `--flag force=true` | A stage's own per-document or per-cell skip |

They are independent. Many stages keep their own fine-grained skip — `anonymize`
compares source and NER content hashes, `evaluate` skips documents that already
carry a topic, `embed` skips on content hash, `matrix` skips cells whose metrics
file exists. **The runner flags do not touch those.** Passing `--force` re-enters
the stage, which then skips every document it has already processed. To redo the
per-item work, pass `--flag force=true` as well.

Note also that the checkpoint's argument comparison is narrow: only the
corpus-defining flags invalidate a skip. Changing any other flag leaves the
checkpoint valid, so use `--force-stage` when a parameter change should take
effect.

## Checks

```bash
pytest                          # unit tests plus the repository invariant suite
python -m pipeline list         # confirms the registry imported cleanly
python -m pipeline graph        # full DAG in execution order
cd article/latex && latexmk -pdf main.tex
```

`pytest` here is unusual: alongside ordinary unit tests it enforces repository
invariants — the layering rule, licence containment, naming conventions, and the
correspondence between manuscript prose and generated numbers. A failure with a
long explanatory message is usually one of those, and the message names the
incident the check exists to prevent.

## Where to go next

| If you are… | Read |
|---|---|
| Adding or reordering a stage | [Stage DAG and Registry](architecture/stage-dag-and-registry.md) |
| Wondering why a stage was skipped, or how to resume | [Run State, Skipping and the Stage Ledger](architecture/run-state-and-resumability.md) |
| Working on graph reads or writes, or testing them offline | [Execution Modes and Graph I/O](architecture/execution-modes-and-graph-io.md) |
| Adding a setting, or redeploying for another institution | [Configuration and Deployment Seams](architecture/configuration-and-deployment-seams.md) |
| Changing the SQL, the corpus definition, or the graph schema | [Ingest and Knowledge Graph Construction](workflows/ingest-and-graph-build.md) |
| Touching document download or text extraction | [Document Acquisition and Parsing](workflows/document-acquisition-and-parsing.md) |
| Working on privacy, PII detection or entity extraction | [Anonymization and Entity Extraction](workflows/anonymization-and-entity-extraction.md) |
| Changing feature blocks, or adding a clustering algorithm | [Process Features and Clustering](workflows/features-and-clustering.md) |
| Adding a sequence model, or changing how paths are evaluated | [Typical Path Discovery and Evaluation](workflows/typical-path-discovery.md) |
| Changing a table, a figure, or a number in a manuscript | [Evidence Composition and Manuscript Delivery](workflows/evidence-and-manuscript-delivery.md) |
| Naming a run, or adding an experimental arm | [Experiment Arms and Run Identifiers](concepts/experiment-arms-and-run-ids.md) |
| Writing an artifact, or debugging the audit | [Artifact Provenance and Audit](concepts/artifact-provenance-and-audit.md) |
| Running, cleaning or containerising the pipeline | [CLI Surface and Operating the Pipeline](operations/cli-and-runbook.md) |
| Adding a test, or hitting an invariant failure | [Test Strategy and Repository Invariants](testing/test-strategy.md) |

## Repository conventions worth knowing early

- **No comments, no docstrings.** The codebase deliberately carries neither, and
  a test enforces it across `pipeline`, `reports`, `scripts` and the article
  figures. Explanation lives in `docs/`, in this wiki, and in assertion messages.
- **Code is English, research prose is Portuguese.** Identifiers and module names
  are English; stage descriptions, research questions and generated table text
  are in the language of the study.
- **`artifacts/` is generated.** Never hand-edit it. A session-scoped test
  fixture fails the whole suite if a test writes into it.
- **Markdown under `docs/` is draft; `.tex` under `article/` is production.**
  When they disagree, the `.tex` wins and the Markdown is simply stale.

## Related pages

- [Stage DAG and Registry](architecture/stage-dag-and-registry.md)
- [CLI Surface and Operating the Pipeline](operations/cli-and-runbook.md)
- [Experiment Arms and Run Identifiers](concepts/experiment-arms-and-run-ids.md)
