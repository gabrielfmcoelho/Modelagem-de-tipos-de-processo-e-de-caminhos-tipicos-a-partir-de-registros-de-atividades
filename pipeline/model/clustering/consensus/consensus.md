# Consenso por co-associação — a partição em que os algoritmos concordam

**Pergunta.** Que partição emerge do **acordo** entre HDBSCAN, k-means e Leiden, em vez de
escolher um deles?

`fit(label_maps, algos, protocolos, k=...)` em `consensus_model.py`. Não é um algoritmo de
agrupamento sobre atributos: é um agrupamento sobre **rótulos já produzidos**.

## Como funciona

1. **`onehot`** — cada clusterização vira uma matriz indicadora: uma coluna por grupo, `1` na
   coluna do grupo do caso. Caso marcado como ruído (`-1`) fica com a **linha inteira zerada**,
   e é assim que a ausência de opinião entra sem virar uma opinião.
2. **`coassociation`** — os blocos são concatenados horizontalmente e a matriz é dividida por
   `√(n_algos)`. Com isso o produto interno entre duas linhas é **exatamente** a fração de
   algoritmos que colocaram os dois casos no mesmo grupo. É a co-associação, representada de
   forma implícita em vez de como matriz n×n.
3. **k-means** sobre esse espaço, `random_state=42`, `n_init=10`.

### Por que `√n` e não a norma da linha

Até 2026-08-10 o passo 2 normalizava **cada linha em L2**, o que dá
`acordos / √(kᵢ·kⱼ)` — com `kᵢ` = quantos algoritmos rotularam o caso `i`. Para dois casos
plenamente rotulados isso coincide com `acordos / n`; mas quando um dos casos é **ruído em algum
algoritmo**, o denominador encolhe e a similaridade **infla**. Medido: dois de três algoritmos
concordando, com um dos casos em ruído, dava `0,8165` onde a taxa verdadeira é `0,6667` — um
fator `√(3/2) ≈ 1,22`.

Como HDBSCAN é a única fonte de ruído do conjunto, o efeito era sistemático e numa direção só:
puxava justamente os casos que a densidade recusou para dentro dos grupos. Dividir por `√n`
corrige, e `test_cluster_catalog.py` trava a propriedade para todos os pares.

Um caso que é ruído em **todos** os algoritmos fica no vetor nulo e tem similaridade zero com
tudo — inclusive consigo mesmo. É o comportamento correto: não há evidência alguma sobre ele.

## Como `k` é escolhido

Por varredura, não por default. `sweep_k` roda k-means para cada `k` da grade (`--flag k_grid`,
default `20…200` de 20 em 20) e `best_k` fica com o de maior silhueta no espaço de
co-associação. A varredura inteira é gravada em `k_sweep.json` e a escolha viaja no
`meta.k_selection` do `labels.json`. `--flag k=<n>` força um valor e registra `mode: fixed`.

Até 2026-08-10 o `k` era `120` fixo — o único parâmetro de agrupamento do estudo que ninguém
tinha selecionado.

**Circularidade que fica:** o `k` é escolhido pela silhueta no mesmo espaço em que o k-means do
consenso otimiza, e empates resolvem para o maior `k`. A varredura é honesta sobre isso porque
grava todos os candidatos, mas o critério não é independente do método.

## Filiação

Não é o CSPA de Strehl & Ghosh como publicado — o CSPA monta a matriz n×n de co-associação e a
particiona com **METIS**. Aqui a partição é k-means sobre a representação normalizada, o que
corresponde à família de consenso por k-means sobre co-associação (Topchy et al.). O
`params.method` grava `coassociation-kmeans`, não `cspa`.

## Espaço das métricas — a armadilha que já custou uma retratação

Os índices internos do consenso são calculados no espaço **de co-associação one-hot**
(`space="coassoc-onehot"`), não no UMAP-50 onde as outras clusterizações são medidas. Silhueta e
DBCV não são comparáveis entre os dois espaços; foi exatamente essa comparação que produziu a
alegação retirada de que "a melhor DBCV dá os piores caminhos".

Por isso o stage também calcula `internal_comparable`, refazendo as métricas sobre as features
originais — e é essa a versão que entra em qualquer comparação. Duas guardas recusam a versão
errada: `intrinsic_vs_downstream` e `selection_score`.

## Entradas, população, determinismo

Só os processos presentes em **todos** os `labels.json` listados são avaliados; a interseção
define a população. **Determinístico** dado `seed=42` — as entradas são rótulos já persistidos e
o k-means final é fixado.
