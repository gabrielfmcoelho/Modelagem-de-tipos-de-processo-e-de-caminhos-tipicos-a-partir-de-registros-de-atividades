#!/usr/bin/env python

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ...core.paths import ROOT

from ...model.predict import MarkovModel, random_split_field
from ...model.typical_eval import cluster_traces, itinerary_alphabet, load_labels, load_protocol_traces, next_step_accuracy
from ..artifact import write_artifact

CUTS = (("exp-anon", "full history"), ("exp-anon-cut0.75", "first 75%"),
        ("exp-anon-cut0.5", "first 50%"), ("exp-anon-cut0.25", "first 25%"))
TRACES = ROOT / "artifacts" / "traces" / "protocol_traces.json.gz"
OUT = ROOT / "artifacts" / "stats" / "temporal_holdout_matched.json"


def build(run_id: str, algo: str, min_traces: int, train_frac: float, seed: int):
    traces = load_protocol_traces(TRACES)
    traces = {p: (tw[0], itinerary_alphabet(tw[1])) for p, tw in traces.items()}
    traces = {p: tw for p, tw in traces.items() if len(tw[1]) >= 2}
    labels = load_labels(ROOT / f"artifacts/clustering/{run_id}/{algo}/labels.json")
    groups = cluster_traces(labels, traces, min_traces=min_traces)
    per_cluster, test_ids, train_all = {}, set(), []
    for cid, tws in groups.items():
        tr_s, te_s = random_split_field(tws, 1, train_frac=train_frac, seed=seed)
        _, te_p = random_split_field(tws, 2, train_frac=train_frac, seed=seed)
        if len(tr_s) < 10 or not te_s:
            continue
        per_cluster[cid] = (tr_s, list(zip(te_p, te_s)))
        train_all.extend(tr_s)
        test_ids |= set(te_p)
    return per_cluster, test_ids, train_all


def hits(model, seqs) -> tuple[int, int]:
    per: list = []
    next_step_accuracy(model, seqs, topk=(1,), per_trace=per)
    return sum(r[0] for r in per), sum(r[-1] for r in per)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Rescore every timeline truncation on the cases all of them evaluate.")
    ap.add_argument("--algo", default="hdbscan")
    ap.add_argument("--min-traces", type=int, default=30)
    ap.add_argument("--train-frac", type=float, default=0.7)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)

    built = {}
    for run_id, label in CUTS:
        built[run_id] = build(run_id, args.algo, args.min_traces, args.train_frac, args.seed)
        print(f"{label:14s} evaluated test cases: {len(built[run_id][1])}", flush=True)

    common = set.intersection(*(built[r][1] for r, _ in CUTS))
    print(f"cases evaluated under all {len(CUTS)} truncations: {len(common)}", flush=True)

    rows = []
    for run_id, label in CUTS:
        per_cluster, _, train_all = built[run_id]
        gm = MarkovModel(order=3)
        gm.fit(train_all)
        ph = pt = gh = gt = 0
        for _, (tr, te) in per_cluster.items():
            te_c = [seq for pf, seq in te if pf in common]
            if not te_c:
                continue
            m = MarkovModel(order=3)
            m.fit(tr)
            a, b = hits(m, te_c)
            ph += a
            pt += b
            a, b = hits(gm, te_c)
            gh += a
            gt += b
        p, g = ph / pt, gh / gt
        rows.append({"features": label, "per_cluster_top1": round(p, 4),
                     "global_model": round(g, 4), "gain_vs_global": round(p - g, 4),
                     "n_steps": pt})
        print(f"  {label:14s} per-cluster={p:.4f} global={g:.4f} gain={p - g:+.4f}", flush=True)

    base, last = rows[0]["gain_vs_global"], rows[-1]["gain_vs_global"]
    payload = {"algo": args.algo, "arm": "exp-anon", "model": "markov3",
               "min_traces": args.min_traces, "train_frac": args.train_frac, "seed": args.seed,
               "n_common_cases": len(common), "rows": rows,
               "retained_frac_at_25pct": round(last / base, 4) if base else None}
    out = write_artifact(payload, args.out, stage="temporal-holdout",
                         params={"algo": args.algo, "min_traces": args.min_traces,
                                 "train_frac": args.train_frac, "seed": args.seed},
                         inputs=[TRACES])
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
