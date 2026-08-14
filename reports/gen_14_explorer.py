#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter
import random
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

sys.path.insert(0, str(_HERE))
from pipeline.model.classifier import get_grupo
from pipeline.model.typical_eval import MODEL_NAMES
from explorer_content import ALGORITHMS, GLOSSARY, PIPELINE_STAGES

OUT = _ROOT / "reports" / "out"
VENDOR = _HERE / "vendor" / "htm-preact-standalone.umd.js"
TYPICAL = _ROOT / "artifacts" / "typical"
CLUSTERING = _ROOT / "artifacts" / "clustering"

COMBOS = [
    ("raw", "hdbscan", "exp-raw", "hdbscan"),
    ("raw", "kmeans", "exp-raw", "kmeans-k=hdbscan"),
    ("raw", "leiden", "exp-raw", "leiden-res=1.0"),
    ("raw", "consensus", "exp-raw", "consensus"),
    ("raw", "kmeans", "exp-raw-kelbow", "kmeans-k=elbow"),
    ("raw", "kmeans", "exp-raw-ksil", "kmeans-k=silhouette"),
    ("raw", "leiden", "exp-raw-lres", "leiden-res=swept"),
    ("raw", "hdbscan", "exp-raw-hcoarse", "hdbscan-coarse"),
    ("anon", "hdbscan", "exp-anon", "hdbscan"),
    ("anon", "kmeans", "exp-anon", "kmeans-k=hdbscan"),
    ("anon", "leiden", "exp-anon", "leiden-res=1.0"),
    ("anon", "consensus", "exp-anon", "consensus"),
    ("anon", "kmeans", "exp-anon-kelbow", "kmeans-k=elbow"),
    ("anon", "kmeans", "exp-anon-ksil", "kmeans-k=silhouette"),
    ("anon", "leiden", "exp-anon-lres", "leiden-res=swept"),
    ("anon", "hdbscan", "exp-anon-hcoarse", "hdbscan-coarse"),
]
MODELS = list(MODEL_NAMES)
METRICS = ["top1", "top3", "suffix_dl", "suffix_dl_c", "suffix_length_ratio",
           "flow_validity_step", "flow_validity_trace",
           "typical_path_distance", "typical_path_distance_proc"]
NAMED_RUN, NAMED_ALGO = "exp-anon", "hdbscan"

_LANE_GROUP = {"markov": "classico", "dfg": "classico",
               "gru": "neural", "lstm": "neural", "transformer": "neural", "gnn": "neural"}


def timelines_for_entry(entry: dict, real, comum, enc) -> list[dict]:
    out = []
    if real:
        out.append({"label": "Real", "kind": "observado", "model": None, "seq": enc(real)})
    if comum:
        out.append({"label": "Comum", "kind": "observado", "model": None, "seq": enc(comum)})
    for m in MODELS:
        md = (entry.get("models") or {}).get(m) or {}
        tr = md.get("trace")
        if tr:
            out.append({"label": m, "kind": _LANE_GROUP[m], "model": m, "seq": enc(tr)})
    return out


def _load(run: str, algo: str) -> dict | None:
    p = TYPICAL / run / algo / "unit" / "metrics.json"
    return json.loads(p.read_text()) if p.is_file() else None


def _clustering(run: str, algo: str) -> dict | None:
    p = CLUSTERING / run / algo / "metrics.json"
    return json.loads(p.read_text()) if p.is_file() else None


def _names(run: str, algo: str) -> dict:
    p = CLUSTERING / run / algo / "names.json"
    if not p.is_file():
        return {}
    return json.loads(p.read_text()).get("names") or {}


def _keywords_by_processo(parsed_dir="parsed_documents") -> dict:
    side = Path("artifacts/cache/keywords_by_processo.json")
    if side.is_file():
        try:
            return {k: list(v) for k, v in json.loads(side.read_text(encoding="utf-8")).items() if v}
        except Exception:
            pass
    out: dict[str, tuple] = {}
    for meta_path in Path(parsed_dir).glob("*/metadata.json"):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        pf = (meta.get("protocolo") or "").replace("_", "/")
        num = meta.get("documento_numero") or ""
        kws = meta.get("keywords") or []
        if not pf or not num or not kws:
            continue
        prev = out.get(pf)
        if prev is None or num < prev[0]:
            out[pf] = (num, list(kws))
    return {pf: k for pf, (_, k) in out.items()}


def _cluster_members(run: str, algo: str) -> dict:
    p = CLUSTERING / run / algo / "labels.json"
    if not p.is_file():
        return {}
    out: dict[str, list[str]] = {}
    for pf, lab in (json.loads(p.read_text()).get("labels") or {}).items():
        key = str(lab.get("macro") if isinstance(lab, dict) else lab)
        if key in ("-1", "None", ""):
            continue
        out.setdefault(key.split("|")[-1], []).append(pf)
    for v in out.values():
        v.sort()
    return out


def _catalog(run: str, algo: str) -> dict:
    p = CLUSTERING / run / algo / "cluster_catalog.json"
    if not p.is_file():
        return {}
    return json.loads(p.read_text()).get("catalog") or {}


def _boot_ci(clusters: dict, model: str, key: str, n: int = 2000, seed: int = 42):
    rng = random.Random(seed)
    items = list(clusters.values())
    if not items:
        return None, None
    ests = []
    for _ in range(n):
        num = den = 0.0
        for _ in range(len(items)):
            c = items[rng.randrange(len(items))]
            m = c["models"].get(model, {})
            if m.get(key) is None or "skipped" in m:
                continue
            num += c["n_traces"] * m[key]
            den += c["n_traces"]
        if den:
            ests.append(num / den)
    if not ests:
        return None, None
    ests.sort()
    return round(ests[int(0.025 * len(ests))], 4), round(ests[int(0.975 * len(ests))], 4)


def _size_buckets(clusters: dict) -> list[dict]:
    buckets = [(30, 60), (60, 120), (120, 300), (300, 10 ** 9)]
    total = sum(c["n_traces"] for c in clusters.values())
    out = []
    for lo, hi in buckets:
        g = [c for c in clusters.values() if lo <= c["n_traces"] < hi]
        if not g:
            continue
        w = sum(c["n_traces"] for c in g)
        tests = sorted(c["n_test"] for c in g)
        row = {
            "label": f"{lo}–{hi}" if hi < 10 ** 9 else f"{lo}+",
            "n_clusters": len(g), "pct_corpus": round(100 * w / total, 1),
            "median_test": tests[len(tests) // 2],
        }
        for model in ("markov", "gru"):
            row[model] = round(sum(c["n_traces"] * c["models"][model]["top1"] for c in g) / w, 3)
        row["gru_minus_markov"] = round(row["gru"] - row["markov"], 3)
        out.append(row)
    return out


def build_payload() -> dict:
    def _keep_models(tm: dict) -> dict:
        return {m: tm["models"][m] for m in MODELS
                if tm["models"].get(m) and "skipped" not in tm["models"][m]}

    def _keep_full(tm: dict) -> dict:
        return {"models": _keep_models(tm)}

    vocab: dict[str, int] = {}

    def _enc(states):
        return [vocab.setdefault(s, len(vocab)) for s in states]

    combos = []
    for arm, algo, run, combo_label in COMBOS:
        tj = _load(run, algo)
        if not tj:
            continue
        cat_by_label = {k.split("|")[-1]: v for k, v in _catalog(run, algo).items()}
        names_by_label = {k.split("|")[-1]: v for k, v in _names(run, algo).items()}
        members_by_label = _cluster_members(run, algo)
        kw_by_pf = _keywords_by_processo()
        rows = []
        items = sorted(tj["clusters"].items(), key=lambda kv: -kv[1]["n_traces"])
        for rank, (cid, tm) in enumerate(items, 1):
            label = str(cid).split("|")[-1]
            ci = cat_by_label.get(label, {})
            nm = names_by_label.get(label, {})
            members = members_by_label.get(label) or list(tm.get("test_protocolos") or [])
            sample = members[:3]
            kw_counts = Counter()
            for _pf in members:
                for _k in kw_by_pf.get(_pf) or []:
                    kw_counts[_k] += 1
            top_kw = [{"k": k, "n": n} for k, n in kw_counts.most_common(12)]
            sample_kw = [{"pf": _pf, "kw": (kw_by_pf.get(_pf) or [])[:6]} for _pf in sample]
            rows.append({
                "rank": rank, "id": cid, "label": label,
                "nome": nm.get("nome") or f"cluster {label}",
                "descricao": nm.get("descricao", ""),
                "marcadores": (nm.get("marcadores") or [])[:8],
                "sample_protocolos": sample, "n_members": len(members),
                "top_keywords": top_kw, "sample_keywords": sample_kw,
                "n": ci.get("n", tm["n_traces"]), "concl": ci.get("concl"),
                "micro": ci.get("micro", 0), "tipos": ci.get("tipos", []),
                "eval": {"n_traces": tm["n_traces"], "n_test": tm["n_test"],
                         "edge_coverage": tm.get("edge_coverage"),
                         "models": {m: {k: v for k, v in md.items() if k != "trace"}
                                    for m, md in _keep_models(tm).items()}},
                "timelines": timelines_for_entry(_keep_full(tm), tm.get("real"), tm.get("comum"), _enc),
            })
        combos.append({"key": f"{arm}·{combo_label}", "arm": arm, "algo": combo_label, "run": run,
                       "n_clusters": len(rows), "clusters": rows})

    per_cluster = (_load(NAMED_RUN, NAMED_ALGO) or {"clusters": {}})["clusters"]
    n_macro = len(_catalog(NAMED_RUN, NAMED_ALGO))

    matrix = []
    for arm, algo, run, label in COMBOS:
        tj = _load(run, algo)
        cj = _clustering(run, algo)
        if not tj:
            continue
        agg = tj["aggregate"]["models"]
        cell = {"arm": arm, "algo": label, "run": run,
                "n_clusters_eval": len(tj["clusters"]),
                "weighted": {m: agg[m].get("weighted", {}) for m in agg},
                "macro": {m: agg[m].get("macro", {}) for m in agg}}
        if cj:
            ex = cj.get("extrinsic") or {}
            same_space = cj.get("space", "umap50-cosine") == "umap50-cosine"
            cell["clustering"] = {
                "n_clusters": cj.get("n_clusters"),
                "dbcv": cj.get("dbcv") if same_space else None,
                "silhouette": cj.get("silhouette") if same_space else None,
                "purity": ex.get("purity"), "nmi": ex.get("nmi"), "ari": ex.get("ari"),
            }
        cell["ci_top1"] = {
            m: dict(zip(("lo", "hi"), _boot_ci(tj["clusters"], m, "top1")))
            for m in ("markov", "gru")
        }
        matrix.append(cell)

    size = _size_buckets(per_cluster) if per_cluster else []
    cm = _clustering(NAMED_RUN, NAMED_ALGO) or {}
    ex = cm.get("extrinsic") or {}

    return {
        "meta": {
            "named_run": NAMED_RUN, "named_algo": NAMED_ALGO,
            "n_macro": n_macro, "n_evaluated": len(per_cluster),
            "dbcv": cm.get("dbcv"), "n_clusters": cm.get("n_clusters"),
            "purity": ex.get("purity"), "nmi": ex.get("nmi"), "ari": ex.get("ari"),
            "caveat": cm.get("meta", {}).get("caveat", ""),
        },
        "combos": combos, "matrix": matrix, "size_buckets": size,
        "models": MODELS, "metrics": METRICS,
        "glossary": GLOSSARY, "pipeline": PIPELINE_STAGES, "algorithms": ALGORITHMS,
        "states": list(vocab), "grupos": [get_grupo(s.split("@", 1)[0]) for s in vocab],
    }


def render_html(payload: dict) -> str:
    vendor = VENDOR.read_text(encoding="utf-8")
    app = (_HERE / "explorer_app.js").read_text(encoding="utf-8")
    return (_PAGE.replace("__STYLE__", _STYLE).replace("__VENDOR__", vendor)
            .replace("__APP__", app)
            .replace("__PAYLOAD__", json.dumps(payload, ensure_ascii=False)))


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--payload", default=None, help="render from a payload JSON file (skips Neo4j)")
    ap.add_argument("--out", default=None, help="output HTML path (default reports/out/explorer.html)")
    args, _ = ap.parse_known_args()
    payload = json.loads(Path(args.payload).read_text(encoding="utf-8")) if args.payload else build_payload()
    html = render_html(payload)
    dest = Path(args.out) if args.out else OUT / "explorer.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(html, encoding="utf-8")
    ncl = sum(c["n_clusters"] for c in payload["combos"])
    print(f"wrote {dest} ({len(payload['combos'])} combos, {ncl} cluster rows)")


_STYLE = """
:root{--bg:#f6f7f9;--card:#fff;--bd:#e5e7eb;--ink:#1f2937;--mut:#6b7280;
 --accent:#4C72B0;--good:#55A868;--hot:#C44E52;--warn:#CC8963;--chip:#eef1f5;
 --abertura:#55A868;--conclusao:#C44E52;--tramitacao:#4C72B0;--assinatura:#8172B3;
 --criacao:#DD8452;--comunicacao:#DA8BC3;--blocos:#937860;--edicao:#8C8C8C;
 --automatico:#CCB974;--outros:#B0B7C3}
@media(prefers-color-scheme:dark){:root{--bg:#0f1115;--card:#181b21;--bd:#2a2f3a;
 --ink:#e6e8ec;--mut:#9aa3b2;--chip:#232833}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
 font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}
a{color:var(--accent)}
.wrap{max-width:1280px;margin:0 auto;padding:20px}
h1{font-size:21px;margin:0 0 2px}.sub{color:var(--mut);margin:0 0 16px;font-size:13px}
.stats{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin-bottom:18px}
.stat{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:12px}
.stat b{display:block;font-size:22px;line-height:1.1}.stat span{color:var(--mut);font-size:11px}
.tabs{display:flex;gap:6px;margin-bottom:16px;border-bottom:1px solid var(--bd)}
.tab{padding:8px 14px;cursor:pointer;border:none;background:none;color:var(--mut);
 font:inherit;font-weight:600;border-bottom:2px solid transparent;margin-bottom:-1px}
.tab.on{color:var(--accent);border-bottom-color:var(--accent)}
.split{display:grid;grid-template-columns:340px 1fr;gap:16px}
@media(max-width:820px){.split{grid-template-columns:1fr}.stats{grid-template-columns:repeat(3,1fr)}}
.panel{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:14px}
.search{width:100%;padding:8px 10px;border:1px solid var(--bd);border-radius:8px;
 background:var(--bg);color:var(--ink);font:inherit;margin-bottom:8px}
.sortbtns{display:flex;gap:4px;margin-bottom:8px;flex-wrap:wrap}
.sortbtns button{font:11px inherit;padding:3px 8px;border:1px solid var(--bd);
 border-radius:6px;background:var(--bg);color:var(--mut);cursor:pointer}
.sortbtns button.on{background:var(--accent);color:#fff;border-color:var(--accent)}
.clist{list-style:none;margin:0;padding:0;max-height:70vh;overflow:auto}
.crow{padding:8px 10px;border-radius:8px;cursor:pointer;display:flex;gap:8px;align-items:baseline}
.crow:hover{background:var(--chip)}.crow.on{background:var(--accent);color:#fff}
.crow .cn{font-weight:600;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.crow .cs{font-size:11px;opacity:.75}
.bigname{font-size:17px;font-weight:700;margin:0 0 2px}
.muted{color:var(--mut);font-size:12px}
.chips{display:flex;gap:5px;flex-wrap:wrap;margin:8px 0}
.chip{background:var(--chip);border-radius:20px;padding:2px 9px;font-size:11px}
.kv{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:14px 0}
.kv .b{font-size:19px;font-weight:700}.kv small{color:var(--mut)}
.mbar{display:grid;grid-template-columns:88px 1fr 46px;gap:8px;align-items:center;margin:5px 0}
.mbar .track{height:16px;background:var(--chip);border-radius:5px;overflow:hidden}
.mbar .fill{height:100%;background:var(--accent)}
.mbar.best .fill{background:var(--good)}
.mbar .val{font-variant-numeric:tabular-nums;text-align:right;font-size:12px}
.mname{font-size:12px;font-weight:600}
table{border-collapse:collapse;width:100%;font-size:12.5px}
th,td{padding:6px 8px;text-align:right;border-bottom:1px solid var(--bd)}
th:first-child,td:first-child{text-align:left}
thead th{color:var(--mut);font-weight:600}
tr.anon td{background:color-mix(in srgb,var(--good) 8%,transparent)}
.ci{color:var(--mut);font-size:11px}
.best td{font-weight:700}
.note{background:color-mix(in srgb,var(--warn) 12%,transparent);border:1px solid var(--bd);
 border-radius:8px;padding:10px 12px;font-size:12.5px;margin:12px 0;line-height:1.55}
.togglebar{display:flex;gap:6px;margin:6px 0 14px}
.togglebar button{padding:5px 12px;border:1px solid var(--bd);border-radius:7px;
 background:var(--bg);color:var(--mut);font:inherit;cursor:pointer}
.togglebar button.on{background:var(--accent);color:#fff;border-color:var(--accent)}
.empty{color:var(--mut);padding:40px;text-align:center}
.gloss{margin:10px 0;font-size:12px}
.gloss summary{cursor:pointer;color:var(--accent);font-weight:600}
.gloss dl{margin:8px 0 0}.gloss dt{font-weight:700;margin-top:6px}
.gloss dd{margin:0 0 4px;color:var(--mut)}
.tgroup{margin:10px 0}.tcap{font-size:12px;font-weight:700;color:var(--mut);margin:6px 0}
.swim{border:1px solid var(--bd);border-radius:8px;margin:6px 0;overflow:hidden;background:var(--card)}
.swim-lbl{padding:4px 10px;font-size:12px;font-weight:600;border-bottom:1px solid var(--bd)}
.swim svg{width:100%;height:auto;display:block;background:var(--card)}
.edge{fill:none}.edge.spine{stroke:#16314e;stroke-width:3.4}
.edge.norm{stroke:#c2cad6;stroke-width:1.5}.edge.back{stroke-dasharray:5 4}
.lane-label{font-size:12px;font-weight:700;fill:var(--ink)}
.phase-band{opacity:.5}.phase-label{font-size:11px;fill:#9aa3af;font-weight:700;letter-spacing:.08em}
.node circle{stroke:#5b6675;stroke-width:1}.node.spine circle{stroke:#111827;stroke-width:2.2}
.node text{font-size:10px;fill:#374151}
.ring{fill:none;stroke-width:2.4}.ring.start{stroke:var(--abertura)}.ring.end{stroke:var(--conclusao)}
.pipe{margin:0;padding-left:20px}.pipe li{margin:4px 0}
.agroup{margin:14px 0}.agroup h4{margin:10px 0 6px;font-size:13px}
.acard{border:1px solid var(--bd);border-radius:8px;padding:10px 12px;margin:6px 0;background:var(--bg)}
.aname{font-weight:700;margin-bottom:4px}
.alab{display:inline-block;min-width:78px;color:var(--mut);font-size:11px;text-transform:uppercase}
"""

_PAGE = """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Explorador de clusters &amp; experimentos</title>
<style>__STYLE__</style></head>
<body><div id="app"></div>
<script id="payload" type="application/json">__PAYLOAD__</script>
<script>__VENDOR__</script>
<script>__APP__</script>
</body></html>"""


if __name__ == "__main__":
    main()
