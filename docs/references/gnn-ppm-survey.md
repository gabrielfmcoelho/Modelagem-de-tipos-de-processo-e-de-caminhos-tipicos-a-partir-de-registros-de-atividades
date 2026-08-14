# GNN for Predictive Process Monitoring — review + DFG-GNN

**Theme file** (the graph-neural-network strand that backs `gcn.py`).

## References
- **Review/benchmark.** *Graph Neural Networks for PPM: Review and Benchmark for Next Activity Predictions*
  (Springer, 2024). https://doi.org/10.1007/978-3-031-78666-2_3
- **DFG + GNN (directly relevant).** *Directly-Follows Graphs Go Predictive Process Monitoring With Graph Neural
  Networks* (2025). https://arxiv.org/abs/2503.03197 — applies GNNs **on the directly-follows graph**, exactly
  the structure our `gcn.py` scores.
- **Interpretable GNN.** PROPHET — *Explainable PPM with Heterogeneous Graph Neural Networks* (IEEE, 2024).
  https://ieeexplore.ieee.org/document/10684096/ — balances accuracy with **interpretability** (AI & Law hook).

## Why it matters to our work
Positions our **`gcn.py`** (a 2-layer GCN regressing DFG node-importance for the "ideal-graph" distillation) inside
the fast-growing GNN-for-process-mining line, and shows the field is moving toward **graph-native, interpretable**
process models — the same direction as our work. The DFG-GNN paper is the closest match: GNNs over the
directly-follows graph. We can cite these to (a) justify the GNN choice and (b) note that explainable GNN-PPM is
an active concern aligned with the journal's transparency focus.

## How we cite it
Related work for the GNN/DFG-importance component; evidence the graph-based, interpretable direction is current.
