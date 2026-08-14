import sys
from pathlib import Path

import numpy as np
from dotenv import dotenv_values
from neo4j import GraphDatabase

ROOT = Path(__file__).resolve().parent.parent.parent
env = dotenv_values(f"{ROOT}/.env")
d = GraphDatabase.driver(env["NEO4J_URI"], auth=(env["NEO4J_USER"], env["NEO4J_PASSWORD"]))

CY = """
MATCH (p:Processo) WHERE p.cluster_features IS NOT NULL
OPTIONAL MATCH (p)-[:CATEGORIZADO_COMO]->(c:CategoriaProcesso {nivel:'macro'})
RETURN p.cluster_features AS f, c.id AS cid, c.nome AS cname
"""
feats, cids, cnames = [], [], []
with d.session() as s:
    for r in s.run(CY):
        feats.append(r["f"]); cids.append(r["cid"]); cnames.append(r["cname"])
d.close()
X = np.asarray(feats, dtype=np.float32)
print(f"loaded X={X.shape}, categorized={sum(1 for c in cids if c)}/{len(cids)}", file=sys.stderr)

import umap

reducer = umap.UMAP(n_components=2, random_state=42, n_neighbors=15, min_dist=0.1, metric="euclidean")
emb = reducer.fit_transform(X)
print(f"umap 2d done: {emb.shape}", file=sys.stderr)

from collections import Counter

sizes = Counter(c for c in cids if c)
top = [cid for cid, _ in sizes.most_common(8)]
name_by_id = {}
for cid, cn in zip(cids, cnames):
    if cid and cid not in name_by_id and cn:
        name_by_id[cid] = cn

def short(name, nwords=4, maxlen=34):
    w = name.split()
    s = " ".join(w[:nwords])
    return (s[:maxlen] + "…") if len(s) > maxlen else s

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({"font.size": 9, "font.family": "DejaVu Serif"})
fig, ax = plt.subplots(figsize=(7.0, 5.2), dpi=300)

cids_arr = np.array([c if c in top else None for c in cids], dtype=object)
bg = np.array([c not in top for c in cids])
ax.scatter(emb[bg,0], emb[bg,1], s=2.0, c="#d9d9d9", alpha=0.45, linewidths=0, rasterized=True, label=None)

palette = plt.get_cmap("tab10").colors
for i, cid in enumerate(top):
    m = np.array([c == cid for c in cids])
    ax.scatter(emb[m,0], emb[m,1], s=5.0, c=[palette[i % 10]], alpha=0.8,
               linewidths=0, rasterized=True, label=f"{short(name_by_id.get(cid, cid))} (n={sizes[cid]})")

ax.set_xlabel("UMAP-1"); ax.set_ylabel("UMAP-2")
ax.set_xticks([]); ax.set_yticks([])
for sp in ax.spines.values(): sp.set_color("#888888")
leg = ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=False,
                fontsize=7.2, title="Largest process types", title_fontsize=7.8,
                handletextpad=0.4, labelspacing=0.5)
ax.set_title("")
fig.tight_layout()
for ext in ("png", "pdf"):
    out = f"{ROOT}/article/figures/clusters-umap.{ext}"
    fig.savefig(out, bbox_inches="tight", dpi=300)
    print(f"wrote {out}", file=sys.stderr)
