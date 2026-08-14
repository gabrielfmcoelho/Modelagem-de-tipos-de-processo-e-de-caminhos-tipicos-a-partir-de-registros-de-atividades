# References — toward an *Artificial Intelligence and Law* article

Curated literature for a future journal article on this project: **process mining of Brazilian state
public-administration processes (SEAD-PI / SEI)** with **machine-learning models (Markov · GRU ·
Transformer)**, **grammar-constrained generation** for structurally-valid process timelines, and
**unsupervised clustering** of administrative process types. Target venue: ***Artificial Intelligence and
Law*** (Springer).

> One file per reference (`<key>.md`) gives the full citation, a link, **why it matters to our work**, and how
> we cite it. This index maps the references to our topics and the article's argument.

## What's in this folder

| kind | files | what it is |
|---|---|---|
| **per-reference notes** | 39 × `<key>.md` | one file per reference: citation, link, why it matters, how we cite it. Indexed by this README |
| **topic surveys** | `lit-*.md` (5) | bulk literature sweeps, each verified against Crossref or the official proceedings: [`lit-ai-law`](lit-ai-law.md) (law & AI governance), [`lit-process-mining`](lit-process-mining.md), [`lit-cluster-validity`](lit-cluster-validity.md), [`lit-brasil-pm`](lit-brasil-pm.md) (Brazilian/lusophone PM & SEI), [`lit-direito-br`](lit-direito-br.md) (Brazilian administrative-law doctrine) |
| **provenance** | [`bibliography-provenance.md`](bibliography-provenance.md) | the audit trail for `article/latex/references.bib` — both verification passes, and what got retracted |

`article/latex/references.bib` is the artifact all of this feeds; nothing here is normative over it.

## The article's argument (problemática → contribution)

1. **Problem.** Public-administration processes are opaque, slow, and hard to audit; administrative-law
   accountability/transparency demands auditable models of *how processes actually run* — not how they're
   prescribed. In Brazil this is a **statutory** duty: the **Lei de Acesso à Informação (12.527/2011)** mandates
   public-process transparency, and the **SEI / Processo Eletrônico Nacional** makes the event log exist and be
   consultable. Our object of study is **protocolos do SEI**. Worse, the **Piauí-government SEI is messy and
   unstandardized** — even similar processes diverge, with **no strong enforcement** of document types, unit
   routing, or when a unit concludes (a classic *spaghetti* log). There **are** norms governing the flow, but
   they are **not enforced and don't cover every procedure** — a textbook *de jure vs de facto* gap. Root cause:
   the SEI was **rolled out during the COVID-19 pandemic** and its use is still **maturing**. So the *prescribed*
   process is unreliable; only the **as-is (de facto)** process can be audited. (→ *AI & Law / e-gov*,
   [`sei-brazil…`](sei-brazil-process-mining.md), [`fuzzy-mining`](gunther-2007-fuzzy-mining.md),
   [`log-imperfection`](suriadi-2017-event-log-imperfection.md), [`conformance`](rozinat-2008-conformance-checking.md),
   [`covid-egov`](covid-egov-brazil-digital-transformation.md))
2. **Approach.** Represent the SEI event log as a **knowledge graph** in Neo4j — protocolos · activities · units ·
   documents, i.e. an **event knowledge graph** (events + entities + *directly-follows* + *correlation*) — then
   **cluster** protocolos into emergent administrative categories and **predict & generate** representative
   process timelines with sequence models. **Unit-of-analysis caveat:** a `protocolo` is our case, but is **not
   always a complete end-to-end process** (often it is one; sometimes a fragment or an object relating to
   others) — *object-centric process mining* names this. We treat each protocolo as a single case: a deliberate,
   stated simplification, and a protocolo is itself a **type** of process that we cluster into families.
   (→ *graphs, process mining, PPM, clustering*)
3. **Gap we hit & fix.** Neural next-activity models (Tax 2017) generate **structurally-invalid / degenerate**
   traces (a RECEBIDO with no prior REMETIDO, infinite activity loops) — and because the **SEI enforces almost
   nothing**, the real traces are noisy and the learned models inherit that noise. Our **grammar-constrained
   decoder** (`FlowState`) is therefore the **enforcement layer the system lacks**: it imposes the
   administrative-flow rules the implementation never did, yielding a clean, **rule-valid** representative from
   messy reality. This is the paper's sharpest contribution. (→ *constrained generation, conformance*)
4. **Why it's AI & Law.** A *valid, representative, explainable* model of an administrative process is an
   instrument for transparency, conformance, and accountability — the journal's core concerns.

## Topics → our work → key references

| topic | where in our work | key refs |
|---|---|---|
| **Graph representation (the core)** | SEI → Neo4j **event knowledge graph** | [Esser 2021 (EKG)](esser-2021-event-knowledge-graphs.md) · [Hogan 2021 (KG)](hogan-2021-knowledge-graphs.md) |
| **Object-centric / case notion** | a *protocolo* ≠ always an end-to-end process | [van der Aalst 2019 (OCPM)](vanderaalst-2019-object-centric-pm.md) |
| **Process mining (foundations)** | event log → graph → discovery | [van der Aalst 2016](vanderaalst-2016-process-mining-book.md) · [Manifesto 2012](ieee-2012-process-mining-manifesto.md) · [Inductive Miner 2013](leemans-2013-inductive-miner.md) |
| **Predictive process monitoring (PPM)** | next-activity accuracy, suffix distance (gen_08/10) | [Tax 2017](tax-2017-lstm-ppm.md) · [Evermann 2017](evermann-2017-deep-learning-process.md) · [Camargo 2019](camargo-2019-lstm-process.md) · [Rama-Maneiro 2021](ramamaneiro-2021-dl-ppm-survey.md) |
| **Sequence models** | Markov · GRU · Transformer (`predict_lstm`) | [Hochreiter 1997](hochreiter-1997-lstm.md) · [Cho 2014](cho-2014-gru.md) · [Vaswani 2017](vaswani-2017-attention.md) |
| **Transformer for PPM** | our `TransformerModel` | [Bukhsh 2021](bukhsh-2021-processtransformer.md) |
| **Trace clustering / variants** | flow-paths, representative medoid (gen_08) | [Greco 2006](greco-2006-clustering-log-traces.md) · [Song 2009](song-2009-trace-clustering.md) |
| **Conformance & constraints** | `FlowState` validity rules | [Pesic 2007 (Declare)](pesic-2007-declare.md) |
| **Constrained generation** | `generate_constrained` / `generate_full` | [Geng 2023](geng-2023-grammar-constrained-decoding.md) · [Hokamp 2017](hokamp-2017-lexically-constrained-decoding.md) |
| **Density clustering + validation** | HDBSCAN macro/micro, DBCV 0.556, UMAP | [Campello 2013](campello-2013-hdbscan.md) · [Moulavi 2014 (DBCV)](moulavi-2014-dbcv.md) · [McInnes 2018 (UMAP)](mcinnes-2018-umap.md) |
| **Embeddings (cluster features)** | first-doc bge-m3 + topic blocks | [Reimers 2019 (SBERT)](reimers-2019-sentence-bert.md) · [Chen 2024 (BGE-M3)](chen-2024-bge-m3.md) |
| **Graph neural networks (PPM)** | DFG node-importance (`gcn.py`); graph-native PPM | [Kipf 2017 (GCN)](kipf-2017-gcn.md) · [GNN-PPM survey](gnn-ppm-survey.md) |
| **Messy / low-enforcement logs** | the Piauí SEI is noisy & unstandardized | [Fuzzy Miner](gunther-2007-fuzzy-mining.md) · [Heuristics Miner](weijters-2011-heuristics-miner.md) · [log-quality](suriadi-2017-event-log-imperfection.md) |
| **Conformance (de jure vs de facto)** | as-is modeling; `validity_score` ≈ fitness | [Rozinat 2008](rozinat-2008-conformance-checking.md) |
| **Pandemic-era digitalization** | SEI deployed in COVID-19, use maturing | [COVID e-gov Brazil](covid-egov-brazil-digital-transformation.md) |
| **Explainability (AI & Law)** | interpretable timelines, attention, rules | [Guidotti 2018 (XAI)](guidotti-2018-xai-survey.md) |
| **LLMs for legal/admin text** | topic / summary / cluster naming (Qwen) | [LLM-legal NLP](llm-legal-nlp-survey.md) |
| **RL for generation** | `fit_rl` conformance reward | [Williams 1992 (REINFORCE)](williams-1992-reinforce.md) |
| **SEI / Brazil (domain)** | the object of study + legal mandate | [SEI / Brazil + LAI](sei-brazil-process-mining.md) |
| **AI & Law / e-government** | the framing + target journal | [Bench-Capon 2012](benchcapon-2012-ai-law-50-papers.md) · [CoE 2022](coe-2022-ai-administrative-law.md) · [PM in public admin](processmining-public-administration.md) |
| **BPM lifecycle / redesign (objective)** | transparency → as-is baseline → redesign | [Dumas 2018](dumas-2018-fundamentals-bpm.md) |

## Keywords (for the manuscript)

`process mining` · `predictive process monitoring` · `next-activity prediction` · `business process management`
· `trace clustering` · `process variants` · `conformance checking` · `declarative constraints` ·
`grammar-constrained decoding` · `constrained sequence generation` · `LSTM` · `GRU` · `Transformer` ·
`attention` · `HDBSCAN` · `UMAP` · `DBCV` · `document embeddings` · `graph neural networks` · `e-government` ·
`public administration` · `administrative law` · `transparency` · `accountability` · `explainable AI` ·
`legal process automation` · `SEI` · `Brazilian public sector` · `event knowledge graph` · `knowledge graph` ·
`Neo4j` · `object-centric process mining` · `case notion` · `spaghetti processes` · `unstructured processes` ·
`event-log quality` · `process discovery` · `Fuzzy Miner` · `Heuristics Miner` · `Inductive Miner` ·
`conformance checking` · `de jure vs de facto` · `concept drift` · `digital transformation` ·
`reinforcement learning`

## Status

**39 references across 17 themes** (classics 1992–2013 + recent 2017–2025). A simplified end-to-end **pipeline
diagram** is in [`../architecture/pipeline-overview.md`](../architecture/pipeline-overview.md). Verify each DOI against the publisher
before submission; arXiv IDs are stable. ✅ Filled: SEI/Brazil + LAI; **graph representation** (event knowledge
graphs in Neo4j, knowledge graphs); the **protocolo ≠ always a process** caveat (object-centric PM); the
**messy / low-enforcement** SEI (Fuzzy + Heuristics miners, log-imperfection patterns); process discovery;
explainability; LLM-for-text; RL. **Excluded on purpose:** legal **NER** — we use LLM topic/summary + embeddings,
not NER. Optional later: a Portuguese-NLP citation and an OCEL 2.0 cite if we add the object-centric extension.
