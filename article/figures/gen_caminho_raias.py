import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parent.parent.parent
METRICS = ROOT / "artifacts/typical/exp-raw-ksil/kmeans/itinerary/metrics.json"
OUT = ROOT / "article/figures/caminho-raias"
CLUSTER = "5"

TASK_FC, TASK_EC = "#eef2fb", "#4C72B0"
REF_FC, REF_EC = "#f6f2ea", "#a08048"
LANE_H, BW, BH, STEP = 0.74, 1.18, 0.52, 1.42
LABEL_W, PANEL_GAP = 2.05, 0.8

cl = json.loads(METRICS.read_text())["clusters"][CLUSTER]
gru = cl["models"]["gru"]
visits = gru["typical_itinerary"]
medoid = cl["path_reference"]["medoid_itinerary"]
n_sampled = cl["path_reference"]["n_test_sampled"]

gru_units = [v["unidade"] for v in visits]
support = [v["n_matching"] for v in visits]

lanes = []
for u in gru_units + medoid:
    if u not in lanes:
        lanes.append(u)

X0 = -LABEL_W
BOX_X0 = 0.62
n_steps = max(len(gru_units), len(medoid))
X1 = BOX_X0 + (n_steps - 1) * STEP + BW / 2 + 0.35
PANEL_H = len(lanes) * LANE_H
TOP = PANEL_H + PANEL_GAP + PANEL_H + 0.55

fig, ax = plt.subplots()
ax.set_xlim(X0 - 0.15, X1 + 0.15)
ax.set_ylim(-0.5, TOP)
ax.axis("off")


def lane_y(panel, unidade):
    base = TOP - 0.55 if panel == 0 else PANEL_H
    return base - (lanes.index(unidade) + 0.5) * LANE_H


def box_x(pos):
    return BOX_X0 + pos * STEP


def draw_panel(panel, units, labels, title, fc, ec):
    base = TOP - 0.55 if panel == 0 else PANEL_H
    ax.text(X0, base + 0.24, title, ha="left", va="bottom", fontsize=7.4,
            fontweight="bold", color="#2b3a55", zorder=1)
    for i, unidade in enumerate(lanes):
        y = base - (i + 1) * LANE_H
        ax.add_patch(plt.Rectangle((X0, y), X1 - X0, LANE_H, zorder=0,
                                   facecolor="#f4f4f4" if i % 2 == 0 else "#fbfbfb",
                                   edgecolor="#cccccc", linewidth=0.8))
        ax.add_patch(plt.Rectangle((X0, y), LABEL_W, LANE_H, facecolor="#e9eef7",
                                   edgecolor="#cccccc", linewidth=0.8, zorder=0.5))
        ax.text(X0 + LABEL_W / 2, y + LANE_H / 2, unidade.replace("SEAD-PI/", ""),
                ha="center", va="center", fontsize=6.0, fontweight="bold",
                color="#2b3a55", zorder=1)

    for pos, unidade in enumerate(units):
        x, y = box_x(pos), lane_y(panel, unidade)
        ax.add_patch(FancyBboxPatch((x - BW / 2, y - BH / 2), BW, BH, zorder=3,
                                    boxstyle="round,pad=0.012,rounding_size=0.06",
                                    facecolor=fc, edgecolor=ec, linewidth=1.2))
        ax.text(x, y, labels[pos], ha="center", va="center", fontsize=6.3,
                color="#1f2937", zorder=4, linespacing=1.25)

    for pos in range(len(units) - 1):
        xa, ya = box_x(pos), lane_y(panel, units[pos])
        xb, yb = box_x(pos + 1), lane_y(panel, units[pos + 1])
        ax.add_patch(FancyArrowPatch((xa + BW / 2, ya), (xb - BW / 2, yb), zorder=2,
                                     arrowstyle="-|>", mutation_scale=11,
                                     color="#333333", linewidth=1.1,
                                     shrinkA=0, shrinkB=0))


draw_panel(0, gru_units, [f"{i + 1}\n{s}/{n_sampled}" for i, s in enumerate(support)],
           "Caminho típico gerado (GRU)", TASK_FC, TASK_EC)
draw_panel(1, medoid, [str(i + 1) for i in range(len(medoid))],
           "Processo real de referência (medoide do grupo)", REF_FC, REF_EC)

assert gru_units == [v["unidade"] for v in gru["typical_itinerary"]]
assert medoid == cl["path_reference"]["medoid_itinerary"]
assert len(support) == len(gru_units) and all(0 <= s <= n_sampled for s in support)
assert set(gru_units) | set(medoid) == set(lanes)

fig.set_size_inches(8.6, 8.6 * (TOP + 0.5) / (X1 - X0 + 0.3))
fig.tight_layout(pad=0.3)
for ext in ("png", "pdf", "svg"):
    fig.savefig(f"{OUT}.{ext}", bbox_inches="tight", dpi=300)

print(f"grupo {CLUSTER}: {cl['n_traces']} traços avaliados, {len(lanes)} raias, "
      f"{len(gru_units)} visitas | top-1 {gru['top1']} | "
      f"rec. unidades {gru['generalization']['unit_recall']}")
