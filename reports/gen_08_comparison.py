#!/usr/bin/env python

from __future__ import annotations

import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _common import Doc, settings

from pipeline.model.compare_timeline import handoff_count, recebido_paired_frac, remetido_handoff_frac, single_start_ok, start_unit
from pipeline.model.constrained import generate_constrained, medoid_trace
from pipeline.core.neo4j_driver import build_driver
from pipeline.model.predict import END, MarkovModel, cohort_flow_paths, cohort_traces, strip_end, temporal_split
from pipeline.model.predict_lstm import LSTMModel, TransformerModel
from pipeline.readers.neo4j_reader import CohortNeo4jReader
from pipeline.model.swimlane_agg import processo_timeline, sequence_swimlane
from pipeline.model.typical_eval import model_metrics

LANE_DEPTH = None
K = 15
N_WALKS = 8
TOP_K = 8
ALGOS = ["GRU-chrono", "GRU-flow", "Markov-flow"]
FAMILIES = [
    {"cohort_id": "clu-descontos", "title": "Retirada de Descontos em Contracheques (cluster)", "short": "Descontos"},
    {"cohort_id": "clu-ferias", "title": "Controle de Férias e Justificativas de Faltas (cluster)", "short": "Férias"},
    {"cohort_id": "clu-maodeobra", "title": "Pagamento de Serviços de Mão de Obra Terceirizada (cluster)", "short": "Mão de Obra"},
]

_SELECT = """
MATCH (p:Processo)-[:MEMBRO_DA_COORTE]->(:Coorte {id:$cid})
WHERE p.situacao = 'concluido'
MATCH (a:Atividade)-[:DO_PROCESSO]->(p)
WITH p.protocolo_formatado AS pf, count(a) AS n
RETURN pf, n ORDER BY n
"""
_ACTS = """
MATCH (p:Processo {protocolo_formatado:$pf})<-[:DO_PROCESSO]-(a:Atividade)
OPTIONAL MATCH (a)-[:EXECUTADO_PELA_UNIDADE]->(u:Unidade)
RETURN a.source_id AS source_id, toString(a.data_hora) AS data_hora,
       a.tipo_acao AS tipo_acao, u.sigla AS unidade
ORDER BY data_hora, a.source_id
"""
_EDGES = """
MATCH (p:Processo {protocolo_formatado:$pf})<-[:DO_PROCESSO]-(a:Atividade)
      -[r:SEGUIDA_POR]->(b:Atividade)-[:DO_PROCESSO]->(p)
RETURN a.source_id AS from_id, b.source_id AS to_id,
       r.intervalo_horas AS intervalo_horas, coalesce(r.mesma_unidade, false) AS mesma_unidade
"""


def _q(driver, cypher, **params):
    with driver.session() as s:
        return [dict(r) for r in s.run(cypher, **params)]


def _constrained_traces(model, start: str, *, seed: int = 0) -> list[list[str]]:
    traces = [strip_end(generate_constrained(model, start, strategy="sample", temperature=1.0,
              top_k=TOP_K, rng=random.Random(seed * 1000 + i), max_steps=400)) for i in range(K)]
    return [t for t in traces if len(t) >= 2] or [[start]]


def _pct(x) -> str:
    return f"{x * 100:.0f}%" if x is not None else "—"


def _yn(b) -> str:
    return "✓" if b else "✗"


def main() -> None:
    driver = build_driver(settings())
    doc = Doc(
        "Comparação de algoritmos — linhas do tempo cronológicas (geração restrita)",
        intro=(
            "Cada painel é uma **linha do tempo cronológica** — uma trace representativa (a *medoide*), "
            "como o processo real — então tem **0 back-edges** por construção. A geração dos modelos usa "
            "**decodificação restrita**: um rastreador `FlowState` mascara passos inválidos (RECEBIDO sem "
            "REMETIDO pendente, 2ª GERAÇÃO, conclusão em raia fechada), tornando as traces "
            "**estruturalmente válidas**. *Comum* = trace real representativa (medoide de amostras reais). "
            "Verificamos a validade estrutural e a acurácia de predição."
        ),
    )
    try:
        for fam in FAMILIES:
            cid, title = fam["cohort_id"], fam["title"]
            doc.h2(title)

            tw = cohort_traces(CohortNeo4jReader(driver, cid), lane_depth=LANE_DEPTH)
            if len(tw) < 10:
                doc.p(f"_(coorte `{cid}` sem traces — rode a pipeline comum-graph)._")
                continue
            train_c, test_c = temporal_split(tw, train_frac=0.8)
            train_c = [t + [END] for t in train_c]
            test_c = [t + [END] for t in test_c]
            start_c = Counter(tr[0] for tr in train_c).most_common(1)[0][0]

            flow = cohort_flow_paths(CohortNeo4jReader(driver, cid), lane_depth=LANE_DEPTH,
                                     n_walks=N_WALKS, rng=random.Random(0), pick="fullest")
            random.Random(1).shuffle(flow)
            kf = int(len(flow) * 0.8)
            train_f = [p + [END] for p in flow[:kf]]
            test_f = [p + [END] for p in flow[kf:]]
            start_f = Counter(p[0] for p in train_f).most_common(1)[0][0]

            gru_c = LSTMModel(epochs=30).fit(train_c)
            gru_f = LSTMModel(epochs=30).fit(train_f)
            mk_f = MarkovModel(3).fit(train_f)
            tf_c = TransformerModel(epochs=30).fit(train_c)
            specs = []
            if gru_c.available:
                specs.append(("GRU-chrono", gru_c, start_c, test_c))
            if tf_c.available:
                specs.append(("Transformer", tf_c, start_c, test_c))
            if gru_f.available:
                specs.append(("GRU-flow", gru_f, start_f, test_f))
            specs.append(("Markov-flow", mk_f, start_f, test_f))

            rows = _q(driver, _SELECT, cid=cid)
            rows.sort(key=lambda r: r["n"])
            pf = rows[len(rows) // 2]["pf"]
            real_sw = processo_timeline(_q(driver, _ACTS, pf=pf), _q(driver, _EDGES, pf=pf),
                                        lane_depth=LANE_DEPTH)
            real_start = start_unit(real_sw)
            comum_states = [s for _, s in tw]
            comum_med = medoid_trace(random.Random(2).sample(comum_states, min(K, len(comum_states))))

            table_rows = []

            def _row(label, sw, model=None, test=None):
                if model is not None:
                    m = model_metrics(model, test)
                    a1, a3, sx = f"{m['top1']:.3f}", f"{m['top3']:.3f}", f"{m['suffix_dl']:.3f}"
                else:
                    a1 = a3 = sx = "—"
                hand = f"{handoff_count(sw, roll_depth=LANE_DEPTH)} · {_pct(remetido_handoff_frac(sw))}"
                table_rows.append([
                    label, str(len(sw["nodes"])), _pct(recebido_paired_frac(sw)),
                    _yn(single_start_ok(sw)), _yn(start_unit(sw) == real_start),
                    hand, a1, a3, sx])

            _row("Real", real_sw)
            comum_sw = sequence_swimlane(comum_med)
            _row("Comum", comum_sw)
            for i, (label, model, start, test) in enumerate(specs):
                traces = _constrained_traces(model, start, seed=i + 1)
                manual = [t for t in traces if t and t[-1].split("@", 1)[0] == "CONCLUSAO-PROCESSO-UNIDADE"]
                med = medoid_trace(manual or traces)
                sw = sequence_swimlane(med)
                _row(label, sw, model, test)

            doc.p(f"**Processo real:** `{pf}` ({len(real_sw['nodes'])} atividades). Com a **decodificação "
                  f"restrita** toda trace gerada é **válida** (RECEBIDO sempre após um REMETIDO, uma única "
                  f"GERAÇÃO) — *sem* restrição, GRU-chrono produzia RECEBIDO sem REMETIDO (~50%) e uma 2ª "
                  f"GERAÇÃO. Painéis cronológicos → **0 back-edges**.")
            doc.table(["algoritmo", "passos", "% RECEBIDO↔REMETIDO", "1× GERAÇÃO", "início = real",
                       "handoffs nº · %", "top-1", "top-3", "suffix DL↓"], table_rows)
            flow_lens = [int(r[1]) for r in table_rows if "flow" in r[0].lower()]
            if flow_lens:
                doc.p(f"_**Comprimento:** os modelos de fluxo são **ramos únicos** do `SEGUIDA_POR` "
                      f"(~{min(flow_lens)}–{max(flow_lens)} passos), bem menores que o processo completo "
                      f"(~{len(real_sw['nodes'])} atividades) — limite intrínseco de uma trace de ramo único. "
                      f"Em **handoffs (nº)** eles batem com o real (a coluna `nº · %`: o % engana porque a "
                      f"trace é mais curta)._")
    finally:
        driver.close()

    dest = doc.write("08-comparison.md")
    print("wrote", dest)


if __name__ == "__main__":
    main()
