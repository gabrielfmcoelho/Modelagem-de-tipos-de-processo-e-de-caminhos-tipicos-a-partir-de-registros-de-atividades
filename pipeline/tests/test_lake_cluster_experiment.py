
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "lake_cluster_experiment.py"


def _load():
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location("lake_cluster_experiment", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


FAMILIAS = {
    "diaria": (["SEAD/GAB", "SEAD/SUPGP", "SEAD/DIARIAS"],
               ["GERACAO-PROCEDIMENTO", "GERACAO-DOCUMENTO", "ASSINATURA-DOCUMENTO",
                "PROCESSO-REMETIDO-UNIDADE", "CONCLUSAO-PROCESSO-UNIDADE"],
               ["concessao diarias", "passagem aerea"]),
    "estagio": (["SEAD/GAB", "SEAD/ESTAGIO", "SEAD/RH"],
                ["GERACAO-PROCEDIMENTO", "RECEBIMENTO-DOCUMENTO", "PROCESSO-CIENCIA",
                 "PROCESSO-REMETIDO-UNIDADE", "CONCLUSAO-PROCESSO-UNIDADE"],
                ["contratacao estagiario", "termo compromisso"]),
    "licitacao": (["SEAD/GAB", "SEAD/CPL", "SEAD/JURIDICO", "SEAD/CPL"],
                  ["GERACAO-PROCEDIMENTO", "GERACAO-DOCUMENTO", "PROCESSO-ANEXADO",
                   "AUTENTICACAO-DOCUMENTO", "CONCLUSAO-PROCESSO-UNIDADE"],
                  ["licitacao pregao eletronico", "ata registro precos"]),
}


def _corpus(n_por_familia=40, dim=32, seed=7, frac_correndo=0.25):
    rng = np.random.default_rng(seed)
    base = {f: rng.normal(size=dim) for f in FAMILIAS}
    processos, esperado = {}, {}
    for fam, (unidades, acoes, kws) in FAMILIAS.items():
        for i in range(n_por_familia):
            pf = f"{fam}-{i:03d}"
            correndo = i % int(1 / frac_correndo) == 0
            n_ev = 5 + (i % 4)
            events, atividades = [], []
            for j in range(n_ev):
                ts = f"2025-01-{1 + j:02d}T00:00:00"
                events.append({"ts": ts, "u": unidades[j % len(unidades)]})
                atividades.append({"ts": ts, "t": acoes[j % len(acoes)]})
            if correndo:
                events, atividades = events[:3], atividades[:3]
            emb = base[fam] + rng.normal(scale=0.25, size=dim)
            processos[pf] = {
                "protocolo": pf,
                "status": "em_andamento" if correndo else "concluido",
                "tipo_procedimento": fam, "keywords": list(kws),
                "entendimento": f"processo de {fam}", "categoria": fam,
                "embedding": emb.tolist(), "events": events, "atividades": atividades,
            }
            esperado[pf] = fam
    return processos, esperado


def _preparar(mod, processos):
    concluidos = sorted(pf for pf, p in processos.items() if p["status"] == "concluido")
    correndo = sorted(pf for pf in processos if pf not in set(concluidos))
    indice, raw = mod.montar_matriz(processos, concluidos, correndo)
    idx_completo = np.array([indice[(pf, 1.0)] for pf in concluidos])
    X = mod.reduzir(raw, idx_completo, n_components=8, seed=42)
    return concluidos, correndo, indice, X, idx_completo


def test_corte_encurta_o_trace_e_o_completo_fica_intacto():
    mod = _load()
    p = _corpus(n_por_familia=4)[0]["diaria-001"]
    inteiro = mod._entrada(p, 1.0)
    metade = mod._entrada(p, 0.5)
    assert len(metade.atividades_tipo_acao) < len(inteiro.atividades_tipo_acao)
    assert len(metade.unidades_cronologicas) < len(inteiro.unidades_cronologicas)
    assert (inteiro.atividades_tipo_acao[:len(metade.atividades_tipo_acao)]
            == metade.atividades_tipo_acao)


def test_processo_em_andamento_nao_recebe_corte_artificial():
    mod = _load()
    processos, _ = _corpus(n_por_familia=4)
    concluidos = sorted(pf for pf, p in processos.items() if p["status"] == "concluido")
    correndo = sorted(pf for pf in processos if pf not in set(concluidos))
    indice, _raw = mod.montar_matriz(processos, concluidos, correndo)
    assert all((pf, None) in indice for pf in correndo)
    assert not any((pf, 0.5) in indice for pf in correndo)
    for pf in concluidos:
        assert all((pf, f) in indice for f in mod.CUTOFFS)


def test_todas_as_visoes_vivem_no_mesmo_espaco():
    mod = _load()
    processos, _ = _corpus(n_por_familia=12)
    _c, _r, _i, X, _ic = _preparar(mod, processos)
    assert X.ndim == 2 and len(set([X.shape[1]])) == 1


@pytest.mark.parametrize("n", [40])
def test_modelo_a_recupera_as_familias_plantadas(n):
    mod = _load()
    processos, esperado = _corpus(n_por_familia=n)
    concluidos, _r, _i, X, idx_completo = _preparar(mod, processos)
    km, sweep = mod.modelo_a(X[idx_completo], k_min=2, k_max=8, k_step=1,
                             seed=42, lam=0.05)
    assert sweep["k_elbow"] == km.n_clusters
    assert "k_best_silhouette" in sweep and "k_combined" in sweep

    from collections import Counter
    puros = 0
    for lab in set(km.labels_.tolist()):
        fams = Counter(esperado[pf] for pf, l in zip(concluidos, km.labels_) if l == lab)
        if fams.most_common(1)[0][1] / sum(fams.values()) >= 0.9:
            puros += 1
    assert puros == len(set(km.labels_.tolist())), "todo cluster deve ser >=90% de uma família"


def test_modelo_b_aprende_o_prefixo_e_bate_os_baselines():
    mod = _load()
    processos, _ = _corpus(n_por_familia=60)
    concluidos, _r, indice, X, idx_completo = _preparar(mod, processos)
    km, _s = mod.modelo_a(X[idx_completo], k_min=2, k_max=6, k_step=1, seed=42, lam=0.05)
    rotulo = {pf: int(l) for pf, l in zip(concluidos, km.labels_)}

    _rf, aval = mod.modelo_b(X, indice, concluidos, rotulo, km.cluster_centers_, seed=42)
    assert set(aval["por_corte"]) == {str(f) for f in mod.CUTOFFS}
    assert all(v["n"] > 0 for v in aval["por_corte"].values())

    assert aval["por_corte"]["1.0"]["baseline_centroide"] > 0.99
    assert aval["ancora_centroide_em_1.0_ok"]

    for frac in ("0.25", "0.5", "0.75"):
        v = aval["por_corte"][frac]
        assert v["acuracia"] > v["baseline_centroide"], (frac, v)
    assert aval["supera_centroide_nos_cortes_truncados"]

    curva = [aval["por_corte"][f]["acuracia"] for f in ("0.25", "0.5", "0.75", "1.0")]
    assert curva[-1] > curva[0], curva
    assert set(aval["recall_por_cluster"]) == {str(l) for l in set(km.labels_.tolist())}


def test_split_por_protocolo_nao_vaza_entre_cortes():
    mod = _load()
    from pipeline.model.predict import is_train_protocolo
    protos = [f"p-{i:04d}" for i in range(500)]
    treino = {p for p in protos if is_train_protocolo(p, seed=42)}
    assert treino == {p for p in protos if is_train_protocolo(p, seed=42)}
    assert 0.6 < len(treino) / len(protos) < 0.8
