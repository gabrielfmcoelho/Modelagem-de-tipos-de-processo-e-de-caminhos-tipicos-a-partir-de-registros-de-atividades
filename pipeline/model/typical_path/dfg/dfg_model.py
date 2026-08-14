from __future__ import annotations

from collections import defaultdict

from ..markov.markov_model import MarkovModel


class DfgModel(MarkovModel):
    def __init__(self, coverage_floor: float = 0.0):
        super().__init__(order=1)
        self.coverage_floor = coverage_floor
        self.edges: set[tuple[str, str]] = set()

    def fit(self, traces) -> DfgModel:
        traces = list(traces)
        procs: dict[tuple[str, str], set[int]] = defaultdict(set)
        for i, tr in enumerate(traces):
            for a, b in zip(tr, tr[1:]):
                procs[(a, b)].add(i)
        total = len(traces) or 1
        self.edges = {e for e, ps in procs.items() if len(ps) / total >= self.coverage_floor}
        for tr in traces:
            for a, b in zip(tr, tr[1:]):
                if (a, b) in self.edges:
                    self.ctx[1][(a,)][b] += 1
        return self
