from __future__ import annotations

from collections import Counter

from ..markov.markov_model import MarkovModel

DEFAULT_HIDDEN = 64
DEFAULT_EPOCHS = 200
DEFAULT_LR = 0.01
DEFAULT_SEED = 42
DEFAULT_WEIGHT_DECAY = 1e-4
MIN_PROB = 1e-6


class GcnModel(MarkovModel):
    def __init__(self, *, hidden: int = DEFAULT_HIDDEN, epochs: int = DEFAULT_EPOCHS,
                 lr: float = DEFAULT_LR, seed: int = DEFAULT_SEED,
                 weight_decay: float = DEFAULT_WEIGHT_DECAY, device: str = "cpu"):
        super().__init__(order=1)
        self.hidden = hidden
        self.epochs = epochs
        self.lr = lr
        self.seed = seed
        self.weight_decay = weight_decay
        self.device = device
        self.available = False
        self.reason = ""
        self.stoi: dict[str, int] = {}
        self.itos: dict[int, str] = {}
        self._probs = None
        self._sources: set[int] = set()
        self.n_states = 0
        self.n_transitions = 0

    def fit(self, traces) -> GcnModel:
        traces = [list(t) for t in traces]
        states = sorted({s for t in traces for s in t})
        if len(states) < 2:
            self.reason = "fewer than two distinct states; a graph needs an edge"
            return self
        pairs = [(a, b) for t in traces for a, b in zip(t, t[1:])]
        if not pairs:
            self.reason = "no observed transitions"
            return self
        try:
            import torch
        except Exception as exc:
            self.reason = f"torch unavailable ({type(exc).__name__}); the GCN cannot be fitted"
            return self

        prev_threads = torch.get_num_threads()
        torch.set_num_threads(1)
        self.stoi = {s: i for i, s in enumerate(states)}
        self.itos = {i: s for s, i in self.stoi.items()}
        self.n_states = len(states)
        self.n_transitions = len(pairs)
        self._sources = {self.stoi[a] for a, _ in pairs}
        v = self.n_states
        dev = torch.device(self.device)

        adj = torch.zeros((v, v), dtype=torch.float32, device=dev)
        for a, b in pairs:
            adj[self.stoi[a], self.stoi[b]] += 1.0
        adj = adj + adj.t() + torch.eye(v, device=dev)
        dinv = adj.sum(1).clamp(min=1e-9).pow(-0.5)
        ahat = dinv.unsqueeze(1) * adj * dinv.unsqueeze(0)

        torch.manual_seed(self.seed)
        w1 = torch.nn.Parameter(torch.empty(v, self.hidden, device=dev))
        w2 = torch.nn.Parameter(torch.empty(self.hidden, v, device=dev))
        torch.nn.init.xavier_uniform_(w1)
        torch.nn.init.xavier_uniform_(w2)
        opt = torch.optim.Adam([w1, w2], lr=self.lr, weight_decay=self.weight_decay)
        loss_fn = torch.nn.CrossEntropyLoss()
        src = torch.tensor([self.stoi[a] for a, _ in pairs], device=dev)
        dst = torch.tensor([self.stoi[b] for _, b in pairs], device=dev)

        for _ in range(self.epochs):
            opt.zero_grad()
            logits = ahat @ torch.relu(ahat @ w1) @ w2
            loss_fn(logits[src], dst).backward()
            opt.step()

        with torch.no_grad():
            logits = ahat @ torch.relu(ahat @ w1) @ w2
            self._probs = torch.softmax(logits, dim=1).cpu().numpy()
        torch.set_num_threads(prev_threads)
        self.available = True
        return self

    def _counts(self, prefix) -> Counter:
        if self._probs is None or not len(prefix):
            return Counter()
        idx = self.stoi.get(prefix[-1])
        if idx is None or idx not in self._sources:
            return Counter()
        row = self._probs[idx]
        return Counter({self.itos[j]: float(p) for j, p in enumerate(row) if p > MIN_PROB})
