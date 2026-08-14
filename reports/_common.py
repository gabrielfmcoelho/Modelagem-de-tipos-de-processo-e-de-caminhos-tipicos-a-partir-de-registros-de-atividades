
from __future__ import annotations

import json
import os
import re
import sys
from contextlib import contextmanager
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_ENV_BIN = os.path.dirname(sys.executable)
if _ENV_BIN not in os.environ.get("PATH", "").split(os.pathsep):
    os.environ["PATH"] = _ENV_BIN + os.pathsep + os.environ.get("PATH", "")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from pipeline.core.config import Settings
from pipeline.core.neo4j_driver import build_driver

OUT = Path(__file__).resolve().parent / "out"
CHARTS = OUT / "charts"

BLUE, ORANGE, GREEN, RED, PURPLE = "#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3"

GRUPO_COLORS = {
    "abertura": GREEN, "conclusao": RED, "tramitacao": BLUE, "assinatura": PURPLE,
    "criacao": ORANGE, "comunicacao": "#DA8BC3", "blocos": "#937860",
    "edicao": "#8C8C8C", "automatico": "#CCB974", "outros": "#B0B7C3",
}

_GENERIC_LABEL_TOKENS = {"PROCESSO", "UNIDADE"}


def _short_label(tipo: str | None, maxlen: int = 14) -> str:
    if not tipo:
        return ""
    toks = [t for t in tipo.split("-") if t not in _GENERIC_LABEL_TOKENS] or [tipo]
    s = "-".join(toks)
    if len(s) <= maxlen:
        return s
    return "-".join(t[:4] for t in toks)


def ensure_dirs() -> None:
    CHARTS.mkdir(parents=True, exist_ok=True)


_settings: Settings | None = None


def settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings


def load_cluster_metrics(run_id: str = "exp-anon", algo: str = "hdbscan") -> dict:
    path = _ROOT / "artifacts" / "clustering" / run_id / algo / "metrics.json"
    if not path.exists():
        raise FileNotFoundError(
            f"cluster metrics artifact not found: {path}. Generate it with "
            f"`python -m pipeline run cluster-eval --flag run_id={run_id} --flag algos={algo} "
            f"--flag features_file=artifacts/features/{run_id}.npz "
            f"--flag labels_file=artifacts/clustering/{run_id}/{algo}/labels.json`, "
            "or re-run the processo-cluster stage with --flag run_id set."
        )
    return json.loads(path.read_text(encoding="utf-8"))


@contextmanager
def neo4j_session():
    driver = build_driver(settings())
    try:
        with driver.session() as session:
            yield session
    finally:
        driver.close()


@contextmanager
def trino_conn():
    from pipeline.core.trino_source import make_trino_conn
    conn = make_trino_conn(settings())
    try:
        yield conn
    finally:
        conn.close()


def scalar(session, cypher: str, **params):
    rec = session.run(cypher, **params).single()
    return rec[0] if rec else None


def rows(session, cypher: str, **params) -> list[dict]:
    return [dict(r) for r in session.run(cypher, **params)]


def slugify(s: str, maxlen: int = 48) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")
    return (s or "x")[:maxlen]


def pct(part: float, whole: float) -> str:
    return f"{(100.0 * part / whole) if whole else 0.0:.1f}%"


def fmt(n) -> str:
    return f"{n:,}" if isinstance(n, int) else str(n)


def md_table(headers: list, rows_: list[list]) -> str:
    out = ["| " + " | ".join(str(h) for h in headers) + " |",
           "|" + "|".join(" --- " for _ in headers) + "|"]
    for r in rows_:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def _save(fig, name: str) -> str:
    ensure_dirs()
    fig.savefig(CHARTS / name, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return f"charts/{name}"


def barh(labels: list[str], values: list[float], title: str, name: str, *,
         xlabel: str = "count", color: str = BLUE) -> str:
    labels, values = labels[::-1], values[::-1]
    fig, ax = plt.subplots(figsize=(8, max(2.4, 0.42 * len(labels) + 1)))
    ax.barh(labels, values, color=color)
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    for i, v in enumerate(values):
        ax.text(v, i, f" {fmt(int(v)) if float(v).is_integer() else round(v,2)}",
                va="center", fontsize=8)
    return _save(fig, name)


def bars(labels: list[str], values: list[float], title: str, name: str, *,
         ylabel: str = "count", color: str = BLUE, rotate: int = 45) -> str:
    fig, ax = plt.subplots(figsize=(max(6, 0.5 * len(labels) + 2), 4))
    ax.bar(labels, values, color=color)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    plt.setp(ax.get_xticklabels(), rotation=rotate, ha="right", fontsize=8)
    return _save(fig, name)


def grouped_bars(group_labels: list[str], series: dict, title: str, name: str, *,
                 ylabel: str = "", ymax: float = 1.0) -> str:
    names = list(series)
    k = max(1, len(names))
    w = 0.8 / k
    x = list(range(len(group_labels)))
    palette = [BLUE, ORANGE, GREEN, RED, PURPLE, "#937860", "#DA8BC3"]
    fig, ax = plt.subplots(figsize=(max(7, 1.8 * len(group_labels) + 2), 4.6))
    for i, nm in enumerate(names):
        xs = [xi + i * w for xi in x]
        ax.bar(xs, series[nm], w, label=nm, color=palette[i % len(palette)])
        for xi, v in zip(xs, series[nm]):
            ax.text(xi, v + 0.012, f"{v:.2f}", ha="center", va="bottom", fontsize=7)
    ax.set_xticks([xi + w * (k - 1) / 2 for xi in x])
    ax.set_xticklabels(group_labels, fontsize=8)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.set_ylim(0, ymax)
    ax.legend(fontsize=8, ncol=min(k, 5), loc="upper center", bbox_to_anchor=(0.5, -0.07))
    return _save(fig, name)


def hist(values: list[float], title: str, name: str, *, bins: int = 40,
         xlabel: str = "", ylabel: str = "processos", color: str = GREEN,
         logy: bool = False) -> str:
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(values, bins=bins, color=color)
    if logy:
        ax.set_yscale("log")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    return _save(fig, name)


def pie(labels: list[str], values: list[float], title: str, name: str) -> str:
    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90,
           colors=[BLUE, ORANGE, GREEN, RED, PURPLE, "#937860", "#DA8BC3"])
    ax.set_title(title)
    return _save(fig, name)


def dfg_chart(transitions: list[tuple], seqpos: dict[str, float], title: str, name: str,
              *, top: int = 14) -> str | None:
    import graphviz

    edges = [(f, t, int(c)) for f, t, c in transitions[:top] if f and t]
    if not edges:
        return None
    wmax = max(c for _, _, c in edges) or 1

    g = graphviz.Digraph(format="png")
    g.attr(rankdir="LR", bgcolor="white", labelloc="t", fontsize="14",
           fontname="Helvetica", label=title, nodesep="0.25", ranksep="0.6")
    g.attr("node", shape="box", style="rounded,filled", fontname="Helvetica",
           fontsize="10", margin="0.12,0.06")
    g.attr("edge", fontname="Helvetica", fontsize="8", color="#777777")

    nodes: set[str] = set()
    for f, t, _ in edges:
        nodes.add(f)
        nodes.add(t)
    for n in sorted(nodes):
        if n.startswith("GERACAO") or n.startswith("REABERTURA"):
            fill, font = GREEN, "white"
        elif n.startswith("CONCLUSAO"):
            fill, font = RED, "white"
        else:
            fill, font = "#DCE3F0", "black"
        g.node(n, label=n.replace("-", "-\\n", 2), fillcolor=fill, fontcolor=font)

    for f, t, c in edges:
        pw = 1.0 + 5.0 * c / wmax
        style = "dashed" if f == t else "solid"
        g.edge(f, t, label=f" {c:,}", penwidth=f"{pw:.1f}", style=style)

    ensure_dirs()
    base = name[:-4] if name.endswith(".png") else name
    out = g.render(filename=base, directory=str(CHARTS), cleanup=True)
    return f"charts/{Path(out).name}"


def swimlane_chart(swimlane: dict, title: str, name: str, *, max_label: int = 22) -> str | None:
    from collections import defaultdict

    from matplotlib.patches import FancyArrowPatch, Rectangle

    lanes = swimlane.get("lanes") or []
    nodes = swimlane.get("nodes") or []
    edges = swimlane.get("edges") or []
    if not nodes:
        return None

    lane_y = {lane["unidade"]: -lane["order"] for lane in lanes}
    n_lanes = max(1, len(lanes))
    max_x = max((n["x"] for n in nodes), default=1)

    cells: dict[tuple, list] = defaultdict(list)
    for n in nodes:
        cells[(n["lane"], n["x"])].append(n)
    pos: dict[str, tuple[float, float]] = {}
    for (lane, x), group in cells.items():
        k = len(group)
        for i, n in enumerate(sorted(group, key=lambda z: -(z.get("coverage") or 0))):
            xoff = (i - (k - 1) / 2) * (0.42 if k > 1 else 0.0)
            pos[n["id"]] = (x + xoff, lane_y.get(lane, 0))

    fig, ax = plt.subplots(
        figsize=(max(9, 2.4 * (max_x + 1)), max(3, 1.25 * n_lanes + 1)))

    for lane in lanes:
        y = -lane["order"]
        xs, xe = lane.get("x_start", 0), lane.get("x_end", max_x)
        ax.add_patch(Rectangle(
            (xs - 0.45, y - 0.42), (xe - xs) + 0.9, 0.84, zorder=0,
            facecolor="#ECF1F8" if lane["order"] % 2 == 0 else "#DEE7F3", edgecolor="none"))
        ax.text(-0.7, y, lane["unidade"], va="center", ha="right",
                fontsize=8, fontweight="bold")

    for e in edges:
        if e["from"] not in pos or e["to"] not in pos:
            continue
        x0, y0 = pos[e["from"]]
        x1, y1 = pos[e["to"]]
        spine = bool(e.get("on_spine"))
        handoff = e.get("kind") == "handoff"
        rad = 0.22 if (handoff and y1 != y0) else 0.0
        ax.add_patch(FancyArrowPatch(
            (x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=12,
            connectionstyle=f"arc3,rad={rad}",
            lw=2.6 if spine else 1.1,
            color="#2B2B2B" if spine else "#9AA5B1",
            linestyle="dashed" if e.get("back_edge") else "solid", zorder=2,
        ))
        if handoff and e.get("mean_interval_h"):
            ax.text((x0 + x1) / 2, (y0 + y1) / 2, f"{e['mean_interval_h']:.0f}h",
                    fontsize=6, color="#556", ha="center", va="center", zorder=2)

    for n in nodes:
        x, y = pos[n["id"]]
        size = 120 + 900 * (n.get("coverage") or 0)
        ax.scatter([x], [y], s=size, zorder=3,
                   color=GRUPO_COLORS.get(n.get("grupo"), "#B0B7C3"),
                   edgecolors="#111" if n.get("on_spine") else "#6B7280",
                   linewidths=2.2 if n.get("on_spine") else 0.8)
        if n.get("is_start"):
            ax.scatter([x], [y], s=size + 280, facecolors="none",
                       edgecolors=GREEN, linewidths=2.2, zorder=3)
        if n.get("is_end"):
            ax.scatter([x], [y], s=size + 280, facecolors="none",
                       edgecolors=RED, linewidths=2.2, zorder=3)
        ax.text(x + 0.10, y + 0.20, _short_label(n.get("label"), max_label),
                fontsize=7, ha="left", va="bottom", rotation=22,
                rotation_mode="anchor")

    ax.set_xlim(-2.2, max_x + 1.6)
    ax.set_ylim(-(n_lanes - 1) - 0.9, 1.5)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(title, pad=16)
    ax.set_xlabel("start → conclusão  (ordem do fluxo; raias = unidades)")
    for spine_name in ("top", "right", "left", "bottom"):
        ax.spines[spine_name].set_visible(False)
    return _save(fig, name)


class Doc:

    def __init__(self, title: str, intro: str = ""):
        self.parts: list[str] = [f"# {title}\n"]
        if intro:
            self.parts.append(intro + "\n")

    def add(self, md: str) -> Doc:
        self.parts.append(md)
        return self

    def h2(self, t: str) -> Doc:
        return self.add(f"\n## {t}\n")

    def h3(self, t: str) -> Doc:
        return self.add(f"\n### {t}\n")

    def p(self, t: str) -> Doc:
        return self.add(t + "\n")

    def table(self, headers: list, rows_: list[list]) -> Doc:
        return self.add(md_table(headers, rows_) + "\n")

    def img(self, rel: str, alt: str = "") -> Doc:
        return self.add(f"\n![{alt}]({rel})\n")

    def write(self, path: str) -> Path:
        OUT.mkdir(parents=True, exist_ok=True)
        dest = OUT / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("\n".join(self.parts) + "\n", encoding="utf-8")
        return dest
