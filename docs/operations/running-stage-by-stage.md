# Pipeline stages — reference & how-to-run

The complete per-stage guide: what each stage does, its command and flags, what
it writes, and how to verify it. For the conceptual data flow see
[`architecture.md`](../architecture/architecture.md); for day-2 operations (resume, replay, disk
pruning, vector-index rebuild) see [`runbook.md`](runbook.md).

> All commands assume you run from the repo root with deps installed and a
> `.env` present. The CLI is `python -m pipeline` (or the `pipeline` console
> script if installed).

---

## 0. Prerequisites

```bash
# create a .env at the repo root and fill in the values below
pip install -r requirements.txt
pip install -r requirements-gpu.txt    # ONLY if you will run `gcn-distill` (torch-geometric) or want GPU embed/NER
docker compose up -d neo4j # graph DB at http://localhost:7474
```

Environment variables (`.env`) by concern:

| Group | Vars | Used by |
| --- | --- | --- |
| Neo4j | `NEO4J_URI` `NEO4J_USER` `NEO4J_PASSWORD` `NEO4J_DATABASE` | every `neo4j`-mode stage |
| **Trino/Iceberg source** | `TRINO_HOST` `TRINO_PORT` `TRINO_USER` `TRINO_PASSWORD` (opt: `TRINO_CATALOG`=iceberg, `TRINO_SCHEMA`=sei_bronze, `TRINO_HTTP_SCHEME`, `TRINO_VERIFY_SSL`) | **`precreate`, `atividades` — the initial load** |
| LLM (Mandu/OpenAI-compat) | `OPENAI_BASE_URL` `OPENAI_API_KEY` `OPENAI_MODEL` `OPENAI_MODEL_EMBEDDING` | `parse`, `embed`, `processo-cluster` |
| SEI API | `SEI_BASE_URL` `SEI_API_USER` `SEI_API_PASSWORD` | `download` |
| Compute | `PIPELINE_DEVICE` `PIPELINE_DTYPE` `PIPELINE_EMBED_BATCH_SIZE` | `embed`, `ner-extract`, `gcn-distill` |

> **No Postgres, no CSV.** The initial load (`precreate`, `atividades`) reads
> `sei_bronze.sei_atividades` from the lakehouse via the `trino` client; the
> graph derives unidades/órgãos/tipos **and their ids** (`id_processo`,
> `id_unidades`) straight from that data. The pipeline has **no Postgres
> dependency** — `download` authenticates with `SEI_API_USER`/`SEI_API_PASSWORD`
> (or `SEI_TOKEN`) from `.env`, or `--flag token=…` / `--flag usuario=…`/`senha=…`.
> (Seeding the API's `unidades_sei`/`tipos_documento`
> tables lives in the API repo.)

---

## 1. CLI you will use constantly

```bash
python -m pipeline list                 # all registered stages + types
python -m pipeline run <stage>...        # run stage(s); dependencies auto-resolve
python -m pipeline run <stage> --dry-resolve   # show the resolved DAG, run nothing
python -m pipeline status                # filesystem + Neo4j + checkpoint state
python -m pipeline                       # interactive wizard
```

`run` flags (from `pipeline/apps/run.py`):

| Flag | Meaning |
| --- | --- |
| `--mode neo4j\|json-emit\|json-replay\|fs` | I/O backend (each stage has a default) |
| `--from YYYY-MM-DD` / `--to YYYY-MM-DD` | creation-date window (Trino discovery) |
| `--limit N` | cap rows/docs processed |
| `--workers N` / `--batch-size N` / `--chunk-size N` | throughput knobs |
| `--emit-dir DIR` (`--emit-json`) / `--read-dir DIR` (`--read-json`) | JSON artifact in/out |
| `--force` | re-run all selected stages, ignoring checkpoints |
| `--force-stage NAME` | re-run only NAME (repeatable) |
| `--no-deps` | run **only** the named stage(s); skip dependency resolution — e.g. `run parse --no-deps` parses whatever's on disk without re-running `download` |
| `--state-dir DIR` | override `.pipeline-state/` |
| `--flag KEY=VALUE` | **stage-specific flag (repeatable)** — how cohort/scoring stages are configured |
| `--neo4j-uri/-user/-password/-database`, `--log-level` | overrides |

**Checkpoints — two levels.** Runner-level stage checkpoints live in
`.pipeline-state/stages/<stage>.json` (with an append-only history in
`.pipeline-state/runs.jsonl`); a completed stage is skipped on re-run. The
skip check only compares `from` / `to` / `limit` / `orgao`, so changing any
other `--flag` does **not** invalidate a checkpoint — use
`--force-stage NAME` to bust one stage's checkpoint, or `--force` to bust
every stage in the resolved plan. Separately, several stages keep a
**stage-internal per-document skip** (parse/evaluate/anonymize/embed/
ner-extract hash or existence checks); the runner flags don't touch those —
pass `--flag force=true` to redo per-document work. The analysis and op
stages (`cohort`, `link-score`, `doc-band`, `dfg-build`, `gcn-distill`,
`comum-graph`, `cluster-eval`, `graph-health`, `resumo`, `clean`) declare
`can_skip_when_done=False`, so they always re-run.

---

## 2. The stages, in execution order

Run them in this order the first time; afterward run any single stage and its
dependencies resolve automatically.

> **Reading log lines.** The runner prints internal *phase letters* from the
> original ETL lineage — `A`=precreate, `B`=atividades, `C`=timeline,
> `D`=permanência (also stored as `"phase"` in json-emit output). They are an
> implementation detail and are **unrelated** to the step groups below — e.g. a
> log line `Phase C: Building timeline DAG` belongs to the **Core graph** group.

### Setup — no bootstrap

There are no Postgres bootstrap stages and no CSV. Unidades, órgãos and tipos —
and their ids (`id_processo` on `:Processo`, `id_unidade` on `:Unidade`, from
`sei_atividades.id_processo`/`id_unidades`) — are derived from the Trino source
during `precreate`. (Seeding the API's `unidades_sei` / `tipos_documento` tables
is done from the API repo, not here.)

### Core graph (`etl`) · `--mode neo4j`

```bash
# All five at once (recommended), scoped to a date window + born-in órgão:
python -m pipeline run etl --from 2025-01-01 --to 2026-01-01 --flag orgao=SEAD-PI
```

> **`--flag orgao=SEAD-PI`** loads **only processos born in SEAD-PI** — those
> whose creation event (`descricao_replace LIKE 'Processo %gerado%'`) was
> executed by a `SEAD-PI/…` unidade — plus their *full* downstream activity
> (including units they were later remitted to). Omit it to load every processo
> created in the window. (Changing `orgao` invalidates the stage checkpoint.)

Or one at a time (each depends on the previous):

| Stage | Command | Writes | Verify (Cypher) |
| --- | --- | --- | --- |
| `precreate` | `python -m pipeline run precreate --from 2025-01-01 --to 2026-01-01` | `Orgao/Unidade/TipoAcao/TipoProcedimento/Usuario` + `Processo` skeleton, `CRIADO_NA_UNIDADE`, `CRIADO_NO_ORGAO` | `MATCH (p:Processo) RETURN count(p)` |
| `atividades` | `python -m pipeline run atividades` | `Atividade` + `DO_PROCESSO/EXECUTADO_*/CONTEM_DOCUMENTO` | `MATCH (a:Atividade) RETURN count(a)` |
| `timeline` | `python -m pipeline run timeline` | `SEGUIDA_POR` / `PRECEDIDA_POR` / `INICIOU_PROCESSO` DAG | `MATCH ()-[r:SEGUIDA_POR]->() RETURN count(r)` |
| `permanencia` | `python -m pipeline run permanencia` | `PASSOU_PELA_UNIDADE/ORGAO` (durations, visits) | `MATCH ()-[r:PASSOU_PELA_UNIDADE]->() RETURN count(r)` |
| `situacao` | `python -m pipeline run situacao` | open/closed state: `Processo.situacao`, `unidades_em_aberto_count`, `:Ciclo`, `EM_ABERTO_NA_UNIDADE` | `MATCH (p:Processo) WHERE NOT (p)-[:EM_ABERTO_NA_UNIDADE]->() RETURN count(p) AS concluded` |

### Document enrichment · `--mode fs` then `--mode neo4j`

`download → parse → ner-extract` run in **`fs`** mode (files only, no graph);
`ner-load` projects the extracted entities into Neo4j.

| Stage | Command (typical) | Writes |
| --- | --- | --- |
| `download` | `python -m pipeline run download --flag orgao=SEAD-PI` — auth from `.env` (`SEI_API_USER`/`SEI_API_PASSWORD` or `SEI_TOKEN`) or `--flag token=…` / `--flag usuario=… --flag senha=…`; add `--flag only_first_doc=true` for one initiating doc/processo | `documentos_sead/<protocolo>/<doc>/…` + `_download_log.ndjson` (per-doc outcomes; stored & cancelled docs skipped on re-run) |
| `parse` | `python -m pipeline run parse` · env `OPENAI_BASE_URL/API_KEY/MODEL` | `parsed_documents/<doc>/text.txt` + `metadata.json` (per document). HTML → body via BeautifulSoup (strips header/signature/footer); PDF uses the native text layer (`pdfplumber`) and only falls back to the vision model (`pdf2image`, needs `poppler-utils`) for scans; Office/`.csv` summarized via LLM |
| `evaluate` | `python -m pipeline run evaluate --mode neo4j` | topic + summary (LLM, pt-BR) → `metadata.json` (+ `:Documento.topic/.summary` in `neo4j`/`json-emit` mode). Depends on `parse`. Details below |
| `ner-extract` | `python -m pipeline run ner-extract --flag mode=hybrid` | reads `parsed_documents/<doc>/text.txt` (depends on `parse`) → `ner_results/<doc>.json`. Modes: `gliner2` (fast), `llm` (LLM-only), `hybrid` (GLiNER2 + LLM consolidation, default). GPU-capable — see [`gpu-acceleration.md`](gpu-acceleration.md), incl. `--shard K/N` parallel workers |
| `ner-load` | `python -m pipeline run ner-load` | `PessoaFisica`/`PessoaJuridica`/`CargoFuncao`/`Legislacao` nodes + `MENCIONA_*` edges to the originating `:Documento` |
| `anonymize` | `python -m pipeline run anonymize --flag verify=true` | `parsed_documents/<doc>/text_anon.txt` + `anon_meta.json` — PII → deterministic typed placeholders (regex + NER spans; soft-dep `ner-extract`). `verify=true` fails the stage on residual regex-detectable PII. Downstream: `embed`/`evaluate` accept `--flag text_variant=anon` — see the runbook's [anonymization arm](runbook.md#anonymization-arm-anonymize--text_variantanon) |

Verify: `MATCH (n) WHERE n:PessoaFisica OR n:PessoaJuridica OR n:CargoFuncao OR n:Legislacao RETURN labels(n)[0] AS entity, count(*) ORDER BY count(*) DESC`

> `parse`, `ner-extract`, `embed` and `evaluate` all read the same
> `parsed_documents/` text — a single, consistent text source; `ner-extract`
> does not re-extract from the raw downloads.

### `evaluate` — topic + summary per document (LLM)

Reads `parsed_documents/<doc_id>/text.txt` + `metadata.json`, asks the text
model (`OPENAI_MODEL_EVALUATE` → `OPENAI_MODEL`) for a short **topic** and a
one-paragraph **summary** (pt-BR), writes them to `metadata.json` and — in
`neo4j`/`json-emit` mode — to `:Documento.topic` / `:Documento.summary`.

- Idempotent: skips documents whose `metadata.json` already has a `topic`.
  Use `--flag force=true` to re-evaluate — the runner-level `--force` only
  busts the stage checkpoint and does **not** bypass this per-doc skip.
- Depends on `parse`; the graph write needs the `:Documento` node (soft-dep `ner-load`).

```bash
python -m pipeline run evaluate --mode neo4j                    # graph + JSON
python -m pipeline run evaluate --mode fs                       # JSON only
python -m pipeline run evaluate --force-stage evaluate --flag force=true   # re-evaluate everything
```

### Embeddings & clustering · `--mode neo4j`

> Algorithm/approach (models, TF-IDF feature blocks, UMAP + HDBSCAN, LLM naming): see [`algorithms.md`](../architecture/algorithms.md).

| Stage | Command | Writes | Verify |
| --- | --- | --- | --- |
| `embed` | `python -m pipeline run embed` — `--flag embedder=mandu\|local\|auto`, `--flag text_variant=raw\|anon` | `Documento.embedding` (1024-d) + `documento_embedding_idx` vector index | `MATCH (d:Documento) WHERE d.embedding IS NOT NULL RETURN count(d)` |
| `similarity` | `python -m pipeline run similarity` | `SIMILAR_DOC {score, tier, intra_processo}` | `MATCH ()-[r:SIMILAR_DOC]->() RETURN r.tier, count(*)` |
| `processo-embed` | `python -m pipeline run processo-embed` — flags: `first_doc_only` (default `true`), `semantic_weight`/`topic_weight`/`unigram_weight`/`bigram_weight`/`tipo_acao_weight` (default `1.0`), `umap_n_components` (50). Soft-deps on `evaluate` for the topic block. `--flag export_features=/path.npz` dumps the feature matrix — pair it with `--flag force_all=true` or hash-skipped processos are missing from the npz | `Processo.cluster_features` (50-d UMAP) | `MATCH (p:Processo) WHERE p.cluster_features IS NOT NULL RETURN count(p)` |
| `processo-cluster` | `python -m pipeline run processo-cluster` | `CategoriaProcesso` + `CATEGORIZADO_COMO` | `MATCH (c:CategoriaProcesso) RETURN c.nivel, count(*)` |

> **Backends & idempotency.** `embed` uses **Mandu** (`/v1/embeddings`, zero local
> cost) with a **sentence-transformers** fallback, and content-hashes
> `sha256(model+text)` so unchanged docs are skipped — switch
> `OPENAI_MODEL_EMBEDDING` to force a recompute. `similarity` runs two passes:
> cross-corpus top-K via the `documento_embedding_idx` vector index, then
> exhaustive intra-processo cosine. `processo-embed` builds five L2-normalized,
> per-block-weighted blocks — **first-doc** semantic + **first-doc** topic/summary
> (from `evaluate`) + unidade unigram/bigram TF-IDF + tipo-ação histogram — then
> `processo-cluster` runs UMAP → HDBSCAN. (Set `--flag first_doc_only=false` for the
> legacy all-docs rank-weighted semantic. See [`algorithms.md`](../architecture/algorithms.md) §3.)

### Cohort analysis & ideal-graph distillation · `--mode neo4j`

This is the cohort → scoring → DFG → GCN chain. Every stage is keyed by a
`cohort_id` and depends on the **Core graph** group (and, for `doc-band`, on `similarity`).
For the algorithm/approach (scoring math, the band metric, DFG node features, GCN
distillation) see [`algorithms.md`](../architecture/algorithms.md).

#### `cohort` — materialize the curated set
Depends on `situacao` (soft: `processo-cluster`). Picks processos **born in**
an órgão within a date window, optionally narrowed to clusters / a manual list,
then capped by process count.

```bash
python -m pipeline run cohort \
  --from 2025-01-01 --to 2026-01-01 \
  --flag cohort_id=contratacao-2025 \
  --flag orgao_prefix=SEAD-PI \
  --flag cluster_ids=<CategoriaProcesso-id>[,<id>...] \
  --flag cap=300
```

| `--flag` | Default | Purpose |
| --- | --- | --- |
| `cohort_id` | *(required)* | identifier for this cohort |
| `cohort_label` | = cohort_id | display label |
| `orgao_prefix` | `SEAD-PI` | creation-órgão (exact sigla prefix) |
| `born_via` | `orgao_edge` | `orgao_edge` (uses `CRIADO_NO_ORGAO`) or `creation_activity` (fallback) |
| `only_concluded` | `true` | keep only concluded processos (`unidades_em_aberto_count == 0`) |
| `cap` | *(none)* | max members (no per-document subsampling) |
| `cap_order` | `oldest` | truncation order: `oldest` or `newest` (concluded always first) |
| `cluster_ids` | — | csv of `CategoriaProcesso.id` to include |
| `manual_protocolos` | — | csv of protocolos, or `@/path/to/file` |
| `add_protocolos` / `remove_protocolos` | — | hard include / exclude overrides |

Verify: `MATCH (:Processo)-[:MEMBRO_DA_COORTE]->(c:Coorte {id:'contratacao-2025'}) RETURN c.n_after_cap, count(*)`

#### `link-score` — contribution-to-conclusion on links/nodes
Depends on `cohort`, `timeline`, `permanencia`, `situacao`.

```bash
python -m pipeline run link-score --flag cohort_id=contratacao-2025
```
Flags: `w_adv` (0.5), `w_speed` (0.2), `rework_penalty` (0.5),
`idle_penalty` (0.4), `idle_factor` (3.0), `idle_floor_h` (24).
Writes `SEGUIDA_POR.{advancement_score,speed_score,rework_flag,idle_flag,contrib_score}`
and `Atividade.node_contrib_score`.

Verify: `MATCH ()-[r:SEGUIDA_POR]->() WHERE r.contrib_cohort_id='contratacao-2025' RETURN min(r.contrib_score), avg(r.contrib_score), max(r.contrib_score)`

#### `doc-band` — embedding band metric
Depends on `cohort`, `similarity` (soft: `embed`).

```bash
python -m pipeline run doc-band --flag cohort_id=contratacao-2025
```
Flags: `band_center` (0.60), `band_halfwidth` (0.20), `band_agg`
(`median`|`mean`), `use_cross_corpus` (false). Writes `Documento.band_score`,
`Atividade.activity_band_score`, `Processo.processo_band_score` (+ `band_imputed`).

Verify: `MATCH (d:Documento) WHERE d.band_score IS NOT NULL RETURN count(d)`

#### `dfg-build` — aggregated directly-follows graph
Depends on `cohort`, `link-score`, `doc-band`.

```bash
python -m pipeline run dfg-build --flag cohort_id=contratacao-2025
# optional: --flag node_identity=tipo_acao_grupo
```
Writes `DfgNode` (with a fixed feature vector) + `DIRECTLY_FOLLOWS`.

Verify: `MATCH (n:DfgNode {cohort_id:'contratacao-2025'}) RETURN count(n)`

#### `gcn-distill` — node importance + ideal graph
Depends on `dfg-build`. Needs `torch-geometric` for `method=gcn`; otherwise it
falls back to the PageRank baseline.

```bash
python -m pipeline run gcn-distill --flag cohort_id=contratacao-2025 --flag method=gcn
# baselines: --flag method=pagerank   or   --flag method=weighted_degree
```
Flags: `w_struct` (0.5), `w_band` (0.2), `w_gcn` (0.3), `prune_quantile`
(0.25), `freq_floor` (1), `hidden_dim` (32), `epochs` (200), `lr` (0.01).
Writes `DfgNode.{gcn_importance,in_ideal_graph}`,
`DIRECTLY_FOLLOWS.{gcn_edge_importance,in_ideal_graph}`, and
`IDEAL_DIRECTLY_FOLLOWS`.

Inspect the distilled "ideal" flow:
```cypher
MATCH (a:DfgNode {cohort_id:'contratacao-2025'})-[:IDEAL_DIRECTLY_FOLLOWS]->(b:DfgNode)
RETURN a.tipo_acao AS from, b.tipo_acao AS to ORDER BY from, to;

MATCH (n:DfgNode {cohort_id:'contratacao-2025'}) WHERE n.in_ideal_graph
RETURN n.tipo_acao, n.gcn_importance ORDER BY n.gcn_importance DESC;
```

> Tip: run `gcn-distill` once with `method=pagerank` and once with `method=gcn`
> and compare `in_ideal_graph` — the GCN should justify itself against the
> baseline (see the plan's "Risks" notes).

### Evidence stages (produce the paper's numbers) · `--mode fs`

These eight run after the matrix and write into `artifacts/stats/`. All are read-only with
respect to the graph, so `--mode fs` is enough and none needs Neo4j. Every figure in
`docs/research/RESULTS.md` and in the manuscript traces to one of them.

| Stage | Command | Purpose |
| --- | --- | --- |
| `select-k` | `python -m pipeline run select-k --flag run_id=… --mode fs` | sweep *k* for the centroid clustering and record silhouette / elbow / combined choice → `k_sweep.json`. **A registered stage**, despite older docs describing it as a standalone script |
| `cluster-stability` | `python -m pipeline run cluster-stability --flag run_id=… --flag algo=hdbscan --mode fs` | cluster-wise stability by subsampling (25 draws at 80%), matched by Jaccard overlap → `stability.json`. Lower bound: the clusterer is refit, the UMAP reduction is not |
| `cluster-audit` | `python -m pipeline run cluster-audit --no-deps --mode fs` | refit **every** clustering from its own stamped `.npz` and compare to stored labels → `artifacts/stats/clustering-audit.json` (19/19 at agreement 1.0). Fails the run on any mismatch unless `--flag strict=false` |
| `cluster-control` | `python -m pipeline run cluster-control --flag run_id=… --mode fs` | build the shuffled-partition null — permutes membership while preserving cluster count, size distribution and evaluated population |
| `ablation` | `python -m pipeline run ablation --no-deps --mode fs` | feature-block and timeline-truncation ablations against the full-history partition → `artifacts/stats/ablation.json` |
| `corpus-bias` | `python -m pipeline run corpus-bias --no-deps --mode fs` | right-censoring estimate by birth month → `artifacts/stats/corpus_bias.json`. The 18.2% it reports is a shortfall **within the concluded population**, not of the year's openings |
| `noninferiority` | `python -m pipeline run noninferiority --no-deps --mode fs` | paired bootstrap of the raw vs anonymised arms against the pre-registered margin (**RQ5**) → `artifacts/stats/noninferiority.json` |
| `keywords` | `python -m pipeline run keywords --mode fs` | build the controlled keyword vocabulary incrementally from opening documents (needs `OPENAI_*`); feeds the sixth feature block |

Four more evidence stages sit slightly apart — two build the substrate the eight above consume,
two answer a question of their own. All are registered stages; nothing here is a loose script.

| Stage | Command | Purpose |
| --- | --- | --- |
| `export-traces` | `python -m pipeline run export-traces --mode neo4j` | read Neo4j **once** and freeze every trace into `artifacts/traces/` with one grouping per clustering. Everything downstream of traces then runs without Neo4j. Also the origin of the unidade acronyms `results` uses to blind the catalogue table |
| `corpus-funnel` | `python -m pipeline run corpus-funnel --no-deps` | count the corpus funnel straight from Trino — opened in the year, concluded within it, and the matching activity volume → the corpus figures quoted in both manuscripts' prose |
| `temporal-holdout` | `python -m pipeline run temporal-holdout --no-deps --force` | rescore each timeline truncation over the cases every cut evaluates → `artifacts/stats/temporal_holdout_matched.json`, the source of `tab:temporal-holdout` |
| `constraint-cost` | `python -m pipeline run constraint-cost --no-deps` | measure what the flow automaton costs the generator: at each retained decision point, compare the Markov chain's top-*k* candidates with and without the filter → `artifacts/stats/constraint_cost.json`, the evidence for the second half of **RQ4** |
| `conformance` | `python -m pipeline run conformance --no-deps --flag run_id=… --flag algo=… --mode fs` | per-cluster fitness and precision (token replay) → `artifacts/conformance/<run_id>/<algo>/pm4py-<alphabet>.json`. One cell per invocation; alignment is expensive |

> **`conformance` runs pm4py as a subprocess, never as an import.** pm4py is **AGPL v3**; the
> computation lives in `scripts/conformance_pm4py.py` so the licence cannot attach to the
> deployable package. The stage exists to give the result provenance, not to move the code
> inside. `test_no_copyleft_dependency_reaches_the_deployable_package` fails if anything under
> `pipeline/` imports it.

> `constraint-cost` and `temporal-holdout` both read `artifacts/traces/protocol_traces.json.gz`,
> so `export-traces` has to have run at least once. `results` hard-raises without it.

---

### Operational

| Stage | Command | Purpose |
| --- | --- | --- |
| `resumo` | `python -m pipeline run resumo` | print graph statistics |
| `graph-health` | `python -m pipeline run graph-health --mode neo4j` | read-only flow-connectivity report — isolated/orphaned/disconnected activities by type (see [`docs/architecture/algorithms.md`](../../docs/architecture/algorithms.md)). Run before/after a `timeline` re-run |
| `cluster-eval` | `python -m pipeline run cluster-eval --flag run_id=…` | read-only clustering evaluation (HDBSCAN/KMeans/Leiden) — metrics persisted under `artifacts/`. Depends on `processo-embed` |
| `cluster-consensus` | `python -m pipeline run cluster-consensus --flag run_id=… --flag k=120 --no-deps` | CSPA co-association consensus over the per-algo `labels.json` sets → `artifacts/clustering/<run_id>/consensus/`. Depends on `cluster-eval`; `--flag force=true` to overwrite |
| `cluster-name` | `python -m pipeline run cluster-name --flag run_id=… --flag algo=…` | LLM naming for any flat clustering (incl. `consensus`) from its `labels.json` → `names.json`. Needs Neo4j + `OPENAI_*` creds; skips if `names.json` exists unless `--flag force=true`; `--flag merge_threshold=0.2` builds the macro/micro hierarchy |
| `comum-graph` | `python -m pipeline run comum-graph --flag cohort_id=…` | "comum" graph — representative cohort timeline in per-unidade swimlanes. Depends on `dfg-build` |
| `clean` | `python -m pipeline run clean --mode neo4j` | wipe the graph (destructive; **deletes immediately, no confirmation prompt**) |
| `graph-census` | `python -m pipeline run graph-census --no-deps --mode neo4j` | freeze the loaded graph → `artifacts/stats/graph_build.json` |
| `document-funnel` | `python -m pipeline run document-funnel --no-deps` | the two document funnels → `artifacts/stats/document_funnel.json` |
| `feature-census` | `python -m pipeline run feature-census --no-deps --mode fs` | inventory the feature matrices → `artifacts/stats/feature_build.json` |
| `compose-evidence` | `python -m pipeline run compose-evidence --no-deps --mode fs` | derive every composed artifact from the cells — see [`../research/artifact-design.md`](../research/artifact-design.md) |
| `artifact-audit` | `python -m pipeline run artifact-audit --no-deps` | walk `artifacts/` and report files with no `_meta` block (undeclared producer) and files whose recorded inputs have since changed (drift). `--flag strict=true` turns the report into a failure |
| `build-arm` | `python -m pipeline run build-arm --flag run_id=… --mode neo4j` | macro: a whole arm end to end — features, parameter selection, the five clusterings (`base`, `kelbow`, `ksil`, `lres`, `hcoarse`), consensus, stability and audit. Replaces the old `scripts/build_arm.sh` |
| `typical-cells` | `python -m pipeline run typical-cells --mode neo4j` | the two auxiliary cell families `results` aggregates beyond the matrix: `artifacts/typical/_temporal_holdout/` (4 cuts × 2 alphabets) and `artifacts/typical/_shared_population/{unrestricted,restricted,restricted_allmodels}/` (2 arms × 4 algorithms). Replaces the `regenerate.sh` that used to live inside the artifact tree |
| `figures` | `python -m pipeline run figures --no-deps` | regenerate the figures both manuscripts include, from the generators in `article/figures/`. `clusters-umap` sits behind `--flag umap=true`: it needs Neo4j and no `.tex` includes it |

---

## 3. Macros (run a whole phase)

| Macro | Expands to |
| --- | --- |
| `etl` | `precreate → atividades → timeline → permanencia → situacao` |
| `etl-full` | `etl + download + parse + ner-extract + ner-load + embed + similarity + processo-cluster` |

```bash
python -m pipeline run etl --from 2025-01-01 --to 2026-01-01
python -m pipeline run etl-full --from 2025-01-01 --to 2026-01-01
```

---

## 4. End-to-end worked example (contratação 2025)

```bash
# 1. Core graph — load ONLY processos born in SEAD-PI, in the window
python -m pipeline run etl --from 2025-01-01 --to 2026-01-01 --flag orgao=SEAD-PI

# 2. (optional) documents + embeddings, needed only for doc-band signals
#    auth: --flag token=SEI_TOKEN  OR  --flag usuario=… --flag senha=…
#    initial smoke pass — one initiating doc/processo (idempotent; re-run without
#    the flag to backfill the rest, existing files are skipped):
python -m pipeline run download --flag token=SEI_TOKEN --flag orgao=SEAD-PI --flag only_first_doc=true
python -m pipeline run download --flag token=SEI_TOKEN --flag orgao=SEAD-PI
python -m pipeline run parse
python -m pipeline run embed
python -m pipeline run similarity

# 3. Cohort → scoring → DFG → GCN  (deps auto-resolve, but explicit is clearer)
python -m pipeline run cohort --from 2025-01-01 --to 2026-01-01 \
    --flag cohort_id=contratacao-2025 --flag orgao_prefix=SEAD-PI --flag cap=300
python -m pipeline run gcn-distill --flag cohort_id=contratacao-2025 --flag method=gcn
#   ^ this single call resolves and runs link-score, doc-band, dfg-build first.
```

---

## 5. Resume, re-run, troubleshoot

```bash
python -m pipeline run etl                       # resumes; skips completed stages
python -m pipeline run situacao --force-stage situacao   # re-run just one stage
python -m pipeline run gcn-distill --flag cohort_id=contratacao-2025 --force
rm -rf .pipeline-state/                            # reset all checkpoints
LOG_LEVEL=DEBUG python -m pipeline run dfg-build --flag cohort_id=contratacao-2025
python -m pipeline run gcn-distill --flag cohort_id=contratacao-2025 --dry-resolve  # show DAG only
```

Remember the two force levels (§1): `--force`/`--force-stage` bust runner
checkpoints; `--flag force=true` busts a stage's internal per-document skip.

If a cohort-analysis stage reports zero rows, confirm the upstream cohort exists
(`MATCH (c:Coorte) RETURN c.id, c.n_after_cap`) and that `situacao` populated
`unidades_em_aberto_count` (cohort's `only_concluded` filter depends on it).
