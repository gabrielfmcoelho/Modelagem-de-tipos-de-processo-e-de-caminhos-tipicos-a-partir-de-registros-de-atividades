from __future__ import annotations

import math
import random
from collections import Counter, defaultdict

from ..._sequence import END, is_conclusion_state


class MarkovModel:
    def __init__(self, order: int = 1):
        self.order = max(1, order)
        self.ctx: dict[int, dict[tuple, Counter]] = {
            o: defaultdict(Counter) for o in range(1, self.order + 1)
        }

    @classmethod
    def from_counts(cls, transitions) -> MarkovModel:
        m = cls(order=1)
        for f, t, c in transitions:
            m.ctx[1][(f,)][t] += c
        return m

    def fit(self, traces) -> MarkovModel:
        for tr in traces:
            for i in range(1, len(tr)):
                for o in range(1, self.order + 1):
                    if i - o >= 0:
                        self.ctx[o][tuple(tr[i - o:i])][tr[i]] += 1
        return self

    def _counts(self, prefix) -> Counter:
        for o in range(min(self.order, len(prefix)), 0, -1):
            c = self.ctx[o].get(tuple(prefix[-o:]))
            if c:
                return c
        return Counter()

    def predict_next(self, prefix, topk: int | None = None):
        ranked = [s for s, _ in self._counts(prefix).most_common()]
        return ranked[:topk] if topk else ranked

    def next_distribution(self, prefix) -> list[tuple[str, float]]:
        counts = self._counts(prefix)
        total = sum(counts.values())
        return [(s, n / total) for s, n in counts.items()] if total else []

    def generate(self, start, *, is_conclusion=is_conclusion_state, max_steps: int = 60,
                 beam: int = 1, strategy: str = "greedy", temperature: float = 1.0,
                 rng=None) -> list[str]:
        if strategy == "sample":
            return self._sample(start, is_conclusion, max_steps, temperature,
                                rng or random.Random(0))
        start_seq = list(start) if isinstance(start, (list, tuple)) else [start]
        beams = [(0.0, start_seq, is_conclusion(start_seq[-1]))]
        for _ in range(max_steps):
            if all(done for _, _, done in beams):
                break
            cand: list[tuple[float, list, bool]] = []
            for lp, seq, done in beams:
                if done:
                    cand.append((lp, seq, True))
                    continue
                counts = self._counts(seq)
                total = sum(counts.values())
                if not total:
                    cand.append((lp, seq, True))
                    continue
                for s, cnt in counts.most_common(beam):
                    cand.append((lp + math.log(cnt / total), seq + [s], is_conclusion(s)))
            cand.sort(key=lambda x: x[0], reverse=True)
            beams = cand[:beam]
        beams.sort(key=lambda x: x[0], reverse=True)
        return beams[0][1]

    def _sample(self, start, is_conclusion, max_steps, temperature, rng) -> list[str]:
        seq = list(start) if isinstance(start, (list, tuple)) else [start]
        for _ in range(max_steps):
            if is_conclusion(seq[-1]):
                break
            counts = self._counts(seq)
            if not counts:
                break
            states = list(counts)
            weights = [counts[s] ** (1.0 / max(temperature, 1e-6)) for s in states]
            seq.append(rng.choices(states, weights=weights, k=1)[0])
        return seq
