---
type: workflow
title: Process Features and Clustering
description: How an administrative process becomes a feature vector and then a member of a process family — the six weighted feature blocks and their content hash, the arm-safety guard on feature files, parameter sweeps, the four interchangeable clustering backends, and the metrics that make partitions comparable.
tags: [features, embeddings, clustering, hdbscan, kmeans, leiden, consensus, metrics]
verified:
  - by: openwiki/0.5.0
    at: 2026-09-10T12:46:32.229Z
sources:
  - id: openwiki-source-99d94b9eaf17b8f0b062046c
    resource: repo://pipeline/model/_result.py
  - id: openwiki-source-0558a8f7f043e62fbe9e8bd6
    resource: repo://pipeline/model/cluster_metrics.py
  - id: openwiki-source-06a79f0156f3a932fae76a1b
    resource: repo://pipeline/model/clustering/_dispatch.py
  - id: openwiki-source-4851a4a4a89dc5ad44f69078
    resource: repo://pipeline/model/clustering/consensus/consensus_model.py
  - id: openwiki-source-3ed2f0a237fee5eaa5fe99f3
    resource: repo://pipeline/model/clustering/hdbscan/hdbscan_model.py
  - id: openwiki-source-edcce0c42002260b2856779f
    resource: repo://pipeline/model/clustering/kmeans/kmeans_model.py
  - id: openwiki-source-071a24931960ee47822418c3
    resource: repo://pipeline/model/clustering/leiden/leiden_model.py
  - id: openwiki-source-18f93105b4227f05663cc949
    resource: repo://pipeline/model/embedding.py
  - id: openwiki-source-d7f05ed521344e7de0398b72
    resource: repo://pipeline/model/processo_features.py
  - id: openwiki-source-06deae6a2c264db7a8fa254c
    resource: repo://pipeline/stages/ablation.py
  - id: openwiki-source-8a8028221080f02daea7e2e0
    resource: repo://pipeline/stages/cluster_eval.py
  - id: openwiki-source-3dab3019deaab997ed09d50b
    resource: repo://pipeline/stages/processo_embed.py
  - id: openwiki-source-0f8104ed7b92cb6274e2b7f3
    resource: repo://pipeline/stages/select_k.py
generated: { by: "claude-code", at: "2026-09-10T12:46:32.229Z" }
---

# Process Features and Clustering

This is where the study's central question is answered: what kinds of
administrative process exist in the log? A process is turned into a single
vector, those vectors are partitioned by several algorithms under several
parameterisations, and the resulting partitions are measured against each other.

## Building a process vector

`pipeline/model/processo_features.py` assembles a vector from six independently
weighted blocks:

| Block | Content |
|---|---|
| semantic | Weighted mean of the process's document embeddings |
| topic | Embedding of the first document's topic |
| unigram | TF-IDF over the set of units the process visited |
| bigram | TF-IDF over consecutive unit transitions |
| tipo_acao | Histogram over the activity-type vocabulary |
| keyword | TF-IDF over extracted keywords |

`BlockWeights` carries one multiplier per block, all defaulting to `1.0`. That
structure is what the ablation stage manipulates: disabling the keyword or topic
contribution is setting one of these to zero, not editing the feature builder.

### Weighting inside the semantic block

`FeatureWeights` does not treat a process's documents equally. The **first**
document carries weight `3.0`, documents up to rank three carry `1.5`, and the
rest carry `1.0`. The opening document is what states what a process is for, so
it dominates the semantic representation by design.

### Stable structural blocks

The activity-type vocabulary is derived deterministically from the task groups —
sorted by group, then by task, with a final `OUTROS` bucket. Sorting rather than
relying on iteration order keeps histogram dimensions stable across runs, and the
catch-all bucket means an unrecognised activity type cannot shift the index of
every other dimension.

Unit sequences are stripped of **consecutive** repeats before bigrams are
formed, so a process that sits in one unit across many activities does not
generate a run of self-transitions that would swamp the block.

Blocks are L2-normalised before being combined, so no block dominates through
raw magnitude alone.

### The feature hash

`feature_hash` produces a content digest covering the algorithm version, every
weight, the per-document embedding hashes, the sorted set of visited units, the
deduplicated chronological sequence, and the sorted activity-type counts. Change
a weight or re-embed a document and the hash changes — this is what makes feature
computation cacheable and invalidation correct.

Two parameters are folded in **conditionally**: the keyword block weight enters
the hash only when it differs from its default, and the temporal cutoff only when
it is less than one. This is deliberate backwards compatibility — adding those
parameters did not invalidate every previously computed hash, only those that
actually use them.

### Embedding backends

`Embedder` is a `Protocol` requiring `model_name`, `dimension` and
`embed_batch`, with two implementations: a remote OpenAI-compatible client
(default model `BAAI/bge-m3` at 1024 dimensions) and a local
sentence-transformers path, which is the one that benefits from a GPU.

The remote embedder does not trust the declared dimension. Its `probe` method
embeds a single token against the live endpoint and reads the dimension off the
response — so a model swap on the server side is detected rather than assumed.
Input text is truncated to a character budget before being sent.

Features are persisted as a compressed `.npz` carrying the protocol list, the
matrix, a feature digest and — critically — the `text_variant` the features were
built from.

## The arm-safety guard

That `text_variant` stamp exists to protect the central comparison of the study.
Both `select-k` and `cluster-eval` derive the expected variant from the run id —
`exp-raw` implies `raw`, `exp-anon` implies `anon`, and parameterised ids resolve
by prefix — and compare it to what the feature file actually declares. On
disagreement they **raise**, refusing to select parameters or cluster on the
wrong arm.

`select-k` adds a second guard: when the run id names an arm but no feature file
was supplied, it raises and states the exact path it expected. Without these
checks, a mislabelled feature file would silently turn the raw-versus-anonymized
comparison into a comparison of one arm against itself, and every downstream
number would be wrong in a way no metric would reveal.

## Selecting parameters

`select-k` sweeps both parameterised algorithms and persists its findings for the
clustering stage to consume.

For k-means it sweeps a range of cluster counts and reports three selections: the
elbow of the inertia curve, the best silhouette, and a combined criterion that
penalises silhouette by a redundancy term. For Leiden it sweeps resolution and
reports the best by silhouette and by the combined criterion.

Its most useful output is `at_grid_edge`: a boolean per selection recording
whether the chosen value landed on the **boundary** of the searched range. A
selection at the edge is evidence that the true optimum lies outside the sweep,
so the stage warns that the range should be widened before the result is trusted
— and `build-arm` re-emits that warning when it consumes the selection.

The stage declares itself conditionally deterministic with the seed recorded in
its artifact parameters.

## The clustering backends

Four algorithms sit behind one uniform signature — `fit(features, **params)`
returning a `ClusterResult` of algorithm name, labels, per-point strengths and
**the parameters actually resolved**. Returning resolved parameters rather than
the ones requested is what lets provenance record what really ran.

Dispatch is a dictionary lookup that raises with the list of available algorithms
on an unknown name.

**HDBSCAN** is the density method. It guards degenerate input — fewer points than
its minimum cluster size — by returning an all-noise labelling rather than
raising, so a small cohort produces an empty partition instead of an exception.
It is the only backend whose `strengths` are meaningful: membership
probabilities, where the others return ones.

**K-means** refuses to invent a cluster count. Calling it without an explicit `k`
raises, with the message stating that no default is assumed — the number of
process families is exactly the parameter the study is trying to justify, so it
must come from the sweep rather than from a library default.

**Leiden** operates on a graph the pipeline builds itself: a cosine
nearest-neighbour graph whose edge weights are one minus the distance, floored at
zero, partitioned with the RB configuration objective at the requested
resolution. Both k-means and Leiden fix their seeds.

**Consensus** clusters the other partitions rather than the features. Each input
partition becomes a one-hot block, blocks are stacked horizontally and scaled by
the inverse square root of the number of algorithms, and k-means runs in that
co-association space. Noise points contribute an all-zero row rather than a
column of their own, so an unassigned process is simply not evidence of
agreement. Its sweep skips values of k that meet or exceed the population and
leaves metrics undefined when a k yields a single cluster, and its selector
returns a human-readable justification alongside the chosen value.

## Measuring a partition

`pipeline/model/cluster_metrics.py` reports internal validity, but with two
decisions that matter for comparability.

First, silhouette, Davies–Bouldin and Calinski–Harabasz are computed **over
assigned points only**, excluding noise, and are left undefined when fewer than
two clusters survive. DBCV is computed over everything. Alongside them the
metrics carry `noise_ratio`, `n_clusters`, `n_samples` and a `space` label — a
score is never reported without stating the space it was computed in.

Second, `full_population_metrics` closes the gap that noise creates. Density
methods leave points unassigned while partitional methods do not, so their
silhouettes are not measured over the same population. This function reassigns
every noise point to the nearest cluster centroid by cosine similarity,
recomputes, and reports `n_reassigned` — making the two families comparable while
keeping the reassignment visible. When there is no noise it short-circuits and
reports zero reassignments, so the two paths agree on a partition that already
covers everything.

## Around the chosen partition

Four stages operate on a produced partition, all declaring
`can_skip_when_done=False` since each re-examines current state:

- `cluster-eval` produces the partitions and their metrics for a run id,
  conditionally deterministic with UMAP and HDBSCAN pinned by a recorded seed;
- `cluster-stability` re-fits over repeated draws to measure how reproducible the
  partition is;
- `cluster-control` produces the shuffled null partition;
- `cluster-name` and `cluster-audit` label and check the resulting catalogue.

## Related pages

- [Experiment Arms and Run Identifiers](../concepts/experiment-arms-and-run-ids.md)
- [Typical Path Discovery and Evaluation](typical-path-discovery.md)
- [Evidence Composition and Manuscript Delivery](evidence-and-manuscript-delivery.md)
