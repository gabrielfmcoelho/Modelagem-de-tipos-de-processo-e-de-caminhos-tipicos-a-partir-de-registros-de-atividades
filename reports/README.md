# reports/

Reproducible report generators for the SEAD-PI / 2025 SEI process-mining study —
Markdown documents + matplotlib/networkx charts, for the **TCC article and presentation**.

## Dependencies

```bash
uv pip install --python .venv/bin/python -r requirements.txt
conda install -n tcc -c conda-forge graphviz python-graphviz   # the `dot` binary + bindings (flow charts)
```

## Run

```bash
# light reports (②, ⑬, ⑭, ① unless skipped) + index; writes reports/out/
.venv/bin/python reports/gen_all.py

# options
.venv/bin/python reports/gen_all.py --skip-datalake   # no Trino/VPN
.venv/bin/python reports/gen_all.py --heavy           # also run the GPU timeline reports (⑧–⑪)

# individually
.venv/bin/python reports/gen_01_datalake.py     # ① needs Trino (VPN)
.venv/bin/python reports/gen_02_dataset.py      # ② Neo4j graph
.venv/bin/python reports/gen_13_matrix.py       # ⑬ artifacts only (no Neo4j)
.venv/bin/python reports/gen_14_explorer.py     # ⑭ single interactive dashboard (Neo4j + clustering artifacts)
```

Start at [`out/00-index.md`](out/00-index.md).

## What each report contains

| script | output | source | content |
|---|---|---|---|
| `gen_01_datalake.py` | `out/01-datalake-schema.md` | Trino + graph | `sei_atividades` schema, peculiarities, raw→graph mapping, extracted slice |
| `gen_02_dataset.py` | `out/02-dataset-overview.md` | Neo4j | corpus profile, per-stage data lineage, state/lifetime, doc coverage, flow health, insights/flaws |
| `gen_08_comparison.py` | `out/08-comparison.md` | Neo4j + GPU | Real × GRU-chrono × Transformer × GRU-flow × Markov timelines per cohort (constrained decoding) |
| `gen_09_richtokens.py` | `out/09-phase2-richtokens.md` | Neo4j + GPU | rich-token (Fase 2) + aux-loss/RL (Fase 3) ablations |
| `gen_10_tuning.py` | `out/10-tuning.md` | Neo4j + GPU | train/val/test hyperparameter sweep (top-1 + generation validity) |
| `gen_11_stitching.py` | `out/11-stitching.md` | Neo4j + GPU | branch-stitching (`generate_full`): structural validity vs length |
| `gen_13_matrix.py` | `out/13-matrix.md` | `artifacts/typical/` | clustering-method × typical-process-model matrix (raw/anon × hdbscan/kmeans/leiden + consensus), from `pipeline/run_typical_eval.py` artifacts |
| `gen_14_explorer.py` | `out/explorer.html` | Neo4j + clustering artifacts | single interactive dashboard — clusters of every algorithm (named), timelines by model, clustering quality, glossaries and algorithms page |
| `gen_all.py` | `out/00-index.md` + all | — | runs the light reports + index (`--heavy` adds ⑧–⑪) |

## Notes
- Configuration (Neo4j/Trino/credentials) comes from the pipeline `.env` (same as the pipeline).
- `_common.py` holds the connection, Markdown and chart helpers (`barh`, `bars`, `hist`, `pie`, `dfg_chart`).
- Charts are PNGs under `out/charts/`, embedded with relative paths so the `.md` renders standalone.
- The numbers reflect the **current graph snapshot**; rerun after any pipeline re-run.
- See [`docs/research/models-and-reports.md`](../docs/research/models-and-reports.md) for the models behind ⑧–⑪/⑬ and deeper how-to-run notes.
