from __future__ import annotations
import argparse
import json
from pathlib import Path
from statistics import mean, median
from ...core.paths import ROOT
from ...model.aggregate import weighted_mean


def _round(x, n=4):
    return round(x, n) if isinstance(x, (int, float)) else None


_wmean = weighted_mean


def _spearman(xs, ys):
    pairs = [(x, y) for x, y in zip(xs, ys)
             if isinstance(x, (int, float)) and isinstance(y, (int, float))]
    if len(pairs) < 4:
        return None
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            mid = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = mid
            i = j + 1
        return r
    a, b = rank([p[0] for p in pairs]), rank([p[1] for p in pairs])
    ma, mb = mean(a), mean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    den = (sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) ** 0.5
    return _round(num / den) if den else None


def _spearman_permutation_p(xs, ys, *, n_perm: int = 20000, seed: int = 42):
    import random as _random
    pairs = [(x, y) for x, y in zip(xs, ys)
             if isinstance(x, (int, float)) and isinstance(y, (int, float))]
    if len(pairs) < 4:
        return None, None
    a = [p[0] for p in pairs]
    b = [p[1] for p in pairs]
    obs = _spearman(a, b)
    if obs is None:
        return None, None
    rng = _random.Random(seed)
    shuffled = list(b)
    hits = 0
    for _ in range(n_perm):
        rng.shuffle(shuffled)
        r = _spearman(a, shuffled)
        if r is not None and abs(r) >= abs(obs):
            hits += 1
    return _round(obs), _round((hits + 1) / (n_perm + 1))


def _spearman_power(n, *, alpha=0.05, null_draws=20000, power_draws=2000, seed=1):
    import math
    import random as _random
    rng = _random.Random(seed)
    base = list(range(n))
    null = []
    for _ in range(null_draws):
        b = base[:]
        rng.shuffle(b)
        null.append(abs(_spearman(base, b)))
    null.sort()
    crit = null[int((1 - alpha) * len(null))]

    def power(true_rho):
        r2 = _random.Random(seed + 7)
        hits = 0
        for _ in range(power_draws):
            xs = [r2.gauss(0, 1) for _ in range(n)]
            ys = [true_rho * x + math.sqrt(max(0.0, 1 - true_rho ** 2)) * r2.gauss(0, 1)
                  for x in xs]
            if abs(_spearman(xs, ys)) >= crit:
                hits += 1
        return hits / power_draws

    grid = [0.30, 0.40, 0.50, 0.60, 0.65, 0.70, 0.75, 0.80]
    curve = {r: _round(power(r)) for r in grid}
    detectable = next((r for r in grid if curve[r] >= 0.80), None)
    return {"n": n, "alpha": alpha, "critical_abs_rho": _round(crit),
            "power_curve": curve, "rho_at_80pct_power": detectable,
            "null_draws": null_draws, "power_draws": power_draws}


def _scale(value, lo, hi):
    if not isinstance(value, (int, float)) or hi == lo:
        return None
    return _round(max(0.0, min(1.0, (value - lo) / (hi - lo))))


def unseen_per_visit(unseen, visits):
    if not isinstance(unseen, (int, float)) or not isinstance(visits, (int, float)) or not visits:
        return None
    return _round(unseen / visits, 4)
