#!/usr/bin/env python

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (
    Doc,
    bars,
    fmt,
    neo4j_session,
    rows,
    scalar,
    settings,
    trino_conn,
)

COL_MEANING = {
    "id": "activity (andamento) id — the `:Atividade.source_id`",
    "id_processo": "internal SEI process id",
    "protocolo_formatado": "human protocol number — the `:Processo` key",
    "data_hora": "activity timestamp (event time)",
    "id_unidades": "internal id of the acting unit",
    "unidade": "acting unit sigla (hierarchical, e.g. `SEAD-PI/GAB/SLC`)",
    "usuario": "acting user",
    "tipo_procedimento": "official SEI process type (the quasi-ground-truth label)",
    "descricao_replace": "free-text activity description (classified into `tipo_acao`)",
    "id_serie": "document series id (links the activity to a document)",
    "data_carga": "lakehouse load timestamp (ETL bookkeeping)",
}


def main() -> None:
    s = settings()
    d = Doc(
        "Report ① — Datalake source: structure & peculiarities",
        f"_Source: Trino/Iceberg `{s.trino_catalog}.{s.trino_schema}.sei_atividades` (the SEAD SEI "
        "data-lakehouse). Schema + raw samples from Trino; loaded profile from the Neo4j graph._",
    )

    d.h2("1. Table schema — `sei_atividades`")
    with trino_conn() as conn:
        from pipeline.core.trino_source import run_query
        desc = run_query(conn, "DESCRIBE sei_atividades")
        d.table(["column", "type", "meaning"],
                [[r.get("Column"), r.get("Type"),
                  COL_MEANING.get(r.get("Column"), "")] for r in desc])
        sample = run_query(conn,
                           "SELECT descricao_replace, tipo_procedimento, unidade "
                           "FROM sei_atividades LIMIT 40")

    d.h2("2. Peculiarities of the raw data")
    d.p(
        "- **`descricao_replace` is the semantic payload.** It is free text that encodes the action "
        "and embeds placeholders/anchors (e.g. *Processo NNN gerado*, *Processo remetido pela unidade X*, "
        "bloco/document references). The pipeline classifies it into ~40 `tipo_acao` codes via regex "
        "(`pipeline/classifier.py`) — this is a modelling choice that shapes every downstream result.\n"
        "- **`unidade` is hierarchical.** The sigla encodes the org tree (`ÓRGÃO/.../SUBUNIDADE`); the "
        "first segment is the **órgão** (the project's `split_part(unidade,'/',1)='SEAD-PI'` filter).\n"
        "- **`tipo_procedimento` is the official type** — a rich, quasi-ground-truth label used for cluster "
        "naming and (future) extrinsic validation.\n"
        "- **`id_serie` links to documents** (the document series), reused by `download`/`embed`.\n"
        "- **`data_hora` vs `data_carga`.** `data_hora` is the *event* time (used for ordering and the "
        "year filter); `data_carga` is ETL bookkeeping. The lakehouse is under active curation — an early "
        "extraction returned stale, much smaller counts later corrected on refresh.\n"
        "- **No explicit activity→activity ordering.** Sequence is reconstructed by the `timeline` stage "
        "from `(data_hora, type)` — see [`timeline-graph-analysis.md`](../../docs/research/timeline-graph-analysis.md)."
    )
    if sample:
        d.h3("Raw `descricao_replace` samples")
        d.add("\n".join(f"- `{(r['descricao_replace'] or '')[:140]}`" for r in sample[:12]) + "\n")

    d.h2("3. From raw columns to the knowledge graph")
    d.table(["raw column(s)", "becomes"],
            [["protocolo_formatado, id_processo, tipo_procedimento", "`:Processo` (+ `TEM_TIPO`→`:TipoProcedimento`)"],
             ["id (source_id), data_hora, descricao_replace", "`:Atividade` (+ classified `tipo_acao`, `is_start`/`is_conclusion`)"],
             ["unidade, id_unidades", "`:Unidade` (+ `EXECUTADO_PELA_UNIDADE`, `SUBUNIDADE_DE` hierarchy)"],
             ["usuario", "`:Usuario` (+ `EXECUTADO_PELO_USUARIO`)"],
             ["id_serie + SEI API", "`:Documento` (+ `REFERENCIA_DOCUMENTO`, embedding, topic/summary)"],
             ["(reconstructed)", "`:Atividade)-[:SEGUIDA_POR]->(:Atividade)` flow + `:Ciclo` per-unit state"]])

    d.h2("4. The extracted slice (SEAD-PI · 2025)")
    with neo4j_session() as sess:
        np_ = scalar(sess, "MATCH (p:Processo) RETURN count(p)")
        na = scalar(sess, "MATCH (a:Atividade) RETURN count(a)")
        nu = scalar(sess, "MATCH (u:Unidade) RETURN count(u)")
        nus = scalar(sess, "MATCH (u:Usuario) RETURN count(u)")
        ntp = scalar(sess, "MATCH (t:TipoProcedimento) RETURN count(t)")
        d.p("Discovery filter: `split_part(unidade,'/',1)='SEAD-PI'` AND `data_hora ∈ [2025-01-01, "
            "2026-01-01)`, matched on the **creation event** (process *born* in SEAD).")
        d.table(["entity", "count"],
                [["Processos", fmt(np_)], ["Atividades", fmt(na)], ["Unidades", fmt(nu)],
                 ["Usuários", fmt(nus)], ["Tipos de procedimento", fmt(ntp)]])
        ym = rows(sess, """MATCH (p:Processo) WHERE p.data_criacao IS NOT NULL
                           RETURN substring(toString(p.data_criacao),0,7) AS ym, count(*) AS c
                           ORDER BY ym""")
        if ym:
            d.img(bars([r["ym"] for r in ym], [r["c"] for r in ym],
                       "Processos criados por mês (2025)", "01_por_mes.png", ylabel="processos"),
                  "by month")

    dest = d.write("01-datalake-schema.md")
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
