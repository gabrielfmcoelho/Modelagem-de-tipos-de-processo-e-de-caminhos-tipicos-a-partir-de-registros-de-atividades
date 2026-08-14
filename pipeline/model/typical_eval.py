
from __future__ import annotations

import json
import math
import random
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from statistics import mean

from .aggregate import both_means, macro_mean, weighted_mean

from .constrained import generate_constrained, medoid_trace, validity_score
from ..core.devices import _cuda_available
from .dfg import _lane
from .typical_path.dfg.dfg_model import DfgModel
from .predict import END, MarkovModel, dl_distance, next_step_accuracy, strip_end, suffix_prefix_distance, random_split, random_split_field, temporal_split, temporal_split_field
from .timeline import sort_and_fix_activities

MODEL_NAMES = ("markov", "dfg", "gnn", "gru", "lstm", "transformer")
ALPHABET_NAMES = ("unit", "itinerary", "procedure")
ALPHABET_AXES = {"unit": ("action", "unit"), "itinerary": ("unit",), "procedure": ("action",)}


def alphabet_carries(alphabet: str, axis: str) -> bool:
    return axis in ALPHABET_AXES.get(alphabet, ())
DFG_COVERAGE_FLOOR = 0.05
_GEN_K = 15
_GEN_TOP_K = 8


def is_end(state: str) -> bool:
    return state == END


@dataclass
class ModelSpec:
    name: str
    build: Callable[[], object]
    requires_gpu: bool = False




def edge_coverage(edges: set[tuple[str, str]], traces) -> float | None:
    total = hits = 0
    for tr in traces:
        for a, b in zip(tr, tr[1:]):
            total += 1
            hits += (a, b) in edges
    return round(hits / total, 4) if total else None


def edge_usage(edges: set[tuple[str, str]], traces) -> float | None:
    if not edges:
        return None
    seen = set()
    for tr in traces:
        for a, b in zip(tr, tr[1:]):
            if (a, b) in edges:
                seen.add((a, b))
    return round(len(seen) / len(edges), 4)


def edge_f1(coverage: float | None, usage: float | None) -> float | None:
    if coverage is None or usage is None or coverage + usage == 0:
        return None
    return round(2 * coverage * usage / (coverage + usage), 4)


def default_specs(models=None, *, epochs: int = 30, allow_cpu: bool = False,
                  dfg_coverage_floor: float = DFG_COVERAGE_FLOOR,
                  gnn_epochs: int = 200):
    names = list(models) if models else list(MODEL_NAMES)
    unknown = [n for n in names if n not in MODEL_NAMES]
    if unknown:
        raise ValueError(f"unknown models {unknown}; choose from {MODEL_NAMES}")
    gpu_ok = allow_cpu or _cuda_available()
    from .predict_lstm import LSTMModel, TransformerModel, TrueLSTMModel
    from .typical_path.gnn.gnn_model import GcnModel

    builders = {
        "markov": ModelSpec("markov", lambda: MarkovModel(3)),
        "dfg": ModelSpec("dfg", lambda: DfgModel(coverage_floor=dfg_coverage_floor)),
        "gnn": ModelSpec("gnn", lambda: GcnModel(epochs=gnn_epochs)),
        "gru": ModelSpec("gru", lambda: LSTMModel(epochs=epochs), requires_gpu=True),
        "lstm": ModelSpec("lstm", lambda: TrueLSTMModel(epochs=epochs), requires_gpu=True),
        "transformer": ModelSpec("transformer", lambda: TransformerModel(epochs=epochs), requires_gpu=True),
    }
    specs: list[ModelSpec] = []
    skipped: dict[str, str] = {}
    for n in names:
        spec = builders[n]
        if spec.requires_gpu and not gpu_ok:
            skipped[n] = "cuda unavailable"
        else:
            specs.append(spec)
    return specs, skipped


def normalize_label(entry) -> str | None:
    if entry is None:
        return None
    if isinstance(entry, dict):
        macro = entry.get("macro")
        return None if macro is None else str(macro)
    value = int(entry)
    return None if value == -1 else str(value)


def load_labels(path) -> dict[str, str | None]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    table = data.get("labels", data)
    return {pf: normalize_label(entry) for pf, entry in table.items()}


def load_protocol_traces(path) -> dict[str, tuple[str, list[str]]]:
    p = Path(path)
    if p.suffix == ".gz":
        import gzip
        raw = json.loads(gzip.open(p, "rt", encoding="utf-8").read())
    else:
        raw = json.loads(p.read_text(encoding="utf-8"))
    table = raw.get("traces", raw)
    return {pf: (rec.get("start") or "", list(rec["states"]))
            for pf, rec in table.items() if rec.get("states")}


def load_protocolo_set(path) -> set[str]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return {str(p) for p in raw}
    table = raw.get("protocolos", raw.get("labels", raw))
    return {str(p) for p in (table if isinstance(table, list) else table.keys())}


def protocol_traces(reader, *, lane_depth: int | None = None, batch_size: int = 500):
    out: dict[str, tuple[str, list[str]]] = {}
    for batch in reader.iter_processo_batches(batch_size=batch_size):
        for pt in batch:
            acts = pt.activities
            if not acts:
                continue
            ordered = sort_and_fix_activities(list(acts))
            states = [f"{a.get('tipo_acao')}@{_lane(a.get('unidade'), lane_depth)}" for a in ordered]
            if len(states) < 2:
                continue
            out[pt.protocolo_formatado] = (ordered[0].get("data_hora") or "", states)
    return out


def cluster_traces(labels: dict, traces: dict, *, min_traces: int = 30):
    groups: dict[str, list[tuple[str, list[str]]]] = defaultdict(list)
    for pf, tw in traces.items():
        cid = labels.get(pf)
        if cid is not None:
            groups[cid].append((tw[0], tw[1], pf))
    return {cid: tws for cid, tws in groups.items() if len(tws) >= min_traces}


def model_metrics(model, test, *, is_conclusion=is_end, prefix_fracs=(0.5,), seed: int = 0,
                  per_trace=None, constrained: bool = True) -> dict:
    acc = next_step_accuracy(model, test, topk=(1, 3), per_trace=per_trace)
    ratios: list[float] = []
    sx = suffix_prefix_distance(model, test, is_conclusion=is_conclusion,
                                prefix_fracs=prefix_fracs, rng=random.Random(seed),
                                length_ratios=ratios)
    sxc = (suffix_prefix_distance(model, test, is_conclusion=is_conclusion,
                                  prefix_fracs=prefix_fracs, rng=random.Random(seed),
                                  generate=partial(generate_constrained, model))
           if constrained else None)
    out = {"top1": round(acc[1], 4), "top3": round(acc[3], 4), "suffix_dl": sx,
           "suffix_length_ratio": round(mean(ratios), 4) if ratios else None}
    if constrained:
        out["suffix_dl_c"] = sxc
    return out


def mean_validity(model, test, *, is_conclusion=is_end) -> tuple[float | None, float | None]:
    steps, whole = [], []
    for tr in test:
        if len(tr) < 2:
            continue
        gen = model.generate(tr[0], is_conclusion=is_conclusion, max_steps=2 * len(tr) + 5)
        score = validity_score(strip_end(gen))
        steps.append(score)
        whole.append(1.0 if score >= 1.0 else 0.0)
    if not steps:
        return None, None
    return round(mean(steps), 4), round(mean(whole), 4)


def _representative_trace(model, start, *, seed=0, k=_GEN_K):
    traces = []
    for i in range(k):
        gen = strip_end(generate_constrained(model, start, strategy="sample",
                        temperature=1.0, top_k=_GEN_TOP_K,
                        rng=random.Random(seed * 1000 + i), max_steps=400))
        if len(gen) >= 2:
            traces.append(gen)
    if not traces:
        return [start]
    manual = [t for t in traces if t[-1].split("@", 1)[0] == "CONCLUSAO-PROCESSO-UNIDADE"]
    return medoid_trace(manual or traces)


_PATH_TEST_SAMPLE = 30
_PATH_TRAIN_SAMPLE = 20
_PATH_CAP = 100


def procedure_alphabet(seq):
    out: list[str] = []
    for s in seq:
        if s == END:
            continue
        t = s.partition("@")[0]
        if not out or out[-1] != t:
            out.append(t)
    return out


def itinerary_visits(seq):
    out: list[list] = []
    for s in seq:
        if s == END:
            continue
        u = s.partition("@")[2] if "@" in s else s
        if out and out[-1][0] == u:
            out[-1][1] += 1
        else:
            out.append([u, 1])
    return out


def itinerary_alphabet(seq):
    return [u for u, _ in itinerary_visits(seq)]


def annotate_itinerary(path, seqs):
    visits = itinerary_alphabet(path)
    if not visits:
        return []
    per_step: list[list[int]] = [[] for _ in visits]
    for s in seqs:
        got = itinerary_visits(s)
        for i, u in enumerate(visits):
            if i < len(got) and got[i][0] == u:
                per_step[i].append(got[i][1])
    out = []
    for i, u in enumerate(visits):
        counts = sorted(per_step[i])
        out.append({
            "unidade": u,
            "position": i,
            "n_matching": len(counts),
            "median_actions": counts[len(counts) // 2] if counts else None,
        })
    return out


def _norm_dl(a, b) -> float:
    return dl_distance(a, b) / max(len(a), len(b), 1)


def _as(seq, mode):
    if mode == "procedure":
        return procedure_alphabet(seq)
    if mode == "itinerary":
        return itinerary_alphabet(seq)
    return strip_end(seq)


def mean_path_distance(path, seqs, *, procedure=False, mode=None, cap=_PATH_CAP):
    if not path or not seqs:
        return None
    mode = mode or ("procedure" if procedure else "unit")
    p = _as(path, mode)[:cap]
    if not p:
        return None
    tot = 0.0
    for s in seqs:
        q = _as(s, mode)[:cap]
        tot += _norm_dl(p, q)
    return round(tot / len(seqs), 4)


def trace_dispersion(seqs, *, procedure=False, mode=None, cap=_PATH_CAP):
    mode = mode or ("procedure" if procedure else "unit")
    reps = [_as(s, mode)[:cap] for s in seqs]
    reps = [r for r in reps if r]
    if len(reps) < 2:
        return None
    tot = n = 0.0
    for i in range(len(reps)):
        for j in range(i + 1, len(reps)):
            tot += _norm_dl(reps[i], reps[j])
            n += 1
    return round(tot / n, 4) if n else None


_NLL_SAMPLE = 40
_NLL_FLOOR = 1e-6


def sequence_nll(model, traces, *, sample=_NLL_SAMPLE, floor=_NLL_FLOOR, seed=0) -> dict:
    if not traces:
        return {"nll": None, "perplexity": None, "oov_rate": None, "n_steps": 0}
    rng = random.Random(seed)
    sub = rng.sample(list(traces), min(sample, len(traces)))
    tot = 0.0
    n = oov = 0
    for tr in sub:
        for i in range(1, len(tr)):
            try:
                dist = dict(model.next_distribution(tr[:i]) or [])
            except Exception:
                return {"nll": None, "perplexity": None, "oov_rate": None, "n_steps": 0}
            p = float(dist.get(tr[i], 0.0))
            if p <= 0.0:
                oov += 1
                p = floor
            tot += -math.log(p)
            n += 1
    if not n:
        return {"nll": None, "perplexity": None, "oov_rate": None, "n_steps": 0}
    nll = tot / n
    return {"nll": round(nll, 4),
            "perplexity": round(math.exp(min(nll, 700.0)), 2),
            "oov_rate": round(oov / n, 4),
            "n_steps": n}


def real_flow_validity(traces) -> tuple[float | None, float | None]:
    steps, whole = [], []
    for tr in traces:
        seq = strip_end(tr)
        if len(seq) < 2:
            continue
        sc = validity_score(seq)
        steps.append(sc)
        whole.append(1.0 if sc >= 1.0 else 0.0)
    if not steps:
        return None, None
    return round(mean(steps), 4), round(mean(whole), 4)


def global_model_accuracy(all_traces, cluster_test, *, order: int = 3, topk: int = 1,
                          split_seed: int = 42, train_frac: float = 0.7) -> float | None:
    train, _ = random_split(all_traces, train_frac=train_frac, seed=split_seed)
    if not train or not cluster_test:
        return None
    m = MarkovModel(order).fit([t + [END] for t in train])
    hits = total = 0
    for tr in cluster_test:
        for i in range(1, len(tr)):
            total += 1
            hits += tr[i] in m.predict_next(tr[:i])[:topk]
    return round(hits / total, 4) if total else None


def successor_baseline_accuracy(train, test) -> float | None:
    table: dict[str, Counter] = defaultdict(Counter)
    for tr in train:
        for a, b in zip(tr, tr[1:]):
            table[a][b] += 1
    best = {a: c.most_common(1)[0][0] for a, c in table.items()}
    hits = total = 0
    for tr in test:
        for a, b in zip(tr, tr[1:]):
            total += 1
            hits += best.get(a) == b
    return round(hits / total, 4) if total else None


def medoid_by_normalized_dl(seqs, *, procedure=False, mode=None, cap=_PATH_CAP):
    cands = [s for s in seqs if s]
    if not cands:
        return []
    best, best_score = None, None
    for c in cands:
        score = mean_path_distance(c, [s for s in cands if s is not c],
                                   procedure=procedure, mode=mode, cap=cap)
        if score is None:
            continue
        if best_score is None or score < best_score:
            best, best_score = c, score
    return list(best) if best is not None else []


def path_support(path, seqs, *, mode="unit", cap=_PATH_CAP, thresholds=(0.25, 0.5)):
    if not path or not seqs:
        return {}
    p = _as(path, mode)[:cap]
    if not p:
        return {}
    d = [_norm_dl(p, _as(s, mode)[:cap]) for s in seqs]
    out = {f"within_{int(t * 100)}": round(sum(1 for x in d if x <= t) / len(d), 4)
           for t in thresholds}
    out["median_distance"] = round(sorted(d)[len(d) // 2], 4)
    return out


def unit_coverage(path, seqs, *, cap=_PATH_CAP):
    if not path or not seqs:
        return {}
    pu = set(itinerary_alphabet(path))
    if not pu:
        return {}
    recs, precs = [], []
    for s in seqs:
        su = set(itinerary_alphabet(s[:cap]))
        if not su:
            continue
        recs.append(len(pu & su) / len(su))
        precs.append(len(pu & su) / len(pu))
    if not recs:
        return {}
    return {"unit_recall": round(mean(recs), 4),
            "unit_precision": round(mean(precs), 4),
            "n_units_path": len(pu)}


def transition_support(path, seqs, *, mode="unit", cap=_PATH_CAP):
    p = _as(path, mode)[:cap]
    if len(p) < 2:
        return {}
    seen: Counter = Counter()
    for s in seqs:
        q = _as(s, mode)[:cap]
        for a, b in zip(q, q[1:]):
            seen[(a, b)] += 1
    n = max(1, len(seqs))
    fracs = [seen.get((a, b), 0) / n for a, b in zip(p, p[1:])]
    return {"transition_support_mean": round(mean(fracs), 4),
            "transition_support_min": round(min(fracs), 4),
            "transitions_unseen": sum(1 for f in fracs if f == 0.0)}


def step_count_agreement(path, seqs, *, cap=_PATH_CAP):
    ann = annotate_itinerary(path, seqs)
    if not ann:
        return {}
    obs = [a["median_actions"] for a in ann if a.get("median_actions") is not None]
    return {"visits_in_path": len(ann),
            "median_actions_per_visit": round(mean(obs), 2) if obs else None,
            "visits_matched_frac": round(mean([a["n_matching"] / max(1, len(seqs))
                                               for a in ann]), 4)}


def generalization_metrics(path, seqs, *, mode="unit", alphabet="unit"):
    out = {}
    out.update(path_support(path, seqs, mode=mode))
    if alphabet_carries(alphabet, "unit"):
        out.update(unit_coverage(path, seqs))
    if _projects(alphabet):
        out.update(step_count_agreement(path, seqs))
    out.update(transition_support(path, seqs, mode=mode))
    return out


def _projects(alphabet: str) -> bool:
    return alphabet_carries(alphabet, "action") and alphabet_carries(alphabet, "unit")


def _path_reference(train, test, *, seed=0, alphabet="unit"):
    rng = random.Random(seed)
    te = rng.sample(test, min(_PATH_TEST_SAMPLE, len(test)))
    trn = rng.sample(train, min(_PATH_TRAIN_SAMPLE, len(train)))
    out: dict = {
        "n_test_sampled": len(te),
        "n_train_sampled": len(trn),
        "dispersion": trace_dispersion(te),
    }
    if _projects(alphabet):
        out["dispersion_proc"] = trace_dispersion(te, mode="procedure")
        out["dispersion_itin"] = trace_dispersion(te, mode="itinerary")
    if trn:
        stripped = [strip_end(t) for t in trn]
        med = medoid_by_normalized_dl(stripped)
        out["medoid_distance"] = mean_path_distance(med, te)
        out["medoid_generalization"] = generalization_metrics(med, te, alphabet=alphabet)
        if _projects(alphabet):
            med_p = medoid_by_normalized_dl(stripped, mode="procedure")
            out["medoid_distance_proc"] = mean_path_distance(med_p, te, mode="procedure")
            med_i = medoid_by_normalized_dl(stripped, mode="itinerary")
            out["medoid_distance_itin"] = mean_path_distance(med_i, te, mode="itinerary")
            out["medoid_itinerary"] = itinerary_alphabet(med_i)
    return out, te


def _real_states(traces_with_time):
    seqs = sorted((tw[1] for tw in traces_with_time), key=len)
    return list(seqs[len(seqs) // 2]) if seqs else []


def _comum_states(traces_with_time, *, seed=0, k=_GEN_K):
    seqs = [tw[1] for tw in traces_with_time]
    if not seqs:
        return []
    sample = random.Random(seed).sample(seqs, min(k, len(seqs)))
    return medoid_trace(sample)


def evaluate_cluster(traces_with_time, specs, *, train_frac: float = 0.7, seed: int = 0,
                     emit_traces: bool = False, split: str = "random",
                     split_seed: int = 42, all_traces=None,
                     alphabet: str = "unit") -> dict | None:
    if split == "temporal":
        train, test = temporal_split(traces_with_time, train_frac=train_frac)
    else:
        train, test = random_split(traces_with_time, train_frac=train_frac, seed=split_seed)
    if not train or not test:
        return None
    train = [t + [END] for t in train]
    test = [t + [END] for t in test]
    dfg = DfgModel(coverage_floor=0.0).fit(train)
    cov = edge_coverage(dfg.edges, test)
    use = edge_usage(dfg.edges, test)
    flow = alphabet_carries(alphabet, "action")
    baseline = {
        "top1_successor": successor_baseline_accuracy(train, test),
        "top1_global_model": (global_model_accuracy(all_traces, test, split_seed=split_seed,
                                                    train_frac=train_frac)
                              if all_traces else None),
    }
    if flow:
        baseline["flow_validity_step_real"], baseline["flow_validity_trace_real"] = \
            real_flow_validity(test)
    out: dict = {
        "n_traces": len(traces_with_time),
        "n_train": len(train),
        "n_test": len(test),
        "edge_coverage": cov,
        "edge_usage": use,
        "edge_f1": edge_f1(cov, use),
        "n_model_edges": len(dfg.edges),
        "baseline": baseline,
        "models": {},
    }
    out["split"] = {"mode": split, "train_frac": train_frac, "seed": split_seed}
    if traces_with_time and len(traces_with_time[0]) > 2:
        out["test_protocolos"] = (
            temporal_split_field(traces_with_time, 2, train_frac=train_frac)[1]
            if split == "temporal" else
            random_split_field(traces_with_time, 2, train_frac=train_frac, seed=split_seed)[1])
    start = Counter(t[0] for t in train).most_common(1)[0][0]
    path_ref, path_test = _path_reference(train, test, seed=seed, alphabet=alphabet)
    out["path_reference"] = path_ref
    for spec in specs:
        model = spec.build()
        model.fit(train)
        if getattr(model, "available", True) is False:
            out["models"][spec.name] = {"skipped": getattr(model, "reason", "unavailable")}
            continue
        records: list = []
        metrics = model_metrics(model, test, seed=seed, per_trace=records, constrained=flow)
        if flow:
            metrics["flow_validity_step"], metrics["flow_validity_trace"] = \
                mean_validity(model, test)
        metrics["per_trace"] = records
        metrics["nll"] = sequence_nll(model, test, seed=seed)
        path = _representative_trace(model, start, seed=seed)
        metrics["typical_path_distance"] = mean_path_distance(path, path_test)
        if _projects(alphabet):
            metrics["typical_path_distance_proc"] = mean_path_distance(path, path_test,
                                                                       mode="procedure")
            metrics["typical_path_distance_itin"] = mean_path_distance(path, path_test,
                                                                       mode="itinerary")
        if alphabet_carries(alphabet, "unit"):
            metrics["typical_itinerary"] = annotate_itinerary(path, path_test)
        metrics["generalization"] = generalization_metrics(path, path_test, alphabet=alphabet)
        if emit_traces:
            metrics["trace"] = path
        out["models"][spec.name] = metrics
    if emit_traces:
        out["real"] = _real_states(traces_with_time)
        out["comum"] = _comum_states(traces_with_time, seed=seed)
        by_states = {tuple(tw[1]): (tw[2] if len(tw) > 2 else None) for tw in traces_with_time}
        out["real_protocolo"] = by_states.get(tuple(out["real"]))
        out["comum_protocolo"] = by_states.get(tuple(out["comum"]))
    return out


SIZE_BANDS = (("small", 0, 60), ("medium", 60, 150), ("large", 150, 10 ** 9))


def size_band(n: int) -> str:
    for name, lo, hi in SIZE_BANDS:
        if lo <= n < hi:
            return name
    return "large"


def evaluate_matrix_by_band(cluster_results: dict) -> dict:
    bands: dict[str, dict] = {}
    for name, _lo, _hi in SIZE_BANDS:
        subset = {k: v for k, v in cluster_results.items()
                  if size_band(v.get("n_traces", 0)) == name}
        if subset:
            bands[name] = evaluate_matrix(subset)
            bands[name]["n_clusters"] = len(subset)
    return bands


def evaluate_matrix(cluster_results: dict) -> dict:
    all_keys = ("top1", "top3", "suffix_dl", "suffix_dl_c", "suffix_length_ratio",
                "flow_validity_step", "flow_validity_trace",
                "typical_path_distance", "typical_path_distance_proc",
                "typical_path_distance_itin")
    present = {k for res in cluster_results.values()
               for m in res["models"].values() if isinstance(m, dict) for k in m}
    metric_keys = tuple(k for k in all_keys if k in present)
    per_model: dict[str, list[tuple[int, dict]]] = defaultdict(list)
    for res in cluster_results.values():
        for name, metrics in res["models"].items():
            if "skipped" in metrics:
                continue
            per_model[name].append((res["n_traces"], metrics))

    def _agg(pairs, weighted: bool) -> dict:
        out = {}
        for key in metric_keys:
            vals = [(w, m.get(key)) for w, m in pairs]
            out[key] = weighted_mean(vals) if weighted else macro_mean([v for _, v in vals])
        return out

    def _fitness_agg(key: str) -> dict:
        return both_means([(res["n_traces"], res.get(key))
                           for res in cluster_results.values()])

    return {
        "n_clusters": len(cluster_results),
        "n_traces": sum(r["n_traces"] for r in cluster_results.values()),
        "edge_coverage": _fitness_agg("edge_coverage"),
        "edge_usage": _fitness_agg("edge_usage"),
        "edge_f1": _fitness_agg("edge_f1"),
        "models": {
            name: {"macro": _agg(pairs, False), "weighted": _agg(pairs, True), "n_clusters": len(pairs)}
            for name, pairs in per_model.items()
        },
    }
