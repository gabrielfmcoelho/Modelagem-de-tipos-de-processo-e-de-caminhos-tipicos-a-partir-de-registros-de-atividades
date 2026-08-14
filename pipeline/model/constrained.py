
from __future__ import annotations

import random

from .predict import END, dl_distance
from .process_state import CONCLUSION_TYPES

GERACAO = "GERACAO-PROCEDIMENTO"
REMETIDO = "PROCESSO-REMETIDO-UNIDADE"
RECEBIDO = "PROCESSO-RECEBIDO-UNIDADE"
REABERTURA = "REABERTURA-PROCESSO-UNIDADE"


def _split(state: str) -> tuple[str, str]:
    tipo, _, lane = (state or "").partition("@")
    return tipo, lane


class FlowState:

    def __init__(self) -> None:
        self.started = False
        self.open: set[str] = set()
        self.pending: set[str] = set()

    def allows(self, state: str) -> bool:
        tipo, lane = _split(state)
        if state == END:
            return True
        if tipo == GERACAO:
            return not self.started
        if tipo == RECEBIDO:
            return lane in self.pending
        if tipo in CONCLUSION_TYPES:
            return lane in self.open
        if tipo == REMETIDO:
            return self.started
        if tipo == REABERTURA:
            return self.started
        return True

    def complete(self) -> bool:
        return self.started and not self.open

    def step(self, state: str) -> None:
        tipo, lane = _split(state)
        if state == END:
            return
        self.started = True
        if tipo == GERACAO:
            self.open.add(lane)
        elif tipo == REMETIDO:
            self.started = True
            self.open.add(lane)
            self.pending.add(lane)
        elif tipo == REABERTURA:
            self.open.add(lane)
        elif tipo == RECEBIDO:
            self.pending.discard(lane)
        elif tipo in CONCLUSION_TYPES:
            self.open.discard(lane)


def generate_constrained(model, start, *, max_steps: int = 200, strategy: str = "sample",
                         temperature: float = 1.0, top_k: int = 8, rng=None,
                         end_token: str = END, is_conclusion=None, beam: int = 1) -> list[str]:
    rng = rng or random.Random(0)
    seq = [start] if isinstance(start, str) else list(start)
    if not seq:
        return []
    fs = FlowState()
    for s in seq:
        fs.step(s)
    for _ in range(max_steps):
        dist = model.next_distribution(seq)
        if not dist:
            break
        cand = [(s, p) for (s, p) in dist if s == end_token or fs.allows(s)]
        if not cand:
            break
        cand.sort(key=lambda sp: sp[1], reverse=True)
        if top_k:
            cand = cand[:top_k]
        states = [s for s, _ in cand]
        if strategy == "greedy":
            nxt = states[0]
        else:
            weights = [max(p, 1e-12) ** (1.0 / max(temperature, 1e-6)) for _, p in cand]
            nxt = rng.choices(states, weights=weights, k=1)[0]
        if nxt == end_token:
            break
        seq.append(nxt)
        fs.step(nxt)
    return seq


def generate_full(model, start: str, *, max_steps: int = 400, strategy: str = "sample",
                  temperature: float = 1.0, top_k: int = 8, rng=None,
                  end_token: str = END) -> list[str]:
    rng = rng or random.Random(0)
    seq = [start]
    fs = FlowState()
    fs.step(start)
    for _ in range(max_steps):
        if fs.complete():
            break
        dist = model.next_distribution(seq)
        if not dist:
            break
        cand = [(s, p) for (s, p) in dist if s != end_token and fs.allows(s)]
        if not cand:
            break
        cand.sort(key=lambda sp: sp[1], reverse=True)
        if top_k:
            cand = cand[:top_k]
        states = [s for s, _ in cand]
        if strategy == "greedy":
            nxt = states[0]
        else:
            weights = [max(p, 1e-12) ** (1.0 / max(temperature, 1e-6)) for _, p in cand]
            nxt = rng.choices(states, weights=weights, k=1)[0]
        seq.append(nxt)
        fs.step(nxt)
    return seq


def valid_mask(prefix, vocab) -> list[bool]:
    fs = FlowState()
    for s in prefix:
        fs.step(s)
    return [fs.allows(v) for v in vocab]


def validity_score(trace) -> float:
    fs = FlowState()
    ok = 0
    for s in trace:
        if fs.allows(s):
            ok += 1
        fs.step(s)
    return ok / len(trace) if trace else 1.0


def medoid_trace(traces: list[list[str]]) -> list[str]:
    traces = [t for t in traces if t]
    if not traces:
        return []
    if len(traces) == 1:
        return traces[0]
    best, best_sum = traces[0], None
    for t in traces:
        total = sum(dl_distance(t, u) for u in traces if u is not t)
        if best_sum is None or total < best_sum:
            best, best_sum = t, total
    return best
