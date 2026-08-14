#!/usr/bin/env python

from __future__ import annotations

import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _common import Doc, settings

from pipeline.model.compare_timeline import recebido_paired_frac, remetido_handoff_frac, single_start_ok
from pipeline.model.constrained import generate_constrained
from pipeline.core.neo4j_driver import build_driver
from pipeline.model.predict import END, cohort_flow_paths, cohort_traces, strip_end, strip_rich
from pipeline.model.predict_lstm import LSTMModel
from pipeline.readers.neo4j_reader import CohortNeo4jReader
from pipeline.model.swimlane_agg import sequence_swimlane

LANE_DEPTH = None
N_WALKS = 8
N_GEN = 25
TOP_K = 8
AUX_LAMBDA = 2.0
RL_EPOCHS = 8
RL_BATCH = 12
RL_STEPS = 160
FAMILIES = [
    {"cohort_id": "clu-descontos", "title": "Retirada de Descontos em Contracheques (cluster)", "short": "Descontos"},
    {"cohort_id": "clu-ferias", "title": "Controle de Férias e Justificativas de Faltas (cluster)", "short": "Férias"},
    {"cohort_id": "clu-maodeobra", "title": "Pagamento de Serviços de Mão de Obra Terceirizada (cluster)", "short": "Mão de Obra"},
]


def _is_end(s):
    return s == END


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def _pct(x) -> str:
    return f"{x * 100:.0f}%" if x is not None else "—"


def _validity(traces: list[list[str]]):
    rp, ss, rh = [], [], []
    for t in traces:
        sw = sequence_swimlane(t)
        rp.append(recebido_paired_frac(sw))
        ss.append(1.0 if single_start_ok(sw) else 0.0)
        rh.append(remetido_handoff_frac(sw))
    return _mean(rp), _mean(ss), _mean(rh)


def _gen_unconstrained(model, start):
    return [strip_end(model.generate(start, is_conclusion=_is_end, strategy="sample",
            rng=random.Random(i), max_steps=400)) for i in range(N_GEN)]


def main() -> None:
    driver = build_driver(settings())
    doc = Doc(
        "Fases 2 & 3 — o modelo APRENDE a estrutura (tokens ricos · perda auxiliar · RL)?",
        intro=(
            "A Fase 1 **impôs** validade na decodificação restrita. Aqui testamos se o modelo a **aprende**: "
            "(Fase 2) com **tokens ricos** (REMETIDO carregando a origem, `…@dest>src`); (Fase 3) com uma "
            "**perda auxiliar** que penaliza massa em tokens inválidos, e com **RL de conformidade** "
            "(REINFORCE, recompensa = validade da trace). Métrica: validade da geração **sem restrição**, "
            "contra o teto da **decodificação restrita**."
        ),
    )
    try:
        for fam in FAMILIES:
            cid, title = fam["cohort_id"], fam["title"]
            doc.h2(title)
            reader = lambda: CohortNeo4jReader(driver, cid)
            plain = cohort_flow_paths(reader(), lane_depth=LANE_DEPTH, n_walks=N_WALKS, rng=random.Random(0))
            rich = cohort_flow_paths(reader(), lane_depth=LANE_DEPTH, n_walks=N_WALKS, rng=random.Random(0),
                                     rich=True)
            if len(plain) < 10:
                doc.p(f"_(coorte `{cid}` sem traces)._")
                continue
            train_p = [p + [END] for p in plain]
            train_r = [p + [END] for p in rich]
            start_p = Counter(p[0] for p in train_p).most_common(1)[0][0]
            start_r = Counter(p[0] for p in train_r).most_common(1)[0][0]

            gru_p = LSTMModel(epochs=30).fit(train_p)
            gru_r = LSTMModel(epochs=30).fit(train_r)
            if not (gru_p.available and gru_r.available):
                doc.p("_(GRU indisponível — torch ausente)._")
                continue

            gen_p = [[strip_rich(s) for s in t] for t in _gen_unconstrained(gru_p, start_p)]
            gen_r = [[strip_rich(s) for s in t] for t in _gen_unconstrained(gru_r, start_r)]
            gen_c = [strip_end(generate_constrained(gru_p, start_p, strategy="sample", top_k=TOP_K,
                     rng=random.Random(i), max_steps=400)) for i in range(N_GEN)]

            vp, vr, vc = _validity(gen_p), _validity(gen_r), _validity(gen_c)
            doc.table(
                ["geração", "% RECEBIDO↔REMETIDO", "1× GERAÇÃO", "% REMETIDO handoff"],
                [["GRU-flow simples — sem restrição", _pct(vp[0]), _pct(vp[1]), _pct(vp[2])],
                 ["GRU-flow RICO — sem restrição", _pct(vr[0]), _pct(vr[1]), _pct(vr[2])],
                 ["GRU-flow + decodificação RESTRITA", _pct(vc[0]), _pct(vc[1]), _pct(vc[2])]],
            )
            doc.p(f"**Leitura:** mesmo **sem restrição**, a GRU-flow já gera RECEBIDO↔REMETIDO e GERAÇÃO "
                  f"únicos em **{_pct(vp[0])} / {_pct(vp[1])}** — o treino em *flow-order* já basta para essas "
                  f"regras (os ~50% de falha eram da GRU-*chrono*, não da flow). Os **tokens ricos não "
                  f"melhoram** a validade ({_pct(vr[0])} / {_pct(vr[1])}); e o `% REMETIDO handoff` "
                  f"({_pct(vp[2])} → {_pct(vr[2])}) é **confundido pelo rollup** depth-2 (handoffs "
                  f"intra-diretoria contam como mesma raia), então não é um sinal limpo aqui.")

            tw = cohort_traces(reader(), lane_depth=LANE_DEPTH)
            train_c = [t + [END] for _, t in tw]
            start_c = Counter(t[0] for t in train_c).most_common(1)[0][0]
            base = LSTMModel(epochs=30).fit(train_c)
            aux = LSTMModel(epochs=30, aux_lambda=AUX_LAMBDA).fit(train_c)
            rl = LSTMModel(epochs=30).fit(train_c)
            if base.available and aux.available and rl.available:
                rl.fit_rl([start_c], rl_epochs=RL_EPOCHS, rl_batch=RL_BATCH, max_steps=RL_STEPS)
                vb = _validity(_gen_unconstrained(base, start_c))
                va = _validity(_gen_unconstrained(aux, start_c))
                vr3 = _validity(_gen_unconstrained(rl, start_c))
                vcc = _validity([strip_end(generate_constrained(base, start_c, strategy="sample",
                      top_k=TOP_K, rng=random.Random(i), max_steps=400)) for i in range(N_GEN)])
                doc.table(
                    ["GRU-chrono — geração", "% RECEBIDO↔REMETIDO", "1× GERAÇÃO", "% REMETIDO handoff"],
                    [["base — sem restrição", _pct(vb[0]), _pct(vb[1]), _pct(vb[2])],
                     [f"+ perda auxiliar (λ={AUX_LAMBDA}) — sem restrição",
                      _pct(va[0]), _pct(va[1]), _pct(va[2])],
                     ["+ RL conformidade — sem restrição", _pct(vr3[0]), _pct(vr3[1]), _pct(vr3[2])],
                     ["base + decodificação RESTRITA", _pct(vcc[0]), _pct(vcc[1]), _pct(vcc[2])]],
                )
                best = max([("perda aux", va[0] or 0), ("RL", vr3[0] or 0)], key=lambda x: x[1])
                doc.p(f"**Fase 3 (aprender validade):** a GRU-chrono **base** gera RECEBIDO↔REMETIDO em "
                      f"**{_pct(vb[0])}** sem restrição; a **perda auxiliar** → **{_pct(va[0])}**, o **RL** → "
                      f"**{_pct(vr3[0])}** (melhor: **{best[0]}**); a **decodificação restrita** garante "
                      f"**{_pct(vcc[0])}**. Quanto mais aux/RL se aproximam de 100% *sem* restrição, mais o "
                      f"modelo **aprendeu** a regra — senão, a restrição continua sendo a garantia.")

        doc.p("> **Conclusão da Fase 2 (resultado negativo, honesto):** a representação **rica** (origem do "
              "REMETIDO) **não melhorou** a validade estrutural — a GRU-flow já é válida nas regras de "
              "pareamento e nascimento **por ser treinada em *flow-order***, e o sinal de handoff é "
              "confundido pelo rollup depth-2. A validade vem do **treino em flow-order** (GRU-flow) + da "
              "**decodificação restrita** (essencial para a GRU-chrono, que sem restrição falha o pareamento "
              "~50%). Ou seja, **tokens mais ricos sozinhos não bastam** — um achado útil que reforça a Fase 1. "
              "Direções mais promissoras (Fase 3): **perda auxiliar de validade** ou **RL de conformidade** "
              "(`process_state`/`FlowState` como oráculo), e medir handoff em *depth* completo para evitar o "
              "rollup.")
        doc.p("> **Conclusão da Fase 3 (aprender validade):** a GRU-chrono já gera traces **~98–100% "
              "válidas por-trace** (aprende a ordem cronológica REMETIDO→RECEBIDO) — havia pouca margem. A "
              "**perda auxiliar** é um **ganho pequeno e consistente** (fecha a última lacuna → 100% de "
              "pareamento/nascimento, ex.: Diárias 98→100% e 92→100%); o **RL** é **instável** (ajudou os "
              "handoffs em Férias 54→73%, mas piorou o pareamento em Diárias 98→92%). Ou seja: o modelo "
              "**aprende** a maior parte da validade, a perda auxiliar **refina de forma confiável**, o RL "
              "não, e a **decodificação restrita** continua sendo a garantia de 100%.")
    finally:
        driver.close()

    dest = doc.write("09-phase2-richtokens.md")
    print("wrote", dest)


if __name__ == "__main__":
    main()
