#!/usr/bin/env python

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _common import OUT, md_table
from pipeline.model.typical_eval import MODEL_NAMES

_ROOT = Path(__file__).resolve().parent.parent

COMBOS = [
    ("raw", "hdbscan", "exp-raw", "hdbscan"),
    ("raw", "kmeans", "exp-raw", "kmeans-k=hdbscan"),
    ("raw", "leiden", "exp-raw", "leiden-res=1.0"),
    ("raw", "consensus", "exp-raw", "consensus"),
    ("raw", "kmeans", "exp-raw-kelbow", "kmeans-k=elbow"),
    ("raw", "kmeans", "exp-raw-ksil", "kmeans-k=silhouette"),
    ("raw", "leiden", "exp-raw-lres", "leiden-res=swept"),
    ("raw", "hdbscan", "exp-raw-hcoarse", "hdbscan-coarse"),
    ("anon", "hdbscan", "exp-anon", "hdbscan"),
    ("anon", "kmeans", "exp-anon", "kmeans-k=hdbscan"),
    ("anon", "leiden", "exp-anon", "leiden-res=1.0"),
    ("anon", "consensus", "exp-anon", "consensus"),
    ("anon", "kmeans", "exp-anon-kelbow", "kmeans-k=elbow"),
    ("anon", "kmeans", "exp-anon-ksil", "kmeans-k=silhouette"),
    ("anon", "leiden", "exp-anon-lres", "leiden-res=swept"),
    ("anon", "hdbscan", "exp-anon-hcoarse", "hdbscan-coarse"),
]
MODELS = list(MODEL_NAMES)
METRICS = [("top1", "top-1 ↑"), ("top3", "top-3 ↑"), ("suffix_dl", "suffix DL ↓"),
           ("suffix_dl_c", "suffix DL constrained ↓"), ("suffix_length_ratio", "suffix length ratio →1"),
           ("typical_path_distance", "typical-path dist ↓"),
           ("typical_path_distance_proc", "typical-path dist (proc) ↓"), ("flow_validity_step", "flow validity (per step) ↑"),
           ("flow_validity_trace", "flow validity (per trace) ↑")]
AGGS = [("weighted", "size-weighted"), ("macro", "macro-averaged")]


def load_matrix(artifacts_root) -> dict:
    rows = []
    for arm, algo, run_id, label in COMBOS:
        path = Path(artifacts_root) / "typical" / run_id / algo / "unit" / "metrics.json"
        row = {"arm": arm, "algo": algo, "run_id": run_id, "label": label,
               "path": str(path), "found": path.exists()}
        if row["found"]:
            data = json.loads(path.read_text(encoding="utf-8"))
            row["meta"] = data.get("meta", {})
            row["aggregate"] = data.get("aggregate", {})
        rows.append(row)
    return {"rows": rows}


def _fmt(value) -> str:
    return f"{value:.3f}" if isinstance(value, int | float) else "—"


def _combo_label(row: dict) -> str:
    return f"{row['arm']} · {row.get('label', row['algo'])}"


def _metric_table(rows: list[dict], agg: str, metric: str) -> list[list[str]]:
    out = []
    for row in rows:
        cells = [_combo_label(row)]
        if not row["found"]:
            cells += ["pending"] * len(MODELS)
        else:
            models = row["aggregate"].get("models", {})
            for m in MODELS:
                cells.append(_fmt(models.get(m, {}).get(agg, {}).get(metric)))
        out.append(cells)
    return out


def _fitness_table(rows: list[dict]) -> list[list[str]]:
    out = []
    for row in rows:
        if not row["found"]:
            out.append([_combo_label(row), "pending", "pending", "—", "—"])
            continue
        agg = row["aggregate"]
        fit = agg.get("edge_coverage", {})
        out.append([_combo_label(row), _fmt(fit.get("weighted")), _fmt(fit.get("macro")),
                    str(agg.get("n_clusters", "—")), str(agg.get("n_traces", "—"))])
    return out


def render_md(payload: dict) -> str:
    rows = payload["rows"]
    parts = [
        "# Matriz de comparação — método de clustering × modelo de processo típico\n",
        "Cada linha é um braço do experimento (raw = texto original, anon = texto anonimizado) × um "
        "algoritmo de clustering; cada coluna é um modelo de próxima atividade treinado por cluster "
        "(mín. 30 traces, split temporal 80/20). Valores agregados sobre os clusters avaliados; "
        "fonte: `artifacts/typical/<run_id>/<algo>/unit/metrics.json`.\n",
    ]
    headers = ["arm · algo"] + MODELS
    for agg_key, agg_label in AGGS:
        parts.append(f"\n## Agregação {agg_label}\n")
        for metric_key, metric_label in METRICS:
            parts.append(f"\n### {metric_label}\n")
            parts.append(md_table(headers, _metric_table(rows, agg_key, metric_key)) + "\n")
    parts.append("\n## edge_coverage — cobertura do holdout pelas arestas DFG do cluster\n")
    parts.append(md_table(["arm · algo", "size-weighted", "macro", "clusters", "traces"], _fitness_table(rows)) + "\n")
    missing = [r for r in rows if not r["found"]]
    if missing:
        parts.append("\n_Pendentes (artefato ainda não gerado): "
                     + ", ".join(_combo_label(r) for r in missing) + "._\n")
    skipped = {f"{_combo_label(r)}: {name} ({reason})"
               for r in rows if r["found"]
               for name, reason in (r.get("meta", {}).get("skipped_models") or {}).items()}
    if skipped:
        parts.append("\n_Modelos pulados: " + "; ".join(sorted(skipped)) + "._\n")
    return "\n".join(parts) + "\n"


def main() -> None:
    payload = load_matrix(_ROOT / "artifacts")
    OUT.mkdir(parents=True, exist_ok=True)
    md_dest = OUT / "13-matrix.md"
    md_dest.write_text(render_md(payload), encoding="utf-8")
    print("wrote", md_dest)


if __name__ == "__main__":
    main()
