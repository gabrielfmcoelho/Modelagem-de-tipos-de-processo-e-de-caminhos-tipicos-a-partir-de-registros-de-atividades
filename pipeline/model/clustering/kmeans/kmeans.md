# k-means — centróides, com `k` que alguém precisa escolher

**Pergunta.** Se o número de grupos for imposto em vez de descoberto, que partição sai — e
quanto o resultado depende dessa imposição?

`fit(features, **params)` em `kmeans_model.py`, sobre `sklearn.cluster.KMeans`.

## O que faz

Particiona os pontos em `k` grupos minimizando a soma das distâncias quadráticas ao centróide.
Todo ponto recebe grupo: **não existe ruído**, e a cobertura é 100% por construção.

## Parâmetros

| parâmetro | valor | origem |
|---|---|---|
| `k` | **obrigatório** | `fit` levanta `ValueError` se ausente |
| `n_init` | `10` | fixo no código |
| `random_state` | `42` | fixo no código |
| métrica | euclidiana | do algoritmo; não é configurável |

**`k` não tem default, e isso é deliberado.** O código recusa a chamada em vez de assumir um
valor: `"kmeans requires an explicit 'k' (number of clusters); no default is assumed"`. Quem
escolhe é o stage `select-k`, por varredura (cotovelo e silhueta), e a escolha fica em
`artifacts/clustering/<arm>/selection.json`.

## As variantes que o estudo roda

O mesmo algoritmo aparece em mais de uma célula da grade, com `k` vindo de critérios diferentes:

- `-kelbow` — `k` no cotovelo da inércia;
- `-ksil` — `k` de maior silhueta.

Elas não são algoritmos diferentes; são a mesma função com uma decisão diferente a montante. É
por isso que o eixo de parameterização existe separado do eixo de algoritmo na grade
experimental.

## O que devolve

`ClusterResult("kmeans", labels, strengths, {...})` com `strengths` todo `1.0` — k-means não
produz confiança de pertencimento. Um ponto na fronteira entre dois centróides e um ponto no
centro de um grupo recebem a mesma força. Onde a força importa, ela não existe aqui.

## Determinismo

**Determinístico** dado o `.npz` e `k`: `random_state=42` e `n_init=10` fixos. `cluster-audit`
reajusta e compara.

## A limitação que a leitura precisa carregar

A silhueta **favorece estruturalmente** k-means, porque ambos otimizam a mesma geometria:
compacidade em torno de um centro contra separação entre centros. Comparar k-means com HDBSCAN
por silhueta é comparar um método com a métrica que ele minimiza. Por isso o critério de
seleção do entregável não é a silhueta sozinha, e por isso os índices internos são reportados
como *descrição da partição*, nunca como prova de que ela é a certa.
