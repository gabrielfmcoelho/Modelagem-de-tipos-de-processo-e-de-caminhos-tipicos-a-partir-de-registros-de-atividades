# Leiden — comunidades num grafo de vizinhança

**Pergunta.** Se os processos forem tratados como um grafo de semelhança em vez de uma nuvem de
pontos, que comunidades emergem?

`fit(features, **params)` em `leiden_model.py`, sobre `leidenalg` + `python-igraph`.

## O que faz, em três passos

1. **Grafo de k-vizinhos.** `NearestNeighbors(n_neighbors=min(n_neighbors+1, n), metric="cosine")`
   — o `+1` porque o vizinho mais próximo de um ponto é ele mesmo, e a posição 0 é descartada
   no laço (`for pos in range(1, ...)`).
2. **Pesos.** `weight = max(0, 1 − distância cosseno)`, isto é, a similaridade cosseno truncada
   em zero. Vizinhos quase opostos entram com peso 0 em vez de peso negativo.
3. **Partição.** `RBConfigurationVertexPartition` com `resolution_parameter` e `seed=42`. É
   modularidade com resolução ajustável — a resolução é o que faz as vezes de `k`.

## Parâmetros

| parâmetro | default | efeito |
|---|---|---|
| `n_neighbors` | `15` | densidade do grafo; mais vizinhos, comunidades maiores |
| `resolution` | `1.0` | acima de 1 fragmenta, abaixo funde. A variante `-lres` usa a resolução varrida por `select-k` |
| `metric` | `"cosine"` | fixo — e aqui a métrica **é** cosseno de facto, ao contrário do HDBSCAN |
| `seed` | `42` | fixo |

## O grafo é dirigido na origem e não dirigido no uso

`NearestNeighbors` produz uma relação **assimétrica**: `j` estar entre os 15 vizinhos de `i` não
implica o contrário. O código emite uma aresta por par ordenado e entrega tudo a
`ig.Graph(..., directed=False)`.

A consequência é mensurável e não é neutra: um par de vizinhos **mútuos** aparece duas vezes na
lista e, como o igraph soma os pesos de arestas paralelas, entra com **peso dobrado** frente a um
par unilateral. Numa amostra do estudo, 2.700 arestas dirigidas colapsaram em 1.887 simples —
30% de duplicatas, ou seja, 30% dos pares recebem esse reforço.

É defensável — a reciprocidade *é* evidência de vizinhança mais forte — mas é uma escolha de
modelagem implícita, não um efeito do algoritmo de Leiden.

## O que devolve

`ClusterResult("leiden", labels, strengths, {...})`, `strengths` todo `1.0`, cobertura total:
como k-means e ao contrário de HDBSCAN, **todo caso recebe comunidade**.

## Determinismo

**Determinístico** dado o `.npz`, `n_neighbors`, `resolution` e `seed=42`.

## A limitação que a leitura precisa carregar

A partição depende do grafo, e o grafo depende de `n_neighbors`, que ninguém varreu — só a
resolução foi. Duas escolhas governam o resultado e apenas uma é selecionada por critério.
