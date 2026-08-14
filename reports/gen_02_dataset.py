#!/usr/bin/env python

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (
    Doc,
    barh,
    fmt,
    hist,
    load_cluster_metrics,
    neo4j_session,
    pct,
    pie,
    rows,
    scalar,
)

PARSED_DIR = Path(__file__).resolve().parent.parent / "parsed_documents"


def main() -> None:
    d = Doc(
        "Report ② — Dataset profile & pipeline data lineage",
        "_Generated from the live Neo4j graph (SEAD-PI processos born in 2025). "
        "Companion to [`project-overview.md`](../../docs/README.md) and "
        "[`algorithms.md`](../../docs/architecture/algorithms.md)._",
    )

    run_id, algo = "exp-anon", "hdbscan"
    metrics_path = f"artifacts/clustering/{run_id}/{algo}/metrics.json"
    metrics = load_cluster_metrics(run_id, algo)
    dbcv = metrics["dbcv"]

    with neo4j_session() as s:
        n_proc = scalar(s, "MATCH (p:Processo) RETURN count(p)")
        n_atv = scalar(s, "MATCH (a:Atividade) RETURN count(a)")
        n_doc = scalar(s, "MATCH (x:Documento) RETURN count(x)")
        n_seg = scalar(s, "MATCH ()-[r:SEGUIDA_POR]->() RETURN count(r)")
        n_uni = scalar(s, "MATCH (u:Unidade) RETURN count(u)")
        n_org = scalar(s, "MATCH (o:Orgao) RETURN count(o)")
        n_usr = scalar(s, "MATCH (u:Usuario) RETURN count(u)")
        n_ciclo = scalar(s, "MATCH (c:Ciclo) RETURN count(c)")
        n_cat = scalar(s, "MATCH (c:CategoriaProcesso) RETURN count(c)")
        n_emb = scalar(s, "MATCH (x:Documento) WHERE x.embedding IS NOT NULL RETURN count(x)")
        n_top = scalar(s, "MATCH (x:Documento) WHERE x.topic IS NOT NULL RETURN count(x)")
        n_feat = scalar(s, "MATCH (p:Processo) WHERE p.cluster_features IS NOT NULL RETURN count(p)")
        parsed_on_disk = sum(1 for _ in PARSED_DIR.iterdir()) if PARSED_DIR.is_dir() else 0

        d.h2("1. Corpus at a glance")
        d.table(
            ["entity", "count"],
            [["Processos (born SEAD-PI, 2025)", fmt(n_proc)],
             ["Atividades (event-log lines)", fmt(n_atv)],
             ["Documentos referenced", fmt(n_doc)],
             ["SEGUIDA_POR edges (flow)", fmt(n_seg)],
             ["Unidades", fmt(n_uni)], ["Órgãos traversed", fmt(n_org)],
             ["Usuários", fmt(n_usr)], ["Ciclos (per-unit open/close)", fmt(n_ciclo)],
             ["CategoriaProcesso (clusters)", fmt(n_cat)]],
        )
        d.p(f"\nMean activities per processo: **{(n_atv / n_proc):.1f}**.")

        d.h2("2. Pipeline data lineage (what each stage consumes / produces)")
        lineage = [
            ("precreate", "Trino `sei_atividades` (creation events)", "Órgão/Unidade/TipoAcao/TipoProcedimento/Usuario + Processo skeleton + schema", fmt(n_proc) + " processos"),
            ("atividades", "Trino `sei_atividades` (all rows for the processos)", "Atividade + DO_PROCESSO/EXECUTADO_*/REFERENCIA_DOCUMENTO + Documento", fmt(n_atv) + " atividades · " + fmt(n_doc) + " docs"),
            ("timeline", "graph activities (per processo)", "SEGUIDA_POR / PRECEDIDA_POR / SEGUIDO_INDEPENDENTEMENTE_POR / INICIOU_PROCESSO", fmt(n_seg) + " SEGUIDA_POR"),
            ("permanencia", "graph activities", "PASSOU_PELA_UNIDADE/ORGAO (durations, visits)", "—"),
            ("situacao", "graph activities (cycles)", "Ciclo + Processo.situacao + EM_ABERTO_NA_UNIDADE", fmt(n_ciclo) + " ciclos"),
            ("download", "SEI REST API (first doc/processo)", "raw documents on disk", "—"),
            ("parse", "raw documents", "parsed_documents/<doc>/{text.txt,metadata.json}", fmt(parsed_on_disk) + " parsed folders"),
            ("evaluate", "parsed text", "Documento.topic/.summary (LLM)", fmt(n_top) + " topics"),
            ("embed", "parsed text", "Documento.embedding (bge-m3, 1024-d)", fmt(n_emb) + " embeddings"),
            ("processo-embed", "first-doc embedding + topic + unidade TF-IDF + tipo-ação", "Processo.cluster_features (UMAP-50)", fmt(n_feat) + " feature vectors"),
            ("processo-cluster", "cluster_features", "CategoriaProcesso + CATEGORIZADO_COMO (HDBSCAN + LLM names)", fmt(n_cat) + " categorias"),
        ]
        d.table(["stage", "consumes", "produces", "live count"], [list(r) for r in lineage])

        d.h2("3. Process state and lifetime")
        sit = rows(s, "MATCH (p:Processo) RETURN coalesce(p.situacao,'(null)') AS s, count(*) AS c ORDER BY c DESC")
        d.img(pie([r["s"] for r in sit], [r["c"] for r in sit], "Situação dos processos", "02_situacao.png"), "situacao")
        d.table(["situação", "processos", "%"],
                [[r["s"], fmt(r["c"]), pct(r["c"], n_proc)] for r in sit])

        apc = [r["c"] for r in rows(s, "MATCH (p:Processo)<-[:DO_PROCESSO]-(a:Atividade) WITH p, count(a) AS c RETURN c")]
        if apc:
            d.img(hist(apc, "Atividades por processo", "02_atividades_por_processo.png",
                       bins=50, xlabel="atividades", logy=True), "activities per processo")
            apc_sorted = sorted(apc)
            med = apc_sorted[len(apc_sorted) // 2]
            d.p(f"\nActivities per processo — min {min(apc)}, median {med}, "
                f"mean {sum(apc)/len(apc):.1f}, max {max(apc)} (y-axis log).")

        life = [r["days"] for r in rows(s, """
            MATCH (p:Processo) WHERE p.situacao='concluido'
            MATCH (p)<-[:DO_PROCESSO]-(a:Atividade)
            WITH p, min(a.data_hora) AS lo, max(a.data_hora) AS hi
            WHERE lo IS NOT NULL AND hi IS NOT NULL
            RETURN duration.inDays(lo, hi).days AS days""") if r.get("days") is not None]
        if life:
            clip = [x for x in life if 0 <= x <= 365]
            d.img(hist(clip, "Duração (dias) dos processos concluídos (≤365d)", "02_lifetime.png",
                       bins=60, xlabel="dias"), "lifetime")
            ls = sorted(life)
            d.p(f"\nLifetime (concluded) — median **{ls[len(ls)//2]} days**, mean "
                f"{sum(life)/len(life):.0f} days, max {max(life)} days "
                f"(histogram clipped at 365d).")

        d.h2("4. Document enrichment coverage")
        d.img(barh(["referenced", "parsed (disk)", "embedded", "with topic"],
                   [n_doc, parsed_on_disk, n_emb, n_top],
                   "Document enrichment funnel", "02_doc_coverage.png", xlabel="documents"),
              "coverage")
        d.p(f"\nOf {fmt(n_doc)} referenced documents, only the **first document per processo** is "
            f"downloaded/parsed (volume + access limits): {fmt(n_emb)} embedded, {fmt(n_top)} with an "
            f"LLM topic/summary.")

        d.h2("5. Most common dimensions")
        tp = rows(s, "MATCH (p:Processo)-[:TEM_TIPO]->(t:TipoProcedimento) RETURN t.nome AS n, count(*) AS c ORDER BY c DESC LIMIT 15")
        if tp:
            d.h3("Top tipo_procedimento (SEI official type)")
            d.img(barh([r["n"][:42] for r in tp], [r["c"] for r in tp],
                       "Top tipos de procedimento", "02_tipo_proc.png", xlabel="processos"), "tipo")
        tu = rows(s, "MATCH (a:Atividade)-[:EXECUTADO_PELA_UNIDADE]->(u:Unidade) RETURN u.sigla AS n, count(*) AS c ORDER BY c DESC LIMIT 15")
        if tu:
            d.h3("Top unidades (by activity volume)")
            d.img(barh([r["n"][-38:] for r in tu], [r["c"] for r in tu],
                       "Top unidades", "02_unidades.png", xlabel="atividades"), "unidades")
        ta = rows(s, "MATCH (a:Atividade) RETURN a.tipo_acao AS n, count(*) AS c ORDER BY c DESC LIMIT 15")
        if ta:
            d.h3("Top tipo_acao (activity type)")
            d.img(barh([r["n"] for r in ta], [r["c"] for r in ta],
                       "Top tipos de ação", "02_tipo_acao.png", xlabel="atividades"), "acao")

        d.h2("6. Flow-graph health (event-log imperfections)")
        iso = scalar(s, "MATCH (a:Atividade) WHERE NOT (a)-[:SEGUIDA_POR]-() RETURN count(a)")
        iso_by = rows(s, "MATCH (a:Atividade) WHERE NOT (a)-[:SEGUIDA_POR]-() RETURN a.tipo_acao AS t, count(*) AS c ORDER BY c DESC LIMIT 10")
        d.p(f"Activities off the flow (no `SEGUIDA_POR`): **{fmt(iso)}** ({pct(iso, n_atv)}). "
            "These are dominated by document-scoped events (signatures, bloco operations) that act "
            "on documents rather than the inter-unit flow — see "
            "[`timeline-graph-analysis.md`](../../docs/research/timeline-graph-analysis.md).")
        if iso_by:
            d.img(barh([r["t"] for r in iso_by], [r["c"] for r in iso_by],
                       "Atividades isoladas do fluxo, por tipo", "02_isolated.png", xlabel="atividades",
                       color="#C44E52"), "isolated")

    d.h2("7. Process attributes used for clustering")
    d.p("Each processo is represented by a single vector concatenating five L2-normalized blocks "
        "(content + process shape), reduced to 50-d by UMAP:")
    d.table(["block", "dim", "source", "captures"],
            [["semantic", "1024", "first-doc bge-m3 embedding", "what the process is about"],
             ["topic", "1024", "bge-m3 of first-doc topic+summary", "distilled subject"],
             ["unigram", "≤500", "TF-IDF over the *set* of unidades", "which units (org. profile)"],
             ["bigram", "≤1000", "TF-IDF over consecutive unidade pairs", "routing/flow shape"],
             ["tipo_acao", "~48", "histogram of action types", "what kinds of acts"]])

    d.h2("8. Extrinsic validation — clusters vs official SEI type")
    ex = metrics.get("extrinsic") or {}
    purity, nmi, ari = ex.get("purity"), ex.get("nmi"), ex.get("ari")
    n_eval = ex.get("n_evaluated") or 0
    if purity is not None:
        d.table(["metric", "value", "meaning"],
                [["Purity", f"{purity:.3f}", "fraction in each cluster's majority SEI type"],
                 ["NMI", f"{nmi:.3f}", "normalized mutual information (cluster vs type)"],
                 ["ARI", f"{ari:.3f}", "adjusted Rand index (chance-corrected agreement)"]])
        d.p(f"\nOver **{fmt(n_eval)}** categorized processos with an SEI `tipo_procedimento` "
            f"(macro labels of run `{run_id}`, algorithm `{metrics['meta']['algo']}`, read from "
            f"`{metrics_path}`). "
            f"Purity **{purity:.1%}** indicates clusters are largely coherent with the official type; "
            "the moderate ARI/NMI is expected — emergent families deliberately split or merge official "
            "types because the clustering also keys on **flow** (unidades) and **content** (first-doc), "
            "not only the declared type. This is the §4.1 extrinsic check from "
            "[`algorithms.md`](../../docs/architecture/algorithms.md).")
    else:
        d.p("\n_Extrinsic metrics unavailable in the artifact "
            f"(`{metrics_path}` has no SEI `tipo_procedimento` reference)._")

    d.h2("9. Unit permanence and inter-unit handovers")
    with neo4j_session() as s:
        hold = rows(s, """MATCH (p:Processo)-[r:PASSOU_PELA_UNIDADE]->(u:Unidade)
                          RETURN u.sigla AS u, count(*) AS visitas, avg(r.duracao_acumulada_horas) AS h
                          ORDER BY h DESC LIMIT 12""")
        if hold:
            d.h3("Units that hold processes longest (avg accumulated time)")
            d.table(["unidade", "visitas", "média (dias)"],
                    [[r["u"], fmt(r["visitas"]), f"{r['h']/24:.0f}"] for r in hold])
            d.img(barh([r["u"][-34:] for r in hold], [r["h"]/24 for r in hold],
                       "Unidades que mais retêm o processo (média, dias)", "02_hold.png",
                       xlabel="dias"), "hold")
        hv = rows(s, """MATCH (a:Atividade {tipo_acao:'PROCESSO-REMETIDO-UNIDADE'})-[:REMETIDO_PELA_UNIDADE]->(src:Unidade)
                        MATCH (a)-[:EXECUTADO_PELA_UNIDADE]->(dst:Unidade)
                        RETURN src.sigla AS s, dst.sigla AS d, count(*) AS c ORDER BY c DESC LIMIT 12""")
        if hv:
            d.h3("Top inter-unit handovers (source → destination, count)")
            d.table(["de (remetente)", "para (destino)", "remessas"],
                    [[r["s"], r["d"], fmt(r["c"])] for r in hv])
        hub = rows(s, """MATCH (a:Atividade {tipo_acao:'PROCESSO-REMETIDO-UNIDADE'})-[:REMETIDO_PELA_UNIDADE]->(src:Unidade)
                         RETURN src.sigla AS u, count(*) AS sent ORDER BY sent DESC LIMIT 6""")
        if hub:
            d.h3("Busiest sender units — where they send to / receive from (top, count)")
            hub_rows = []
            for h in hub:
                st = rows(s, """MATCH (a:Atividade {tipo_acao:'PROCESSO-REMETIDO-UNIDADE'})-[:REMETIDO_PELA_UNIDADE]->(:Unidade {sigla:$u})
                                MATCH (a)-[:EXECUTADO_PELA_UNIDADE]->(dst:Unidade)
                                RETURN dst.sigla AS d, count(*) AS c ORDER BY c DESC LIMIT 1""", u=h["u"])
                rf = rows(s, """MATCH (a:Atividade {tipo_acao:'PROCESSO-REMETIDO-UNIDADE'})-[:EXECUTADO_PELA_UNIDADE]->(:Unidade {sigla:$u})
                                MATCH (a)-[:REMETIDO_PELA_UNIDADE]->(src:Unidade)
                                RETURN src.sigla AS s, count(*) AS c ORDER BY c DESC LIMIT 1""", u=h["u"])
                hub_rows.append([h["u"], fmt(h["sent"]),
                                 f"{st[0]['d']} ({fmt(st[0]['c'])})" if st else "—",
                                 f"{rf[0]['s']} ({fmt(rf[0]['c'])})" if rf else "—"])
            d.table(["unidade", "remessas enviadas", "→ envia mais p/", "← recebe mais de"], hub_rows)

    d.h2("10. Insights, flaws and observations")
    d.p(
        "- **Right-censoring (survivorship bias).** Clustering covers all processos, but ~37% are still "
        "`em_andamento` with incomplete traces; long-running types (e.g. `Licitação`) therefore bias the "
        "downstream trace models (typical-process, prediction) rather than cluster membership — see "
        "[`algorithms.md`](../../docs/architecture/algorithms.md).\n"
        "- **First-document-only bottleneck.** Only the initiating document is analysed; a process "
        "whose subject evolves is characterized by its opening act alone, dispersing it among unrelated "
        "families (the 'missing' contratação cluster).\n"
        "- **Event-log imperfections (Suriadi et al., 2017).** SEI emits concurrent per-remittance "
        "conclusions and unreliably-ordered receipts; the corrected timeline builder reduces isolated "
        "*conclusions* to ≈0; residual isolated activities are document-scoped events by design.\n"
        "- **A fixed feature bug.** The clustering query read the unit from a non-existent "
        "`:Atividade.unidade` property; it now traverses `EXECUTADO_PELA_UNIDADE` — this run is the first "
        "to include the unidade flow signal (unigram/bigram).\n"
        f"- **Validation.** Internal validity **DBCV = {dbcv:.3f}** (from `{metrics_path}`); "
        "extrinsic validation against `tipo_procedimento` is in §8 above.\n"
        "- **Lakehouse in development.** An early extraction returned stale, much smaller counts later "
        "corrected on refresh — results are tied to a snapshot."
    )

    dest = d.write("02-dataset-overview.md")
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
