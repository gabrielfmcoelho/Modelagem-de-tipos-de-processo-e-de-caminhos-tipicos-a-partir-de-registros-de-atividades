from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = f"{ROOT}/article/figures"

STYLE = {
    "src": ("#e8e8e8", "#333333"),
    "step": ("#ffffff", "#555555"),
    "model": ("#ffffff", "#555555"),
    "out": ("#e8e8e8", "#333333"),
    "art": ("#f4f4f4", "#777777"),
}

MACRO = [
    ("1  Fonte", "Trino / Iceberg — sei_bronze, sei_gold", "src",
     "processos nascidos na SEAD-PI em 2025 e concluídos no mesmo ano"),
    ("2  Grafo de eventos", "etl", "step",
     "precreate · atividades · timeline · permanencia · situacao   →   grafo de conhecimento de eventos"),
    ("3  Documentos", "download · parse · anonimização · tópico · palavras-chave", "step",
     "primeiro documento por processo; texto, tópico/resumo e palavras-chave normalizadas"),
    ("4  Atributos", "embed → processo-embed", "step",
     "seis blocos de atributos concatenados → redução de dimensionalidade"),
    ("5  Agrupamento", "select-k → cluster-eval → consensus → catálogo", "step",
     "HDBSCAN · k-means · Leiden · consenso   +   estabilidade e auditoria"),
    ("6  Caminho típico", "cluster-control  +  run_typical_eval", "model",
     "células de avaliação × dois alfabetos de traço × cinco famílias de modelo"),
    ("7  Evidência", "noninferiority · ablation · corpus-bias", "step",
     "privacidade (RQ5) · dependência temporal e blocos · viés de duração"),
    ("8  Entrega", "tabelas de resultado  ·  catálogo navegável", "out",
     "tabelas geradas dos artefatos, verificadas contra deriva"),
]

MICROS = {
    "etl": ("Fase 2 — grafo de eventos (etl)", [
        ("sei_atividades, sei_unidades, processos_metadados", "src", "filtro: SEAD-PI · 2025 · concluido"),
        ("precreate", "step", "nós Processo a partir de 'Processo gerado'"),
        ("atividades", "step", "eventos + tipo_acao + unidade executora"),
        ("timeline", "step", "relação SEGUIDA_POR — ordem do log"),
        ("permanencia", "step", "tempo de posse por unidade"),
        ("situacao", "step", "regras de estoque · 1.500/1.500 vs oráculo canônico"),
        ("Neo4j — Processo · Atividade · Unidade · Documento", "art", "grafo de conhecimento de eventos"),
    ]),
    "docs": ("Fase 3 — documentos", [
        ("download", "step", "apenas o primeiro documento (only_first_doc)"),
        ("parse", "step", "PDF/HTML → text.txt"),
        ("anonymize", "step", "PII → marcadores — braço exp-anon"),
        ("evaluate", "step", "LLM: tópico + resumo → :Documento.topic (sincroniza disco↔grafo)"),
        ("keywords", "step", "vocabulário controlado crescente · 2.973 termos, 517 com df≥3"),
        ("artifacts/cache — doc_embeddings · topic_embeddings · keywords_by_processo", "art",
         "caches em disco garantem features reprodutíveis entre braços"),
    ]),
    "features": ("Fase 4 — atributos do processo", [
        ("embed — bge-m3", "step", "1.024-d por documento"),
        ("semântico 1024", "step", "embedding do 1º documento"),
        ("tópico 1024", "step", "tópico+resumo do LLM, embutido"),
        ("unigrama 500  ·  bigrama 1000", "step", "TF-IDF de unidades e transições"),
        ("tipo_acao 48", "step", "histograma de tipos de ação"),
        ("keyword 517", "step", "TF-IDF do vocabulário controlado, min_df=3"),
        ("processo-embed → UMAP-50 (cosseno, seed 42)", "step", "raw_dim 4.113 → 50 · digest carimbado no .npz"),
    ]),
    "cluster": ("Fase 5 — agrupamento", [
        ("select-k", "step", "varredura de k (cotovelo, silhueta) e de resolução"),
        ("cluster-eval", "step", "HDBSCAN · k-means · Leiden — rótulos + métricas internas"),
        ("cluster-consensus", "step", "co-associação entre algoritmos"),
        ("cluster-stability", "step", "Jaccard bootstrap, 25 reajustes"),
        ("cluster-audit", "step", "reajusta do .npz carimbado — 19/19 reproduzem"),
        ("processo-cluster", "step", "nomeia via LLM · escreve cluster_catalog.json"),
    ]),
    "typical": ("Fase 6 — caminho típico", [
        ("cluster-control", "model", "rótulos permutados — piso da hipótese nula"),
        ("divisão 70/30 por processo", "model", "hash blake2b do protocolo — consistente em qualquer subconjunto"),
        ("alfabetos: unit (ação@unidade) · itinerary (unidades visitadas)", "model", ""),
        ("markov(3) · dfg · gru · lstm · transformer", "model", "um conjunto por cluster, min_traces=30"),
        ("decodificação restrita (FlowState)", "model", "caminho válido por construção"),
        ("métricas: top-1 · unit_recall · transition_support · transitions_unseen", "model",
         "contra medoide, sucessor, modelo global e partição embaralhada"),
    ]),
    "evidence": ("Fases 7–8 — evidência e entrega", [
        ("noninferiority", "step", "bootstrap pareado por processo · 20/20 não-inferior"),
        ("ablation", "step", "cortes 0,75/0,5/0,25 + sem-keyword + sem-tópico"),
        ("corpus-bias", "step", "censura à direita — ~18% dos processos de 2025 ausentes"),
        ("results", "out", "agrega artefatos → 20 tabelas em RESULTS.md"),
        ("gen_13_matrix · gen_14_explorer", "out", "explorer.html — clusters × modelos × qualidade"),
    ]),
}


def render(title, rows, path, width=10.4, box_x=1.1, box_w=9.8):
    n = len(rows)
    fig, ax = plt.subplots(figsize=(width, 0.95 * n + 1.15))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, n + 0.75)
    ax.axis("off")

    ys = []
    for i, row in enumerate(rows):
        label, kind, sub = row[0], row[1], row[2]
        y = n - i - 0.15
        ys.append(y)
        fc, ec = STYLE[kind]
        h = 0.68 if sub else 0.48
        ax.add_patch(FancyBboxPatch(
            (box_x, y - h / 2), box_w, h,
            boxstyle="round,pad=0.045,rounding_size=0.09",
            linewidth=1.5, facecolor=fc, edgecolor=ec, zorder=3))
        ax.text(box_x + 0.20, y + (0.11 if sub else 0), label, ha="left", va="center",
                fontsize=10.8, fontweight="bold", color="#1a1a1a", zorder=4)
        if sub:
            ax.text(box_x + 0.20, y - 0.15, sub, ha="left", va="center",
                    fontsize=9.0, color="#3d3d3d", zorder=4)

    mid = box_x + box_w / 2
    for i in range(n - 1):
        ax.add_patch(FancyArrowPatch(
            (mid, ys[i] - 0.32), (mid, ys[i + 1] + 0.32),
            arrowstyle="-|>", mutation_scale=13, linewidth=1.2,
            color="#8a8a8a", zorder=2, shrinkA=0, shrinkB=0))

    ax.text(mid, n + 0.52, title, ha="center", va="center",
            fontsize=13.6, fontweight="bold", color="#1a1a1a")
    fig.tight_layout(pad=0.5)
    for ext in ("svg", "pdf", "png"):
        fig.savefig(f"{path}.{ext}", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return n


MACRO_EN_BLIND = [
    ("1  Source", "Data lake — administrative case records", "src",
     "cases opened and concluded within one calendar year at one secretariat"),
    ("2  Event graph", "ETL", "step",
     "cases · activities · timeline · holding time · status   →   event knowledge graph"),
    ("3  Documents", "download → parse → anonymise · topic/summary · keywords", "step",
     "opening document per case; text, LLM topic, normalised controlled vocabulary"),
    ("4  Features", "embed → case-level features", "step",
     "six feature blocks concatenated → dimensionality reduction"),
    ("5  Clustering", "select-k → cluster → consensus → catalogue", "step",
     "HDBSCAN · k-means · Leiden · consensus   +   stability and reproducibility audit"),
    ("6  Typical paths", "shuffled control  +  per-cluster models", "model",
     "evaluation cells × two trace alphabets × five model families"),
    ("7  Evidence", "non-inferiority · ablations · censoring estimate", "step",
     "privacy (RQ5) · temporal dependency and feature blocks · duration bias"),
    ("8  Output", "generated result tables  ·  interactive catalogue", "out",
     "every reported figure regenerated from artefacts, verified against drift"),
]


def build():
    rows = [(f"{ph}  —  {name}", kind, sub) for ph, name, kind, sub in MACRO]
    n = render("Pipeline de processamento: das fontes ao catálogo de tipos e caminhos típicos",
               rows, f"{OUT}/pipeline-macro")
    print(f"wrote pipeline-macro.{{svg,pdf,png}}  ({n} fases)")
    rows_en = [(f"{ph}  —  {name}", kind, sub) for ph, name, kind, sub in MACRO_EN_BLIND]
    n = render("Processing pipeline: from source records to catalogue of types and typical paths",
               rows_en, f"{OUT}/pipeline-macro-en")
    print(f"wrote pipeline-macro-en.{{svg,pdf,png}}  ({n} phases, anonymised, English)")
    for key, (title, rows) in MICROS.items():
        n = render(title, rows, f"{OUT}/pipeline-micro-{key}")
        print(f"wrote pipeline-micro-{key}.{{svg,pdf,png}}  ({n} etapas)")


if __name__ == "__main__":
    build()
