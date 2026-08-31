#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from pipeline.core.config import Settings
from pipeline.core.logging_setup import configure_logging
from pipeline.core.paths import ARTIFACTS
from pipeline.core.trino_source import make_trino_conn
from pipeline.evidence.artifact import write_artifact
from pipeline.evidence.clustering import select_k as sk
from pipeline.model.predict import is_train_protocolo
from pipeline.model.processo_features import (
    ProcessoInput, apply_cutoff, build_batch_features,
)

log = configure_logging(__name__)

DESCRIPTION = (
    "Modelo A (k-means + cotovelo + nomeacao) sobre os processos CONCLUIDOS do lake "
    "e Modelo B (random forest sobre prefixos de trace) para inferir a familia dos "
    "que ainda estao correndo. Protocolo, limitacoes e como ler a saida: "
    "docs/research/lake-cluster-experiment.md"
)

CUTOFFS = (0.25, 0.5, 0.75, 1.0)
STATUS_CONCLUIDO = "concluido"

_META_SQL = """
SELECT m.protocolo_formatado, m.status, m.tipo_procedimento,
       ia.palavras_chave, ia.entendimento_inicial, ia.categoria,
       d.embedding
FROM iceberg.sei_gold.processos_metadados m
LEFT JOIN iceberg.sei_gold.processos_ia ia
  ON m.protocolo_formatado = ia.protocolo_formatado
LEFT JOIN iceberg.sei_gold.documentos_texto d
  ON d.doc_numero = m.primeiro_doc_numero
WHERE m.orgao_origem = ?
"""

_TRACE_SQL = """
SELECT s.protocolo_formatado,
       CAST(s.data_hora AS VARCHAR) AS ts,
       s.tipo_acao,
       s.unidade
FROM iceberg.sei_silver.processos_atividades s
JOIN iceberg.sei_gold.processos_metadados m
  ON s.protocolo_formatado = m.protocolo_formatado
WHERE m.orgao_origem = ?
  AND s.unidade IS NOT NULL AND s.unidade <> ''
ORDER BY s.protocolo_formatado, s.data_hora
"""


def extrair(conn, orgao: str, limit: int = 0) -> dict[str, dict]:
    cur = conn.cursor()
    try:
        cur.execute(_META_SQL, [orgao])
        cols = [c[0] for c in cur.description]
        processos: dict[str, dict] = {}
        for row in cur.fetchall():
            r = dict(zip(cols, row))
            pf = r["protocolo_formatado"]
            processos[pf] = {
                "protocolo": pf,
                "status": r.get("status"),
                "tipo_procedimento": r.get("tipo_procedimento"),
                "keywords": list(r.get("palavras_chave") or []),
                "entendimento": r.get("entendimento_inicial") or "",
                "categoria": r.get("categoria") or "",
                "embedding": list(r.get("embedding") or []),
                "events": [],
                "atividades": [],
            }
        log.info("extração: %d processos de %s", len(processos), orgao)

        cur.execute(_TRACE_SQL, [orgao])
        n = 0
        while True:
            lote = cur.fetchmany(20000)
            if not lote:
                break
            for pf, ts, tipo, unidade in lote:
                p = processos.get(pf)
                if p is None:
                    continue
                p["events"].append({"ts": ts, "u": unidade})
                p["atividades"].append({"ts": ts, "t": tipo or "OUTROS"})
                n += 1
        log.info("extração: %d atividades", n)
    finally:
        cur.close()

    if limit:
        mantidos = sorted(processos)[:limit]
        processos = {pf: processos[pf] for pf in mantidos}
        log.info("extração: --limit %d aplicado", limit)
    return processos


def _entrada(p: dict, frac: float) -> ProcessoInput:
    events, atividades = p["events"], p["atividades"]
    if frac < 1.0:
        events, atividades = apply_cutoff(events, atividades, frac)
    cronologia = [e["u"] for e in events if e.get("u")]
    return ProcessoInput(
        protocolo_formatado=p["protocolo"],
        documentos=[{"embedding": p["embedding"]}] if p["embedding"] else [],
        unidades_visitadas=sorted(set(cronologia)),
        unidades_cronologicas=cronologia,
        atividades_tipo_acao=[a["t"] for a in atividades if a.get("t")],
        keywords=p["keywords"] or None,
    )


def montar_matriz(processos: dict[str, dict], concluidos: list[str],
                  correndo: list[str]) -> tuple[dict, np.ndarray]:
    entradas, chaves = [], []
    for pf in concluidos:
        for frac in CUTOFFS:
            entradas.append(_entrada(processos[pf], frac))
            chaves.append((pf, frac))
    for pf in correndo:
        entradas.append(_entrada(processos[pf], 1.0))
        chaves.append((pf, None))

    log.info("features: %d visões (%d concluídos × %d cortes + %d em andamento)",
             len(entradas), len(concluidos), len(CUTOFFS), len(correndo))
    batch = build_batch_features(entradas)
    log.info("features: matriz crua %d × %d (semantic=%d topic=%d uni=%d bi=%d "
             "tipo_acao=%d keyword=%d)", *batch.raw.shape, batch.semantic_dim,
             batch.topic_dim, batch.unigram_dim, batch.bigram_dim,
             batch.tipo_acao_dim, batch.keyword_dim)
    return {chave: i for i, chave in enumerate(chaves)}, batch.raw


def reduzir(raw: np.ndarray, idx_treino: np.ndarray, *, n_components: int = 50,
            seed: int = 42) -> np.ndarray:
    import umap
    t0 = time.perf_counter()
    reducer = umap.UMAP(n_components=n_components, metric="cosine",
                        n_neighbors=15, random_state=seed)
    reducer.fit(raw[idx_treino])
    X = reducer.transform(raw).astype(np.float32)
    log.info("UMAP: %d × %d -> %d dims em %.0fs (ajustado em %d linhas)",
             *raw.shape, n_components, time.perf_counter() - t0, len(idx_treino))
    return X


def modelo_a(X: np.ndarray, *, k_min: int, k_max: int, k_step: int, seed: int,
             lam: float) -> tuple[np.ndarray, dict]:
    from sklearn.cluster import KMeans

    ks = list(range(k_min, min(k_max, len(X) - 1) + 1, k_step))
    if not ks:
        raise ValueError(f"grade de k vazia para {len(X)} processos")
    rows, sil_scope = sk.sweep_kmeans(X, ks, seed)
    k_elbow = ks[sk.elbow_index(ks, [r["inertia"] for r in rows])]
    sweep = {
        "algo": "kmeans", "grid": rows,
        "k_elbow": k_elbow,
        "k_best_silhouette": sk._best_by_silhouette(rows, "k"),
        "k_combined": sk._best_by_combined(rows, "k", lam),
        "elbow_method": sk.ELBOW_METHOD,
        "selection": "k_elbow é primário (regra do cotovelo); os demais são comparação",
        "silhouette_metric": "cosine", "silhouette_scope": sil_scope,
        "seed": seed, "redundancy_lambda": lam,
        "kmeans_params": {"n_init": 10, "random_state": seed},
        "grid_spec": {"k_min": k_min, "k_max": k_max, "step": k_step},
        "at_grid_edge": k_elbow in (ks[0], ks[-1]),
    }
    if sweep["at_grid_edge"]:
        log.warning("modelo A: k_elbow=%d caiu na BORDA da grade — alargue a "
                    "varredura antes de confiar nele", k_elbow)
    km = KMeans(n_clusters=k_elbow, random_state=seed, n_init=10).fit(X)
    log.info("modelo A: k_elbow=%d (silhueta=%s, combinado=%s)",
             k_elbow, sweep["k_best_silhouette"], sweep["k_combined"])
    return km, sweep


def nomear(membros: dict[int, list[str]], processos: dict[str, dict], settings,
           *, samples: int = 5, workers: int = 8) -> dict[str, dict]:
    from concurrent.futures import ThreadPoolExecutor

    from pipeline.model.clustering.naming import (
        _disambiguate_names, distinctive_keywords, name_cluster, near_duplicate_groups,
    )
    from pipeline.stages.processo_cluster import _build_llm_call

    llm_call = _build_llm_call(settings)
    corpus_kw: Counter = Counter()
    for p in processos.values():
        corpus_kw.update(p["keywords"])
    n_corpus = max(1, len(processos))

    def _amostra(pf: str) -> dict:
        p = processos[pf]
        return {
            "protocolo": pf,
            "topic": p["categoria"],
            "summary": p["entendimento"],
            "top_unidades": [u for u, _ in Counter(
                e["u"] for e in p["events"] if e.get("u")).most_common(4)],
            "top_tipos_acao": [t for t, _ in Counter(
                a["t"] for a in p["atividades"]).most_common(4)],
        }

    def _kw_counts(protos) -> Counter:
        c: Counter = Counter()
        for pf in protos:
            c.update(processos[pf]["keywords"])
        return c

    def _nome(item):
        lab, protos = item
        cc = _kw_counts(protos)
        return lab, name_cluster(
            [_amostra(pf) for pf in protos[:samples]], llm_call,
            top_keywords=cc.most_common(12),
            distinctive_keywords=distinctive_keywords(
                cc, corpus_kw, n_cluster=len(protos), n_corpus=n_corpus),
        )

    itens = sorted(membros.items(), key=lambda kv: -len(kv[1]))
    out: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for lab, info in pool.map(_nome, itens):
            info["n_members"] = len(membros[lab])
            out[str(lab)] = info

    grupos = near_duplicate_groups({c: i["nome"] for c, i in out.items()}, threshold=0.55)
    colidentes = [g for g in grupos if len(g) > 1]
    if colidentes:
        log.info("nomeação: %d grupos quase-homônimos voltam à LLM com as rivais à vista",
                 len(colidentes))

        def _renomeia(grupo):
            perfis = [f"{out[c]['nome']} ({out[c]['n_members']} processos)" for c in grupo]
            saida = []
            for cid in grupo:
                lab = int(cid)
                protos = membros[lab]
                cc = _kw_counts(protos)
                saida.append((cid, name_cluster(
                    [_amostra(pf) for pf in protos[:samples]], llm_call,
                    sibling_profiles=[p for p in perfis if not p.startswith(out[cid]["nome"])],
                    top_keywords=cc.most_common(12),
                    distinctive_keywords=distinctive_keywords(
                        cc, corpus_kw, n_cluster=len(protos), n_corpus=n_corpus),
                )))
            return saida
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for saida in pool.map(_renomeia, colidentes):
                for cid, info in saida:
                    info["n_members"] = out[cid]["n_members"]
                    out[cid] = info

    _disambiguate_names(out, list(out))
    return out


def modelo_b(X: np.ndarray, indice: dict, concluidos: list[str],
             rotulo_completo: dict[str, int], centroides: np.ndarray, *, seed: int):
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, f1_score

    treino = [pf for pf in concluidos if is_train_protocolo(pf, seed=seed)]
    teste = [pf for pf in concluidos if not is_train_protocolo(pf, seed=seed)]
    log.info("modelo B: %d treino / %d teste (split blake2b por protocolo — um "
             "processo nunca cai dos dois lados em corte nenhum)", len(treino), len(teste))

    def _matriz(protos, fracs):
        linhas = [(pf, f) for pf in protos for f in fracs]
        idx = [indice[(pf, f)] for pf, f in linhas]
        return X[idx], np.array([rotulo_completo[pf] for pf, _ in linhas]), linhas

    Xtr, ytr, _ = _matriz(treino, CUTOFFS)
    rf = RandomForestClassifier(n_estimators=300, class_weight="balanced",
                                random_state=seed, n_jobs=-1).fit(Xtr, ytr)

    majoritaria = Counter(ytr).most_common(1)[0][0]
    por_corte = {}
    for frac in CUTOFFS:
        Xte, yte, _ = _matriz(teste, [frac])
        pred = rf.predict(Xte)
        d = ((Xte[:, None, :] - centroides[None, :, :]) ** 2).sum(axis=2)
        pred_centroide = d.argmin(axis=1)
        por_corte[str(frac)] = {
            "n": int(len(yte)),
            "acuracia": round(float(accuracy_score(yte, pred)), 4),
            "f1_macro": round(float(f1_score(yte, pred, average="macro", zero_division=0)), 4),
            "baseline_centroide": round(float(accuracy_score(yte, pred_centroide)), 4),
            "baseline_majoritaria": round(float((yte == majoritaria).mean()), 4),
        }
        log.info("modelo B corte %.2f: acurácia=%.3f f1=%.3f (centróide=%.3f, majoritária=%.3f)",
                 frac, por_corte[str(frac)]["acuracia"], por_corte[str(frac)]["f1_macro"],
                 por_corte[str(frac)]["baseline_centroide"],
                 por_corte[str(frac)]["baseline_majoritaria"])

    truncados = [v for k, v in por_corte.items() if float(k) < 1.0]
    ganha = all(v["acuracia"] > v["baseline_centroide"] for v in truncados)
    ancora_ok = por_corte["1.0"]["baseline_centroide"] > 0.99
    if not ancora_ok:
        log.error("modelo B: o centróide não fecha em 1.0 no trace COMPLETO (%.3f) — "
                  "espaço e rótulos inconsistentes, o resto da tabela não significa nada",
                  por_corte["1.0"]["baseline_centroide"])
    if not ganha:
        log.warning("modelo B NÃO bate o centróide-mais-próximo nos cortes truncados — "
                    "nesse caso ele não se paga: pontue por centróide e descarte o Modelo B")
    fracos = [k for k, v in por_corte.items() if v["acuracia"] < v["baseline_majoritaria"]]
    if fracos:
        log.warning("modelo B perde para a classe MAJORITÁRIA nos cortes %s — com essa "
                    "evidência não há sinal; considere um piso de confiança mais alto",
                    ", ".join(fracos))

    Xte, yte, _ = _matriz(teste, [1.0])
    pred = rf.predict(Xte)
    recall = {}
    for lab in sorted(set(yte.tolist())):
        m = yte == lab
        recall[str(lab)] = {"n_teste": int(m.sum()),
                            "recall": round(float((pred[m] == lab).mean()), 4)}

    return rf, {"cutoffs": list(CUTOFFS), "n_treino": len(treino), "n_teste": len(teste),
                "por_corte": por_corte,
                "supera_centroide_nos_cortes_truncados": ganha,
                "ancora_centroide_em_1.0_ok": ancora_ok,
                "cortes_abaixo_da_majoritaria": fracos,
                "recall_por_cluster": recall, "seed": seed,
                "rf_params": {"n_estimators": 300, "class_weight": "balanced"},
                "nota": "um único modelo treinado sobre TODOS os cortes: em produção não "
                        "se sabe em que fração do ciclo um processo em andamento está, "
                        "então o modelo tem de funcionar em qualquer prefixo. O preço é "
                        "acurácia menor no trace completo que um modelo dedicado a ele."}


def main() -> int:
    ap = argparse.ArgumentParser(description=DESCRIPTION)
    ap.add_argument("--run-id", default="exp-lake")
    ap.add_argument("--orgao", default="SEAD-PI")
    ap.add_argument("--limit", type=int, default=0, help="recorte determinístico p/ ensaio")
    ap.add_argument("--k-min", type=int, default=20)
    ap.add_argument("--k-max", type=int, default=320)
    ap.add_argument("--k-step", type=int, default=10)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--redundancy-lambda", type=float, default=0.05)
    ap.add_argument("--samples-per-cluster", type=int, default=5)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--skip-naming", action="store_true")
    ap.add_argument("--confianca-min", type=float, default=0.35,
                    help="abaixo disto o Modelo B não grava rótulo")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    settings = Settings.from_env()
    out_dir = ARTIFACTS / "clustering" / args.run_id / "kmeans"
    out_dir.mkdir(parents=True, exist_ok=True)
    params = {"run_id": args.run_id, "orgao": args.orgao, "seed": args.seed}

    conn = make_trino_conn(settings)
    try:
        processos = extrair(conn, args.orgao, args.limit)
    finally:
        conn.close()

    aptos = {pf: p for pf, p in processos.items() if p["events"] and p["embedding"]}
    sem_embedding = sum(1 for p in processos.values() if p["events"] and not p["embedding"])
    concluidos = sorted(pf for pf, p in aptos.items() if p["status"] == STATUS_CONCLUIDO)
    correndo = sorted(pf for pf in aptos if pf not in set(concluidos))
    log.info("corpus: %d aptos (%d concluídos + %d em andamento); %d descartados sem "
             "embedding do 1º documento", len(aptos), len(concluidos), len(correndo),
             sem_embedding)
    if len(concluidos) < args.k_min * 2:
        log.error("concluídos de menos (%d) para varrer k a partir de %d — rode a DAG de "
                  "IA/embeddings antes", len(concluidos), args.k_min)
        return 2

    indice, raw = montar_matriz(aptos, concluidos, correndo)
    idx_completo = np.array([indice[(pf, 1.0)] for pf in concluidos])
    X = reduzir(raw, idx_completo, seed=args.seed)

    km, sweep = modelo_a(X[idx_completo], k_min=args.k_min, k_max=args.k_max,
                         k_step=args.k_step, seed=args.seed, lam=args.redundancy_lambda)
    rotulo = {pf: int(l) for pf, l in zip(concluidos, km.labels_)}
    membros: dict[int, list[str]] = {}
    for pf, lab in rotulo.items():
        membros.setdefault(lab, []).append(pf)

    write_artifact(sweep, out_dir / "k_sweep.json", force=args.force,
                   stage="lake-cluster", params=params)
    write_artifact({"meta": {**params, "algo": "kmeans", "k": int(km.n_clusters),
                             "n": len(rotulo)}, "labels": rotulo},
                   out_dir / "labels.json", force=args.force,
                   stage="lake-cluster", params=params)

    nomes: dict[str, dict] = {}
    if args.skip_naming:
        nomes = {str(l): {"nome": f"Cluster #{l}", "descricao": "", "marcadores": [],
                          "n_members": len(m)} for l, m in membros.items()}
    else:
        nomes = nomear(membros, aptos, settings, samples=args.samples_per_cluster,
                       workers=args.workers)
    write_artifact({"meta": {**params, "algo": "kmeans", "n_clusters": len(nomes)},
                    "names": nomes}, out_dir / "names.json", force=args.force,
                   stage="lake-cluster", params=params)

    rf, avaliacao = modelo_b(X, indice, concluidos, rotulo, km.cluster_centers_,
                             seed=args.seed)
    write_artifact(avaliacao, out_dir / "model_b.json", force=args.force,
                   stage="lake-cluster", params=params)

    atribuicoes = [{"protocolo_formatado": pf, "cluster_id": lab,
                    "cluster_nome": nomes.get(str(lab), {}).get("nome", f"Cluster #{lab}"),
                    "cluster_confianca": 1.0, "cluster_origem": "kmeans-A"}
                   for pf, lab in sorted(rotulo.items())]
    abaixo_do_piso = 0
    if correndo:
        idx = np.array([indice[(pf, None)] for pf in correndo])
        proba = rf.predict_proba(X[idx])
        classes = rf.classes_
        for pf, linha in zip(correndo, proba):
            j = int(linha.argmax())
            conf = float(linha[j])
            if conf < args.confianca_min:
                abaixo_do_piso += 1
                continue
            lab = int(classes[j])
            atribuicoes.append({
                "protocolo_formatado": pf, "cluster_id": lab,
                "cluster_nome": nomes.get(str(lab), {}).get("nome", f"Cluster #{lab}"),
                "cluster_confianca": round(conf, 4), "cluster_origem": "rf-B"})
    log.info("atribuições: %d (%d em andamento ficaram sem rótulo por confiança < %.2f)",
             len(atribuicoes), abaixo_do_piso, args.confianca_min)

    write_artifact({"meta": {**params, "confianca_min": args.confianca_min,
                             "abaixo_do_piso": abaixo_do_piso},
                    "assignments": atribuicoes},
                   out_dir / "assignments.json", force=args.force,
                   stage="lake-cluster", params=params)
    print(json.dumps({"run_id": args.run_id, "k": int(km.n_clusters),
                      "concluidos": len(concluidos), "em_andamento": len(correndo),
                      "atribuicoes": len(atribuicoes),
                      "modelo_b": avaliacao["por_corte"],
                      "supera_centroide": avaliacao["supera_centroide_nos_cortes_truncados"],
                      "out": str(out_dir)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
