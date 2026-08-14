import json
import math
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parent.parent.parent
CENSUS = ROOT / "artifacts/stats/graph_build.json"
OUT = ROOT / "article/figures/graph-schema"

FLOW_C = "#C44E52"
DIM_C = "#9aa0a6"
NODE_FC = "#eef2fb"
NODE_EC = "#4C72B0"
HUB_FC = "#fde2e2"
HUB_EC = "#C44E52"


def _fmt(n):
    if n is None:
        return ""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}k"
    return str(n)


def _badge(ax, x, y, num):
    ax.add_patch(plt.Circle((x, y), 0.022, fc="white", ec=FLOW_C, lw=1.5, zorder=6))
    ax.text(x, y, str(num), ha="center", va="center", fontsize=7.5, color=FLOW_C,
            weight="bold", zorder=7)


def _layout(labels, hubs):
    spokes = [x for x in labels if x not in hubs]
    pos = {}
    if len(hubs) == 2:
        pos[hubs[0]] = (0.5, 0.70)
        pos[hubs[1]] = (0.5, 0.34)
    else:
        for i, h in enumerate(hubs):
            pos[h] = (0.5, 0.7 - 0.36 * i)
    n = len(spokes)
    for i, lab in enumerate(spokes):
        ang = 2 * math.pi * i / n - math.pi / 2
        pos[lab] = (0.5 + 0.42 * math.cos(ang), 0.52 + 0.44 * math.sin(ang))
    return pos


def main() -> None:
    if not CENSUS.is_file():
        raise FileNotFoundError(
            f"{CENSUS} is missing. This figure is drawn from the graph census, never from a "
            "hand-written schema: run `pipeline run graph-census` first, so every node, edge "
            "and count on it is the graph that actually exists.")
    res = json.loads(CENSUS.read_text(encoding="utf-8"))["results"]
    triples = res.get("schema_triples") or []
    if not triples:
        raise ValueError(
            f"{CENSUS} carries no schema_triples. Re-run graph-census: the figure enumerates "
            "the schema from the database rather than assuming it.")
    nodes = res["nodes_by_label"]

    degree = defaultdict(int)
    for t in triples:
        degree[t["src"]] += t["n"]
        degree[t["dst"]] += t["n"]
    labels = sorted(degree, key=lambda x: (-degree[x], x))
    hubs = labels[:2]
    pos = _layout(labels, hubs)

    fig, (ax, side) = plt.subplots(
        1, 2, figsize=(16, 9.5), gridspec_kw={"width_ratios": [2.35, 1]})
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.04, 1.06)
    ax.axis("off")
    side.axis("off")
    flow_legend = []

    pair_seen = defaultdict(int)
    for t in sorted(triples, key=lambda x: (not x["flow"], -x["n"])):
        src, rel, dst, n, flow = t["src"], t["rel"], t["dst"], t["n"], t["flow"]
        if src not in pos or dst not in pos:
            continue
        colour = FLOW_C if flow else DIM_C
        lw = 2.2 if flow else 0.9
        alpha = 0.95 if flow else 0.45
        x1, y1 = pos[src]
        x2, y2 = pos[dst]
        key = tuple(sorted((src, dst)))
        k = pair_seen[key]
        pair_seen[key] += 1
        if src == dst:
            ax.add_patch(FancyArrowPatch((x1 - 0.045, y1 + 0.030), (x1 + 0.045, y1 + 0.030),
                                         connectionstyle="arc3,rad=1.7", arrowstyle="-|>",
                                         mutation_scale=12, color=colour, lw=lw, zorder=2))
            if flow:
                flow_legend.append((len(flow_legend) + 1, src, rel, dst, n))
                _badge(ax, x1 - 0.052 + 0.052 * k, y1 + 0.092, len(flow_legend))
            continue
        rad = (0.14 + 0.11 * k) * (1 if flow else -1)
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2),
                                     connectionstyle=f"arc3,rad={rad}", arrowstyle="-|>",
                                     mutation_scale=11, color=colour, lw=lw, alpha=alpha,
                                     shrinkA=30, shrinkB=30, zorder=2 if flow else 1))
        if flow:
            mx = (x1 + x2) / 2 - (y2 - y1) * rad * 0.78
            my = (y1 + y2) / 2 + (x2 - x1) * rad * 0.78
            flow_legend.append((len(flow_legend) + 1, src, rel, dst, n))
            _badge(ax, mx, my, len(flow_legend))

    for lab, (x, y) in pos.items():
        n = nodes.get(lab)
        hub = lab in hubs
        w = max(0.13, 0.017 * len(lab))
        ax.add_patch(FancyBboxPatch((x - w / 2, y - 0.032), w, 0.064,
                                    boxstyle="round,pad=0.007",
                                    fc=HUB_FC if hub else NODE_FC,
                                    ec=HUB_EC if hub else NODE_EC,
                                    lw=2.0 if hub else 1.3, zorder=4))
        ax.text(x, y + 0.009, lab, ha="center", va="center", fontsize=9,
                weight="bold", color="#7a1f22" if hub else "#12305e", zorder=5)
        ax.text(x, y - 0.017, _fmt(n), ha="center", va="center", fontsize=7.8,
                color="#4a5568", zorder=5)

    side.set_xlim(0, 1)
    side.set_ylim(0, 1)
    side.text(0, 0.97, "Relações de fluxo", fontsize=12, weight="bold", color=FLOW_C,
              va="top")
    side.text(0, 0.925, "como o processo anda", fontsize=9, color="#4a5568", va="top",
              style="italic")
    y = 0.865
    for num, src, rel, dst, n in flow_legend:
        side.add_patch(plt.Circle((0.025, y + 0.006), 0.019, fc=FLOW_C, ec="none",
                                  transform=side.transData, zorder=3))
        side.text(0.025, y + 0.006, str(num), ha="center", va="center", fontsize=7.5,
                  color="white", weight="bold", zorder=4)
        side.text(0.065, y + 0.018, rel, fontsize=8.6, weight="bold", color="#7a1f22", va="top")
        side.text(0.065, y - 0.005, f"{src} → {dst}", fontsize=7.8, color="#4a5568", va="top")
        side.text(1.0, y + 0.010, _fmt(n), fontsize=8.4, color="#12305e", ha="right",
                  weight="bold", va="center")
        y -= 0.072
    n_dim = sum(1 for t in triples if not t["flow"])
    side.text(0, y - 0.005, f"+ {n_dim} relações de dimensão (cinza, não rotuladas):",
              fontsize=8.6, color="#4a5568", va="top", weight="bold")
    dim = sorted({t["rel"] for t in triples if not t["flow"]})
    side.text(0, y - 0.045, "\n".join("· " + d for d in dim), fontsize=7.2,
              color="#6b7280", va="top", linespacing=1.55)

    n_flow = sum(1 for t in triples if t["flow"])
    tot = res["totals"]
    proc = res["processo"]
    fig.suptitle(
        f"Esquema do grafo de eventos — {_fmt(tot['nodes'])} nós, "
        f"{_fmt(tot['relationships'])} relações, {len(triples)} tipos de aresta\n"
        f"{proc['total']} processos · {proc['concluded']} concluídos · "
        f"{proc['with_cluster_features']} com vetor de atributos",
        fontsize=12.5, weight="bold", color="#12305e", y=0.98)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "svg", "png"):
        fig.savefig(f"{OUT}.{ext}", bbox_inches="tight", dpi=200)
    plt.close(fig)
    print(f"wrote {OUT.relative_to(ROOT)}.{{pdf,svg,png}} from {len(triples)} schema triples "
          f"({n_flow} flow)")


if __name__ == "__main__":
    raise SystemExit(main())
