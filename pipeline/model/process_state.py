
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .classification import extract_orgao
from .timeline import sort_and_fix_activities

ACTIVATION_TYPES: frozenset[str] = frozenset({
    "GERACAO-PROCEDIMENTO",
    "PROCESSO-REMETIDO-UNIDADE",
    "REABERTURA-PROCESSO-UNIDADE",
})

CONCLUSION_TYPES: frozenset[str] = frozenset({
    "CONCLUSAO-PROCESSO-UNIDADE",
    "CONCLUSAO-AUTOMATICA-UNIDADE",
})

SIGNIFICANT_TYPES: frozenset[str] = frozenset(
    ACTIVATION_TYPES | CONCLUSION_TYPES | {"PROCESSO-RECEBIDO-UNIDADE"}
)


def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _hours_between(a: str | None, b: str | None) -> float:
    da = _parse_dt(a)
    db = _parse_dt(b)
    if da is None or db is None:
        return 0.0
    return (db - da).total_seconds() / 3600.0


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def compute_processo_state(
    activities: list[dict[str, Any]],
    *,
    protocolo_formatado: str | None = None,
    now_iso: str | None = None,
) -> dict[str, Any]:
    if not activities:
        return _empty_state(protocolo_formatado, now_iso or _now_iso())

    pf = protocolo_formatado or activities[0].get("protocolo_formatado") or "unknown"
    now = now_iso or _now_iso()
    now_dt = _parse_dt(now) or datetime.now(UTC)

    sorted_activities = sort_and_fix_activities(list(activities))

    data_inicio = sorted_activities[0]["data_hora"]
    data_ultima_atividade = sorted_activities[-1]["data_hora"]
    atividade_mais_recente_id = sorted_activities[-1]["source_id"]

    units = _walk_units(sorted_activities, pf)

    orgaos = _aggregate_orgaos(units, data_ultima_atividade)

    abertas_siglas = sorted(u["unidade"] for u in units if u["situacao"] == "em_aberto")
    concluido = len(abertas_siglas) == 0

    data_conclusao_global: str | None = None
    if concluido:
        for atv in reversed(sorted_activities):
            if atv["tipo_acao"] in CONCLUSION_TYPES:
                data_conclusao_global = atv["data_hora"]
                break

    duracao_lifetime_horas = (
        _hours_between(data_inicio, data_conclusao_global) if concluido else None
    )

    for u in units:
        u["dias_sem_atividade"] = _days_since(u["ultima_atividade_data_hora"], now_dt)
    for o in orgaos:
        o["dias_sem_atividade"] = _days_since(o["ultima_atividade_data_hora"], now_dt)

    return {
        "processo": {
            "protocolo_formatado": pf,
            "situacao": "concluido" if concluido else "em_andamento",
            "unidades_em_aberto": abertas_siglas,
            "unidades_em_aberto_count": len(abertas_siglas),
            "data_inicio": data_inicio,
            "data_ultima_atividade": data_ultima_atividade,
            "data_conclusao_global": data_conclusao_global,
            "duracao_lifetime_horas": duracao_lifetime_horas,
            "duracao_lifetime_dias": (
                round(duracao_lifetime_horas / 24.0, 2)
                if duracao_lifetime_horas is not None else None
            ),
            "atividade_mais_recente_id": atividade_mais_recente_id,
            "situacao_computed_at": now,
        },
        "unidades": units,
        "orgaos": orgaos,
    }


def _empty_state(pf: str | None, now: str) -> dict[str, Any]:
    return {
        "processo": {
            "protocolo_formatado": pf or "unknown",
            "situacao": "em_andamento",
            "unidades_em_aberto": [],
            "unidades_em_aberto_count": 0,
            "data_inicio": None,
            "data_ultima_atividade": None,
            "data_conclusao_global": None,
            "duracao_lifetime_horas": None,
            "duracao_lifetime_dias": None,
            "atividade_mais_recente_id": None,
            "situacao_computed_at": now,
        },
        "unidades": [],
        "orgaos": [],
    }


def _days_since(iso: str | None, now_dt: datetime) -> int | None:
    dt = _parse_dt(iso)
    if dt is None:
        return None
    if dt.tzinfo is None and now_dt.tzinfo is not None:
        now_dt = now_dt.replace(tzinfo=None)
    elif dt.tzinfo is not None and now_dt.tzinfo is None:
        dt = dt.replace(tzinfo=None)
    delta = now_dt - dt
    return max(int(delta.total_seconds() // 86400), 0)


def _walk_units(
    sorted_activities: list[dict[str, Any]],
    protocolo: str,
) -> list[dict[str, Any]]:
    state: dict[str, dict[str, Any]] = {}

    for atv in sorted_activities:
        unit = atv.get("unidade")
        if not unit:
            continue
        tipo = atv.get("tipo_acao")
        data_hora = atv.get("data_hora")
        sid = atv.get("source_id")

        st = state.setdefault(unit, {
            "ciclos": [],
            "open_cycle": None,
            "last_significant": None,
            "first_seen": data_hora,
            "last_seen": data_hora,
        })
        st["last_seen"] = data_hora

        if tipo in ACTIVATION_TYPES:
            if st["open_cycle"] is not None:
                _close_cycle_implicit(st["open_cycle"], st.get("last_seen"))
                st["ciclos"].append(st["open_cycle"])
                st["open_cycle"] = None

            ordem = len(st["ciclos"]) + (1 if st["open_cycle"] else 0)
            st["open_cycle"] = {
                "id": f"{protocolo}|{unit}|{ordem}",
                "ordem": ordem,
                "entrada": data_hora,
                "saida": None,
                "duracao_horas": 0.0,
                "status": "em_aberto",
                "abertura_atividade_id": sid,
                "abertura_tipo_acao": tipo,
                "conclusao_atividade_id": None,
                "conclusao_tipo_acao": None,
            }
            st["last_significant"] = atv

        elif tipo in CONCLUSION_TYPES:
            if st["open_cycle"] is not None:
                cycle = st["open_cycle"]
                cycle["saida"] = data_hora
                cycle["duracao_horas"] = round(
                    _hours_between(cycle["entrada"], data_hora), 2
                )
                cycle["status"] = "concluida"
                cycle["conclusao_atividade_id"] = sid
                cycle["conclusao_tipo_acao"] = tipo
                st["ciclos"].append(cycle)
                st["open_cycle"] = None
            else:
                ordem = len(st["ciclos"])
                st["ciclos"].append({
                    "id": f"{protocolo}|{unit}|{ordem}",
                    "ordem": ordem,
                    "entrada": data_hora,
                    "saida": data_hora,
                    "duracao_horas": 0.0,
                    "status": "concluida",
                    "abertura_atividade_id": None,
                    "abertura_tipo_acao": None,
                    "conclusao_atividade_id": sid,
                    "conclusao_tipo_acao": tipo,
                })
            st["last_significant"] = atv

        elif tipo == "PROCESSO-RECEBIDO-UNIDADE":
            st["last_significant"] = atv


    for _unit, st in state.items():
        if st["open_cycle"] is not None:
            cycle = st["open_cycle"]
            cycle["duracao_horas"] = round(
                _hours_between(cycle["entrada"], st["last_seen"]), 2
            )
            st["ciclos"].append(cycle)
            st["open_cycle"] = None

    records: list[dict[str, Any]] = []
    for unit, st in state.items():
        ciclos = st["ciclos"]
        last = st["last_significant"]
        em_aberto = bool(ciclos) and ciclos[-1]["status"] == "em_aberto"

        duracao_acumulada = sum(
            c["duracao_horas"] for c in ciclos if c["status"] == "concluida"
        )
        primeira_entrada = ciclos[0]["entrada"] if ciclos else st["first_seen"]
        ultima_saida = (
            ciclos[-1]["saida"] if ciclos and ciclos[-1]["status"] == "concluida" else None
        )
        duracao_lifetime = _hours_between(primeira_entrada, st["last_seen"])

        records.append({
            "unidade": unit,
            "situacao": "em_aberto" if em_aberto else "concluida",
            "duracao_acumulada_horas": round(duracao_acumulada, 2),
            "duracao_lifetime_horas": round(duracao_lifetime, 2),
            "visitas": len(ciclos),
            "primeira_entrada": primeira_entrada,
            "ultima_saida": ultima_saida,
            "ultima_atividade_id": (last or {}).get("source_id"),
            "ultima_atividade_data_hora": (last or {}).get("data_hora"),
            "ultima_atividade_tipo_acao": (last or {}).get("tipo_acao"),
            "dias_sem_atividade": None,
            "ciclos": ciclos,
        })

    return records


def _close_cycle_implicit(cycle: dict[str, Any], at_data_hora: str | None) -> None:
    cycle["saida"] = at_data_hora
    cycle["duracao_horas"] = round(
        _hours_between(cycle["entrada"], at_data_hora), 2
    )
    cycle["status"] = "concluida_implicita"
    cycle["implicit_close"] = True


def _aggregate_orgaos(
    unit_records: list[dict[str, Any]],
    fallback_ultima_atividade: str | None,
) -> list[dict[str, Any]]:
    by_orgao: dict[str, dict[str, Any]] = {}
    for u in unit_records:
        orgao = extract_orgao(u["unidade"])
        agg = by_orgao.setdefault(orgao, {
            "orgao": orgao,
            "duracao_acumulada_horas": 0.0,
            "duracao_lifetime_horas": 0.0,
            "visitas": 0,
            "primeira_entrada": u["primeira_entrada"],
            "ultima_saida": u["ultima_saida"],
            "ultima_atividade_data_hora": u["ultima_atividade_data_hora"],
            "unidades_abertas": [],
            "unidades_total": [],
        })
        agg["duracao_acumulada_horas"] += u["duracao_acumulada_horas"]
        agg["duracao_lifetime_horas"] = max(agg["duracao_lifetime_horas"], u["duracao_lifetime_horas"])
        agg["visitas"] += u["visitas"]
        agg["unidades_total"].append(u["unidade"])
        if u["situacao"] == "em_aberto":
            agg["unidades_abertas"].append(u["unidade"])

        if u["primeira_entrada"] and (
            not agg["primeira_entrada"] or u["primeira_entrada"] < agg["primeira_entrada"]
        ):
            agg["primeira_entrada"] = u["primeira_entrada"]
        if u["ultima_saida"] and (
            not agg["ultima_saida"] or u["ultima_saida"] > agg["ultima_saida"]
        ):
            agg["ultima_saida"] = u["ultima_saida"]
        if u["ultima_atividade_data_hora"] and (
            not agg["ultima_atividade_data_hora"]
            or u["ultima_atividade_data_hora"] > agg["ultima_atividade_data_hora"]
        ):
            agg["ultima_atividade_data_hora"] = u["ultima_atividade_data_hora"]

    return [
        {
            "orgao": agg["orgao"],
            "situacao": "em_aberto" if agg["unidades_abertas"] else "concluida",
            "unidades_abertas_count": len(agg["unidades_abertas"]),
            "unidades_abertas": sorted(agg["unidades_abertas"]),
            "duracao_acumulada_horas": round(agg["duracao_acumulada_horas"], 2),
            "duracao_lifetime_horas": round(agg["duracao_lifetime_horas"], 2),
            "visitas": agg["visitas"],
            "primeira_entrada": agg["primeira_entrada"],
            "ultima_saida": agg["ultima_saida"] if not agg["unidades_abertas"] else None,
            "ultima_atividade_data_hora": agg["ultima_atividade_data_hora"],
            "dias_sem_atividade": None,
        }
        for agg in by_orgao.values()
    ]
