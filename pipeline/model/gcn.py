
from __future__ import annotations

from collections import defaultdict, deque


def _edge_weight(e: dict) -> float:
    freq = float(e.get("frequency") or 0.0)
    contrib = float(e.get("mean_contrib_score") or 0.0)
    return freq * (0.5 + 0.5 * contrib)


def _normalize(raw: dict[str, float]) -> dict[str, float]:
    if not raw:
        return {}
    hi = max(raw.values())
    if hi <= 0:
        return {k: 0.0 for k in raw}
    return {k: round(v / hi, 4) for k, v in raw.items()}


def weighted_degree_importance(nodes, edges) -> dict[str, float]:
    raw = {n["state_key"]: 0.0 for n in nodes}
    for e in edges:
        w = _edge_weight(e)
        raw[e["from_key"]] = raw.get(e["from_key"], 0.0) + w
        raw[e["to_key"]] = raw.get(e["to_key"], 0.0) + w
    return _normalize(raw)


def pagerank_importance(
    nodes, edges, *, damping: float = 0.85, iters: int = 100, tol: float = 1e-9,
) -> dict[str, float]:
    keys = [n["state_key"] for n in nodes]
    if not keys:
        return {}
    n = len(keys)
    idx = {k: i for i, k in enumerate(keys)}

    out_w: dict[int, float] = defaultdict(float)
    out_edges: dict[int, list[tuple[int, float]]] = defaultdict(list)
    for e in edges:
        if e["from_key"] not in idx or e["to_key"] not in idx:
            continue
        w = _edge_weight(e)
        if w <= 0:
            continue
        u, v = idx[e["from_key"]], idx[e["to_key"]]
        out_edges[u].append((v, w))
        out_w[u] += w

    conclusion = [idx[n["state_key"]] for n in nodes if n.get("is_conclusion")]
    pvec = [0.0] * n
    if conclusion:
        for c in conclusion:
            pvec[c] = 1.0 / len(conclusion)
    else:
        pvec = [1.0 / n] * n

    pr = [1.0 / n] * n
    for _ in range(iters):
        new = [(1.0 - damping) * pvec[i] for i in range(n)]
        dangling = 0.0
        for i in range(n):
            if out_w[i] <= 0:
                dangling += pr[i]
        for u in range(n):
            if out_w[u] <= 0:
                continue
            share = damping * pr[u] / out_w[u]
            for v, w in out_edges[u]:
                new[v] += share * w
        if dangling > 0:
            for i in range(n):
                new[i] += damping * dangling * pvec[i]
        delta = sum(abs(new[i] - pr[i]) for i in range(n))
        pr = new
        if delta < tol:
            break

    return _normalize({keys[i]: pr[i] for i in range(n)})


def gcn_importance(
    nodes, edges, *, hidden: int = 32, epochs: int = 200, lr: float = 0.01,
    weight_decay: float = 5e-4, seed: int = 42,
) -> dict[str, float]:
    try:
        import torch
        import torch.nn.functional as F
        from torch_geometric.nn import GCNConv
    except Exception as exc:
        raise RuntimeError(
            "gcn method requires torch + torch-geometric "
            "(pip install -r requirements-gpu.txt)"
        ) from exc

    if not nodes:
        return {}

    from ..core.devices import select_device
    device = select_device()

    keys = [n["state_key"] for n in nodes]
    idx = {k: i for i, k in enumerate(keys)}
    x = torch.tensor([n["features"] for n in nodes], dtype=torch.float32, device=device)
    y = torch.tensor([[float(n.get("mean_contrib") or 0.0)] for n in nodes],
                     dtype=torch.float32, device=device)

    src, dst, ew = [], [], []
    for e in edges:
        if e["from_key"] in idx and e["to_key"] in idx:
            src.append(idx[e["from_key"]])
            dst.append(idx[e["to_key"]])
            ew.append(_edge_weight(e))
    if src:
        edge_index = torch.tensor([src, dst], dtype=torch.long, device=device)
        edge_weight = torch.tensor(ew, dtype=torch.float32, device=device)
    else:
        n = len(keys)
        edge_index = torch.tensor([list(range(n)), list(range(n))], dtype=torch.long, device=device)
        edge_weight = torch.ones(len(keys), dtype=torch.float32, device=device)

    torch.manual_seed(seed)

    class _GCN(torch.nn.Module):
        def __init__(self, in_dim, hidden):
            super().__init__()
            self.c1 = GCNConv(in_dim, hidden)
            self.c2 = GCNConv(hidden, 1)

        def forward(self, x, ei, ew):
            h = F.relu(self.c1(x, ei, ew))
            return self.c2(h, ei, ew)

    model = _GCN(x.size(1), hidden).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    model.train()
    for _ in range(epochs):
        opt.zero_grad()
        out = model(x, edge_index, edge_weight)
        loss = F.mse_loss(out, y)
        loss.backward()
        opt.step()

    model.eval()
    with torch.no_grad():
        pred = model(x, edge_index, edge_weight).squeeze(-1).cpu().tolist()

    raw = {keys[i]: max(0.0, pred[i]) for i in range(len(keys))}
    return _normalize(raw)


def blend_importance(
    nodes, learned: dict[str, float], *,
    w_struct: float = 0.5, w_band: float = 0.2, w_gcn: float = 0.3,
) -> dict[str, float]:
    raw = {}
    for n in nodes:
        k = n["state_key"]
        raw[k] = (
            w_struct * float(n.get("mean_contrib") or 0.0)
            + w_band * float(n.get("mean_activity_band") or 0.0)
            + w_gcn * float(learned.get(k, 0.0))
        )
    return _normalize(raw)


def quantile(values, q: float) -> float:
    xs = sorted(values)
    if not xs:
        return 0.0
    if q <= 0:
        return xs[0]
    if q >= 1:
        return xs[-1]
    pos = q * (len(xs) - 1)
    lo = int(pos)
    frac = pos - lo
    if lo + 1 < len(xs):
        return xs[lo] + frac * (xs[lo + 1] - xs[lo])
    return xs[lo]


def select_kept(
    nodes, importance: dict[str, float], *,
    prune_quantile: float = 0.25, freq_floor: int = 1,
    coverage_floor: float = 0.0, total_processos: int | None = None,
) -> set[str]:
    thr = quantile(list(importance.values()), prune_quantile)
    kept: set[str] = set()
    for n in nodes:
        k = n["state_key"]
        if n.get("is_activation") or n.get("is_conclusion"):
            kept.add(k)
            continue
        coverage = (n.get("n_processos") or 0) / total_processos if total_processos else 1.0
        if (
            importance.get(k, 0.0) >= thr
            and (n.get("frequency") or 0) >= freq_floor
            and coverage >= coverage_floor
        ):
            kept.add(k)
    return kept


def contract_edges(edges, kept: set[str]) -> set[tuple[str, str]]:
    adj: dict[str, set[str]] = defaultdict(set)
    for e in edges:
        adj[e["from_key"]].add(e["to_key"])

    ideal: set[tuple[str, str]] = set()
    for src in kept:
        seen: set[str] = set()
        dq = deque(adj.get(src, ()))
        while dq:
            x = dq.popleft()
            if x in seen:
                continue
            seen.add(x)
            if x in kept:
                if x != src:
                    ideal.add((src, x))
            else:
                dq.extend(adj.get(x, ()))
    return ideal
