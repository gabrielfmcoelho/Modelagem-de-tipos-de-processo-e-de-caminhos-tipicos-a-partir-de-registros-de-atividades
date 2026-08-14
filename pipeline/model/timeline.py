
from __future__ import annotations

from datetime import datetime

CONCLUSION_TYPES = {
    "CONCLUSAO-AUTOMATICA-UNIDADE",
    "CONCLUSAO-PROCESSO-UNIDADE",
}

TRANSFER_TYPES = {
    "CONCLUSAO-AUTOMATICA-UNIDADE",
    "CONCLUSAO-PROCESSO-UNIDADE",
    "PROCESSO-REMETIDO-UNIDADE",
    "PROCESSO-RECEBIDO-UNIDADE",
}

FLOW_ACTIVATION_TYPES = {
    "GERACAO-PROCEDIMENTO",
    "PROCESSO-REMETIDO-UNIDADE",
    "REABERTURA-PROCESSO-UNIDADE",
}


def transfer_priority(tipo_acao: str) -> int:
    if tipo_acao == "PROCESSO-REMETIDO-UNIDADE":
        return 0
    if tipo_acao in CONCLUSION_TYPES:
        return 2
    return 1


def _parse_dt(s: str) -> datetime:
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return datetime.min


def sort_and_fix_activities(activities: list[dict]) -> list[dict]:
    activities.sort(
        key=lambda a: (
            a.get("data_hora", ""),
            transfer_priority(a["tipo_acao"]),
            a["source_id"],
        )
    )

    i = 0
    while i < len(activities):
        if activities[i]["tipo_acao"] != "PROCESSO-RECEBIDO-UNIDADE":
            i += 1
            continue
        recebido_time = _parse_dt(activities[i].get("data_hora", ""))
        recebido_unidade = activities[i].get("unidade")
        j = i + 1
        while j < len(activities):
            candidate = activities[j]
            cand_time = _parse_dt(candidate.get("data_hora", ""))
            if (cand_time - recebido_time).total_seconds() > 60:
                break
            if (
                candidate["tipo_acao"] == "PROCESSO-REMETIDO-UNIDADE"
                and candidate.get("unidade") == recebido_unidade
            ):
                activities.insert(i, activities.pop(j))
            else:
                j += 1
        i += 1

    return activities


def compute_interval(from_atv: dict, to_atv: dict) -> tuple[float | None, float | None]:
    from_dt = from_atv.get("data_hora", "")
    to_dt = to_atv.get("data_hora", "")
    if not from_dt or not to_dt:
        return None, None
    try:
        delta = datetime.fromisoformat(to_dt) - datetime.fromisoformat(from_dt)
        total = delta.total_seconds()
        return round(total / 3600, 2), round(total / 86400, 2)
    except (ValueError, TypeError):
        return None, None


def build_edges_for_processo(
    activities: list[dict],
) -> tuple[list[dict], list[dict]]:
    if len(activities) < 2:
        return [], []

    activities = sort_and_fix_activities(activities)

    activated_units: set[str] = set()
    for atv in activities:
        if atv["tipo_acao"] in FLOW_ACTIVATION_TYPES:
            activated_units.add(atv["unidade"])

    flow_edges: list[dict] = []
    independent_edges: list[dict] = []
    last_at: dict[str, dict] = {}
    last_chainable_at: dict[str, dict] = {}
    pending_remetidos: dict[str, list[dict]] = {}
    pending_reab: dict[str, dict] = {}

    for atv in activities:
        u = atv["unidade"]
        tipo = atv["tipo_acao"]
        sid = atv["source_id"]

        if u not in activated_units:
            continue

        edges_before = len(flow_edges)

        if tipo == "PROCESSO-REMETIDO-UNIDADE":
            src = atv.get("source_unidade")
            bridge = None
            mesma = False
            if src and src in last_chainable_at:
                bridge, mesma = last_chainable_at[src], False
            elif u in last_chainable_at:
                bridge, mesma = last_chainable_at[u], True
            if bridge is not None:
                h, d = compute_interval(bridge, atv)
                flow_edges.append({
                    "from_id": bridge["source_id"],
                    "to_id": sid,
                    "mesma_unidade": mesma,
                    "intervalo_horas": h,
                    "intervalo_dias": d,
                })
            pending_remetidos.setdefault(u, []).append(atv)

        elif tipo == "PROCESSO-RECEBIDO-UNIDADE":
            if u in pending_remetidos and pending_remetidos[u]:
                for rem in pending_remetidos[u]:
                    h, d = compute_interval(rem, atv)
                    flow_edges.append({
                        "from_id": rem["source_id"],
                        "to_id": sid,
                        "mesma_unidade": True,
                        "intervalo_horas": h,
                        "intervalo_dias": d,
                    })
                pending_remetidos[u] = []
            elif u in last_at:
                if last_at[u]["tipo_acao"] not in CONCLUSION_TYPES:
                    h, d = compute_interval(last_at[u], atv)
                    flow_edges.append({
                        "from_id": last_at[u]["source_id"],
                        "to_id": sid,
                        "mesma_unidade": True,
                        "intervalo_horas": h,
                        "intervalo_dias": d,
                    })

        else:
            if tipo == "REABERTURA-PROCESSO-UNIDADE":
                pred = None
            elif tipo in CONCLUSION_TYPES:
                pred = last_chainable_at.get(u)
            elif u in last_at and last_at[u]["tipo_acao"] not in CONCLUSION_TYPES:
                pred = last_at[u]
            else:
                pred = None
            if pred is not None:
                h, d = compute_interval(pred, atv)
                flow_edges.append({
                    "from_id": pred["source_id"],
                    "to_id": sid,
                    "mesma_unidade": True,
                    "intervalo_horas": h,
                    "intervalo_dias": d,
                })

        if tipo != "REABERTURA-PROCESSO-UNIDADE" and pending_reab.get(u) is not None:
            reab = pending_reab[u]
            already = any(
                e["from_id"] == reab["source_id"] and e["to_id"] == sid
                for e in flow_edges[edges_before:]
            )
            if not already:
                h, d = compute_interval(reab, atv)
                flow_edges.append({
                    "from_id": reab["source_id"],
                    "to_id": sid,
                    "mesma_unidade": True,
                    "intervalo_horas": h,
                    "intervalo_dias": d,
                })
            pending_reab[u] = None

        if tipo == "REABERTURA-PROCESSO-UNIDADE":
            pending_reab[u] = atv

        last_at[u] = atv
        if tipo not in CONCLUSION_TYPES:
            last_chainable_at[u] = atv

    linked_to = {e["to_id"] for e in flow_edges}
    chainable_by_unit: dict[str, list[dict]] = {}
    for atv in activities:
        if atv["unidade"] in activated_units and atv["tipo_acao"] not in CONCLUSION_TYPES:
            chainable_by_unit.setdefault(atv["unidade"], []).append(atv)
    for atv in activities:
        sid = atv["source_id"]
        tipo = atv["tipo_acao"]
        if sid in linked_to or atv["unidade"] not in activated_units:
            continue
        if tipo == "PROCESSO-REMETIDO-UNIDADE":
            cand_unit = atv.get("source_unidade") or atv["unidade"]
        elif tipo in CONCLUSION_TYPES:
            cand_unit = atv["unidade"]
        else:
            continue
        t = atv.get("data_hora", "") or ""
        pred = None
        for cand in chainable_by_unit.get(cand_unit, ()):
            if cand["source_id"] != sid and (cand.get("data_hora", "") or "") <= t:
                pred = cand
        if pred is not None:
            h, d = compute_interval(pred, atv)
            flow_edges.append({
                "from_id": pred["source_id"],
                "to_id": sid,
                "mesma_unidade": cand_unit == atv["unidade"],
                "intervalo_horas": h,
                "intervalo_dias": d,
            })
            linked_to.add(sid)

    flow_pairs = {(e["from_id"], e["to_id"]) for e in flow_edges}
    by_ref: dict[str, list[dict]] = {}
    for atv in activities:
        rid = atv.get("ref_id")
        if rid:
            by_ref.setdefault(rid, []).append(atv)
    for rid, group in by_ref.items():
        for prev, cur in zip(group, group[1:]):
            pair = (prev["source_id"], cur["source_id"])
            if pair[0] == pair[1] or pair in flow_pairs:
                continue
            independent_edges.append(
                {"from_id": pair[0], "to_id": pair[1], "ref_id": rid}
            )

    return flow_edges, independent_edges
