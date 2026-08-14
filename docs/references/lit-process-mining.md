# Process-Mining Literature — Verified References

Compiled for the *Artificial Intelligence and Law* (Springer) submission on
emergent process types + typical paths over a SEI event knowledge graph.

**Verification method.** Every entry below was resolved through the Crossref
REST API (`api.crossref.org/works/<DOI>`), which returns registered publisher
metadata: title, author list, container title, volume, issue, page range, ISBN,
and issued date. Abstracts, where quoted, come from the Semantic Scholar Graph
API, arXiv, or the publisher page. **Nothing here is reconstructed from memory.**
Fields that Crossref does not register (e.g. LNCS/LNBIP series volume numbers)
are deliberately omitted rather than guessed — add them only from the physical
proceedings.

**Dedup against `latex/references.bib` (61 entries).** Entries already present
are marked `IN BIB`. Everything else is `NEW`. A prior annotated bibliography
covering anonymisation/LGPD/clustering-algorithms lives in
`docs/references/bibliography-provenance.md`; this file does **not** repeat it.

**Count: 43 verified references** (35 `NEW`, 8 `IN BIB` re-verified).

---

# §1 — Trace clustering in process mining

## 1.1 Greco, Guzzo, Pontieri & Saccà (2006) `IN BIB` (`greco2006clustering`)

```bibtex
@article{greco2006clustering,
  author  = {Greco, Gianluigi and Guzzo, Antonella and Pontieri, Luigi and Sacc{\`a}, Domenico},
  title   = {Discovering Expressive Process Models by Clustering Log Traces},
  journal = {IEEE Transactions on Knowledge and Data Engineering},
  volume  = {18},
  number  = {8},
  pages   = {1010--1027},
  year    = {2006},
  doi     = {10.1109/TKDE.2006.123}
}
```

**Claims.** Mining one model from a heterogeneous log yields a "spaghetti" model
that describes no actual behaviour. The authors iteratively partition traces by
structural features and discover a specialised workflow schema per cluster,
organised into a hierarchy of increasingly refined models.

**Relation.** Foundational justification for our clustering step: it is the
original argument that *one global model is the wrong deliverable* for a
heterogeneous log. We build on it; we differ in that our per-cluster artefact is
a single sequence (typical path), not a workflow schema.

## 1.2 Song, Günther & van der Aalst (2009) `IN BIB` (`song2009trace`)

```bibtex
@incollection{song2009trace,
  author    = {Song, Minseok and G{\"u}nther, Christian W. and van der Aalst, Wil M. P.},
  title     = {Trace Clustering in Process Mining},
  booktitle = {Business Process Management Workshops},
  series    = {Lecture Notes in Business Information Processing},
  publisher = {Springer},
  pages     = {109--120},
  year      = {2009},
  doi       = {10.1007/978-3-642-00328-8_11},
  isbn      = {978-3-642-00328-8}
}
```

**Claims.** Introduces *trace profiles* — activity, transition, performance,
case-attribute, event-attribute and originator profiles — that map each trace to
a feature vector, so any standard vector-space clustering algorithm becomes
applicable to event logs. Clustering on different profiles yields materially
different partitions.

**Relation.** This is the direct ancestor of our feature construction. Our
"unit" alphabet (`action@unit`) is essentially a *transition + originator*
profile; our "itinerary" alphabet is an originator-only profile. **Flag:** the
choice-of-profile question we pose is Song et al.'s question, so we cannot claim
to have raised it.

## 1.3 Bose & van der Aalst (2009) `IN BIB` (`bose2009context`)

```bibtex
@inproceedings{bose2009context,
  author    = {Jagadeesh Chandra Bose, R. P. and van der Aalst, Wil M. P.},
  title     = {Context Aware Trace Clustering: Towards Improving Process Mining Results},
  booktitle = {Proceedings of the 2009 SIAM International Conference on Data Mining (SDM)},
  publisher = {Society for Industrial and Applied Mathematics},
  pages     = {401--412},
  year      = {2009},
  doi       = {10.1137/1.9781611972795.35}
}
```

**Claims.** Bag-of-activities profiles discard order. The paper instead builds
features from conserved *subsequences* (maximal repeats, tandem arrays) — the
"context" of an activity — and shows that the resulting clusters produce process
models with better fitness and comprehensibility than profile-based clustering.

**Relation.** Supports our decision to encode order rather than just activity
frequency. Contrasts with our approach in that we obtain order sensitivity from
document text plus routing history rather than from repeat-based motifs.

## 1.4 De Weerdt, vanden Broucke, Vanthienen & Baesens (2013) — ActiTraC `NEW`

```bibtex
@article{deweerdt2013actitrac,
  author  = {De Weerdt, Jochen and vanden Broucke, Seppe and Vanthienen, Jan and Baesens, Bart},
  title   = {Active Trace Clustering for Improved Process Discovery},
  journal = {IEEE Transactions on Knowledge and Data Engineering},
  volume  = {25},
  number  = {12},
  pages   = {2708--2720},
  year    = {2013},
  doi     = {10.1109/TKDE.2013.64}
}
```

**Claims.** All prior trace clustering optimises a *distance* in feature space,
which is only a proxy for what analysts actually want. ActiTraC instead performs
"active" clustering: it seeds clusters from selected traces and admits a
further trace **only if the accuracy (fitness) of the process model discovered
for that cluster does not significantly degrade**. It reports more accurate
sub-process models at comparable complexity versus distance-based baselines.

**Relation. This is the closest prior work to our core methodological claim.**
"Score the clustering by the downstream model it enables" is precisely
ActiTraC's thesis. See §8 for the exact delta. **Must cite; must not present
model-driven clustering evaluation as new.**

## 1.5 Zandkarimi, Rehse, Soudmand & Hoehle (2020) `NEW`

```bibtex
@inproceedings{zandkarimi2020generic,
  author    = {Zandkarimi, Fareed and Rehse, Jana-Rebecca and Soudmand, Pouya and Hoehle, Hartmut},
  title     = {A Generic Framework for Trace Clustering in Process Mining},
  booktitle = {2020 2nd International Conference on Process Mining (ICPM)},
  publisher = {IEEE},
  pages     = {177--184},
  year      = {2020},
  doi       = {10.1109/ICPM49681.2020.00034}
}
```

**Claims.** A systematic literature review of ~15 years of trace clustering,
distilled into a generic framework whose dimensions are: trace representation,
clustering algorithm, evaluation strategy, and use of additional (non-control-flow)
information. The stated goal of the field is grouping a log into cohesive
sub-logs so discovered models become less complex and easier to understand.

**Relation.** The map we must position against. Use it to state where our
configuration sits in the design space (text + routing representation, HDBSCAN /
Leiden / k-means algorithms, prediction-based evaluation). **Flag:** the paper
already enumerates "evaluation by downstream model quality" as an existing
strategy dimension.

## 1.6 Ferreira, Zacarias, Malheiros & Ferreira (2007) `NEW`

```bibtex
@incollection{ferreira2007sequence,
  author    = {Ferreira, Diogo and Zacarias, Marielba and Malheiros, Miguel and Ferreira, Pedro},
  title     = {Approaching Process Mining with Sequence Clustering: Experiments and Findings},
  booktitle = {Business Process Management (BPM 2007)},
  series    = {Lecture Notes in Computer Science},
  publisher = {Springer},
  pages     = {360--374},
  year      = {2007},
  doi       = {10.1007/978-3-540-75183-0_26},
  isbn      = {978-3-540-75183-0}
}
```

**Claims.** Clusters traces with a **mixture of first-order Markov chains**: each
cluster *is* a Markov model, and a trace is assigned to the cluster whose model
most probably generated it. Clustering and per-cluster sequence-model learning
are therefore a single expectation-maximisation procedure.

**Relation. Second-closest prior work.** "One sequence model per cluster of
traces" is exactly this paper, twenty years earlier, at Markov order 1. Our
3rd-order Markov baseline is a direct descendant. **We must not claim
per-cluster sequence modelling as novel.** Our delta is order, neural
comparators, the explicit typical-path extraction, and the controls.

## 1.7 De Koninck, vanden Broucke & De Weerdt (2018) — act2vec `NEW`

```bibtex
@incollection{dekoninck2018act2vec,
  author    = {De Koninck, Pieter and vanden Broucke, Seppe and De Weerdt, Jochen},
  title     = {act2vec, trace2vec, log2vec, and model2vec: Representation Learning for Business Processes},
  booktitle = {Business Process Management (BPM 2018)},
  series    = {Lecture Notes in Computer Science},
  publisher = {Springer},
  pages     = {305--321},
  year      = {2018},
  doi       = {10.1007/978-3-319-98648-7_18},
  isbn      = {978-3-319-98648-7}
}
```

**Claims.** Adapts word2vec/doc2vec to process data at four granularities
(activity, trace, log, model) and shows learned embeddings beat hand-crafted
profiles on trace clustering and other downstream tasks.

**Relation.** Precedent for representing traces as *learned dense vectors*
before clustering — which is what our sentence-embedding pipeline does. Cite so
that "embed then cluster" is properly attributed. **Flag:** embedding-based
trace clustering is established; only our *text-of-documents* signal is unusual.

## 1.8 De Koninck & De Weerdt (2019) — super-instance trace clustering `NEW`

```bibtex
@inproceedings{dekoninck2019scalable,
  author    = {De Koninck, Pieter and De Weerdt, Jochen},
  title     = {Scalable Mixed-Paradigm Trace Clustering using Super-Instances},
  booktitle = {2019 International Conference on Process Mining (ICPM)},
  publisher = {IEEE},
  pages     = {17--24},
  year      = {2019},
  doi       = {10.1109/ICPM.2019.00014}
}
```

**Claims.** Bridges "model-driven" clustering (expensive, e.g. ActiTraC) and
"similarity-driven" clustering (cheap, e.g. Song et al.) by first collapsing the
log into super-instances and then applying model-quality-driven refinement,
recovering most of the quality at a fraction of the cost.

**Relation.** Useful cost argument if a reviewer asks why we do not run an
ActiTraC-style wrapper on 5,243 cases. Supports our two-stage design (cheap
embedding clustering, then downstream scoring).

## 1.9 De Koninck, Nelissen, vanden Broucke, Baesens, Snoeck & De Weerdt (2021) `NEW`

```bibtex
@article{dekoninck2021expert,
  author  = {De Koninck, Pieter and Nelissen, Klaas and vanden Broucke, Seppe and Baesens, Bart and Snoeck, Monique and De Weerdt, Jochen},
  title   = {Expert-driven trace clustering with instance-level constraints},
  journal = {Knowledge and Information Systems},
  volume  = {63},
  number  = {5},
  pages   = {1197--1220},
  year    = {2021},
  doi     = {10.1007/s10115-021-01548-6}
}
```

**Claims.** Injects must-link/cannot-link constraints elicited from domain
experts into trace clustering, arguing that purely data-driven partitions often
do not match the partitions practitioners consider meaningful.

**Relation.** Directly relevant to our "emergent process types" framing: it is
prior evidence that emergent clusters and administratively meaningful categories
can diverge. Either cite as a limitation (we did not use expert constraints) or
as motivation for our human-readable catalog. **Contrasts** with our fully
unsupervised stance.

## 1.10 Taymouri, La Rosa, Dumas & Maggi (2021) — variant analysis survey `NEW`

```bibtex
@article{taymouri2021variant,
  author  = {Taymouri, Farbod and La Rosa, Marcello and Dumas, Marlon and Maggi, Fabrizio Maria},
  title   = {Business process variant analysis: Survey and classification},
  journal = {Knowledge-Based Systems},
  volume  = {211},
  pages   = {106557},
  year    = {2021},
  doi     = {10.1016/j.knosys.2020.106557}
}
```

**Claims.** Surveys and taxonomises methods that compare two or more variants of
a process, distinguishing techniques by the artefacts compared (logs vs models),
the differences detected (control flow, data, performance), and the statistical
guarantees offered.

**Relation.** The vocabulary authority for "process variant". Important for
terminological hygiene: what we call *process types* are, in this literature,
closer to *discovered variants*. Cite to avoid inventing a term that already
exists.

## 1.11 Bolt, de Leoni & van der Aalst (2018) `NEW`

```bibtex
@article{bolt2018variant,
  author  = {Bolt, Alfredo and de Leoni, Massimiliano and van der Aalst, Wil M. P.},
  title   = {Process variant comparison: Using event logs to detect differences in behavior and business rules},
  journal = {Information Systems},
  volume  = {74},
  pages   = {53--66},
  year    = {2018},
  doi     = {10.1016/j.is.2017.12.006}
}
```

**Claims.** Annotates transition systems built from two event logs and applies
statistical significance testing to highlight where the variants genuinely
differ in behaviour and in the decision rules governing routing.

**Relation.** Method we could build on for a future "which clusters actually
differ" test. Currently relevant as a **control-design precedent**: it is
standard in this literature to test whether an observed difference between
partitions is statistically real — which is what our shuffled-partition control
does.

## 1.12 de Leoni, van der Aalst & Dees (2016) `IN BIB` (`deleoni2016general`)

```bibtex
@article{deleoni2016general,
  author  = {de Leoni, Massimiliano and van der Aalst, Wil M. P. and Dees, Marcus},
  title   = {A general process mining framework for correlating, predicting and clustering dynamic behavior based on event logs},
  journal = {Information Systems},
  volume  = {56},
  pages   = {235--257},
  year    = {2016},
  doi     = {10.1016/j.is.2015.07.003}
}
```

**Claims.** A unified feature-extraction framework that converts event logs into
tabular form so that off-the-shelf correlation, prediction and clustering
methods all become applicable to the same representation.

**Relation.** Prior art for "one representation, several downstream tasks" —
which is structurally our pipeline. Cite when describing the shared feature
layer feeding both clustering and sequence models.

## 1.13 Song & van der Aalst (2008) — organisational mining `NEW`

```bibtex
@article{song2008organizational,
  author  = {Song, Minseok and van der Aalst, Wil M. P.},
  title   = {Towards comprehensive support for organizational mining},
  journal = {Decision Support Systems},
  volume  = {46},
  number  = {1},
  pages   = {300--317},
  year    = {2008},
  doi     = {10.1016/j.dss.2008.07.002}
}
```

**Claims.** Develops the *organisational perspective* of process mining:
discovering organisational models, social networks and role assignments from the
originator field of event logs, including clustering of originators into roles.

**Relation. Direct justification for the "itinerary" alphabet.** Analysing the
sequence of organisational units visited — rather than activities — is the
organisational perspective. This is the citation that keeps our unit-vs-itinerary
comparison from looking ad hoc. **Flag:** the organisational-unit view of a trace
is not new; our contribution is the *controlled comparison* of the two alphabets
on the same downstream task.

---

# §2 — Representative / typical trace discovery

## 2.1 Bose & van der Aalst (2010) — trace alignment `NEW`

```bibtex
@incollection{bose2010tracealignment,
  author    = {Jagadeesh Chandra Bose, R. P. and van der Aalst, Wil M. P.},
  title     = {Trace Alignment in Process Mining: Opportunities for Process Diagnostics},
  booktitle = {Business Process Management (BPM 2010)},
  series    = {Lecture Notes in Computer Science},
  publisher = {Springer},
  pages     = {227--242},
  year      = {2010},
  doi       = {10.1007/978-3-642-15618-2_17},
  isbn      = {978-3-642-15618-2}
}
```

## 2.2 Bose & van der Aalst (2012) — journal version `NEW`

```bibtex
@article{bose2012diagnostics,
  author  = {Jagadeesh Chandra Bose, R. P. and van der Aalst, Wil M. P.},
  title   = {Process diagnostics using trace alignment: Opportunities, issues, and challenges},
  journal = {Information Systems},
  volume  = {37},
  number  = {2},
  pages   = {117--141},
  year    = {2012},
  doi     = {10.1016/j.is.2011.08.003}
}
```

**Claims (2.1/2.2).** Borrows multiple-sequence alignment from bioinformatics and
applies it to event logs: traces are aligned column-wise so that the *consensus*
(conserved core) and the deviations become visually and computationally
explicit. The 2012 journal version extends this with a full diagnostics
methodology and an honest discussion of scalability and interpretation issues.

**Relation. This is the canonical "consensus/representative execution" method
and the strongest alternative to our typical-path extraction.** A reviewer will
ask why we did not align traces per cluster and read off the consensus row.
We need an explicit answer (we do; ours is model-derived rather than
alignment-derived, and yields a probability-scored path). **Must cite.**

## 2.3 Chatain, Carmona & van Dongen (2017) — alignment-based trace clustering `NEW`

```bibtex
@incollection{chatain2017alignment,
  author    = {Chatain, Thomas and Carmona, Josep and van Dongen, Boudewijn},
  title     = {Alignment-Based Trace Clustering},
  booktitle = {Conceptual Modeling (ER 2017)},
  series    = {Lecture Notes in Computer Science},
  publisher = {Springer},
  pages     = {295--308},
  year      = {2017},
  doi       = {10.1007/978-3-319-69904-2_24},
  isbn      = {978-3-319-69904-2}
}
```

**Claims (from the published abstract).** Clusters traces using **model traces as
the centroids of the detected clusters**, computed via a generalisation of
alignment, so that "model explanations of observed behaviour are the driving
force to compute the clusters, instead of current model agnostic approaches
[which] group log traces merely on their vector-space similarity." Requires a
process model as an additional input.

**Relation. Closest prior work on the "typical path per cluster" idea itself:
here the cluster representative is literally a single model trace.** Difference:
they *assume* a model and derive centroids from it; we have no as-is model — that
is the whole problem — and derive the representative from a learned sequence
model. **Must cite; must not claim "representative execution as cluster
centroid" as new.**

## 2.4 Boltenhagen, Chatain & Carmona (2019) `NEW`

```bibtex
@incollection{boltenhagen2019generalized,
  author    = {Boltenhagen, Mathilde and Chatain, Thomas and Carmona, Josep},
  title     = {Generalized Alignment-Based Trace Clustering of Process Behavior},
  booktitle = {Application and Theory of Petri Nets and Concurrency (PETRI NETS 2019)},
  series    = {Lecture Notes in Computer Science},
  publisher = {Springer},
  pages     = {237--257},
  year      = {2019},
  doi       = {10.1007/978-3-030-21571-2_14},
  isbn      = {978-3-030-21571-2}
}
```

## 2.5 Boltenhagen, Chatain & Carmona (2021) — model-based variant analysis `NEW`

```bibtex
@article{boltenhagen2021modelbased,
  author  = {Boltenhagen, Mathilde and Chatain, Thomas and Carmona, Josep},
  title   = {Model-based trace variant analysis of event logs},
  journal = {Information Systems},
  volume  = {102},
  pages   = {101675},
  year    = {2021},
  doi     = {10.1016/j.is.2020.101675}
}
```

**Claims (2.4/2.5).** Generalise Chatain et al. (2017) so the cluster centroid is
not a single model trace but a *sub-model* (a set of runs), and formalise variant
analysis where each variant is summarised by a model-level representative rather
than a frequency-ranked trace.

**Relation.** Establishes that "cluster → compact representative behaviour" is a
mature line of research with formal machinery. **Novelty risk:** if we describe
the typical path as "the first method to summarise a cluster by one canonical
execution", these papers refute it.

## 2.6 van Dongen, Carmona & Chatain (2016) — anti-alignments `NEW`

```bibtex
@incollection{vandongen2016antialignments,
  author    = {van Dongen, Boudewijn F. and Carmona, Josep and Chatain, Thomas},
  title     = {A Unified Approach for Measuring Precision and Generalization Based on Anti-alignments},
  booktitle = {Business Process Management (BPM 2016)},
  series    = {Lecture Notes in Computer Science},
  publisher = {Springer},
  pages     = {39--56},
  year      = {2016},
  doi       = {10.1007/978-3-319-45348-4_3},
  isbn      = {978-3-319-45348-4}
}
```

## 2.7 Chatain, Boltenhagen & Carmona (2021) — anti-alignments journal `NEW`

```bibtex
@article{chatain2021antialignments,
  author  = {Chatain, Thomas and Boltenhagen, Mathilde and Carmona, Josep},
  title   = {Anti-alignments---Measuring the precision of process models and event logs},
  journal = {Information Systems},
  volume  = {98},
  pages   = {101708},
  year    = {2021},
  doi     = {10.1016/j.is.2020.101708}
}
```

**Claims (2.6/2.7).** An *anti-alignment* is a model run maximally distant from
anything in the log; measuring how far a model can stray from observed behaviour
yields principled precision and generalisation metrics.

**Relation.** The formal counterpart to our typical path. If the typical path is
the "most representative" run, the anti-alignment is the "least representative"
one — and its existence is what makes precision measurable. Cite in the
conformance/precision discussion (§4) to justify why a representative path alone
is not a sufficient quality claim.

## 2.8 Delias, Doumpos, Grigoroudis, Manolitzas & Matsatsinis (2015) `NEW`

```bibtex
@article{delias2015robust,
  author  = {Delias, Pavlos and Doumpos, Michael and Grigoroudis, Evangelos and Manolitzas, Panagiotis and Matsatsinis, Nikolaos},
  title   = {Supporting healthcare management decisions via robust clustering of event logs},
  journal = {Knowledge-Based Systems},
  volume  = {84},
  pages   = {203--213},
  year    = {2015},
  doi     = {10.1016/j.knosys.2015.04.012}
}
```

**Claims.** Applies a robust (outlier-tolerant) clustering scheme to real
hospital event logs so that management can reason about coherent groups of cases
rather than a single unusable model, explicitly targeting decision support for
non-technical stakeholders.

**Relation.** Precedent for the *managerial-deliverable* framing of trace
clustering in a public-service setting. Supports our transparency-instrument
argument; weakens any claim that "clustering for stakeholder consumption" is new.

---

# §3 — Next-activity prediction and predictive process monitoring

## 3.1 Tax, Verenich, La Rosa & Dumas (2017) `IN BIB` (`tax2017lstm`)

```bibtex
@incollection{tax2017lstm,
  author    = {Tax, Niek and Verenich, Ilya and La Rosa, Marcello and Dumas, Marlon},
  title     = {Predictive Business Process Monitoring with LSTM Neural Networks},
  booktitle = {Advanced Information Systems Engineering (CAiSE 2017)},
  series    = {Lecture Notes in Computer Science},
  publisher = {Springer},
  pages     = {477--492},
  year      = {2017},
  doi       = {10.1007/978-3-319-59536-8_30},
  isbn      = {978-3-319-59536-8}
}
```

**Claims.** A single LSTM trained on activity + time features predicts the next
activity, its timestamp, the remaining case suffix, and remaining time, beating
the task-specific methods that preceded it.

**Relation.** The canonical LSTM baseline our LSTM/GRU arm reproduces. Note our
setting differs: they predict for a *running* case (operational support); we use
next-activity accuracy as a **retrospective proxy for how learnable a cluster
is**. That reframing needs to be stated explicitly or a reviewer will read our
numbers as a weak PPM result.

## 3.2 Evermann, Rehse & Fettke (2017) `IN BIB` (`evermann2017predicting`)

```bibtex
@article{evermann2017predicting,
  author  = {Evermann, Joerg and Rehse, Jana-Rebecca and Fettke, Peter},
  title   = {Predicting process behaviour using deep learning},
  journal = {Decision Support Systems},
  volume  = {100},
  pages   = {129--140},
  year    = {2017},
  doi     = {10.1016/j.dss.2017.04.003}
}
```

**Claims.** Casts next-event prediction as an NLP-style language-modelling
problem, using embeddings + RNNs over activity sequences, and reports competitive
results on BPI Challenge logs.

**Relation.** The "traces as language" framing that licenses our use of an
alphabet (`action@unit` / unit itinerary) and sequence models over it.

## 3.3 Rama-Maneiro, Vidal & Lama (2023) `IN BIB` (`ramamaneiro2023dlppm`)

```bibtex
@article{ramamaneiro2023dlppm,
  author  = {Rama-Maneiro, Efr{\'e}n and Vidal, Juan C. and Lama, Manuel},
  title   = {Deep Learning for Predictive Business Process Monitoring: Review and Benchmark},
  journal = {IEEE Transactions on Services Computing},
  volume  = {16},
  number  = {1},
  pages   = {739--756},
  year    = {2023},
  doi     = {10.1109/TSC.2021.3139807}
}
```

**Claims.** Systematic review plus a controlled re-implementation and evaluation
of ten deep-learning PPM approaches over twelve public logs. Finds that reported
superiority is often not reproducible under a common protocol and that no
architecture dominates across logs.

**Relation. Central to our "controls" argument.** It is the published evidence
that architecture rankings are log-dependent — so our finding that the
Transformer does not dominate is *consistent with the literature*, not an
anomaly, and must be presented that way.

## 3.4 Tax, Teinemaa & van Zelst (2020) — interdisciplinary comparison `NEW`

```bibtex
@article{tax2020interdisciplinary,
  author  = {Tax, Niek and Teinemaa, Irene and van Zelst, Sebastiaan J.},
  title   = {An interdisciplinary comparison of sequence modeling methods for next-element prediction},
  journal = {Software and Systems Modeling},
  volume  = {19},
  number  = {6},
  pages   = {1345--1365},
  year    = {2020},
  doi     = {10.1007/s10270-020-00789-3}
}
```

**Claims (verbatim from the abstract).** Compares machine-learning sequence
models (Markov models, RNNs), process-discovery models, and grammar-inference
models on next-element prediction over four real-life datasets. "The results
indicate that machine learning techniques that generally have no aim at
interpretability in terms of accuracy outperform techniques from the process
mining and grammar inference fields that aim to yield interpretable models."

**Relation. This is the accuracy-vs-interpretability trade-off our whole
deliverable sits on**, stated and measured. It supports our design (use the
accurate model to *score*, deliver the interpretable artefact) and it is also the
paper that legitimises our Markov baseline as a serious competitor rather than a
straw man. **Must cite.**

## 3.5 Neu, Lahann & Fettke (2022) `NEW`

```bibtex
@article{neu2022slr,
  author  = {Neu, Dominic A. and Lahann, Johannes and Fettke, Peter},
  title   = {A systematic literature review on state-of-the-art deep learning methods for process prediction},
  journal = {Artificial Intelligence Review},
  volume  = {55},
  number  = {2},
  pages   = {801--827},
  year    = {2022},
  doi     = {10.1007/s10462-021-09960-8}
}
```

**Claims.** Reviews the deep-learning process-prediction literature and finds
recurring methodological weaknesses: inconsistent preprocessing, non-comparable
evaluation setups, and missing baselines.

**Relation.** Supports our decision to run explicit **global-model and
shuffled-partition controls**. Cite where we justify the control design.

## 3.6 Peeperkorn, vanden Broucke & De Weerdt (2023) `NEW`

```bibtex
@article{peeperkorn2023rnnstructure,
  author  = {Peeperkorn, Jari and vanden Broucke, Seppe and De Weerdt, Jochen},
  title   = {Can recurrent neural networks learn process model structure?},
  journal = {Journal of Intelligent Information Systems},
  volume  = {61},
  number  = {1},
  pages   = {27--51},
  year    = {2023},
  doi     = {10.1007/s10844-022-00765-x}
}
```

**Claims.** Builds an evaluation framework combining fitness, precision and
generalisation with a k-fold protocol, and shows that LSTMs achieving good
next-activity accuracy can still fail to capture the underlying process
structure, particularly when generalising to unseen variants.

**Relation. The most useful critique for us.** It is direct published evidence
that high next-activity accuracy does *not* license claims about having captured
a process — exactly the overclaim our typical-path deliverable is exposed to.
Cite as a limitation and as a reason our path is validated by conformance
measures, not accuracy alone.

## 3.7 Weytjens & De Weerdt (2020) — CNN vs LSTM `NEW`

```bibtex
@incollection{weytjens2020cnnlstm,
  author    = {Weytjens, Hans and De Weerdt, Jochen},
  title     = {Process Outcome Prediction: CNN vs. LSTM (with Attention)},
  booktitle = {Business Process Management Workshops},
  series    = {Lecture Notes in Business Information Processing},
  publisher = {Springer},
  pages     = {321--333},
  year      = {2020},
  doi       = {10.1007/978-3-030-66498-5_24},
  isbn      = {978-3-030-66498-5}
}
```

**Claims.** Head-to-head comparison of CNNs and (attention-augmented) LSTMs for
outcome prediction; finds the simpler CNN competitive with — and cheaper than —
the recurrent and attention models.

**Relation.** Supports "simple is competitive" without us having to say it
unbacked. Useful precedent for reporting that our Transformer's advantage is
narrow.

## 3.8 Weytjens & De Weerdt (2022) — data leakage `NEW`

```bibtex
@incollection{weytjens2022leakage,
  author    = {Weytjens, Hans and De Weerdt, Jochen},
  title     = {Creating Unbiased Public Benchmark Datasets with Data Leakage Prevention for Predictive Process Monitoring},
  booktitle = {Business Process Management Workshops},
  series    = {Lecture Notes in Business Information Processing},
  publisher = {Springer},
  pages     = {18--29},
  year      = {2022},
  doi       = {10.1007/978-3-030-94343-1_2},
  isbn      = {978-3-030-94343-1}
}
```

**Claims.** Shows that the standard random or prefix-based splits used across the
PPM literature leak information between train and test, inflating reported
performance, and proposes leakage-free dataset construction.

**Relation. Methodological obligation.** If our splits are case-level and
time-aware we should say so and cite this; if they are not, this is a reviewer's
first attack. Also relevant to the shuffled-partition control.

## 3.9 Di Francescomarino, Dumas, Maggi & Teinemaa (2019) `NEW`

```bibtex
@article{difrancescomarino2019clusteringppm,
  author  = {Di Francescomarino, Chiara and Dumas, Marlon and Maggi, Fabrizio Maria and Teinemaa, Irene},
  title   = {Clustering-Based Predictive Process Monitoring},
  journal = {IEEE Transactions on Services Computing},
  volume  = {12},
  number  = {6},
  pages   = {896--909},
  year    = {2019},
  doi     = {10.1109/TSC.2016.2645153}
}
```

**Claims (from the abstract).** A two-phase framework: "prefixes of previous
(completed) cases are clustered according to control flow information", then "a
classifier is built for each cluster"; at runtime a running case is mapped to a
cluster and that cluster's classifier is applied. Implemented in ProM, validated
on a hospital log.

**Relation. Third-closest prior work, and the one that most directly pre-empts
"cluster, then model per cluster, then predict."** Differences: they cluster
*prefixes* for online outcome prediction; we cluster *complete cases* for a
retrospective catalog, and we use the predictive score to *evaluate the
partition* rather than to serve predictions. **Must cite.**

## 3.10 Teinemaa, Dumas, La Rosa & Maggi (2019) `IN BIB` (`teinemaa2019outcome`)

```bibtex
@article{teinemaa2019outcome,
  author  = {Teinemaa, Irene and Dumas, Marlon and La Rosa, Marcello and Maggi, Fabrizio Maria},
  title   = {Outcome-Oriented Predictive Process Monitoring: Review and Benchmark},
  journal = {ACM Transactions on Knowledge Discovery from Data},
  volume  = {13},
  number  = {2},
  pages   = {1--57},
  year    = {2019},
  doi     = {10.1145/3301300}
}
```

**Claims.** Taxonomy plus benchmark of outcome-oriented PPM methods across many
logs, with a strong emphasis on the sequence-encoding choice (last state,
aggregation, index, tensor) as a first-order determinant of performance.

**Relation.** The encoding taxonomy is where our unit-vs-itinerary comparison
belongs conceptually. Also a template for how a benchmark section should be
reported.

## 3.11 Verenich, Dumas, La Rosa, Maggi & Teinemaa (2019) `NEW`

```bibtex
@article{verenich2019remainingtime,
  author  = {Verenich, Ilya and Dumas, Marlon and La Rosa, Marcello and Maggi, Fabrizio Maria and Teinemaa, Irene},
  title   = {Survey and Cross-benchmark Comparison of Remaining Time Prediction Methods in Business Process Monitoring},
  journal = {ACM Transactions on Intelligent Systems and Technology},
  volume  = {10},
  number  = {4},
  pages   = {1--34},
  year    = {2019},
  doi     = {10.1145/3331449}
}
```

**Claims.** Cross-benchmarks remaining-time prediction methods and finds that
relative performance is highly dataset-dependent, with simpler methods often
close to the best.

**Relation.** Second independent source for "no dominant method"; useful if we
want that point supported by more than the Rama-Maneiro benchmark.

## 3.12 Breuker, Matzner, Delfmann & Becker (2016) `NEW`

```bibtex
@article{breuker2016comprehensible,
  author  = {Breuker, Dominic and Matzner, Martin and Delfmann, Patrick and Becker, J{\"o}rg},
  title   = {Comprehensible Predictive Models for Business Processes},
  journal = {MIS Quarterly},
  volume  = {40},
  number  = {4},
  pages   = {1009--1034},
  year    = {2016},
  doi     = {10.25300/MISQ/2016/40.4.10}
}
```

**Claims.** Argues that predictive process models must be *comprehensible* to be
usable by managers, and develops RegPFA — probabilistic finite automata learned
by Bayesian model selection — as an accurate yet inspectable alternative to
black-box predictors.

**Relation.** An MIS Quarterly-level statement of exactly our thesis
(interpretable artefact for organisational stakeholders), predating it. **Flag:**
this is the strongest evidence that "interpretable process prediction for
decision-makers" is a well-established goal. Cite it and inherit its framing
rather than claiming it.

## 3.13 Bukhsh, Saeed & Dijkman (2021) `IN BIB` (`bukhsh2021processtransformer`)

Transformer baseline; retained as cited. No change needed.

---

# §4 — Conformance checking, fitness and precision

## 4.1 Rozinat & van der Aalst (2008) `IN BIB` (`rozinat2008conformance`)

```bibtex
@article{rozinat2008conformance,
  author  = {Rozinat, A. and van der Aalst, W. M. P.},
  title   = {Conformance checking of processes based on monitoring real behavior},
  journal = {Information Systems},
  volume  = {33},
  number  = {1},
  pages   = {64--95},
  year    = {2008},
  doi     = {10.1016/j.is.2007.07.001}
}
```

**Claims.** Introduces token-based replay fitness and the appropriateness
(precision) dimension, establishing that a model must be judged on *both* how
much observed behaviour it permits and how much unobserved behaviour it wrongly
permits.

**Relation.** The origin of the fitness/precision pair we report for the typical
path. Note the well-known token-replay pathologies (see 4.6) if we use replay.

## 4.2 Adriansyah, van Dongen & van der Aalst (2011) `NEW`

```bibtex
@inproceedings{adriansyah2011costbased,
  author    = {Adriansyah, A. and van Dongen, B. F. and van der Aalst, W. M. P.},
  title     = {Conformance Checking Using Cost-Based Fitness Analysis},
  booktitle = {2011 IEEE 15th International Enterprise Distributed Object Computing Conference (EDOC)},
  publisher = {IEEE},
  pages     = {55--64},
  year      = {2011},
  doi       = {10.1109/EDOC.2011.12}
}
```

**Claims.** Replaces token replay with **alignments**: fitness is the minimum
cost of transforming an observed trace into a model-permitted run. Unlike token
replay, alignments always yield an interpretable, complete explanation of where
and how a trace deviates.

**Relation.** The technique we should use (or explicitly justify not using) when
measuring how well the typical path represents its cluster. Alignments give a
per-trace deviation account, which is precisely what an *auditable* catalog needs.

## 4.3 Muñoz-Gama & Carmona (2010) `NEW`

```bibtex
@incollection{munozgama2010precision,
  author    = {Mu{\~n}oz-Gama, Jorge and Carmona, Josep},
  title     = {A Fresh Look at Precision in Process Conformance},
  booktitle = {Business Process Management (BPM 2010)},
  series    = {Lecture Notes in Computer Science},
  publisher = {Springer},
  pages     = {211--226},
  year      = {2010},
  doi       = {10.1007/978-3-642-15618-2_16},
  isbn      = {978-3-642-15618-2}
}
```

**Claims.** Defines ETC-precision by comparing, at each prefix in the log, the
activities the model allows against those actually observed — a scalable
alternative to earlier precision notions.

**Relation.** The standard precision metric. Directly relevant because a
*single* typical path is maximally precise and minimally general by
construction — we must report this honestly rather than presenting precision as
a virtue we earned.

## 4.4 van der Aalst, Adriansyah & van Dongen (2012) `NEW`

```bibtex
@article{vanderaalst2012replaying,
  author  = {van der Aalst, Wil and Adriansyah, Arya and van Dongen, Boudewijn},
  title   = {Replaying history on process models for conformance checking and performance analysis},
  journal = {WIREs Data Mining and Knowledge Discovery},
  volume  = {2},
  number  = {2},
  pages   = {182--192},
  year    = {2012},
  doi     = {10.1002/widm.1045}
}
```

**Claims.** Overview of replay-based conformance and performance analysis:
aligning history against a model both diagnoses deviation and projects timing
information onto the model.

**Relation.** Best short, citable overview for a non-process-mining (law)
audience. Good introductory citation in the conformance subsection.

## 4.5 Buijs, van Dongen & van der Aalst (2012 / 2014) `NEW`

```bibtex
@incollection{buijs2012quality,
  author    = {Buijs, Joos C. A. M. and van Dongen, Boudewijn F. and van der Aalst, Wil M. P.},
  title     = {On the Role of Fitness, Precision, Generalization and Simplicity in Process Discovery},
  booktitle = {On the Move to Meaningful Internet Systems: OTM 2012},
  series    = {Lecture Notes in Computer Science},
  publisher = {Springer},
  pages     = {305--322},
  year      = {2012},
  doi       = {10.1007/978-3-642-33606-5_19},
  isbn      = {978-3-642-33606-5}
}

@article{buijs2014quality,
  author  = {Buijs, J. C. A. M. and van Dongen, B. F. and van der Aalst, W. M. P.},
  title   = {Quality Dimensions in Process Discovery: The Importance of Fitness, Precision, Generalization and Simplicity},
  journal = {International Journal of Cooperative Information Systems},
  volume  = {23},
  number  = {1},
  pages   = {1440001},
  year    = {2014},
  doi     = {10.1142/S0218843014400012}
}
```

**Claims.** Establishes the four-dimensional quality frame and demonstrates that
the dimensions genuinely trade off: maximising fitness and precision together
tends to destroy generalisation and simplicity. Uses a configurable genetic
discovery algorithm to sweep the trade-off surface.

**Relation. The precision/generalisation trade-off citation the brief asks for.**
Essential: a typical path is a deliberate move to the *simplicity* corner at the
cost of fitness and generalisation, and this paper gives us the vocabulary to say
so without it reading as a weakness we failed to notice.

## 4.6 Tax, Lu, Sidorova, Fahland & van der Aalst (2018) `NEW`

```bibtex
@article{tax2018imprecisions,
  author  = {Tax, Niek and Lu, Xixi and Sidorova, Natalia and Fahland, Dirk and van der Aalst, Wil M. P.},
  title   = {The imprecisions of precision measures in process mining},
  journal = {Information Processing Letters},
  volume  = {135},
  pages   = {1--8},
  year    = {2018},
  doi     = {10.1016/j.ipl.2018.01.013}
}
```

**Claims.** Proposes axioms that any precision measure should satisfy and shows
that **no existing precision measure satisfies all of them**, so precision values
must be interpreted with care and not compared naively across models.

**Relation.** Required caution. If we report precision numbers for the typical
path, this paper obliges us to hedge them. Also protects us: it means a
reviewer cannot demand a single "correct" precision figure.

## 4.7 Janssenswillen, Donders, Jouck & Depaire (2017) `NEW`

```bibtex
@article{janssenswillen2017comparative,
  author  = {Janssenswillen, Gert and Donders, Niels and Jouck, Toon and Depaire, Beno{\^i}t},
  title   = {A comparative study of existing quality measures for process discovery},
  journal = {Information Systems},
  volume  = {71},
  pages   = {1--15},
  year    = {2017},
  doi     = {10.1016/j.is.2017.06.002}
}
```

**Claims.** Empirically compares the available fitness/precision/generalisation
implementations and finds they frequently disagree, sometimes ranking the same
pair of models in opposite orders.

**Relation.** Justifies reporting more than one conformance metric, and
justifies not over-reading small differences between clusters.

## 4.8 Carmona, van Dongen, Solti & Weidlich (2018) — book `NEW`

```bibtex
@book{carmona2018conformance,
  author    = {Carmona, Josep and van Dongen, Boudewijn and Solti, Andreas and Weidlich, Matthias},
  title     = {Conformance Checking: Relating Processes and Models},
  publisher = {Springer},
  year      = {2018},
  doi       = {10.1007/978-3-319-99414-7},
  isbn      = {978-3-319-99414-7}
}
```

**Claims.** The standard monograph: alignments, precision/generalisation,
multi-perspective conformance, and how conformance results feed process
improvement.

**Relation.** Single citable anchor for conformance concepts in a paper whose
readers are not process-mining specialists.

## 4.9 Leemans, Fahland & van der Aalst (2018) `NEW`

```bibtex
@article{leemans2018scalable,
  author  = {Leemans, Sander J. J. and Fahland, Dirk and van der Aalst, Wil M. P.},
  title   = {Scalable process discovery and conformance checking},
  journal = {Software \& Systems Modeling},
  volume  = {17},
  number  = {2},
  pages   = {599--631},
  year    = {2018},
  doi     = {10.1007/s10270-016-0545-x}
}
```

**Claims.** The Inductive Miner family: discovery that guarantees sound,
block-structured models and scales to large logs, with matching scalable
conformance approximation.

**Relation.** The obvious comparator a reviewer will name ("why not just run
Inductive Miner per cluster?"). We need an answer; citing this shows we know it
exists.

## 4.10 van der Aalst (2019) — DFG limitations `NEW`

```bibtex
@article{vanderaalst2019dfg,
  author  = {van der Aalst, Wil M. P.},
  title   = {A practitioner's guide to process mining: Limitations of the directly-follows graph},
  journal = {Procedia Computer Science},
  volume  = {164},
  pages   = {321--328},
  year    = {2019},
  doi     = {10.1016/j.procs.2019.12.189}
}
```

**Claims.** Directly-follows graphs — the default view in most commercial tools —
systematically mislead: they cannot represent concurrency, and filtering them
produces graphs implying behaviour that never occurred.

**Relation. Mandatory, because we use a DFG as one of our path learners.** We
must acknowledge this limitation explicitly; not citing it in a transparency
paper would be a serious omission.

---

# §5 — Process mining in the public sector, auditability and accountability

Already in `references.bib` and **not repeated here**: `araujo2023mineracao`
(Brazilian public-sector transparency), `delgado2022discovery` (e-government
case study), `racis2025donot` (public-sector adoption, Italy),
`trottier2025using` (government service delivery), `limaesilva2026analise`
(SEI / TRE-Tocantins), `nai2024` (public procurement), `ieee2012manifesto`.

The additions below supply the **auditability** leg, which the current
bibliography lacks entirely.

## 5.1 van der Aalst, van Hee, van der Werf & Verdonk (2010) `NEW`

```bibtex
@article{vanderaalst2010auditing,
  author  = {van der Aalst, Wil M. P. and van Hee, Kees M. and van der Werf, Jan Martijn and Verdonk, Marc},
  title   = {Auditing 2.0: Using Process Mining to Support Tomorrow's Auditor},
  journal = {Computer},
  volume  = {43},
  number  = {3},
  pages   = {90--93},
  year    = {2010},
  doi     = {10.1109/MC.2010.61}
}
```

**Claims.** Sampling-based auditing is obsolete once every event is recorded:
process mining permits auditing the *whole* population of cases against
prescribed behaviour, shifting audit from retrospective sampling to continuous
conformance.

**Relation. The founding citation for our auditability claim.** It is the
statement that complete event data changes what accountability can mean —
exactly our argument for a public administration.

## 5.2 Jans, Alles & Vasarhelyi (2013) `NEW`

```bibtex
@article{jans2013case,
  author  = {Jans, Mieke and Alles, Michael and Vasarhelyi, Miklos},
  title   = {The case for process mining in auditing: Sources of value added and areas of application},
  journal = {International Journal of Accounting Information Systems},
  volume  = {14},
  number  = {1},
  pages   = {1--20},
  year    = {2013},
  doi     = {10.1016/j.accinf.2012.06.015}
}
```

**Claims.** Argues from the auditing side that process mining adds value that
traditional analytical procedures cannot: it uses the *meta-data of the process*
(who did what, when, in what order) rather than only transaction values, and
therefore detects control violations invisible to sampling.

**Relation.** Bridges process mining to an accountability audience — useful for
an *AI and Law* readership that will not know the process-mining literature.

## 5.3 Jans, Alles & Vasarhelyi (2014) `NEW`

```bibtex
@article{jans2014fieldstudy,
  author  = {Jans, Mieke and Alles, Michael G. and Vasarhelyi, Miklos A.},
  title   = {A Field Study on the Use of Process Mining of Event Logs as an Analytical Procedure in Auditing},
  journal = {The Accounting Review},
  volume  = {89},
  number  = {5},
  pages   = {1751--1773},
  year    = {2014},
  doi     = {10.2308/accr-50807}
}
```

**Claims.** A real audit engagement at a large bank in which process mining
surfaced control violations that the incumbent audit procedures had missed.

**Relation.** Empirical evidence that the auditability claim is not merely
rhetorical. Strengthens the practical-contribution section.

## 5.4 van der Aalst (2019) — object-centric process mining `NEW`

```bibtex
@incollection{vanderaalst2019ocpm,
  author    = {van der Aalst, Wil M. P.},
  title     = {Object-Centric Process Mining: Dealing with Divergence and Convergence in Event Data},
  booktitle = {Software Engineering and Formal Methods (SEFM 2019)},
  series    = {Lecture Notes in Computer Science},
  publisher = {Springer},
  pages     = {3--25},
  year      = {2019},
  doi       = {10.1007/978-3-030-30446-1_1},
  isbn      = {978-3-030-30446-1}
}
```

**Claims.** Flattening multi-object reality into a single case notion causes
*divergence* (repeated activities that are not repetitions) and *convergence*
(events duplicated across cases), silently corrupting downstream analysis.

**Relation. Direct threat to validity for our data.** A SEI process involves
documents, units and people; we chose "process" as the case notion. This paper
names the distortions that choice introduces and must be cited in the
limitations.

---

# §6 — Privacy and anonymisation in process mining

This whole section is `NEW`; `references.bib` currently has text-anonymisation
references but **no process-mining privacy references at all**.

## 6.1 Mannhardt, Koschmider, Baracaldo, Weidlich & Michael (2019) `NEW`

```bibtex
@article{mannhardt2019privacy,
  author  = {Mannhardt, Felix and Koschmider, Agnes and Baracaldo, Nathalie and Weidlich, Matthias and Michael, Judith},
  title   = {Privacy-Preserving Process Mining: Differential Privacy for Event Logs},
  journal = {Business \& Information Systems Engineering},
  volume  = {61},
  number  = {5},
  pages   = {595--614},
  year    = {2019},
  doi     = {10.1007/s12599-019-00613-3}
}
```

**Claims.** Event logs are inherently personal data because a trace is a
behavioural fingerprint of an individual. Provides differentially private
mechanisms for releasing the two most-used log queries — the directly-follows
relation and the trace-variant distribution — and quantifies the resulting
utility loss.

**Relation. Foundational for our anonymisation section**, and specifically for
the claim that removing names is not sufficient: the *sequence itself* can
identify. Our raw-vs-anonymised comparison inherits this framing.

## 6.2 Fahrenkrog-Petersen, van der Aa & Weidlich (2019) — PRETSA `NEW`

```bibtex
@inproceedings{fahrenkrogpetersen2019pretsa,
  author    = {Fahrenkrog-Petersen, Stephan A. and van der Aa, Han and Weidlich, Matthias},
  title     = {PRETSA: Event Log Sanitization for Privacy-aware Process Discovery},
  booktitle = {2019 International Conference on Process Mining (ICPM)},
  publisher = {IEEE},
  pages     = {1--8},
  year      = {2019},
  doi       = {10.1109/ICPM.2019.00012}
}
```

**Claims.** Sanitises a log to satisfy k-anonymity and t-closeness over the
*trace variants* by transforming a prefix tree, deliberately optimising for
retention of process-discovery utility rather than generic data utility.

**Relation.** The clearest precedent for "anonymise, then measure what the
downstream analysis lost" — the shape of our raw-vs-anonymised experiment.
**Flag:** privacy/utility trade-off measurement in process mining is established;
our specific novelty is measuring it on *clustering and next-activity
prediction*, not on discovery. State it that narrowly.

## 6.3 Fahrenkrog-Petersen, van der Aa & Weidlich (2020) — PRIPEL `NEW`

```bibtex
@incollection{fahrenkrogpetersen2020pripel,
  author    = {Fahrenkrog-Petersen, Stephan A. and van der Aa, Han and Weidlich, Matthias},
  title     = {PRIPEL: Privacy-Preserving Event Log Publishing Including Contextual Information},
  booktitle = {Business Process Management (BPM 2020)},
  series    = {Lecture Notes in Computer Science},
  publisher = {Springer},
  pages     = {111--128},
  year      = {2020},
  doi       = {10.1007/978-3-030-58666-9_7},
  isbn      = {978-3-030-58666-9}
}
```

**Claims.** Extends privacy-preserving publishing beyond the control flow to the
*contextual attributes* attached to events, achieving differential privacy at
event level while preserving much of the contextual signal.

**Relation.** Closest published analogue to our situation, where the sensitive
content sits in **document text attached to events**, not only in the sequence.
Cite when justifying that we anonymise attributes rather than only trace shapes.

## 6.4 Fahrenkrog-Petersen, van der Aa & Weidlich (2023) `NEW`

```bibtex
@article{fahrenkrogpetersen2023optimal,
  author  = {Fahrenkrog-Petersen, Stephan A. and van der Aa, Han and Weidlich, Matthias},
  title   = {Optimal event log sanitization for privacy-preserving process mining},
  journal = {Data \& Knowledge Engineering},
  volume  = {145},
  pages   = {102175},
  year    = {2023},
  doi     = {10.1016/j.datak.2023.102175}
}
```

**Claims.** Formalises log sanitisation as an optimisation problem — maximise
utility subject to a privacy guarantee — and gives algorithms with optimality
properties, superseding heuristic sanitisers.

**Relation.** Current state of the art; cite so our simpler
detection-and-masking approach is positioned as a pragmatic deployment choice,
not ignorance of the formal work.

## 6.5 Rafiei & van der Aalst (2021) `NEW`

```bibtex
@article{rafiei2021group,
  author  = {Rafiei, Majid and van der Aalst, Wil M. P.},
  title   = {Group-based privacy preservation techniques for process mining},
  journal = {Data \& Knowledge Engineering},
  volume  = {134},
  pages   = {101908},
  year    = {2021},
  doi     = {10.1016/j.datak.2021.101908}
}
```

**Claims.** Adapts group-based privacy models (k-anonymity and relatives) to the
sequential structure of event data, showing that naive application of tabular
anonymity notions to traces fails.

**Relation.** Supports the argument that our organisational units, being
group-level, carry lower re-identification risk than individual actors — relevant
to why the *itinerary* alphabet is the privacy-safer representation. Useful in
the LGPD discussion.

## 6.6 Elkoumy, Fahrenkrog-Petersen, Fani Sani, Koschmider, Mannhardt, von Voigt, Rafiei & von Waldthausen (2022) `NEW`

```bibtex
@article{elkoumy2022privacy,
  author  = {Elkoumy, Gamal and Fahrenkrog-Petersen, Stephan A. and Fani Sani, Mohammadreza and Koschmider, Agnes and Mannhardt, Felix and von Voigt, Saskia Nu{\~n}ez and Rafiei, Majid and von Waldthausen, Leopold},
  title   = {Privacy and Confidentiality in Process Mining: Threats and Research Challenges},
  journal = {ACM Transactions on Management Information Systems},
  volume  = {13},
  number  = {1},
  pages   = {1--17},
  year    = {2022},
  doi     = {10.1145/3468877}
}
```

*(Crossref: online 2021-10-05, print issue 2022-03-31.)*

**Claims.** Community position paper cataloguing privacy and confidentiality
threats across the process-mining lifecycle — data extraction, analysis,
publication — and identifying open research challenges, including the lack of
utility metrics for anonymised logs.

**Relation. The single best citation for framing our privacy contribution**, and
for our claim that downstream-utility measurement is underexplored: the challenge
is named here as open. Use this rather than asserting the gap on our own
authority.

## 6.7 Elkoumy & Dumas (2022) — Libra `NEW`

```bibtex
@inproceedings{elkoumy2022libra,
  author    = {Elkoumy, Gamal and Dumas, Marlon},
  title     = {Libra: High-Utility Anonymization of Event Logs for Process Mining via Subsampling},
  booktitle = {2022 4th International Conference on Process Mining (ICPM)},
  publisher = {IEEE},
  pages     = {144--151},
  year      = {2022},
  doi       = {10.1109/ICPM57379.2022.9980619}
}
```

**Claims.** Achieves differential privacy for event logs by subsampling plus
noise calibration, reporting substantially better utility at equal privacy budget
than prior noise-injection methods.

**Relation.** Optional; include only if we want to show the utility frontier has
moved recently.

---

# §7 — Event knowledge graphs and multi-entity event data

## 7.1 Esser & Fahland (2021) `IN BIB` (`esser2021ekg`)

```bibtex
@article{esser2021ekg,
  author  = {Esser, Stefan and Fahland, Dirk},
  title   = {Multi-Dimensional Event Data in Graph Databases},
  journal = {Journal on Data Semantics},
  volume  = {10},
  number  = {1-2},
  pages   = {109--141},
  year    = {2021},
  doi     = {10.1007/s13740-021-00122-1}
}
```

**Claims.** Proposes a labelled-property-graph data model for event data in which
events, entities and their correlations are first-class nodes, together with
Cypher query patterns for building and analysing the graph. Removes the need to
flatten multi-entity behaviour into a single case identifier.

**Relation.** The schema our Neo4j event knowledge graph implements. Core
citation for the data-model section.

## 7.2 Esser & Fahland (2019) — earlier conference version `NEW`

```bibtex
@incollection{esser2019storing,
  author    = {Esser, Stefan and Fahland, Dirk},
  title     = {Storing and Querying Multi-dimensional Process Event Logs Using Graph Databases},
  booktitle = {Business Process Management Workshops},
  series    = {Lecture Notes in Business Information Processing},
  publisher = {Springer},
  pages     = {632--644},
  year      = {2019},
  doi       = {10.1007/978-3-030-37453-2_51},
  isbn      = {978-3-030-37453-2}
}
```

**Relation.** Cite only if a short reference is wanted; the 2021 journal version
supersedes it.

## 7.3 Fahland (2022) — Process Mining Handbook chapter `NEW`

```bibtex
@incollection{fahland2022ekg,
  author    = {Fahland, Dirk},
  title     = {Process Mining over Multiple Behavioral Dimensions with Event Knowledge Graphs},
  booktitle = {Process Mining Handbook},
  series    = {Lecture Notes in Business Information Processing},
  publisher = {Springer},
  pages     = {274--319},
  year      = {2022},
  doi       = {10.1007/978-3-031-08848-3_9},
  isbn      = {978-3-031-08848-3}
}
```

**Claims.** Tutorial-level, complete treatment of event knowledge graphs: how to
build them, how to query behaviour across entity types, and what analyses become
possible that are impossible on flattened logs.

**Relation. Best single citation for the EKG method**, and the right one for a
non-specialist audience. Prefer this over the 2021 article when a
methodological (rather than data-model) citation is needed.

## 7.4 Klijn, Mannhardt & Fahland (2023) `NEW`

```bibtex
@incollection{klijn2023aggregating,
  author    = {Klijn, Eva L. and Mannhardt, Felix and Fahland, Dirk},
  title     = {Aggregating Event Knowledge Graphs for Task Analysis},
  booktitle = {Process Mining Workshops},
  series    = {Lecture Notes in Business Information Processing},
  publisher = {Springer},
  pages     = {493--505},
  year      = {2023},
  doi       = {10.1007/978-3-031-27815-0_36},
  isbn      = {978-3-031-27815-0}
}
```

**Claims.** Aggregates an EKG into higher-level "task" structures by clustering
recurring behavioural patterns in the graph, producing a compact summary of what
actors actually do.

**Relation. Uncomfortably close to our contribution, at graph level:**
aggregating an EKG into a small set of recurring behavioural units is what our
process-type catalog does. Different granularity (tasks within cases vs whole
case types) and different method, but this must be cited and distinguished.

## 7.5 van Zelst, Mannhardt, de Leoni & Koschmider (2021) — event abstraction `NEW`

```bibtex
@article{vanzelst2021abstraction,
  author  = {van Zelst, Sebastiaan J. and Mannhardt, Felix and de Leoni, Massimiliano and Koschmider, Agnes},
  title   = {Event abstraction in process mining: literature review and taxonomy},
  journal = {Granular Computing},
  volume  = {6},
  number  = {3},
  pages   = {719--736},
  year    = {2021},
  doi     = {10.1007/s41066-020-00226-2}
}
```

**Claims.** Reviews and taxonomises event-abstraction techniques — methods that
map low-level recorded events onto higher-level, human-meaningful activities —
and identifies the evaluation of abstractions as an open problem.

**Relation. Directly governs our alphabet choice.** `action@unit` versus
`unit`-only is an *event abstraction* decision in this taxonomy's terms. Cite it
so the comparison is framed in the field's own vocabulary — and note that the
review already flags "how do we evaluate an abstraction?" as open, which is the
question our downstream-scoring answer addresses.

---

# §8 — Closest prior work: how we differ

Ranked by threat to our novelty claim.

### 1. De Weerdt et al. (2013), ActiTraC — *the* closest

**They do:** cluster traces such that the *process model discovered for each
cluster* stays accurate. Clustering is explicitly driven by downstream model
quality.

**We do:** cluster on document text + routing history, then score the partition
by the *predictive* performance of sequence models trained per cluster.

**Real differences, stated conservatively:**
- ActiTraC's downstream artefact is a discovered **process model** scored by
  replay fitness; ours is a **next-activity predictor** scored by accuracy. Model
  fitness and predictive accuracy are different objectives and can disagree
  (Peeperkorn et al. 2023 shows exactly this).
- ActiTraC uses the score *inside* the clustering loop (a wrapper method); we use
  it *after*, as an external evaluation across independently produced partitions
  and two alphabets. That is a comparison protocol, not a new clustering
  algorithm — say so.
- ActiTraC has no controls; we add a shuffled-partition null and a global-model
  baseline.

**What we must NOT say:** "we are the first to evaluate a trace clustering by
what it enables downstream."

### 2. Ferreira et al. (2007), sequence clustering

**They do:** clustering *is* a mixture of first-order Markov chains — one
sequence model per cluster, learned jointly.

**We do:** cluster first, then fit per-cluster models at Markov order 3, plus
GRU/LSTM/Transformer.

**Real differences:** model order and family; a separate typical-path extraction
step; controls. **Not** the idea of a per-cluster sequence model.

### 3. Di Francescomarino et al. (2019), clustering-based PPM

**They do:** cluster prefixes by control flow, train a classifier per cluster,
route running cases to the matching cluster's classifier at runtime.

**We do:** cluster complete cases, train per-cluster sequence models, and use
their performance to *evaluate the partition* and to *derive an artefact*.

**Real differences:** online vs retrospective; prefixes vs whole cases;
prediction as product vs prediction as measuring instrument. The
"cluster-then-model" architecture is theirs.

### 4. Chatain et al. (2017) + Boltenhagen et al. (2019, 2021), alignment-based clustering

**They do:** cluster with **model traces as centroids** — a representative
execution per cluster is the central object.

**We do:** derive a representative path from a learned sequence model.

**Real differences:** they require an input process model (we have none — a
public administration with no documented as-is model is our premise); their
representative is exact under an alignment cost, ours is probabilistic under a
learned model. **The concept "one canonical execution per cluster" is theirs.**

### 5. Bose & van der Aalst (2010, 2012), trace alignment

**They do:** multiple-sequence alignment yields a consensus across a set of
traces.

**We do:** model-derived typical path.

**Reviewer question we must pre-empt:** why not just align? Honest answer: our
paths carry a likelihood and are directly comparable across alphabets and model
families; alignment consensus is a strong baseline we did not run. If we can run
it, we should.

### 6. Klijn et al. (2023), aggregating EKGs

Aggregating an event knowledge graph into recurring behavioural units. Different
granularity, same instinct. Cite and distinguish.

### What actually remains defensible as our contribution

1. **The application and the deliverable.** An as-is catalog of 5,243 concluded
   administrative processes from a Brazilian state SEI installation, with a
   representative path per type, produced where no documented as-is model exists,
   framed as a legal-administrative transparency instrument. No prior work in
   §1–§7 does this on this data or with this framing.
2. **The controlled alphabet comparison.** `action@unit` vs unit-itinerary,
   evaluated on the same clusters and the same downstream models. This is an
   event-abstraction question (van Zelst et al. 2021) that the review itself
   flags as under-evaluated.
3. **The controls.** Shuffled-partition null + global-model baseline. Rare in
   trace-clustering papers (Zandkarimi et al. 2020's review does not report them
   as standard) and a genuine methodological contribution to *how partitions are
   evaluated*, even though *that* they should be evaluated downstream is not new.
4. **Privacy/utility on unsupervised + predictive tasks.** Prior work measures
   sanitisation impact on *discovery* (PRETSA) or supervised NLP. Measuring it on
   clustering quality and next-activity accuracy appears unclaimed — but see the
   caveat below.
5. **The five-model comparison on one real public-sector log** including a
   third-order Markov baseline that is competitive, consistent with Tax et al.
   (2020) and Rama-Maneiro et al. (2023).

---

# §9 — Novelty risks: claims we must NOT make

Each item is a sentence we must not write, with the reference that refutes it.

| Do **not** claim | Refuted by |
|---|---|
| "We are the first to cluster traces into process types." | Greco et al. 2006; Song et al. 2009; Bose & van der Aalst 2009 |
| "We are the first to evaluate a clustering by the downstream model it enables." | **De Weerdt et al. 2013 (ActiTraC)**; De Koninck & De Weerdt 2019; Zandkarimi et al. 2020 lists this as an existing evaluation dimension |
| "We are the first to learn one sequence model per cluster." | **Ferreira et al. 2007** (mixture of Markov chains); Di Francescomarino et al. 2019 (classifier per cluster) |
| "We introduce the idea of a representative/typical execution per cluster." | **Chatain et al. 2017** (model traces as centroids); Boltenhagen et al. 2019, 2021; Bose & van der Aalst 2010/2012 (alignment consensus) |
| "Trace clustering for stakeholder-facing process summaries is new." | Delias et al. 2015; Breuker et al. 2016; De Koninck et al. 2021 |
| "Deep models outperform classical baselines for next-activity prediction." | Tax et al. 2020; Rama-Maneiro et al. 2023; Weytjens & De Weerdt 2020 — all show it is log-dependent |
| "High next-activity accuracy shows we captured the process." | **Peeperkorn et al. 2023** — accuracy can be high while process structure is not learned |
| "Our typical path is a faithful process model." | Buijs et al. 2012/2014 (a single path maximises simplicity and sacrifices generalisation); van der Aalst 2019 (DFG limitations) |
| "Precision of X shows the path is good." | Tax et al. 2018 (no precision measure satisfies all reasonable axioms); Janssenswillen et al. 2017 (implementations disagree) |
| "Anonymisation impact on process mining utility is unstudied." | PRETSA 2019; PRIPEL 2020; Fahrenkrog-Petersen et al. 2023; Elkoumy et al. 2022. **Narrow the claim to: impact on *clustering quality* and *next-activity prediction* specifically.** |
| "Removing names anonymises the log." | Mannhardt et al. 2019; Elkoumy et al. 2022 — the trace itself is a behavioural fingerprint |
| "Process mining for public-sector accountability is new." | van der Aalst et al. 2010; Jans et al. 2013, 2014; plus the public-sector refs already in `references.bib` |
| "Event knowledge graphs let us avoid all case-notion problems." | van der Aalst 2019 (OCPM): we still chose a case notion (the process), so divergence/convergence still apply |
| "Analysing the sequence of organisational units is a new perspective." | Song & van der Aalst 2008 (organisational mining) |

### Two framings that are safe

- *"We evaluate emergent process-type partitions by the predictive performance of
  per-cluster sequence models, extending the model-driven evaluation principle of
  De Weerdt et al. (2013) from process-model fitness to next-activity prediction,
  and adding shuffled-partition and global-model controls that this literature
  does not routinely report."*
- *"Prior work quantifies the utility cost of event-log sanitisation for process
  discovery (Fahrenkrog-Petersen et al. 2019, 2023) and of text anonymisation for
  supervised NLP; to our knowledge the effect on unsupervised trace clustering
  quality and on next-activity prediction has not been reported."*

---

# §10 — Reference count and integration checklist

- **43 verified references** in this file: 35 `NEW`, 8 `IN BIB` re-verified
  against Crossref.
- **Must-add before submission (novelty defence, non-optional):**
  `deweerdt2013actitrac`, `ferreira2007sequence`, `chatain2017alignment`,
  `difrancescomarino2019clusteringppm`, `bose2012diagnostics`,
  `tax2020interdisciplinary`, `peeperkorn2023rnnstructure`, `buijs2014quality`,
  `vanderaalst2019dfg`, `mannhardt2019privacy`, `elkoumy2022privacy`,
  `fahland2022ekg`, `vanzelst2021abstraction`, `song2008organizational`.
- **Strongly recommended:** `zandkarimi2020generic`, `taymouri2021variant`,
  `adriansyah2011costbased`, `munozgama2010precision`, `tax2018imprecisions`,
  `vanderaalst2010auditing`, `jans2014fieldstudy`,
  `fahrenkrogpetersen2019pretsa`, `vanderaalst2019ocpm`, `klijn2023aggregating`,
  `weytjens2022leakage`.
- **Optional / depth:** the remainder.
- Fields deliberately omitted: LNCS/LNBIP **series volume numbers** and
  **editor lists** (not registered in Crossref). Add from the physical
  proceedings if the Springer style file requires them; do not invent them.
