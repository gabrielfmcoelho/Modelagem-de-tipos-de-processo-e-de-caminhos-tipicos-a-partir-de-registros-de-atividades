
from __future__ import annotations

import math
import random
from collections import Counter, defaultdict
from statistics import mean

from .dfg import _lane
from ._sequence import END, is_conclusion_state, state_tipo
from .typical_path.markov.markov_model import MarkovModel
from .timeline import build_edges_for_processo, sort_and_fix_activities




def trace_states(activities, *, lane_depth: int | None = None) -> list[str]:
    ordered = sort_and_fix_activities(list(activities))
    return [f"{a.get('tipo_acao')}@{_lane(a.get('unidade'), lane_depth)}" for a in ordered]


def cohort_traces(reader, *, lane_depth: int | None = None, batch_size: int = 500):
    out: list[tuple[str, list[str]]] = []
    for batch in reader.iter_processo_batches(batch_size=batch_size):
        for pt in batch:
            acts = pt.activities
            if not acts:
                continue
            ordered = sort_and_fix_activities(list(acts))
            states = [f"{a.get('tipo_acao')}@{_lane(a.get('unidade'), lane_depth)}" for a in ordered]
            if len(states) < 2:
                continue
            out.append((ordered[0].get("data_hora") or "", states))
    return out


def flow_paths(activities, flow_edges, *, lane_depth: int | None = None,
               n_walks: int = 3, rng=None, rich: bool = False,
               pick: str = "sample") -> list[list[str]]:
    rng = rng or random.Random(0)
    if rich:
        state = {a.get("source_id"): _rich_state(a, lane_depth) for a in activities}
    else:
        state = {a.get("source_id"): f"{a.get('tipo_acao')}@{_lane(a.get('unidade'), lane_depth)}"
                 for a in activities}
    adj: dict[str, list[str]] = defaultdict(list)
    indeg: Counter = Counter()
    for e in flow_edges:
        f, t = e.get("from_id"), e.get("to_id")
        if f in state and t in state:
            adj[f].append(t)
            indeg[t] += 1
    roots = [sid for sid in state if indeg[sid] == 0]
    ger = [sid for sid in roots if state[sid].split("@", 1)[0] == "GERACAO-PROCEDIMENTO"]
    starts = ger or roots or list(state)

    def _walk() -> list[str]:
        cur = rng.choice(starts)
        path, seen = [cur], {cur}
        while adj.get(cur):
            nxts = [t for t in adj[cur] if t not in seen]
            if not nxts:
                break
            cur = rng.choice(nxts)
            path.append(cur)
            seen.add(cur)
        return [state[sid] for sid in path]

    if pick == "fullest":
        def _nlanes(p):
            return len({s.split("@", 1)[1].split(">", 1)[0] for s in p if "@" in s})
        def _ends_manual(p):
            return bool(p) and p[-1].split("@", 1)[0] == "CONCLUSAO-PROCESSO-UNIDADE"
        cands = [_walk() for _ in range(max(n_walks, 24))]
        return [max(cands, key=lambda p: (_ends_manual(p), _nlanes(p), len(p)))]
    return [_walk() for _ in range(n_walks)]


def cohort_flow_paths(reader, *, lane_depth: int | None = None, n_walks: int = 3,
                      batch_size: int = 500, rng=None, rich: bool = False,
                      pick: str = "sample") -> list[list[str]]:
    rng = rng or random.Random(0)
    out: list[list[str]] = []
    for batch in reader.iter_processo_batches(batch_size=batch_size):
        for pt in batch:
            acts = list(pt.activities)
            if len(acts) < 2:
                continue
            flow_edges, _ = build_edges_for_processo(acts)
            out.extend(flow_paths(acts, flow_edges, lane_depth=lane_depth,
                                  n_walks=n_walks, rng=rng, rich=rich, pick=pick))
    return out


def is_train_protocolo(protocolo: str, *, train_frac: float = 0.7, seed: int = 42) -> bool:
    import hashlib
    h = hashlib.blake2b(f"{seed}:{protocolo}".encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(h, "big") / float(1 << 64) < train_frac


def random_split_field(traces_with_time, index: int, *, train_frac: float = 0.7, seed: int = 42):
    s = sorted(traces_with_time, key=lambda x: (x[2] if len(x) > 2 else x[0]))
    if s and len(s[0]) > 2:
        train = [t[index] for t in s if is_train_protocolo(t[2], train_frac=train_frac, seed=seed)]
        test = [t[index] for t in s if not is_train_protocolo(t[2], train_frac=train_frac, seed=seed)]
        return train, test
    import random as _random
    idx = list(range(len(s)))
    _random.Random(seed).shuffle(idx)
    k = int(len(s) * train_frac)
    return ([s[i][index] for i in idx[:k]], [s[i][index] for i in idx[k:]])


def random_split(traces_with_time, *, train_frac: float = 0.7, seed: int = 42):
    return random_split_field(traces_with_time, 1, train_frac=train_frac, seed=seed)


def temporal_split_field(traces_with_time, index: int, *, train_frac: float = 0.8):
    s = sorted(traces_with_time, key=lambda x: x[0])
    k = int(len(s) * train_frac)
    return [t[index] for t in s[:k]], [t[index] for t in s[k:]]


def temporal_split(traces_with_time, *, train_frac: float = 0.8):
    return temporal_split_field(traces_with_time, 1, train_frac=train_frac)


def train_val_test_split(traces_with_time, *, train_frac: float = 0.6, val_frac: float = 0.2):
    s = sorted(traces_with_time, key=lambda x: x[0])
    n = len(s)
    a, b = int(n * train_frac), int(n * (train_frac + val_frac))
    take = lambda xs: [t for _, t in xs]
    return take(s[:a]), take(s[a:b]), take(s[b:])






def strip_end(seq):
    return [s for s in seq if s != END]


def strip_rich(s: str) -> str:
    return s.split(">", 1)[0]


def _rich_state(a, lane_depth) -> str:
    tipo = a.get("tipo_acao")
    s = f"{tipo}@{_lane(a.get('unidade'), lane_depth)}"
    if tipo == "PROCESSO-REMETIDO-UNIDADE":
        src = _lane(a.get("source_unidade"), lane_depth)
        if src and src != "?":
            s += ">" + src
    return s


def dl_distance(a, b) -> int:
    a, b = list(a), list(b)
    na, nb = len(a), len(b)
    if na == 0:
        return nb
    if nb == 0:
        return na
    d = [[0] * (nb + 1) for _ in range(na + 1)]
    for i in range(na + 1):
        d[i][0] = i
    for j in range(nb + 1):
        d[0][j] = j
    for i in range(1, na + 1):
        for j in range(1, nb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            d[i][j] = min(
                d[i - 1][j] + 1,
                d[i][j - 1] + 1,
                d[i - 1][j - 1] + cost,
            )
            if (i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]):
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[na][nb]




def next_step_accuracy(model, traces, topk=(1, 3), *, per_trace=None) -> dict[int, float]:
    hits = {k: 0 for k in topk}
    total = 0
    for tr in traces:
        th = {k: 0 for k in topk}
        tt = 0
        for i in range(1, len(tr)):
            preds = model.predict_next(tr[:i])
            tt += 1
            for k in topk:
                if tr[i] in preds[:k]:
                    th[k] += 1
        for k in topk:
            hits[k] += th[k]
        total += tt
        if per_trace is not None:
            per_trace.append([th[k] for k in topk] + [tt])
    return {k: (hits[k] / total if total else 0.0) for k in topk}


def suffix_distance(model, traces, *, is_conclusion=is_conclusion_state, beam: int = 1):
    dists = []
    for tr in traces:
        if len(tr) < 2:
            continue
        gen = model.generate(tr[0], is_conclusion=is_conclusion,
                             max_steps=2 * len(tr) + 5, beam=beam)
        dists.append(dl_distance(gen, tr) / max(len(gen), len(tr), 1))
    return round(mean(dists), 4) if dists else None


def suffix_prefix_distance(model, traces, *, is_conclusion=is_conclusion_state,
                           prefix_fracs=(0.25, 0.5, 0.75), strategy: str = "greedy", rng=None,
                           generate=None, length_ratios=None):
    gen_fn = generate or model.generate
    dists = []
    for tr in traces:
        if len(tr) < 3:
            continue
        for f in prefix_fracs:
            L = max(1, int(len(tr) * f))
            if L >= len(tr):
                continue
            gen = gen_fn(tr[:L], is_conclusion=is_conclusion,
                         max_steps=2 * len(tr) + 5, strategy=strategy, rng=rng)
            gen_suffix, act_suffix = gen[L:], tr[L:]
            dists.append(dl_distance(gen_suffix, act_suffix)
                         / max(len(gen_suffix), len(act_suffix), 1))
            if length_ratios is not None and act_suffix:
                length_ratios.append(len(gen_suffix) / len(act_suffix))
    return round(mean(dists), 4) if dists else None
