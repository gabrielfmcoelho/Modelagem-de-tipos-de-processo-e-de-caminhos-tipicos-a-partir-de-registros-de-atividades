---
type: workflow
title: Typical Path Discovery and Evaluation
description: How a representative path is distilled per process family — the three trace alphabets, six interchangeable sequence models behind one interface, the flow automaton that constrains decoding and training alike, and the paired bootstrap that decides whether a result survives.
tags: [process-mining, sequence-models, markov, neural, constrained-decoding, bootstrap, evaluation]
verified:
  - by: openwiki/0.5.0
    at: 2026-09-10T12:46:32.229Z
sources:
  - id: openwiki-source-da5ad2a37fece147eb4c8b6b
    resource: repo://pipeline/evidence/typical_path/paired_bootstrap.py
  - id: openwiki-source-e9c288adeed44d30884073df
    resource: repo://pipeline/model/constrained.py
  - id: openwiki-source-e54abf91ea7fc6ad75babcb0
    resource: repo://pipeline/model/typical_eval.py
  - id: openwiki-source-8238328ae3d4012a765ef98d
    resource: repo://pipeline/model/typical_path/_torch_base.py
  - id: openwiki-source-d976c7279573d2727e2fac47
    resource: repo://pipeline/model/typical_path/dfg/dfg_model.py
  - id: openwiki-source-0e399b31586e82dded071973
    resource: repo://pipeline/model/typical_path/markov/markov_model.py
  - id: openwiki-source-d8982b7dafcb27776e3ecfe7
    resource: repo://pipeline/stages/cohort.py
  - id: openwiki-source-c3c22bcf7d6c1443dcf21c09
    resource: repo://pipeline/stages/dfg_build.py
  - id: openwiki-source-87b3bf677f3cb053a67e43d8
    resource: repo://pipeline/stages/matrix.py
  - id: openwiki-source-a01c40ac0ec64656d7702d41
    resource: repo://pipeline/stages/noninferiority.py
generated: { by: "claude-code", at: "2026-09-10T12:46:32.229Z" }
---

# Typical Path Discovery and Evaluation

Having partitioned processes into families, the study asks what each family
*does*: what sequence of steps is typical of it, and whether modelling a family
separately predicts its next step better than modelling the corpus as a whole.

## Traces and alphabets

An activity becomes a state of the form `TIPO@lane` — an action type and the
unit it occurred in. Three alphabets project that differently, and
`ALPHABET_AXES` declares which axes each retains:

| Alphabet | Retains | Answers |
|---|---|---|
| `unit` | action and unit | The full step: what happened, and where |
| `itinerary` | unit only | The route through the organisation |
| `procedure` | action only | The procedure, independent of who performed it |

`alphabet_carries` is the single predicate everything else consults, so no
downstream code re-derives which alphabet has a lane. Results are never
aggregated across alphabets — each has its own complete matrix.

Traces are grouped by cluster label with a minimum-support rule: a family with
fewer than thirty traces is dropped rather than modelled on too little evidence.

## Six models behind one interface

Every model implements the same small surface — `fit`, `predict_next`,
`next_distribution` and `generate` — which is what lets the evaluation harness
treat them interchangeably.

`default_specs` builds them and validates the requested names against the
canonical list, raising with the valid set on an unknown name.

**Markov** is a **back-off** n-gram, not a fixed-order one. It keeps a separate
count table for every order up to its configured maximum (three, in the study's
configuration) and, when predicting, falls back from the longest available
context to progressively shorter ones until it finds counts.

**DFG** subclasses the first-order Markov model. It fits in two passes: first
counting how many distinct traces contain each transition, keeping only those
above a coverage floor, then counting transitions over the surviving edges alone.
The directly-follows graph is therefore a frequency-filtered first-order chain —
which is exactly why it is a fair baseline against the higher-order model rather
than a different kind of object.

**GRU, LSTM and Transformer** share `_TorchSeqModel`. It builds a vocabulary from
the training traces with padding and unknown reserved at indices zero and one,
encodes a fixed-size left-padded window of recent states, and resolves its device
through the shared device selector.

Its import handling is notable: a failure importing torch sets `available = False`
and records the reason instead of raising, so a missing dependency degrades that
model rather than failing the evaluation.

### GPU gating is explicit

The three neural families declare `requires_gpu`. When no accelerator is
available and CPU execution has not been permitted, `default_specs` **omits them
and returns a dictionary of skipped models with the reason recorded**. A cell
evaluated without them therefore says so, rather than appearing to have compared
six models when it compared three.

## The flow automaton

`FlowState` encodes the legality rules of the administrative process itself. It
tracks whether the process has started and maintains two sets of units: those
where the process is currently open, and those to which it has been sent but
which have not yet acknowledged receipt.

From that state it decides what may come next: generation only before the
process has started; a receipt only in a unit with a pending dispatch; a
conclusion only in a unit where the process is open; dispatch and reopening only
once started. The terminal token is always allowed.

### Constrained decoding

`generate_constrained` applies the automaton at decode time. At each step it asks
the model for its next-state distribution, **filters out states the automaton
forbids**, truncates to the top candidates, and samples. If nothing legal
survives, generation stops rather than emitting an impossible step.

Because it consumes only `next_distribution`, this works with every model
uniformly — the constraint is a property of the decoder, not of any model.

The same automaton is reused inside neural training: with a non-zero auxiliary
weight, `_TorchSeqModel` builds a per-step legality mask from `FlowState` while
encoding the training data, so the network can be supervised toward flow-legal
predictions. Decoder and training loop therefore share one definition of legal.

## What is measured

`model_metrics` reports next-step accuracy at ranks one and three, the
Damerau–Levenshtein distance between a generated suffix and the true one, and the
ratio of generated to true suffix length.

Critically, when constrained generation is enabled it reports a **second** suffix
distance computed with the constraint applied. Having both side by side is what
makes the cost of the constraint measurable rather than assumed — the same figure
the constraint-cost evidence consumes.

Three edge statistics describe how well a model's edge set matches reality:
coverage (the share of observed transitions the edge set contains), usage (the
share of edges actually exercised) and their harmonic mean. Each returns
undefined rather than zero when there is nothing to divide by, so an empty cell
is distinguishable from a genuinely zero score.

## The representative path

The "typical path" is not a greedy decode. `_representative_trace` generates
fifteen constrained samples from distinct seeds at temperature one over a small
candidate set, prefers those that end in a conclusion state, and returns the
**medoid** — the sampled trace minimising distance to the others.

Choosing a medoid of sampled traces rather than the single most probable path
means the reported path is representative of the model's distribution rather than
of its mode, and preferring completed traces means the path shown is one that
actually finishes.

## Deciding whether a result survives

`paired_bootstrap` compares two arms over the processes **both** evaluated,
raising when that intersection is empty rather than comparing populations that
are not the same.

Its pairing is checked, not assumed: when a cluster's protocol list and per-trace
row count disagree it aborts with both counts, guarding against a silent
misalignment that would compare one process's result against another's.

Accuracy is micro-averaged — hits summed over totals summed, rather than
averaging per-process rates — so a long trace contributes in proportion to its
length. The procedure resamples processes with replacement over two thousand
replicates under a recorded seed, and reports point estimates with
ninety-five-percent intervals for each arm, the same for their difference, and a
**one-sided ninety-percent lower bound** on that difference.

That last quantity is the one the non-inferiority stage compares against a
pre-registered margin: the anonymized arm is judged non-inferior when the lower
bound sits above the negated margin.

## Getting there

Two stages prepare the input. `cohort` materialises a curated cohort — processes
born in the agency, within a date window, restricted to selected clusters or an
explicit list, capped by count — and `dfg-build` constructs the cohort's
aggregated directly-follows graph, with activity types as nodes and frequency
plus scores as weights. Both are deterministic and neither reuses a checkpoint.

`matrix` then evaluates every cell of the grid. It is resumable at cell
granularity: a cell whose metrics file already exists is skipped, which matters
for a stage documented as taking on the order of a day.

## Related pages

- [Process Features and Clustering](features-and-clustering.md)
- [Evidence Composition and Manuscript Delivery](evidence-and-manuscript-delivery.md)
- [Ingest and Knowledge Graph Construction](ingest-and-graph-build.md)
