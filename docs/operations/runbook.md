# Runbook

Common operational tasks. Assumes you have `.env` configured and Neo4j
running.

## Inspect pipeline status

```bash
python -m pipeline status
# Shows: filesystem artifact counts, Neo4j node/edge metrics, checkpoint history
```

## Rerun a single stage

```bash
# Bust only this stage's runner checkpoint (deps still skip if complete)
python -m pipeline run ner-extract --force-stage ner-extract

# --force busts the checkpoint of EVERY stage in the resolved plan
# (here: download + parse + ner-extract); each stage's internal per-doc
# skip still avoids redoing finished work
python -m pipeline run ner-extract --force

# Limit scope
python -m pipeline run parse --flag processo=00019.000123/2025-01
python -m pipeline run parse --limit 50

# Enrich sequence (document enrichment, in order):
python -m pipeline run parse                                       # extract text → parsed_documents/<doc_id>/
python -m pipeline run evaluate --mode neo4j                       # topic + summary per document (after parse)
python -m pipeline run ner-extract --flag mode=hybrid              # entities → ner_results/
python -m pipeline run ner-load                                    # project into the graph
python -m pipeline run embed                                       # embeddings → Documento.embedding
python -m pipeline run similarity                                  # SIMILAR_DOC edges
```

Two force levels, easy to conflate:

- `--force` / `--force-stage NAME` — runner-level: ignore the completion
  record in `.pipeline-state/stages/<name>.json` and enter the stage again.
- `--flag force=true` — stage-internal: many stages also keep a per-document
  skip (evaluate skips docs whose `metadata.json` already has a `topic`,
  anonymize skips docs whose source/NER hashes match, embed skips on content
  hash). The runner flags do not touch these; pass `--flag force=true` to
  redo per-document work.

## Resume after a failure

The runner consults `.pipeline-state/stages/*.json` (one record per stage)
to skip completed stages; `.pipeline-state/runs.jsonl` is an append-only
history log. To pick up where the pipeline died:

```bash
python -m pipeline run etl       # skips already-completed stages
```

To restart from scratch:

```bash
python -m pipeline run clean --mode neo4j     # wipe graph (batched; drops indexes/constraints)
rm -rf .pipeline-state/                        # reset checkpoints
python -m pipeline run etl
```

## Anonymization arm (`anonymize` + `text_variant=anon`)

`anonymize` is fs-only: it reads `parsed_documents/<doc_id>/text.txt` (plus
the doc's `ner_results/<doc_id>.json` when present — soft-dep on
`ner-extract`; regex-only otherwise) and writes `text_anon.txt` +
`anon_meta.json` **next to each parsed document**, replacing PII with
deterministic typed placeholders. Method and evaluation:
[`algorithms.md`](../architecture/algorithms.md).

```bash
python -m pipeline run anonymize --flag verify=true
```

- `--flag verify=true` re-runs the regex PII detectors over the anonymized
  output and **fails the stage** (RuntimeError) if any residual
  regex-detectable PII remains. Per-doc residual counts land in
  `anon_meta.json` (`residual_regex_hits`) and in the log.
- Idempotent: a doc is skipped when its `source_sha256` + `ner_sha256` in
  `anon_meta.json` still match. `--flag force=true` regenerates everything.

Downstream stages select the text variant with `--flag text_variant=anon`
(default `raw`). Changing a `--flag` does **not** invalidate the runner
checkpoint, so after a completed raw run you must also bust it:

```bash
python -m pipeline run embed    --no-deps --force-stage embed \
    --flag text_variant=anon
python -m pipeline run evaluate --no-deps --force-stage evaluate --mode neo4j \
    --flag text_variant=anon --flag force=true
```

**IMPORTANT — this updates the LIVE graph in place.** There is no parallel
"anon graph": an anon `embed` overwrites `Documento.embedding`, an anon
`evaluate` overwrites `Documento.topic/.summary` (and the `metadata.json`
topic/summary). This is accepted by design. What protects the arms is that feature matrices are
stamped with a digest of their inputs and `cluster-eval` aborts on a stamp mismatch, plus
cached embeddings that restore identical vectors on an arm switch. **After switching arms you
must re-run `evaluate --no-deps --force`** to re-sync topic/summary on disk with the graph
(`docs/research/RUNBOOK.md` §2),
and the raw state is re-derivable by re-running with
`--flag text_variant=raw` (embed recomputes automatically because the
content hash changes; evaluate additionally needs `--flag force=true`).

Two gotchas verified in code:

- **`evaluate` only regenerates topics with `--flag force=true`.** Its
  per-doc skip only checks that a `topic` exists in `metadata.json` —
  without force, an anon run silently reuses the raw topics and reports
  them as "skipped".
- **`processo-embed` needs `--flag force_all=true` when exporting a
  full-corpus features npz** via `--flag export_features=/path/to.npz`.
  Without it, processos skipped by the per-processo feature hash are
  missing from the npz (the stage logs a warning when this happens).

## Rebuild the article (tables, figures, PDFs)

Nothing in either manuscript is maintained by hand. The pipeline owns the evidence; LaTeX only
typesets it.

```bash
python -m pipeline run results --no-deps --force   # -> RESULTS.md + 19 EN + 19 pt-BR tables/*.tex
python -m pipeline run figures --no-deps --force   # -> article/figures/*.{svg,pdf,png}

cd article/latex      && latexmk -pdf main.tex     # EN, double-blind
cd article/latex-ptbr && latexmk -pdf main.tex     # pt-BR, ABNT, identified
```

To change a number, change the artifact and re-run `results` — never the `.tex`. To check
whether the committed tables still match the artifacts:

```bash
python -m pipeline run results --no-deps --force --flag check=true
```

It fails and names each drifted file. `results` also **aborts** if the matrix is missing, if
`RESULTS.md` lost a `<!-- fig:NAME -->` marker, or if any LaTeX table renders empty — it will
not emit a silently-empty table.

`latexmk -C` clears build artifacts when a stale `.aux`/`.bbl` is in the way. Full reproduction
order for the evidence base itself is in [`../research/RUNBOOK.md`](../research/RUNBOOK.md) §7.

## Inspect what landed in Neo4j

```bash
# Open the Neo4j browser
xdg-open http://localhost:7474

# Useful queries:
MATCH (p:Processo) RETURN count(p);
MATCH (n) RETURN labels(n)[0] AS label, count(*) AS n ORDER BY n DESC;
MATCH ()-[r]->() RETURN type(r) AS rel, count(*) AS n ORDER BY n DESC;

# Find a specific processo's full activity timeline
MATCH (p:Processo {protocolo_formatado: "00019.000123/2025-01"})<-[:DO_PROCESSO]-(a:Atividade)
RETURN a ORDER BY a.data_hora;

# Find similar documents to a given one
MATCH (d:Documento {numero: "0001234"})-[s:SIMILAR_DOC]->(other)
RETURN other.numero, s.score ORDER BY s.score DESC LIMIT 10;
```

## Wipe the graph

```bash
python -m pipeline run clean --mode neo4j
# In Cypher: MATCH (n) DETACH DELETE n; (slow on large graphs)
# Prefer the stage — it batches and drops indexes/constraints too.
# WARNING: `pipeline run clean` deletes immediately, with NO confirmation prompt.
```

## Debug a stuck stage

```bash
# Run with verbose logging
LOG_LEVEL=DEBUG python -m pipeline run ner-extract --flag processo=00019.000123/2025-01

# Check disk space — pipeline artifacts can balloon
du -sh parsed_documents/ ner_results/ graphify-out/

# Check Neo4j health
docker compose ps neo4j
docker compose logs neo4j --tail 50

# Check for orphan locks
docker compose exec neo4j cypher-shell \
  -u neo4j -p $NEO4J_PASSWORD \
  "CALL dbms.listTransactions() YIELD transactionId, currentQuery, status RETURN *;"

# A stale runner lock (crashed run) lives at .pipeline-state/lock — the
# runner clears it automatically if the recorded PID is dead.
```

## Emit a stage to JSON (audit / transport / replay)

Useful for code review, audit, or air-gapped replication. There is no
separate `replay` command; emit and replay are `run` modes.

```bash
# Emit NDJSON instead of writing Neo4j (passing --emit-dir implies --mode json-emit)
python -m pipeline run atividades --mode json-emit --emit-dir ./emit

# Review or transport the NDJSON
ls emit/nodes/ emit/edges/ emit/templates/
head emit/templates/load_atividades.ndjson

# Stages whose `pipeline list` entry includes json-replay (timeline,
# permanencia, situacao, similarity, resumo) can recompute from the
# emitted NDJSON instead of the live graph:
python -m pipeline run timeline --mode json-replay --read-dir ./emit
```

## Vector index issues

If `similarity` is slow or returns empty results:

```cypher
SHOW INDEXES YIELD name, state WHERE name CONTAINS 'embedding';
# Expected: documento_embedding_idx, state: ONLINE
```

Rebuild:

```cypher
DROP INDEX documento_embedding_idx IF EXISTS;
```

Then rerun `embed` (the stage creates the index if missing).

## Update GLiNER2 / sentence-transformers model

```bash
# Change the model name via stage flag (default: fastino/gliner2-base-v1)
python -m pipeline run ner-extract --flag model=fastino/gliner2-large-v1

# Embeddings are content-hashed; switching OPENAI_MODEL_EMBEDDING forces
# recompute on next `embed` run (existing embeddings stay until overwritten).
```

## Disk pressure

The pipeline produces several large directories that grow with the corpus:

```bash
# Audit
du -sh parsed_documents/ ner_results/ graphify-out/ documentos_sead/

# Prune parsed_documents older than 90 days (safe — regeneratable)
find parsed_documents/ -mtime +90 -delete

# Prune raw SEI documents older than 30 days (regeneratable via download)
find documentos_sead/ -mtime +30 -delete
```

Note: `embed` keeps a `sha256(model + text)` hash on each `:Documento`, so
deleting `parsed_documents/` does NOT trigger re-embedding — but it does
make the source un-auditable. Move them to cold storage rather than
deleting if you need traceability.

## Experimento ad-hoc: famílias no corpus VIVO do lake

O estudo agrupou processos **concluídos**. A operação precisa saber a família de
um processo que ainda está **correndo** — justamente aquele cujo trace está
incompleto. `scripts/lake_cluster_experiment.py` (run id `exp-lake`) reusa a
varredura de `k`, o cotovelo e a nomeação contrastiva deste repositório sobre os
dados do lake, e treina um classificador sobre PREFIXOS de trace para inferir a
família dos que estão em andamento.

```bash
PY=.venv/bin/python
$PY scripts/lake_cluster_experiment.py --limit 400 --skip-naming   # ensaio
$PY scripts/lake_cluster_experiment.py --run-id exp-lake           # completo
```

Protocolo, baselines, como ler a curva e a limitação conhecida:
[`lake-cluster-experiment.md`](lake-cluster-experiment.md). Nada dele entra no
pipeline reprodutível, e nenhum número dele vai para `RESULTS.md`.
