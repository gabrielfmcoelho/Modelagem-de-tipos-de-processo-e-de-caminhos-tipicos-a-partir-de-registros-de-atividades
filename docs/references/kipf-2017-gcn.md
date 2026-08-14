# Kipf & Welling 2017 — Graph Convolutional Networks

**Citation.** Kipf, T. N., & Welling, M. (2017). Semi-Supervised Classification with Graph Convolutional
Networks. *ICLR 2017*. arXiv:1609.02907.
**Link.** https://arxiv.org/abs/1609.02907 · **Type.** classic · **Topic.** graph neural networks

## Why it matters to our work
The GCN our `gcn.py` implements to regress **node importance over the directly-follows graph** (the `gcn-distill`
stage), smoothing a node's signal over its graph neighborhood to rank which activities/edges matter for the
"ideal" distilled process model. It connects our work to the **GNN-for-process-mining** strand (a fast-growing
area, e.g. graph-based next-activity prediction).

## Key takeaways
- Spectral-motivated, localized first-order graph convolution; the default GNN baseline.

## How we cite it
Method (DFG node-importance / graph distillation) and a pointer to the emerging GNN-PPM literature.
