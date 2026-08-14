#!/usr/bin/env python
from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

DESCRIPTION = (
    "Alignment/token-replay conformance per cluster via pm4py, computed from frozen "
    "trace artifacts only. Kept out of pipeline/ because pm4py is AGPL v3 and must not "
    "reach the deployable product."
)

_EPOCH = datetime(2025, 1, 1, tzinfo=UTC)


def _procedure(seq):
    out = []
    for s in seq:
        t = s.partition("@")[0]
        if not out or out[-1] != t:
            out.append(t)
    return out


def _frame(traces, alphabet):
    import pandas as pd
    rows = []
    for cid, seq in enumerate(traces):
        states = _procedure(seq) if alphabet == "procedure" else seq
        for i, s in enumerate(states):
            rows.append({"case:concept:name": str(cid), "concept:name": s,
                         "time:timestamp": _EPOCH + timedelta(minutes=i)})
    return pd.DataFrame(rows)


def _conformance(traces, alphabet, noise):
    import pm4py
    df = _frame(traces, alphabet)
    if df.empty:
        return None
    log = pm4py.format_dataframe(df, case_id="case:concept:name",
                                 activity_key="concept:name",
                                 timestamp_key="time:timestamp")
    net, im, fm = pm4py.discover_petri_net_inductive(log, noise_threshold=noise)
    fit = pm4py.fitness_token_based_replay(log, net, im, fm)
    prec = pm4py.precision_token_based_replay(log, net, im, fm)
    return {
        "fitness_token_replay": round(float(fit.get("log_fitness", 0.0)), 4),
        "perc_fit_traces": round(float(fit.get("percentage_of_fitting_traces", 0.0)), 4),
        "precision_token_replay": round(float(prec), 4),
        "n_places": len(net.places),
        "n_transitions": len(net.transitions),
        "noise_threshold": noise,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=DESCRIPTION)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--algo", required=True)
    ap.add_argument("--alphabet", choices=("unit", "procedure"), default="procedure")
    ap.add_argument("--noise-threshold", type=float, default=0.2)
    ap.add_argument("--max-clusters", type=int, default=0)
    ap.add_argument("--max-traces", type=int, default=200)
    ap.add_argument("--cap-length", type=int, default=200)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    tp = _ROOT / "artifacts" / "traces" / "protocol_traces.json.gz"
    gp = _ROOT / "artifacts" / "traces" / args.run_id / args.algo / "grouping.json.gz"
    for p in (tp, gp):
        if not p.is_file():
            raise SystemExit(f"missing artifact: {p} (run python -m pipeline run export-traces first)")

    traces = json.loads(gzip.open(tp, "rb").read())["traces"]
    groups = json.loads(gzip.open(gp, "rb").read())["clusters"]
    ordered = sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    if args.max_clusters:
        ordered = ordered[: args.max_clusters]

    out: dict = {"meta": {"run_id": args.run_id, "algo": args.algo,
                          "alphabet": args.alphabet,
                          "noise_threshold": args.noise_threshold,
                          "max_traces": args.max_traces, "cap_length": args.cap_length,
                          "generated_at": datetime.now(UTC).isoformat()},
                 "clusters": {}}
    t0 = time.time()
    for i, (cid, pfs) in enumerate(ordered, 1):
        seqs = [traces[p]["states"][: args.cap_length] for p in pfs if p in traces]
        seqs = [s for s in seqs if len(s) >= 2][: args.max_traces]
        if len(seqs) < 5:
            continue
        try:
            res = _conformance(seqs, args.alphabet, args.noise_threshold)
        except Exception as e:
            res = {"error": f"{type(e).__name__}: {e}"}
        out["clusters"][cid] = res
        print(f"[{i}/{len(ordered)}] {cid}: {res}", flush=True)

    vals = [c for c in out["clusters"].values() if c and "error" not in c]
    if vals:
        out["aggregate"] = {
            "n_clusters": len(vals),
            "fitness_token_replay": round(sum(v["fitness_token_replay"] for v in vals) / len(vals), 4),
            "precision_token_replay": round(sum(v["precision_token_replay"] for v in vals) / len(vals), 4),
        }
    out["meta"]["duration_seconds"] = round(time.time() - t0, 1)

    dest = Path(args.out) if args.out else (
        _ROOT / "artifacts" / "conformance" / args.run_id / args.algo / f"pm4py-{args.alphabet}.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {dest.relative_to(_ROOT)}  aggregate={out.get('aggregate')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
