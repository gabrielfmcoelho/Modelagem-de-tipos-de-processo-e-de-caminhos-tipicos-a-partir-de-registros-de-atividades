# Automated Discovery and Modeling of Administrative Process Types from Event Logs

**Process Mining and AI-Driven Knowledge Discovery for Digital Transformation**

## Research Contribution

This repository contains the reproducible engineering artifact of an undergraduate thesis (*Trabalho de Conclusão de Curso*) conducted at the Instituto de Educação, Ciência e Tecnologia do Piauí (iCEV), Engenharia de Software, under the supervision of Prof. Dimmy Karson. The research was carried out with institutional approval and operational support from the Secretaria de Administração do Estado do Piauí (SEAD-PI).

### Research Objective

Many public organizations lack transparency into the actual procedural flows of their administrative processes. This research develops an **automated, evidence-based approach** to discovering process families and distilling their representative models from raw event logs, using **process mining, machine learning, and knowledge graph construction**. The output provides an **auditable foundation** for administrative transparency and supports evidence-based digital transformation initiatives.

### Research Outputs

Two peer-reviewed write-ups of the same empirical study:

1. **`article/latex-ptbr/main.pdf`** — TCC manuscript (Portuguese, ABNT formatting, identified)
   - Audience: Academia and SEAD-PI administration
   - Status: Complete, ready for defense
   
2. **`article/latex/main.pdf`** — Double-blind journal article (English, Springer format)
   - Audience: *Artificial Intelligence and Law* (peer review pending)
   - Status: Legacy reference implementation

---

## System Overview

An end-to-end pipeline that transforms SEI (Sistema Eletrônico de Informações) administrative event logs into actionable knowledge:

```
SEI Event Log (Trino/Iceberg) 
    ↓
[Parsing & NER] → [Knowledge Graph Construction] → [Embedding & Feature Extraction]
    ↓
[Unsupervised Clustering] → [Typical Path Distillation] → [Validation & Evidence]
    ↓
Neo4j Knowledge Graph + Reproducible Artifacts
```

**Core components:**
- Multimodal document parsing (PDF/HTML vision LLM)
- Named entity extraction (GLiNER2 for administrative entities)
- Process graph construction (Neo4j with domain-specific schema)
- Process embedding and feature extraction (bge-m3 + 6 feature blocks)
- Unsupervised clustering (UMAP + HDBSCAN with k-selection)
- Typical path modeling (Markov chains, DFG, GRU, LSTM, Transformers)

> **Getting started?** See [`docs/README.md`](docs/README.md) for the full research context, methodology, corpus description, institutional framing, and limitations (in English and Portuguese).

## Research Methodology

### Data Source & Scope
- **Corpus:** SEI administrative events from Governo do Estado do Piauí (2025)
- **Scale:** 5,445 processes, 283,841 activity events
- **Access:** Read-only via Trino/Iceberg datalake (D-1 mirror)
- **Ethics:** LGPD-compliant anonymization; pre-registered non-inferiority design

### Pipeline Phases
1. **Event Graph Construction** — Parse SEI metadata, construct Processo→Atividade DAG, compute temporal features
2. **Document Analysis** — Extract and parse first document per process; perform NER and PII anonymization
3. **Feature Extraction** — Generate 6 embedding blocks (topics, keywords, temporal features, activity sequences)
4. **Unsupervised Clustering** — UMAP dimensionality reduction + HDBSCAN with k-selection and stability verification
5. **Typical Path Extraction** — Fit multiple models per cluster (Markov, DFG, GRU, LSTM, Transformer)
6. **Validation & Evidence** — Non-inferiority testing, ablation studies, corpus-bias analysis

### Deliverables
- **Knowledge Graph:** Neo4j database with schema covering Processo, Atividade, Unidade, Documento, CategoriaProcesso
- **Reproducible Artifacts:** All results stamped with provenance; full provenance trail in `artifact-contract.md`
- **Evidence Artifact:** `docs/research/RESULTS.md` (authoritative numeric source, generated not hand-edited)
- **Reproducibility:** Docker containerization, stage-by-stage runbook, full parameter logging

## Reproducing the Research

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Access to Trino/Iceberg datalake (SEAD-PI D-1 environment)
- OpenAI API key for vision parsing and LLM features
- 16GB+ RAM; GPU optional but recommended for embedding phases

### Setup & Execution

```bash
# 1. Clone and install dependencies
git clone <repo>
cd ai-pipeline-neo4j
pip install -r requirements.txt

# 2. Configure environment (.env)
# See docs/operations/deployment.md for all variables
cp .env.template .env  # edit with your PG_*, NEO4J_*, OPENAI_*, SEI_* credentials

# 3. Start Neo4j
docker compose up -d neo4j
# Access at http://localhost:7474 (user: neo4j, password from .env)

# 4. Run pipeline stages
python -m pipeline run --help                          # See all available stages
python -m pipeline run download --from 2025-01-01    # Fetch documents
python -m pipeline run etl                            # Build knowledge graph
python -m pipeline run processo-cluster               # Run clustering + model selection
python -m pipeline run results                        # Generate evidence artifacts
```

**Full documentation:**
- Stage-by-stage reference: [`docs/operations/running-stage-by-stage.md`](docs/operations/running-stage-by-stage.md)
- Common operations & debugging: [`docs/operations/runbook.md`](docs/operations/runbook.md)
- GPU acceleration setup: [`docs/operations/gpu-acceleration.md`](docs/operations/gpu-acceleration.md)
- Reproducibility guide: [`docs/research/RUNBOOK.md`](docs/research/RUNBOOK.md)

## Repository Structure

### Core Research & Writing (`article/`, `docs/`)

| Directory | Contents |
|-----------|----------|
| **`article/latex-ptbr/`** | **Main TCC deliverable** (Portuguese, ABNT, identified author) — includes main manuscript, 8 sections, 19 generated tables, bibliography |
| **`article/latex/`** | Journal article (English, Springer format, double-blind) — 12 sections, 19 tables, 130 bibliography entries |
| **`article/figures/`** | Figure generators and renderings (all `.pdf`/`.png`/`.svg` produced from single Python sources) |
| **`docs/architecture/`** | System design: [`architecture.md`](docs/architecture/architecture.md) (schema, idempotency), [`pipeline-overview.md`](docs/architecture/pipeline-overview.md) (macro/micro flows), [`algorithms.md`](docs/architecture/algorithms.md) (embeddings, clustering, path models), [`pipeline-story.md`](docs/architecture/pipeline-story.md) (narrative explanation) |
| **`docs/operations/`** | Runbooks and deployment: [`runbook.md`](docs/operations/runbook.md), [`deployment.md`](docs/operations/deployment.md), [`running-stage-by-stage.md`](docs/operations/running-stage-by-stage.md), [`gpu-acceleration.md`](docs/operations/gpu-acceleration.md) |
| **`docs/research/`** | Empirical evidence: [`RESULTS.md`](docs/research/RESULTS.md) (authoritative numeric source), [`RUNBOOK.md`](docs/research/RUNBOOK.md) (reproducibility guide), [`artifact-contract.md`](docs/research/artifact-contract.md) (provenance specification), model cards for each clustering/path algorithm |
| **`docs/paper/`** | Writing pipeline: [`PAPER-MAP.md`](docs/paper/PAPER-MAP.md) (binding brief, forbidden numbers), OUTLINE.md, ARGUMENT.md, ABNT conversion plan, adversarial reviews |
| **`docs/references/`** | Annotated bibliography: 39 per-reference notes, 5 topic surveys, verification trail |

### Implementation (`pipeline/`)

```
pipeline/
├── cli.py                       # Typer entry point (python -m pipeline)
├── runner.py                    # Stage resolver & executor
├── config.py                    # Configuration (env-driven)
├── neo4j_driver.py             # Neo4j client wrapper
├── cypher.py                    # Cypher templates (MERGE, queries)
├── sql.py                       # SQL templates for SEI schema
├── embedding.py                 # Embedding backends (bge-m3, sentence-transformers)
├── stages/                      # One module per pipeline stage
│   ├── download.py             # Document acquisition
│   ├── parse.py                # Vision LLM → text
│   ├── ner_extract.py          # GLiNER2 named entity extraction
│   ├── atividades.py           # Build activity DAG in Neo4j
│   ├── timeline.py             # Temporal sequencing (SEGUIDA_POR)
│   ├── permanencia.py          # Time-in-state features
│   ├── processo_embed.py       # Feature blocks & embeddings
│   ├── processo_cluster.py     # UMAP + HDBSCAN + k-selection
│   ├── typical_path.py         # Model per cluster
│   └── [others...]             # Evaluation, anonymization, audit
├── model/                       # Algorithm implementations with model cards
│   ├── clustering/hdbscan/     # HDBSCAN model card + code
│   ├── clustering/leiden/      # Leiden model card + code
│   ├── typical_path/markov/    # Markov model card + code
│   └── [others...]
├── readers/                     # Data source adapters (JSON, Neo4j, SQL)
├── writers/                     # Output formatters (JSON, Neo4j, CSV)
├── tests/                       # pytest suite
└── cost/                        # Reference data (IdUnidade lookup table)
```

### Generated Artifacts (`artifacts/`)
- **Stamped artifacts:** Each output carries provenance (stage, run_id, timestamp, commit hash)
- **Caching:** `artifacts/cache/` for intermediate embeddings and features
- **Results:** `artifacts/stats/results_figures.json` — authoritative numeric source for paper tables

### Auxiliary (`scripts/`, `reports/`)
- Ad-hoc analyses (never part of the reproducible pipeline)
- Report generators for interactive exploration
│                                   # article depends on runs from here
├── Dockerfile                      # Python 3.11 + poppler + pip install
├── docker-compose.yml              # Neo4j + pipeline runner
├── requirements.txt                # runtime deps
└── pyproject.toml                  # `pipeline` console script + package discovery
```

Runtime-generated dirs (gitignored):

| Dir | Producer stage | Consumer stage |
| --- | --- | --- |
| `parsed_documents/` | `parse` | `ner_extract`, `resumo`, `situacao` |
| `ner_results/` | `ner_extract` | `ner_load`, downstream graph queries |
| `graphify-out/` | various | snapshots / debugging |
| `.pipeline-state/runs.jsonl` | runner | resume logic, replay |

## Documentation

- [`docs/architecture/architecture.md`](docs/architecture/architecture.md) — data flow, stage graph, idempotency model
- [`docs/operations/running-stage-by-stage.md`](docs/operations/running-stage-by-stage.md) — per-stage reference + how-to-run (command, flags, writes, verify)
- [`docs/architecture/algorithms.md`](docs/architecture/algorithms.md) — algorithms & approach (embeddings, clustering, analytics, GCN, timeline models)
- [`docs/research/RESULTS.md`](docs/research/RESULTS.md) — **the only numeric source.** Generated by `pipeline run results`; every figure in either write-up traces to a `fig:` block here
- [`docs/paper/PAPER-MAP.md`](docs/paper/PAPER-MAP.md) — binding brief for both write-ups: iron rules, forbidden numbers, retracted claims
- [`docs/architecture/algorithms.md`](docs/architecture/algorithms.md) — process clustering: algorithm and design rationale. Figures live in `RESULTS.md`, never here
- [`docs/architecture/algorithms.md`](docs/architecture/algorithms.md) — the `SEGUIDA_POR` flow graph + conformance
- [`docs/research/models-and-reports.md`](docs/research/models-and-reports.md) — **timeline models (Markov / GRU / Transformer) + report generators + how to run**
- [`docs/operations/deployment.md`](docs/operations/deployment.md) — Docker, volumes, scheduling
- [`docs/operations/runbook.md`](docs/operations/runbook.md) — common ops (rerun a stage, prune Neo4j, debug)
- [`docs/operations/gpu-acceleration.md`](docs/operations/gpu-acceleration.md) — CUDA setup for RTX cards (follow-up work)

### Reports & visualizations

The `reports/gen_*.py` scripts read Neo4j and write self-contained pages to `reports/out/`:

- **`explorer.html`** — the single interactive dashboard (`gen_14_explorer.py`): clusters of every algorithm (named), timelines by model, clustering quality, glossaries and an algorithms page

```bash
PY=.venv/bin/python
$PY reports/gen_14_explorer.py     # → reports/out/explorer.html
```

See [`docs/research/models-and-reports.md`](docs/research/models-and-reports.md) for every generator and the end-to-end
**clustering → cohort → comparison** flow.

---

## Research Framing & Context

### Problem Statement
Administrative agencies routinely struggle with process transparency and standardization. Managers often lack empirical understanding of how processes actually execute (as-is) versus how they should execute (to-be). This research addresses that gap by:
- Automating discovery of emergent process types from event logs
- Distilling representative process models per type
- Providing evidence for informed process redesign

### Theoretical Grounding
- **Process Mining:** van der Aalst, W.M.P. (2016) on automated process discovery and conformance checking
- **Unsupervised Learning:** Density-based clustering (HDBSCAN) + dimensionality reduction (UMAP) for high-dimensional process features
- **Knowledge Graphs:** Semantic representations of administrative entities and their relationships
- **Administrative Law:** Brazilian LGPD (Lei Geral de Proteção de Dados), Lei 13.460 (Citizen Charter), and administrative transparency principles

Full bibliography with 39 annotated references: [`docs/references/`](docs/references/README.md)

### Institutional Context
- **Research Institution:** Instituto de Educação, Ciência e Tecnologia do Piauí (iCEV), Engenharia de Software
- **Advisor:** Prof. Dimmy Karson
- **Partner Organization:** Secretaria de Administração do Estado do Piauí (SEAD-PI), Governo do Estado do Piauí
- **Approval:** Institutional review and data governance agreement (LGPD-compliant)

---

## Key Documentation Pointers

### For Researchers & Students
- **Study Overview:** [`docs/README.md`](docs/README.md) — methodology, corpus description, institutional framing, limitations
- **Experiment Design:** [`docs/research/RUNBOOK.md`](docs/research/RUNBOOK.md) — end-to-end reproducibility
- **Numeric Evidence:** [`docs/research/RESULTS.md`](docs/research/RESULTS.md) — **the only authoritative source for figures**
- **Algorithm Details:** [`docs/architecture/algorithms.md`](docs/architecture/algorithms.md) with per-model cards in `pipeline/model/`

### For Reproducers & DevOps
- **Deployment:** [`docs/operations/deployment.md`](docs/operations/deployment.md) — Docker, volumes, scheduling
- **Stage Reference:** [`docs/operations/running-stage-by-stage.md`](docs/operations/running-stage-by-stage.md) — every stage with flags and verification steps
- **Debugging:** [`docs/operations/runbook.md`](docs/operations/runbook.md) — common ops, rerunning stages, pruning artifacts

### For Writers & Reviewers
- **Paper Rules:** [`docs/paper/PAPER-MAP.md`](docs/paper/PAPER-MAP.md) — binding brief, iron rules, **forbidden numbers**
- **Outline & Argument:** [`docs/paper/OUTLINE.md`](docs/paper/OUTLINE.md), [`docs/paper/ARGUMENT.md`](docs/paper/ARGUMENT.md)
- **Review History:** [`docs/paper/reviews/`](docs/paper/reviews/) — adversarial review, past referee feedback

### For Agents & Automation
- **Agent Onboarding:** [`CLAUDE.md`](CLAUDE.md) — orientation for AI agents; authority stack; common traps

---

## Known Limitations

1. **Corpus Scope:** Limited to SEAD-PI administrative processes concluded in 2025; generalization to other jurisdictions requires validation
2. **Document Coverage:** Only first document per process analyzed; partial document sets may bias clustering
3. **Anonymization Arm:** Pre-anonymization required for PII protection; baseline (raw) arm analysis is separate
4. **Temporal Window:** Single-year snapshot; longitudinal process evolution not captured
5. **Model Selection:** k-selection via stability voting; no statistical guarantee of global optimality
6. **Path Models:** Typical paths distilled per model type; ensemble evaluation pending

See [`docs/README.md`](docs/README.md) for detailed limitations discussion and methodological constraints.

---

## Citation

If you use this work in research, cite the TCC:

```bibtex
@thesis{coelho2026,
  author = {Coelho, Gabriel Feitosa Melo},
  title = {Automated Discovery and Modeling of Administrative Process Types from Event Logs},
  school = {Instituto de Educação, Ciência e Tecnologia do Piauí},
  year = {2026},
  type = {Trabalho de Conclusão de Curso}
}
```

And the journal article (when published):
```bibtex
@article{coelho2026-journal,
  author = {Coelho, Gabriel Feitosa Melo and Karson, Dimmy},
  title = {Process Mining and AI-Driven Knowledge Discovery for Administrative Transparency},
  journal = {Artificial Intelligence and Law},
  year = {2026}
}
```

---

## Licenses & Reuse

- **Code:** See LICENSE file
- **Data:** Anonymized artifacts may be used under SEAD-PI institutional agreement
- **Manuscripts:** Protected under academic copyright; contact authors for reuse permissions
- **Figures:** Regenerable from source; single-source generators in `article/figures/gen_*.py`

---

## Contact

- **Gabriel Feitosa Melo Coelho** — Author
- **Prof. Dimmy Karson** — Advisor
- **SEAD-PI** — Institutional Partner

For inquiries regarding institutional data, collaboration, or deployment: contact SEAD-PI administration.

## History

Extracted from `visualizador-de-processos-api` (commit `8187548` and earlier)
via `git filter-branch`, preserving the history of files under
`scripts/pipeline/`, `notebooks/`, `requirements.scripts.txt`, and the
pre-refactor scripts (`extract_ner_gliner2.py`, `etl_neo4j.py`,
`parse_documents.py`, `download_documentos_sead.py`).
