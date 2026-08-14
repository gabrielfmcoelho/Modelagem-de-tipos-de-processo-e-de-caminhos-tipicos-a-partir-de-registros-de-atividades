# Deployment

## Local development

```bash
# 1. Configure
# Create a .env at the repo root with your NEO4J_*, TRINO_*, OPENAI_* and
# SEI_* values (see the env-var table in running-stage-by-stage.md §0).

# 2. Start Neo4j (background)
docker compose up -d neo4j

# 3. Install pipeline deps (host Python ≥ 3.11 — venv or an existing
#    conda env both work)
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 4. Run the pipeline (host)
python -m pipeline run --help
python -m pipeline run download --flag orgao=SEAD-PI
python -m pipeline run precreate
python -m pipeline run parse
python -m pipeline run ner-extract
# ... etc
```

The CLI is registered via `pyproject.toml` as `pipeline`, so after
`pip install -e .` you can shorten to:

```bash
pipeline run precreate --from 2025-01-01
```

## Containerized

```bash
# Build the pipeline image
docker compose --profile runner build pipeline

# Run a single stage in a one-shot container
docker compose --profile runner run --rm pipeline run download
docker compose --profile runner run --rm pipeline run parse
docker compose --profile runner run --rm pipeline run ner-extract

# Run the full ETL DAG
docker compose --profile runner run --rm pipeline run etl
```

The `pipeline` service is behind a `runner` profile so `docker compose up`
alone only starts Neo4j (the long-running dependency). Pipeline runs are
ephemeral one-shots. Inside the container, `NEO4J_URI` is overridden to
`bolt://neo4j:7687` (docker network) regardless of `.env`.

### Volume layout

| Host path | Container path | Purpose |
| --- | --- | --- |
| `./parsed_documents/` | `/app/parsed_documents/` | parsed text + metadata |
| `./ner_results/` | `/app/ner_results/` | NER JSON outputs |
| `./graphify-out/` | `/app/graphify-out/` | JSON-emit snapshots |
| `./.pipeline-state/` | `/app/.pipeline-state/` | checkpoints + run history |
| `./pipeline/` | `/app/pipeline/` | source bind-mount (dev only) |

`./documentos_sead/` (raw SEI downloads) is **not** mounted — add a volume
for it if you run `download` inside the container, otherwise the raw files
vanish with the container.

For production, **drop the source bind-mount** and rely on the image's
copy — otherwise local edits silently take effect inside the container.

### Neo4j tuning

`docker-compose.yml` ships with 4 GB heap / 3 GB page cache, sized for the
`atividades` bulk load (~1.2M nodes + ~5M edges). Lower them if the host
has under 12 GB of RAM; raise (heap 6G / pagecache 4G) if you have the
headroom — never past host memory:

```yaml
NEO4J_server_memory_heap_max__size: "6G"
NEO4J_server_memory_pagecache_size: "4G"
```

Vector indexes need a healthy page cache to perform — under-provisioning
will surface as slow `similarity` runs.
