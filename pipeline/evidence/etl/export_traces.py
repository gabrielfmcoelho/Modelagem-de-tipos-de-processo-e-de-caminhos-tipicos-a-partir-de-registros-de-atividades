#!/usr/bin/env python
from __future__ import annotations

import argparse
import gzip
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from ...core.paths import ROOT as _ROOT

from ...core.config import Settings
from ...core.neo4j_driver import build_driver
from ...readers.neo4j_reader import Neo4jReader
from ...model.typical_eval import cluster_traces, load_labels, protocol_traces
from ..artifact import write_artifact, write_sidecar

DESCRIPTION = (
    "Freeze corpus traces and every matrix cell's cluster grouping as artifacts. "
    "Traces are corpus-wide and identical across cells, so Neo4j is read once. "
    "Downstream trace-level work then runs with no Neo4j and no GPU."
)

CELLS = [
    ("exp-raw", "hdbscan"), ("exp-raw", "kmeans"),
    ("exp-raw", "leiden"), ("exp-raw", "consensus"),
    ("exp-anon", "hdbscan"), ("exp-anon", "kmeans"), ("exp-anon", "leiden"),
    ("exp-anon", "consensus"),
]


def _write(payload: dict, path: Path, *, params: dict | None = None, inputs=()) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wb") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    write_sidecar(path, stage="export-traces", params=params or {}, inputs=inputs)
    return path.stat().st_size


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=DESCRIPTION)
    ap.add_argument("--min-traces", type=int, default=30)
    ap.add_argument("--out-dir", default=str(_ROOT / "artifacts" / "traces"))
    args = ap.parse_args(argv)
    out_dir = Path(args.out_dir)

    driver = build_driver(Settings.from_env())
    try:
        t0 = time.time()
        traces = protocol_traces(Neo4jReader(driver))
    finally:
        driver.close()
    print(f"traces: {len(traces)} processos read in {time.time() - t0:.0f}s", flush=True)

    corpus = {"meta": {"n_processos": len(traces),
                       "generated_at": datetime.now(UTC).isoformat(),
                       "source": "neo4j"},
              "traces": {pf: {"start": str(tw[0]), "states": list(tw[1])}
                         for pf, tw in traces.items()}}
    size = _write(corpus, out_dir / "protocol_traces.json.gz",
                  params={"n_processos": len(traces), "source": "neo4j"})
    print(f"wrote protocol_traces.json.gz ({size / 1e6:.1f} MB)")

    summary = []
    for run_id, algo in CELLS:
        lp = _ROOT / "artifacts" / "clustering" / run_id / algo / "labels.json"
        if not lp.is_file():
            print(f"skip {run_id}/{algo}: no labels at {lp}")
            continue
        labels = load_labels(lp)
        kept = cluster_traces(labels, traces, min_traces=args.min_traces)
        allc = cluster_traces(labels, traces, min_traces=1)
        n_kept = sum(len(v) for v in kept.values())
        n_all = sum(len(v) for v in allc.values())
        row = {"run_id": run_id, "algo": algo,
               "clusters_total": len(allc), "clusters_kept": len(kept),
               "clusters_below_floor": len(allc) - len(kept),
               "processos_labelled": n_all, "processos_kept": n_kept,
               "processos_below_floor": n_all - n_kept,
               "processos_unlabelled": len(traces) - n_all,
               "coverage_of_labelled": round(n_kept / n_all, 4) if n_all else 0.0,
               "coverage_of_corpus": round(n_kept / len(traces), 4) if traces else 0.0,
               "min_traces": args.min_traces}
        summary.append(row)
        _write({"meta": row,
                "clusters": {cid: [t[2] for t in tws] for cid, tws in kept.items()},
                "below_floor": {cid: [t[2] for t in tws]
                                for cid, tws in allc.items() if cid not in kept}},
               out_dir / run_id / algo / "grouping.json.gz",
               params={"run_id": run_id, "algo": algo, "min_traces": args.min_traces},
               inputs=[lp, out_dir / "protocol_traces.json.gz"])
        print(f"{run_id}/{algo}: {len(kept):>3}/{len(allc):>3} clusters, "
              f"{n_kept:>5}/{len(traces)} of corpus ({row['coverage_of_corpus']:.1%}), "
              f"unlabelled {row['processos_unlabelled']:>5}")

    idx = out_dir / "index.json"
    write_artifact({"generated_at": datetime.now(UTC).isoformat(),
                    "min_traces": args.min_traces, "n_processos": len(traces),
                    "cells": summary}, idx, stage="export-traces",
                   params={"min_traces": args.min_traces, "out_dir": str(out_dir)},
                   inputs=[out_dir / "protocol_traces.json.gz",
                           *sorted(out_dir.rglob("grouping.json.gz"))])
    print(f"wrote {idx.relative_to(_ROOT)}")

    with gzip.open(out_dir / "protocol_traces.json.gz", "rb") as fh:
        back = json.loads(fh.read())
    assert len(back["traces"]) == len(traces), "round-trip lost traces"
    a = next(iter(traces))
    assert back["traces"][a]["states"] == list(traces[a][1]), "round-trip corrupted states"
    print("round-trip check ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
