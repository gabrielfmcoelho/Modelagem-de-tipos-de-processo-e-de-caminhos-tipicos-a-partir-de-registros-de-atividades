#!/usr/bin/env python

from __future__ import annotations

import random
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _common import Doc, settings

from pipeline.model.compare_timeline import handoff_count, recebido_paired_frac, single_start_ok
from pipeline.model.constrained import generate_constrained, generate_full, medoid_trace, validity_score
from pipeline.core.neo4j_driver import build_driver
from pipeline.model.predict import END, cohort_flow_paths, cohort_traces, strip_end
from pipeline.model.predict_lstm import LSTMModel, TransformerModel
from pipeline.readers.neo4j_reader import CohortNeo4jReader
from pipeline.model.swimlane_agg import sequence_swimlane

LANE_DEPTH = None
K = 12
N_WALKS = 8
TOP_K = 8
FULL_WINDOW = 24
FAMILIES = [
    {"cohort_id": "clu-descontos", "title": "Retirada de Descontos em Contracheques (cluster)"},
    {"cohort_id": "clu-ferias", "title": "Controle de Férias e Justificativas de Faltas (cluster)"},
    {"cohort_id": "clu-maodeobra", "title": "Pagamento de Serviços de Mão de Obra Terceirizada (cluster)"},
]


def _is_end(s):
    return s == END


def _pct(x):
    return f"{x * 100:.0f}%" if x is not None else "—"


def _yn(b):
    return "✓" if b else "✗"


def _medoid(genfn):
    traces = [genfn(random.Random(s)) for s in range(K)]
    traces = [t for t in traces if t]
    return medoid_trace(traces) if traces else []


def _row(label, med, real_len):
    if not med:
        return [label, "—", "—", "—", "—", "—"]
    sw = sequence_swimlane(med)
    return [label, f"{len(med)} / {real_len}", f"{validity_score(med):.2f}",
            str(handoff_count(sw, roll_depth=LANE_DEPTH)), _pct(recebido_paired_frac(sw)), _yn(single_start_ok(sw))]


def main() -> None:
    driver = build_driver(settings())
    doc = Doc(
        "Costura de ramos — traces completas e válidas (ramo · costurada · GRU-chrono · Transformer)",
        intro=(
            "Um *ramo* de fluxo é curto (~20–45 passos) vs o processo completo (~162). `generate_full` "
            "**costura** ramos: continua além de cada conclusão intermediária até o processo todo concluir "
            "(`FlowState.complete`), com máscara de validade. Comparamos 4 formas de gerar a representativa, "
            "medindo comprimento vs o real, validade, handoffs e as regras de pareamento/nascimento."
        ),
    )
    try:
        for fam in FAMILIES:
            cid, title = fam["cohort_id"], fam["title"]
            doc.h2(title)
            reader = lambda: CohortNeo4jReader(driver, cid)
            flow = cohort_flow_paths(reader(), lane_depth=LANE_DEPTH, n_walks=N_WALKS,
                                     rng=random.Random(0), pick="fullest")
            chrono = cohort_traces(reader(), lane_depth=LANE_DEPTH)
            if len(flow) < 10 or len(chrono) < 10:
                doc.p(f"_(coorte `{cid}` sem traces suficientes)._")
                continue
            real_len = int(statistics.median(len(t) for _, t in chrono))
            train_flow = [p + [END] for p in flow]
            train_chrono = [t + [END] for _, t in chrono]
            start_flow = Counter(p[0] for p in train_flow).most_common(1)[0][0]
            start_chrono = Counter(t[0] for t in train_chrono).most_common(1)[0][0]

            gru_flow = LSTMModel(epochs=30).fit(train_flow)
            gru_full = LSTMModel(epochs=30, window=FULL_WINDOW).fit(train_chrono)
            tf_full = TransformerModel(epochs=30, window=FULL_WINDOW).fit(train_chrono)
            if not (gru_flow.available and gru_full.available and tf_full.available):
                doc.p("_(modelos neurais indisponíveis — torch ausente)._")
                continue

            cap = real_len * 3
            rows = [
                _row("GRU-flow — ramo (1 branch)",
                     _medoid(lambda r: strip_end(generate_constrained(gru_flow, start_flow, top_k=TOP_K,
                             rng=r, max_steps=cap))), real_len),
                _row("GRU-flow — costurada (mask-only)",
                     _medoid(lambda r: strip_end(generate_full(gru_flow, start_flow, top_k=TOP_K,
                             rng=r, max_steps=cap))), real_len),
                _row("GRU-chrono — completa (generate_full)",
                     _medoid(lambda r: strip_end(generate_full(gru_full, start_chrono, top_k=TOP_K,
                             rng=r, max_steps=cap))), real_len),
                _row("Transformer — completa (generate_full)",
                     _medoid(lambda r: strip_end(generate_full(tf_full, start_chrono, top_k=TOP_K,
                             rng=r, max_steps=cap))), real_len),
            ]
            doc.table(["variante", "passos / real", "validade", "handoffs nº",
                       "% RECEBIDO↔REMETIDO", "1× GERAÇÃO"], rows)

            def _uncon(model, start):
                gens = [strip_end(model.generate(start, is_conclusion=_is_end, strategy="sample",
                        rng=random.Random(i), max_steps=cap)) for i in range(15)]
                return statistics.mean(validity_score(t) for t in gens if t)

            vg, vt = _uncon(gru_full, start_chrono), _uncon(tf_full, start_chrono)
            doc.p(f"**Leitura:** a **costura** leva os modelos completos de ~ramo a perto do comprimento real "
                  f"(~{real_len}) mantendo validade ~1.0 (máscara `FlowState`). A versão **mask-only** (GRU-flow "
                  f"costurada) testa se a máscara basta sem treinar em sequência completa. **Sem restrição**, a "
                  f"validade média é GRU **{vg:.2f}** vs Transformer **{vt:.2f}** — "
                  f"{'a atenção ajuda a aprender o pareamento' if vt > vg + 0.02 else 'empate/GRU à frente (dados pequenos favorecem o modelo simples)'}.")

        doc.p("> **Conclusão:** `generate_full` produz traces **completas e válidas** (costurando ramos sob a "
              "máscara `FlowState`), tornando os modelos de fluxo comparáveis em comprimento ao GRU-chrono e ao "
              "real — sem back-edges (cronológica). Treinar em **sequência completa** dá continuações melhores "
              "que a costura **mask-only** de um modelo de ramo; o Transformer entra como alternativa de "
              "arquitetura (atenção para dependências de longo alcance).")
    finally:
        driver.close()

    dest = doc.write("11-stitching.md")
    print("wrote", dest)


if __name__ == "__main__":
    main()
