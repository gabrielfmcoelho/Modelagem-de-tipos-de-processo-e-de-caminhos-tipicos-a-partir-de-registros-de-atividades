# scripts/debug

Standalone diagnostic tools for the pipeline. Each is a plain `python` script
(run from the repo root) — they are *not* pipeline stages and have no entry in
the `runs.jsonl` ledger.

| Script | What it inspects | Needs |
| --- | --- | --- |
| `debug_processo.py` | A single processo's graph state in **Neo4j** (unidades it passed through, permanência, current open unidade, documents, document creator). | A reachable Neo4j (`NEO4J_*` env or `--neo4j-uri`). |
| `analyse_downloads.py` | The on-disk `documentos_sead/` tree — file counts by extension, parseable vs unsupported, and `parsed_documents/` / `ner_results/` progress. | Local artifact dirs only (stdlib). |
| `analyse_download_logs.py` | A `download` stage log file — success/failure/cancelled stats, per-unidade resolution, retry hotspots, throughput. | A log file path (stdlib). |

```bash
# From the repo root
python scripts/debug/debug_processo.py "00002.000175/2025-63"
python scripts/debug/debug_processo.py "00002.000175/2025-63" --documento 1234567

python scripts/debug/analyse_downloads.py --input ./documentos_sead \
    --parsed ./parsed_documents --ner-output ./ner_results

python scripts/debug/analyse_download_logs.py /path/to/download.log --top 20
```