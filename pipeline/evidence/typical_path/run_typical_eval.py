#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from ...core.paths import ROOT as _ROOT

from ...evidence.artifact import write_artifact

from ...core.config import Settings
from ...core.neo4j_driver import build_driver
from pipeline.readers.neo4j_reader import Neo4jReader
from ...model.typical_eval import DFG_COVERAGE_FLOOR, MODEL_NAMES, cluster_traces, default_specs, evaluate_cluster, evaluate_matrix, evaluate_matrix_by_band, size_band, load_labels, itinerary_alphabet, load_protocol_traces, load_protocolo_set, procedure_alphabet, protocol_traces


def _rel(path: Path) -> str:
    return str(path.relative_to(_ROOT)) if path.is_relative_to(_ROOT) else str(path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Evaluate typical-process models per cluster for one run_id×algo combo.")
    ap.add_argument("--run-id", required=True, help="clustering run id, e.g. exp-raw, exp-anon, exp-raw-ksil")
    ap.add_argument("--algo", required=True, help="clustering algorithm (hdbscan, kmeans, leiden)")
    ap.add_argument("--labels-file", default=None,
                    help="labels artifact (default artifacts/clustering/<run_id>/<algo>/labels.json)")
    ap.add_argument("--models", default=None, help=f"comma list from {','.join(MODEL_NAMES)} (default all)")
    ap.add_argument("--min-traces", type=int, default=30, help="minimum traces per cluster")
    ap.add_argument("--epochs", type=int, default=30, help="neural training epochs")
    ap.add_argument("--gnn-epochs", type=int, default=200,
                    help="GCN training epochs (CPU, tiny graph)")
    ap.add_argument("--dfg-floor", type=float, default=DFG_COVERAGE_FLOOR,
                    help="minimum share of traces an edge must appear in to survive")
    ap.add_argument("--max-clusters", type=int, default=0, help="cap on clusters (largest first, 0 = all)")
    ap.add_argument("--allow-cpu", action="store_true", help="train neural models without CUDA")
    ap.add_argument("--emit-traces", action="store_true",
                    help="persist a representative medoid trace per model + real/comum per cluster")
    ap.add_argument("--force", action="store_true", help="recompute even if the metrics artifact exists")
    ap.add_argument("--alphabet", choices=("unit", "procedure", "itinerary"), default="unit",
                    help="trace state alphabet: tipo_acao@unidade, or tipo_acao with repeats collapsed")
    ap.add_argument("--traces-file", default=None,
                    help="read traces from a protocol_traces json(.gz) artifact instead of Neo4j")
    ap.add_argument("--restrict-to", default=None,
                    help="json list of protocolos (or a labels artifact) bounding the evaluated population")
    ap.add_argument("--stage", default="matrix",
                    help="registered stage to record as the producer of this cell")
    ap.add_argument("--out", default=None, help="override the metrics artifact path")
    args = ap.parse_args(argv)

    out_path = (Path(args.out) if args.out
                else _ROOT / "artifacts" / "typical" / args.run_id / args.algo / args.alphabet
                / "metrics.json")
    if out_path.exists() and not args.force:
        print(f"skip: {_rel(out_path)} exists (use --force to recompute)")
        return 0

    labels_path = (Path(args.labels_file) if args.labels_file
                   else _ROOT / "artifacts" / "clustering" / args.run_id / args.algo / "labels.json")
    if not labels_path.exists():
        print(f"error: labels artifact not found: {labels_path}", file=sys.stderr)
        return 1

    models = [m.strip() for m in args.models.split(",") if m.strip()] if args.models else None
    specs, skipped = default_specs(models, epochs=args.epochs, allow_cpu=args.allow_cpu,
                                   dfg_coverage_floor=args.dfg_floor,
                                   gnn_epochs=args.gnn_epochs)
    for name, reason in skipped.items():
        print(f"model {name} skipped: {reason}", flush=True)

    labels = load_labels(labels_path)
    t0 = time.time()
    if args.traces_file:
        traces = load_protocol_traces(Path(args.traces_file))
        src = _rel(Path(args.traces_file))
    else:
        driver = build_driver(Settings.from_env())
        try:
            traces = protocol_traces(Neo4jReader(driver))
        finally:
            driver.close()
        src = "neo4j"
    print(f"traces: {len(traces)} processos read from {src} in {time.time() - t0:.0f}s", flush=True)

    if args.restrict_to:
        keep = load_protocolo_set(Path(args.restrict_to))
        before = len(traces)
        traces = {pf: tw for pf, tw in traces.items() if pf in keep}
        print(f"restrict-to {_rel(Path(args.restrict_to))}: {before} -> {len(traces)} processos",
              flush=True)
        if not traces:
            print("error: --restrict-to left no traces", file=sys.stderr)
            return 1

    n_before_min_states = len(traces)
    if args.alphabet != "unit":
        fn = procedure_alphabet if args.alphabet == "procedure" else itinerary_alphabet
        traces = {pf: (tw[0], fn(tw[1])) for pf, tw in traces.items()}
        traces = {pf: tw for pf, tw in traces.items() if len(tw[1]) >= 2}
        print(f"alphabet={args.alphabet}: {len(traces)} processos with >=2 states "
              f"({n_before_min_states - len(traces)} dropped), "
              f"vocab={len({s for tw in traces.values() for s in tw[1]})}", flush=True)

    groups = cluster_traces(labels, traces, min_traces=args.min_traces)
    ordered = sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    if args.max_clusters:
        ordered = ordered[: args.max_clusters]
    print(f"clusters: {len(ordered)} with >= {args.min_traces} traces "
          f"(models: {', '.join(s.name for s in specs)})", flush=True)

    all_tws = [tw for tws in groups.values() for tw in tws]
    results: dict[str, dict] = {}
    for i, (cid, tws) in enumerate(ordered, 1):
        t0 = time.time()
        res = evaluate_cluster(tws, specs, emit_traces=args.emit_traces,
                               all_traces=all_tws, alphabet=args.alphabet)
        if res is None:
            continue
        res["size_band"] = size_band(res["n_traces"])
        results[cid] = res
        print(f"[{i}/{len(ordered)}] {cid}: n={res['n_traces']} edge_coverage={res['edge_coverage']} "
              f"({time.time() - t0:.0f}s)", flush=True)

    payload = {
        "meta": {
            "run_id": args.run_id,
            "algo": args.algo,
            "alphabet": args.alphabet,
            "restrict_to": args.restrict_to,
            "traces_file": args.traces_file,
            "labels_file": _rel(labels_path),
            "min_traces": args.min_traces,
            "epochs": args.epochs,
            "gnn_epochs": args.gnn_epochs,
            "dfg_coverage_floor": args.dfg_floor,
            "train_frac": 0.7,
            "split": "random",
            "models": [s.name for s in specs],
            "skipped_models": skipped,
            "n_processos_with_traces": len(traces),
            "n_processos_before_min_states": n_before_min_states,
            "n_dropped_by_min_states": n_before_min_states - len(traces),
            "generated_at": datetime.now(UTC).isoformat(),
        },
        "aggregate": evaluate_matrix(results),
        "aggregate_by_size": evaluate_matrix_by_band(results),
        "clusters": results,
    }
    cell_inputs = [labels_path]
    if args.traces_file:
        cell_inputs.append(Path(args.traces_file))
    write_artifact(payload, out_path, force=True, stage=args.stage,
                   params={"run_id": args.run_id, "algo": args.algo,
                           "alphabet": args.alphabet, "min_traces": args.min_traces,
                           "epochs": args.epochs, "gnn_epochs": args.gnn_epochs,
                           "dfg_coverage_floor": args.dfg_floor, "models": args.models,
                           "restrict_to": args.restrict_to},
                   inputs=cell_inputs)
    print(f"wrote {_rel(out_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
