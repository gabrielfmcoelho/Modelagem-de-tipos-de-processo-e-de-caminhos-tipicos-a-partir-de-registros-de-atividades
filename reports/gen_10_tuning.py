#!/usr/bin/env python

from __future__ import annotations

import random
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _common import Doc, grouped_bars, settings

from pipeline.model.constrained import validity_score
from pipeline.core.neo4j_driver import build_driver
from pipeline.model.predict import END, MarkovModel, cohort_traces, next_step_accuracy, strip_end, train_val_test_split
from pipeline.model.predict_lstm import LSTMModel
from pipeline.readers.neo4j_reader import CohortNeo4jReader

LANE_DEPTH = None
CID, TITLE = "clu-descontos", "Retirada de Descontos em Contracheques (cluster, concluded)"


def _top1(model, test) -> float:
    return next_step_accuracy(model, test, topk=(1,))[1]


def main() -> None:
    driver = build_driver(settings())
    doc = Doc(
        "Ajuste de hiperparâmetros — divisão treino / validação / teste",
        intro=(
            "Metodologia que faltava: em vez de defaults fixos, varremos **um fator por vez** medindo a "
            "**acurácia top-1 na validação** (divisão temporal 60/20/20), escolhemos o melhor valor por "
            "botão, e avaliamos a config recomendada **uma vez** no **teste**. Foco em uma família para "
            "ser tratável."
        ),
    )
    try:
        tw = cohort_traces(CohortNeo4jReader(driver, CID), lane_depth=LANE_DEPTH)
        tr, va, te = train_val_test_split(tw, train_frac=0.6, val_frac=0.2)
        tr = [t + [END] for t in tr]
        va = [t + [END] for t in va]
        te = [t + [END] for t in te]
        doc.p(f"**{TITLE}** · treino **{len(tr)}** / val **{len(va)}** / teste **{len(te)}** "
              f"(divisão temporal). Cada figura mostra o efeito do botão em **top-1 na validação** e na "
              f"**validade da geração** (`validity_score` das traces geradas sem restrição).")

        def gru(epochs=30, hidden=64, window=8):
            return LSTMModel(epochs=epochs, hidden=hidden, window=window).fit(tr)

        start = Counter(t[0] for t in tr).most_common(1)[0][0]

        def _measure(model):
            t1 = _top1(model, va)
            gens = [strip_end(model.generate(start, is_conclusion=lambda s: s == END, strategy="sample",
                    rng=random.Random(i), max_steps=400)) for i in range(15)]
            vals = [validity_score(t) for t in gens if t]
            return t1, (statistics.mean(vals) if vals else 0.0)

        sweeps = {
            "epochs": [(e, *_measure(gru(epochs=e))) for e in (20, 30, 50)],
            "hidden": [(h, *_measure(gru(hidden=h))) for h in (32, 64, 128)],
            "window": [(w, *_measure(gru(window=w))) for w in (4, 8, 12)],
            "markov_order": [(o, *_measure(MarkovModel(o).fit(tr))) for o in (1, 2, 3, 4)],
        }
        best = {}
        for axis, triples in sweeps.items():
            b = max(triples, key=lambda x: x[1])
            best[axis] = b[0]
            doc.h2(f"Sensibilidade — {axis}")
            doc.table(["valor", "val top-1", "validade ger."],
                      [[str(v), f"{t1:.3f}", f"{vl:.2f}"] for v, t1, vl in triples])
            img = grouped_bars([str(v) for v, _, _ in triples],
                               {"val top-1": [t1 for _, t1, _ in triples],
                                "validade ger.": [vl for _, _, vl in triples]},
                               f"efeito de {axis}: top-1 (val) + validade (geração)",
                               f"tuning-{axis}.png", ylabel="")
            doc.img(img, axis)
            doc.p(f"Melhor **{axis} = {b[0]}** (val top-1 **{b[1]:.3f}**, validade {b[2]:.2f}).")

        g = gru()

        def _gen_validity(temp):
            gens = [strip_end(g.generate(start, is_conclusion=lambda s: s == END, strategy="sample",
                    temperature=temp, rng=random.Random(i), max_steps=400)) for i in range(20)]
            return statistics.mean(validity_score(t) for t in gens if t)

        temps = [(t, _gen_validity(t)) for t in (0.7, 1.0, 1.3)]
        doc.h2("Sensibilidade — temperature (validade da geração)")
        doc.table(["temperature", "validade média"], [[str(t), f"{v:.2f}"] for t, v in temps])
        doc.p(f"Melhor **temperature = {max(temps, key=lambda x: x[1])[0]}** (mais validade sem restrição).")

        rec = gru(epochs=best["epochs"], hidden=best["hidden"], window=best["window"])
        rec_test, def_test = _top1(rec, te), _top1(gru(), te)
        doc.h2("Config recomendada — avaliada no teste")
        doc.p(f"GRU **epochs={best['epochs']}, hidden={best['hidden']}, window={best['window']}** → "
              f"**teste top-1 {rec_test:.3f}** (default 30/64/8 = {def_test:.3f}, "
              f"Δ {(rec_test - def_test) * 100:+.1f} pts); Markov melhor ordem = **{best['markov_order']}**. "
              f"*(Varredura OFAT numa família — uma busca em grade conjunta poderia render mais.)*")
    finally:
        driver.close()

    dest = doc.write("10-tuning.md")
    print("wrote", dest)


if __name__ == "__main__":
    main()
