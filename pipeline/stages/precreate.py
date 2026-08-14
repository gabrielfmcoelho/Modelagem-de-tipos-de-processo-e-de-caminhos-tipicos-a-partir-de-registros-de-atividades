
from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from datetime import datetime

from ..core._stage_base import RunContext, StageMeta
from ..model.classification import extract_orgao
from ..model.classifier import get_all_grupo_records, get_all_tipo_acao_records
from ..core.cypher import PRECREATE_PROCESSOS_CYPHER, PRECREATE_USUARIOS_CYPHER, SEED_TIPOS_CYPHER, SETUP_CONSTRAINTS
from ..model.discovery import discover
from ..model.hierarchy import parent_unidade
from ..core.registry import stage
from ..writers import GraphWriter

log = logging.getLogger(__name__)


def ensure_schema(writer: GraphWriter) -> None:
    for cypher in SETUP_CONSTRAINTS:
        try:
            writer.execute_template("setup_constraint", cypher, {}, phase="A")
        except Exception as e:
            log.debug("schema setup skipped: %s", e)


def precreate_shared_nodes(
    writer: GraphWriter,
    processos: Iterable[Mapping],
    all_unidades: set[str],
    user_orgao: dict[str, str],
    *,
    unidade_ids: dict[str, int],
) -> None:
    log.info("Phase A: Pre-creating shared dimension nodes...")
    writer.open_phase("A")

    ensure_schema(writer)

    processos = list(processos)

    grupos = get_all_grupo_records()
    tipos = get_all_tipo_acao_records()
    writer.write_nodes("GrupoAtividade", ["chave"], grupos, phase="A", props=["label", "horas"])
    writer.execute_template("seed_tipos", SEED_TIPOS_CYPHER, {"types": tipos}, phase="A")
    log.info("  Seeded %d groups and %d action types", len(grupos), len(tipos))

    all_orgaos = sorted({extract_orgao(u) for u in all_unidades})
    writer.write_nodes(
        "Orgao", ["sigla"],
        [{"sigla": o} for o in all_orgaos],
        phase="A",
    )
    log.info("  Pre-created %d orgaos", len(all_orgaos))

    unit_list = [
        {"sigla": u, "id_unidade": unidade_ids.get(u)}
        for u in all_unidades
    ]
    writer.write_nodes(
        "Unidade", ["sigla"], unit_list,
        phase="A", props=["id_unidade"],
    )
    log.info("  Pre-created %d unidades (id from source data)", len(unit_list))

    unidade_orgao_links = [{"unidade": u, "orgao": extract_orgao(u)} for u in all_unidades]
    writer.write_edges(
        "PERTENCE_AO_ORGAO",
        "Unidade", {"unidade": "sigla"},
        "Orgao", {"orgao": "sigla"},
        unidade_orgao_links,
        phase="A",
    )
    log.info("  Linked unidades to orgaos")

    subunidade_links = []
    for u in all_unidades:
        parent = parent_unidade(u)
        if parent and parent in all_unidades:
            subunidade_links.append({"child": u, "parent": parent})
    writer.write_edges(
        "SUBUNIDADE_DE",
        "Unidade", {"child": "sigla"},
        "Unidade", {"parent": "sigla"},
        subunidade_links,
        phase="A",
    )
    log.info("  Linked %d subunidade relationships", len(subunidade_links))

    proc_rows = []
    for row in processos:
        data_criacao_str = None
        if row["data_hora"]:
            dt = row["data_hora"]
            data_criacao_str = (
                dt.strftime("%Y-%m-%dT%H:%M:%S") if isinstance(dt, datetime) else str(dt)
            )
        proc_rows.append({
            "protocolo_formatado": row["protocolo_formatado"],
            "tipo_procedimento": row["tipo_procedimento"],
            "data_criacao": data_criacao_str,
            "id_processo": row.get("id_processo"),
        })
    for i in range(0, len(proc_rows), 1000):
        batch = proc_rows[i:i + 1000]
        writer.execute_template("precreate_processos", PRECREATE_PROCESSOS_CYPHER, {"rows": batch}, phase="A")
    log.info("  Pre-created %d processos (with data_criacao)", len(proc_rows))

    creation_rows = [
        {
            "protocolo_formatado": row["protocolo_formatado"],
            "unidade": row["unidade"] or "DESCONHECIDA",
        }
        for row in processos
        if row["unidade"]
    ]
    writer.write_edges(
        "CRIADO_NA_UNIDADE",
        "Processo", {"protocolo_formatado": "protocolo_formatado"},
        "Unidade", {"unidade": "sigla"},
        creation_rows,
        phase="A",
    )
    log.info("  Linked processos to creation unidades")

    orgao_rows = [
        {
            "protocolo_formatado": row["protocolo_formatado"],
            "orgao": extract_orgao(row["unidade"]) if row["unidade"] else "DESCONHECIDO",
        }
        for row in processos
        if row["unidade"]
    ]
    writer.write_edges(
        "CRIADO_NO_ORGAO",
        "Processo", {"protocolo_formatado": "protocolo_formatado"},
        "Orgao", {"orgao": "sigla"},
        orgao_rows,
        phase="A",
    )
    log.info("  Linked processos to creation orgaos")

    user_rows = [{"nome": u, "orgao": o} for u, o in user_orgao.items()]
    for i in range(0, len(user_rows), 1000):
        batch = user_rows[i:i + 1000]
        writer.execute_template("precreate_usuarios", PRECREATE_USUARIOS_CYPHER, {"users": batch}, phase="A")
    log.info("  Pre-created %d usuarios (linked to orgaos)", len(user_rows))

    writer.close_phase("A")
    log.info("Phase A complete")


@stage(StageMeta(
    name="precreate",
    phase="graph",
    question="Quais sao os nos-dimensao do grafo?",
    deterministic=True,
    description="Cria nós-dimensão (Orgao, Unidade, TipoAcao, …) antes do load paralelo.",
    type="core",
    depends_on=(),
    soft_depends_on=("unidades",),
    modes=("neo4j", "json-emit"),
    estimated_duration="~1-3min",
))
def run(ctx: RunContext) -> None:
    ctx.settings.require_trino()
    discovery = ctx.cached(
        "discovery",
        lambda: discover(
            ctx.settings,
            ctx.flags.get("from_date"),
            ctx.flags.get("to_date"),
            ctx.flags.get("orgao"),
            ctx.flags.get("limit"),
            status=ctx.flags.get("status"),
            concluded_before=ctx.flags.get("concluded_before"),
        ),
    )
    if not discovery["protocolo_ids"]:
        log.info("No processos found — nothing to precreate.")
        ctx.cache["precreate_summary"] = {"processos": 0, "unidades": 0, "usuarios": 0}
        return

    writer = ctx.require_writer()
    precreate_shared_nodes(
        writer,
        discovery["processos"],
        discovery["all_unidades"],
        discovery["user_orgao"],
        unidade_ids=discovery["unidade_ids"],
    )
    ctx.cache["precreate_summary"] = {
        "processos": len(discovery["protocolo_ids"]),
        "unidades": len(discovery["all_unidades"]),
        "usuarios": len(discovery["user_orgao"]),
    }
