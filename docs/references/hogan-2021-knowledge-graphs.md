# Hogan 2021 — Knowledge Graphs

**Citation.** Hogan, A., Blomqvist, E., Cochez, M., d'Amato, C., de Melo, G., Gutierrez, C., et al. (2021).
Knowledge Graphs. *ACM Computing Surveys*, 54(4), 1–37.
**Link.** https://doi.org/10.1145/3447772 · arXiv:2003.02320 · **Type.** recent (definitive survey) · **Topic.** knowledge graphs

## Why it matters to our work
The general foundation for representing our domain as a **knowledge graph**: a graph of data whose nodes are
entities and whose edges are typed relations, under a **property-graph** model — precisely the Neo4j model we use
to integrate the heterogeneous SEI data (processos, activities, units, users, documents, clusters) into one
queryable structure. It also covers **graph embeddings and graph neural networks** as the learning layer over
KGs — connecting our GCN node-importance and clustering-feature work to the broader KG-representation-learning
program.

## Key takeaways
- KG = entities + typed relations in a (directed-labelled / property) graph; flexible, schema-light integration.
- Representation learning over graphs (embeddings, GNNs) is a core KG sub-area — our `gcn.py` sits here.

## How we cite it
Method/framing: justifying the knowledge-graph representation of SEI data and locating our graph-ML components.
