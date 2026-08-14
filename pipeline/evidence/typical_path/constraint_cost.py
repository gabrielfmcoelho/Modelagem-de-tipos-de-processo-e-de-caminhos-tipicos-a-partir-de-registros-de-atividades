#!/usr/bin/env python

from __future__ import annotations

import argparse
from pathlib import Path

from ...core.paths import ROOT

from ..artifact import write_artifact
from ...model.constrained import FlowState
from ...model.predict import END, MarkovModel, random_split
from ...model.typical_eval import cluster_traces, itinerary_alphabet, load_labels, load_protocol_traces, procedure_alphabet

OUT = ROOT / "artifacts" / "stats" / "constraint_cost.json"
TRACES = ROOT / "artifacts" / "traces" / "protocol_traces.json.gz"
ALPHABETS = {"itinerary": itinerary_alphabet, "procedure": procedure_alphabet}


def measure(labels: dict, traces: dict, *, order: int = 3, top_k: int = 8,
            min_traces: int = 30, train_frac: float = 0.7, split_seed: int = 42) -> dict:
    steps = alters = argmax_changed = argmax_illegal = no_legal = 0
    groups = cluster_traces(labels, traces, min_traces=min_traces)
    scored = 0
    for _cid, tws in sorted(groups.items(), key=lambda kv: str(kv[0])):
        train, test = random_split(tws, train_frac=train_frac, seed=split_seed)
        if not train or not test:
            continue
        scored += 1
        model = MarkovModel(order).fit([t + [END] for t in train])
        for tr in (t + [END] for t in test):
            fs = FlowState()
            for i in range(1, len(tr)):
                fs.step(tr[i - 1])
                ranked = model.predict_next(tr[:i])
                legal = [s for s in ranked if fs.allows(s)]
                steps += 1
                if set(ranked[:top_k]) != set(legal[:top_k]):
                    alters += 1
                if ranked and legal and ranked[0] != legal[0]:
                    argmax_changed += 1
                if ranked and not fs.allows(ranked[0]):
                    argmax_illegal += 1
                if ranked and not legal:
                    no_legal += 1

    def frac(n: int) -> float:
        return round(n / steps, 6) if steps else 0.0

    return {"n_clusters": scored, "n_decision_steps": steps,
            "constraint_alters_topk_frac": frac(alters),
            "constraint_changes_argmax_frac": frac(argmax_changed),
            "unconstrained_argmax_illegal_frac": frac(argmax_illegal),
            "no_legal_candidate_frac": frac(no_legal)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Measure what the flow automaton costs a Markov generator: at every "
                    "held-out decision point, the top-k candidates with and without the filter.")
    ap.add_argument("--run-id", default="exp-raw")
    ap.add_argument("--algo", default="kmeans")
    ap.add_argument("--alphabet", choices=("unit", "procedure", "itinerary"), default="unit")
    ap.add_argument("--order", type=int, default=3)
    ap.add_argument("--top-k", type=int, default=8)
    ap.add_argument("--min-traces", type=int, default=30)
    ap.add_argument("--train-frac", type=float, default=0.7)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--traces-file", default=str(TRACES))
    ap.add_argument("--labels-file", default=None)
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)

    labels_path = Path(args.labels_file) if args.labels_file else (
        ROOT / "artifacts" / "clustering" / args.run_id / args.algo / "labels.json")
    if not labels_path.is_file():
        raise SystemExit(f"labels artifact not found: {labels_path}")
    traces_path = Path(args.traces_file)
    if not traces_path.is_file():
        raise SystemExit(f"traces artifact not found: {traces_path} "
                         "-- run `pipeline run export-traces` first")

    labels = load_labels(labels_path)
    traces = load_protocol_traces(traces_path)
    convert = ALPHABETS.get(args.alphabet)
    if convert is not None:
        traces = {pf: (tw[0], convert(tw[1])) for pf, tw in traces.items()}

    result = measure(labels, traces, order=args.order, top_k=args.top_k,
                     min_traces=args.min_traces, train_frac=args.train_frac,
                     split_seed=args.seed)
    payload = {"cell": f"{args.run_id}/{args.algo}", "alphabet": args.alphabet,
               "model": f"markov{args.order}", "top_k": args.top_k, **result}

    out = write_artifact(
        payload, args.out, stage="constraint-cost",
        params={"order": args.order, "top_k": args.top_k, "min_traces": args.min_traces,
                "train_frac": args.train_frac, "seed": args.seed, "alphabet": args.alphabet,
                "run_id": args.run_id, "algo": args.algo},
        inputs=[labels_path, traces_path])
    print(f"wrote {out}  ({payload['n_decision_steps']} decision steps over "
          f"{payload['n_clusters']} clusters, alters "
          f"{payload['constraint_alters_topk_frac']:.4%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
