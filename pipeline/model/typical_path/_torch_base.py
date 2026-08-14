
from __future__ import annotations

import random

from .._sequence import END, is_conclusion_state

PAD, UNK = 0, 1


class _TorchSeqModel:

    def __init__(self, *, hidden: int = 64, embed: int = 32, window: int = 8,
                 epochs: int = 30, lr: float = 0.01, dropout: float = 0.2,
                 batch_size: int = 2048, seed: int = 42, aux_lambda: float = 0.0):
        self.hidden, self.embed, self.window = hidden, embed, window
        self.epochs, self.lr, self.dropout = epochs, lr, dropout
        self.batch_size, self.seed = batch_size, seed
        self.aux_lambda = aux_lambda
        self.available = False
        self.reason = ""
        self.stoi: dict[str, int] = {}
        self.itos: dict[int, str] = {}
        self._net = None
        self._device = "cpu"

    def _build_net(self, V, nn):
        raise NotImplementedError

    def _encode(self, prefix) -> list[int]:
        ids = [self.stoi.get(s, UNK) for s in prefix][-self.window:]
        return [PAD] * (self.window - len(ids)) + ids

    def fit(self, traces) -> _TorchSeqModel:
        try:
            import torch
            import torch.nn as nn
        except Exception as exc:
            self.available, self.reason = False, str(exc)
            return self
        from ...core.devices import select_device
        device = self._device = select_device()

        vocab = sorted({s for tr in traces for s in tr})
        self.stoi = {s: i + 2 for i, s in enumerate(vocab)}
        self.itos = {i: s for s, i in self.stoi.items()}
        V = len(self.stoi) + 2

        from ..constrained import FlowState
        xs, ys, masks = [], [], []
        for tr in traces:
            ids = [self.stoi[s] for s in tr]
            fs = FlowState() if self.aux_lambda > 0 else None
            for i in range(1, len(ids)):
                if fs is not None:
                    fs.step(tr[i - 1])
                    masks.append([fs.allows(self.itos.get(v, "")) for v in range(V)])
                ctx = ids[max(0, i - self.window):i]
                xs.append([PAD] * (self.window - len(ctx)) + ctx)
                ys.append(ids[i])
        if not xs:
            self.available, self.reason = False, "no training samples"
            return self

        torch.manual_seed(self.seed)
        X = torch.tensor(xs, dtype=torch.long, device=device)
        Y = torch.tensor(ys, dtype=torch.long, device=device)
        M = torch.tensor(masks, dtype=torch.bool) if self.aux_lambda > 0 else None

        self._net = self._build_net(V, nn).to(device)
        opt = torch.optim.Adam(self._net.parameters(), lr=self.lr, weight_decay=1e-4)
        lossf = nn.CrossEntropyLoss()
        n, bs = X.size(0), self.batch_size
        self._net.train()
        for _ in range(self.epochs):
            perm = torch.randperm(n, device=device)
            for i in range(0, n, bs):
                idx = perm[i:i + bs]
                opt.zero_grad()
                logits = self._net(X[idx])
                loss = lossf(logits, Y[idx])
                if M is not None:
                    invalid = (~M[idx.cpu()]).to(device=device, dtype=torch.float32)
                    loss = loss + self.aux_lambda * (torch.softmax(logits, -1) * invalid).sum(1).mean()
                loss.backward()
                opt.step()
        self._net.eval()
        self.available = True
        return self

    def fit_rl(self, starts, *, rl_epochs: int = 15, rl_batch: int = 24, max_steps: int = 80,
               lr: float = 0.003, rng=None) -> _TorchSeqModel:
        if not self.available:
            return self
        import torch

        from ..constrained import validity_score
        rng = rng or random.Random(0)
        opt = torch.optim.Adam(self._net.parameters(), lr=lr)
        self._net.train()
        for _ in range(rl_epochs):
            logps, rewards = [], []
            for _ in range(rl_batch):
                seq = [rng.choice(starts)]
                step_lp = []
                for _ in range(max_steps):
                    x = torch.tensor([self._encode(seq)], dtype=torch.long, device=self._device)
                    dist = torch.distributions.Categorical(logits=self._net(x)[0])
                    a = dist.sample()
                    step_lp.append(dist.log_prob(a))
                    tok = self.itos.get(int(a))
                    if tok is None or tok == END:
                        break
                    seq.append(tok)
                if step_lp:
                    logps.append(torch.stack(step_lp).sum())
                    rewards.append(validity_score([s for s in seq if s != END]))
            if not rewards:
                continue
            baseline = sum(rewards) / len(rewards)
            loss = -torch.stack([lp * (r - baseline) for lp, r in zip(logps, rewards)]).mean()
            opt.zero_grad()
            loss.backward()
            opt.step()
        self._net.eval()
        return self

    def predict_next(self, prefix, topk: int | None = None):
        if not self.available:
            return []
        import torch
        with torch.no_grad():
            logits = self._net(torch.tensor([self._encode(prefix)], dtype=torch.long,
                                            device=self._device))[0]
        order = torch.argsort(logits, descending=True).cpu().tolist()
        ranked = [self.itos[i] for i in order if i in self.itos]
        return ranked[:topk] if topk else ranked

    def _next_dist(self, prefix):
        if not self.available:
            return []
        import torch
        with torch.no_grad():
            logits = self._net(torch.tensor([self._encode(prefix)], dtype=torch.long,
                                            device=self._device))[0]
        probs = torch.softmax(logits, dim=-1).cpu().tolist()
        return [(self.itos[i], probs[i]) for i in range(len(probs)) if i in self.itos]

    def next_distribution(self, prefix):
        return self._next_dist(prefix)

    def generate(self, start, *, is_conclusion=is_conclusion_state, max_steps: int = 60,
                 beam: int = 1, strategy: str = "greedy", temperature: float = 1.0,
                 rng=None) -> list[str]:
        seq = list(start) if isinstance(start, (list, tuple)) else [start]
        if not self.available:
            return seq
        rng = rng or random.Random(0)
        for _ in range(max_steps):
            if is_conclusion(seq[-1]):
                break
            if strategy == "sample":
                pairs = self._next_dist(seq)
                if not pairs:
                    break
                states = [p[0] for p in pairs]
                weights = [max(p[1], 1e-12) ** (1.0 / max(temperature, 1e-6)) for p in pairs]
                seq.append(rng.choices(states, weights=weights, k=1)[0])
            else:
                nxt = self.predict_next(seq, topk=1)
                if not nxt:
                    break
                seq.append(nxt[0])
        return seq
