from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

from ...core.paths import ROOT as _ROOT
from ...model.typical_eval import ALPHABET_NAMES


def _cell(run: str, algo: str, alphabet: str) -> dict:
    p = _ROOT / "artifacts" / "typical" / run / algo / alphabet / "metrics.json"
    if not p.is_file():
        raise FileNotFoundError(f"missing artifact: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def per_process(cell: dict, model: str, k: int = 1) -> dict[str, tuple[int, int]]:
    col = 0 if k == 1 else 1
    out: dict[str, tuple[int, int]] = {}
    for cid, rec in cell["clusters"].items():
        protos = rec.get("test_protocolos")
        m = rec["models"].get(model, {})
        rows = m.get("per_trace")
        if not protos or not rows:
            continue
        if len(protos) != len(rows):
            raise SystemExit(f"cluster {cid}: {len(protos)} protocolos vs {len(rows)} per-trace rows")
        for pf, r in zip(protos, rows):
            if r[2]:
                out[pf] = (r[col], r[2])
    return out


def _micro(pairs) -> float:
    hits = sum(h for h, _ in pairs)
    total = sum(t for _, t in pairs)
    return hits / total if total else 0.0


def paired_bootstrap(a: dict, b: dict, *, n: int = 2000, seed: int = 42):
    shared = sorted(set(a) & set(b))
    if not shared:
        raise SystemExit("no shared protocolos between the two arms")
    rng = random.Random(seed)
    point_a, point_b = _micro([a[p] for p in shared]), _micro([b[p] for p in shared])
    diffs, arm_a, arm_b = [], [], []
    idx = range(len(shared))
    for _ in range(n):
        draw = [shared[rng.choice(idx)] for _ in idx]
        va, vb = _micro([a[p] for p in draw]), _micro([b[p] for p in draw])
        arm_a.append(va)
        arm_b.append(vb)
        diffs.append(vb - va)
    diffs.sort()
    arm_a.sort()
    arm_b.sort()

    def q(xs, p):
        return xs[min(len(xs) - 1, max(0, int(round(p * (len(xs) - 1)))))]

    return {
        "n_shared_processes": len(shared),
        "arm_a": {"point": round(point_a, 4), "ci95": [round(q(arm_a, 0.025), 4), round(q(arm_a, 0.975), 4)]},
        "arm_b": {"point": round(point_b, 4), "ci95": [round(q(arm_b, 0.025), 4), round(q(arm_b, 0.975), 4)]},
        "difference_b_minus_a": {
            "point": round(point_b - point_a, 4),
            "ci95": [round(q(diffs, 0.025), 4), round(q(diffs, 0.975), 4)],
            "ci90_one_sided_lower": round(q(diffs, 0.05), 4),
        },
        "replicates": n,
        "seed": seed,
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Paired process-level bootstrap of next-activity accuracy between two matrix cells.")
    ap.add_argument("--arm-a", required=True, help="baseline cell as run/algo, e.g. exp-raw/hdbscan")
    ap.add_argument("--arm-b", required=True, help="comparison cell as run/algo, e.g. exp-anon/hdbscan")
    ap.add_argument("--model", default="gru", help="model family (default gru)")
    ap.add_argument("--alphabet", default="unit", choices=ALPHABET_NAMES,
                    help="the alphabet whose cells are compared; both arms must use the same "
                         "one, because a pair scored across alphabets is not a pair")
    ap.add_argument("--topk", type=int, default=1, choices=(1, 3), help="top-1 or top-3 (default 1)")
    ap.add_argument("--margin", type=float, default=None,
                    help="non-inferiority margin delta; omit to report the interval only")
    ap.add_argument("--replicates", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=None, help="write the result JSON here")
    args = ap.parse_args()

    ra, aa = args.arm_a.split("/", 1)
    rb, ab = args.arm_b.split("/", 1)
    a = per_process(_cell(ra, aa, args.alphabet), args.model, args.topk)
    b = per_process(_cell(rb, ab, args.alphabet), args.model, args.topk)
    res = paired_bootstrap(a, b, n=args.replicates, seed=args.seed)
    res["arm_a_cell"] = args.arm_a
    res["arm_b_cell"] = args.arm_b
    res["model"] = args.model
    res["metric"] = f"top{args.topk}"

    d = res["difference_b_minus_a"]
    if args.margin is not None:
        res["margin"] = args.margin
        res["non_inferior"] = bool(d["ci90_one_sided_lower"] > -abs(args.margin))

    print(json.dumps(res, indent=2))
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
