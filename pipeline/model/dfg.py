
from __future__ import annotations

from collections import Counter
from statistics import mean

from .classifier import TASK_GROUPS, get_grupo
from .process_state import ACTIVATION_TYPES, CONCLUSION_TYPES

GRUPO_VOCAB = sorted(TASK_GROUPS.keys())
_GRUPO_INDEX = {g: i for i, g in enumerate(GRUPO_VOCAB)}

NODE_FEATURE_NAMES = [
    "node_frequency_norm",
    "process_coverage",
    "in_degree_norm",
    "out_degree_norm",
    "mean_node_contrib",
    "mean_node_advancement",
    "mean_node_speed",
    "mean_activity_band",
    "is_activation",
    "is_conclusion",
] + [f"grupo__{g}" for g in GRUPO_VOCAB]
NODE_FEATURE_DIM = len(NODE_FEATURE_NAMES)


def node_key(
    tipo_acao: str, node_identity: str = "tipo_acao", unidade: str | None = None
) -> str:
    if node_identity == "tipo_acao_grupo":
        return f"{tipo_acao}@{get_grupo(tipo_acao)}"
    if node_identity == "tipo_acao_unidade":
        return f"{tipo_acao}@{unidade if unidade is not None else '?'}"
    return tipo_acao


def canonical_unidade(unidade: str | None) -> str:
    u = (unidade or "?").strip().rstrip("/")
    if not u or u == "?":
        return "?"
    parts = [x.strip() for x in u.split("/") if x.strip()]
    if len(parts) < 2:
        return u
    return f"{parts[0]}/{parts[-1]}"


def _lane(unidade: str | None, lane_depth: int | None) -> str:
    u = unidade or "?"
    if lane_depth and lane_depth > 0:
        return "/".join(u.split("/")[:lane_depth])
    return u


def _mean(xs, default=0.0):
    vals = [x for x in xs if x is not None]
    return round(mean(vals), 4) if vals else default


def _new_node(key, tipo, unidade_lane=None):
    return {
        "key": key, "tipo_acao": tipo, "grupo": get_grupo(tipo),
        "unidade_lane": unidade_lane,
        "freq": 0, "procs": set(),
        "contrib": [], "adv": [], "speed": [], "band": [],
    }


def build_dfg(
    activity_rows,
    edge_rows,
    *,
    total_processos: int,
    node_identity: str = "tipo_acao",
    lane_depth: int | None = None,
):
    unit_mode = node_identity == "tipo_acao_unidade"
    nodes: dict[str, dict] = {}
    for a in activity_rows:
        tipo = a.get("tipo_acao") or "OUTROS"
        lane = _lane(a.get("unidade"), lane_depth) if unit_mode else None
        k = node_key(tipo, node_identity, lane)
        n = nodes.get(k) or nodes.setdefault(k, _new_node(k, tipo, lane))
        n["freq"] += 1
        n["procs"].add(a.get("protocolo"))
        n["contrib"].append(a.get("node_contrib_score"))
        n["adv"].append(a.get("node_advancement_score"))
        n["speed"].append(a.get("node_speed_score"))
        if a.get("activity_band_score") is not None:
            n["band"].append(a.get("activity_band_score"))

    edges: dict[tuple[str, str], dict] = {}
    for e in edge_rows:
        ft = e.get("from_tipo") or "OUTROS"
        tt = e.get("to_tipo") or "OUTROS"
        from_lane = _lane(e.get("from_unidade"), lane_depth) if unit_mode else None
        to_lane = _lane(e.get("to_unidade"), lane_depth) if unit_mode else None
        fk = node_key(ft, node_identity, from_lane)
        tk = node_key(tt, node_identity, to_lane)
        for kk, tp, ln in ((fk, ft, from_lane), (tk, tt, to_lane)):
            if kk not in nodes:
                nodes[kk] = _new_node(kk, tp, ln)
        ed = edges.get((fk, tk))
        if ed is None:
            ed = edges[(fk, tk)] = {
                "from_key": fk, "to_key": tk, "freq": 0, "procs": set(),
                "contrib": [], "adv": [], "speed": [], "interval": [],
            }
        ed["freq"] += 1
        ed["procs"].add(e.get("protocolo"))
        ed["contrib"].append(e.get("contrib_score"))
        ed["adv"].append(e.get("advancement_score"))
        ed["speed"].append(e.get("speed_score"))
        if e.get("intervalo_horas") is not None:
            ed["interval"].append(e.get("intervalo_horas"))

    out_deg: Counter = Counter()
    in_deg: Counter = Counter()
    for (fk, tk) in edges:
        out_deg[fk] += 1
        in_deg[tk] += 1

    max_freq = max((n["freq"] for n in nodes.values()), default=0) or 1
    max_out = max(out_deg.values(), default=0) or 1
    max_in = max(in_deg.values(), default=0) or 1
    tp_total = total_processos or 1

    node_records = []
    for k, n in nodes.items():
        is_act = 1.0 if n["tipo_acao"] in ACTIVATION_TYPES else 0.0
        is_con = 1.0 if n["tipo_acao"] in CONCLUSION_TYPES else 0.0
        feats = [
            round(n["freq"] / max_freq, 4),
            round(len(n["procs"]) / tp_total, 4),
            round(in_deg[k] / max_in, 4),
            round(out_deg[k] / max_out, 4),
            _mean(n["contrib"]),
            _mean(n["adv"]),
            _mean(n["speed"]),
            _mean(n["band"]),
            is_act,
            is_con,
        ]
        grupo_hot = [0.0] * len(GRUPO_VOCAB)
        grupo_hot[_GRUPO_INDEX.get(n["grupo"], _GRUPO_INDEX["outros"])] = 1.0
        feats += grupo_hot
        node_records.append({
            "state_key": k,
            "tipo_acao": n["tipo_acao"],
            "grupo": n["grupo"],
            "unidade_lane": n["unidade_lane"],
            "frequency": n["freq"],
            "n_processos": len(n["procs"]),
            "is_activation": bool(is_act),
            "is_conclusion": bool(is_con),
            "features": feats,
            "feature_dim": len(feats),
            "mean_contrib": _mean(n["contrib"]),
            "mean_advancement": _mean(n["adv"]),
            "mean_speed": _mean(n["speed"]),
            "mean_activity_band": _mean(n["band"]),
        })

    edge_records = []
    for (fk, tk), ed in edges.items():
        edge_records.append({
            "from_key": fk,
            "to_key": tk,
            "frequency": ed["freq"],
            "n_processos": len(ed["procs"]),
            "mean_contrib_score": _mean(ed["contrib"]),
            "mean_advancement": _mean(ed["adv"]),
            "mean_speed": _mean(ed["speed"]),
            "mean_intervalo_horas": _mean(ed["interval"], default=None),
        })

    node_records.sort(key=lambda r: r["state_key"])
    edge_records.sort(key=lambda r: (r["from_key"], r["to_key"]))
    return node_records, edge_records
