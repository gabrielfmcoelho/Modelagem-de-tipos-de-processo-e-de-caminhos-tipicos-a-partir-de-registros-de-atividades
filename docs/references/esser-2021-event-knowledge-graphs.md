# Esser & Fahland 2021 — Event Knowledge Graphs (process data in Neo4j)

**Citation.** Esser, S., & Fahland, D. (2021). Multi-Dimensional Event Data in Graph Databases. *Journal of Data
Semantics*, 10(1–2), 109–141. (See also Fahland, *Process Mining over Multiple Behavioral Dimensions with Event
Knowledge Graphs*, 2022.)
**Link.** https://doi.org/10.1007/s13740-021-00122-1 · data/queries: https://doi.org/10.5281/zenodo.3865222
**Type.** recent (the graph-DB process-data foundation) · **Topic.** event knowledge graphs · graph databases

## Why it matters to our work — *we map SEI into a graph*
**This is the methodological foundation for our entire representation: process/event data as a graph in Neo4j.**
An Event Knowledge Graph (EKG) is a **labeled property graph** with node labels `{Event, Entity}` and relationship
labels `{df (directly-follows), corr (correlation)}`, stored and queried in **Neo4j with Cypher** — which is
*exactly* our schema: `Atividade` (events), `Processo`/`Unidade`/`Documento` (entities), `SEGUIDA_POR`
(directly-follows), `DO_PROCESSO`/`EXECUTADO_PELA_UNIDADE` (correlation). Our pipeline is, in their terms, an EKG
construction + analysis system for SEI.

Crucially, EKGs are the bridge to the object-centric view (see
[`vanderaalst-2019…`](vanderaalst-2019-object-centric-pm.md)): the graph natively carries the multi-object
structure that a flat case-log loses — supporting the protocolo↔documento↔unidade relations we already store but
analyze (for now) one protocolo at a time.

## Key takeaways
- EKG = property graph (`Event`/`Entity`, `df`/`corr`) in Neo4j; analysis = Cypher over the graph.
- Lets process mining work over **multiple behavioral dimensions** at once (per unit, per document, per process).

## How we cite it
Method (the graph-database representation of our event data) and motivation for the graph-native approach;
the cornerstone of a graph-focused framing.
