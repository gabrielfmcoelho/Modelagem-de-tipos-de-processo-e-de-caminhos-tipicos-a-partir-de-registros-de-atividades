# Protocolo de avaliação — como um modelo por família é medido

**Pergunta.** Dada uma partição do corpus em famílias, quanto um modelo de caminho ajustado
**por família** prevê melhor o próximo passo do que um modelo único para todos?

`evaluate_cluster` / `evaluate_matrix` em `pipeline/model/typical_eval.py`, orquestrados por
`run_typical_eval.py` (uma célula) e pelo stage `matrix` (todas as células). O resultado de uma
célula é `artifacts/typical/<run_id>/<algo>/<alfabeto>/metrics.json`.

## As unidades

| unidade | o que é |
|---|---|
| **traço** | a sequência ordenada de eventos de **um** processo, no alfabeto da célula, com `END` acrescentado. Um traço por processo |
| **passo de decisão** | cada posição do traço: dado o prefixo `t[:j]`, qual é `t[j]`. Um traço de comprimento *n* contribui *n−1* passos |
| **família** | um cluster da partição que está a ser avaliada |
| **célula** | o cruzamento `run_id × algo × alfabeto` — uma partição, um alfabeto, os seis modelos |

`top1` é medido **sobre passos de decisão**, não sobre traços: traços longos pesam mais dentro
da sua família. `top3` é o mesmo com as três melhores previsões.

## O funil, e porque `k` não é o `k` do clustering

```
processos com traço            <- lidos do grafo; exige >= 2 estados
  ∩ processos com rótulo       <- quem não tem documento de abertura parseado não tem feature, logo não tem cluster
  ∩ famílias com >= min_traces <- cluster_traces(min_traces=30) descarta as famílias pequenas
```

O `n_clusters` publicado por uma célula é o número de famílias que **sobreviveram** ao piso de
`min_traces`, não o número de clusters que o algoritmo produziu. O piso existe porque uma
família dividida 70/30 precisa de casos de teste suficientes para que uma acurácia signifique
alguma coisa. Duas partições com o mesmo número de clusters podem apresentar `n_clusters`
diferentes aqui, porque distribuem a massa de forma diferente.

## A divisão treino/teste é global, e é por isso que a comparação é honesta

`is_train_protocolo` (em `predict.py`) decide por **hash do protocolo**:

```python
h = blake2b(f"{seed}:{protocolo}").digest()
treino  <=>  int(h) / 2**64 < train_frac        # train_frac=0.7, seed=42
```

Não é um embaralhamento de lista: a pertença é uma **função pura do protocolo**. Um processo é
treino em toda a parte ou teste em toda a parte — dentro da sua família, dentro do baseline
global, em qualquer célula e em qualquer alfabeto.

Isto é o que impede o vazamento. O baseline global treina na união dos conjuntos de treino das
famílias avaliadas; como a pertença não depende da lista, **nenhum traço de teste entra no
treino do modelo global**. Sem esta propriedade o baseline global seria otimista e a comparação
não valeria nada.

> A ramificação de fallback de `random_split_field` (embaralhamento por seed) só actua quando os
> traços não carregam o protocolo. No caminho da matriz eles carregam — `cluster_traces` devolve
> triplos `(data_hora, estados, protocolo)`. Se algum dia deixarem de carregar, o vazamento volta
> em silêncio.

## O que acontece dentro de uma família

```
para cada família C_i com |C_i| >= min_traces:
    treino, teste = split_por_hash(C_i)              # 70/30 global
    para cada um dos seis modelos m:
        m_i = m.fit(treino)                          # só os traços desta família
        a_i(m) = acurácia de m_i sobre os passos de teste de C_i
```

Cada modelo é ajustado **de novo** em cada família. É essa a hipótese em teste: especializar
compensa.

## Agregação — o que é agregado, onde, e com que peso

**Tudo o que sai numa figura ou numa tabela é uma agregação sobre as `n` famílias de uma
célula.** Não existe medida publicada ao nível do processo individual; a unidade de agregação é
sempre a família.

Duas leituras, ambas produzidas:

| | fórmula | lê-se como |
|---|---|---|
| `macro` | média simples de `a_i` sobre as famílias | cada **família** vale o mesmo |
| `weighted` | média de `a_i` ponderada por `n_traces_i` | cada **processo** vale o mesmo |

Ambas vêm de **uma só** implementação, `pipeline/model/aggregate.py`
(`macro_mean`, `weighted_mean`, `both_means`). A camada de evidência importa a mesma função
(`evidence/shared/stats.py` reexporta-a como `_wmean`), de modo que existe uma única definição de
"ponderado" em todo o repositório. Antes havia três — `_agg` em `evaluate_matrix`, `_wmean` na
camada de evidência e uma terceira para as métricas de aresta — que concordavam por coincidência.

### Onde vive cada nível

| nível | onde | quem lê |
|---|---|---|
| por família | `.clusters[<cid>]` do `metrics.json` da célula | **tudo** — todos os sítios de agregação da camada de figuras iteram este nível |
| por célula | `.aggregate` e `.aggregate_by_size` | **ninguém** — são escritos e nunca lidos |

A camada de figuras **re-agrega sempre a partir de `.clusters`**, porque precisa de filtrar
(por modelo, por banda de tamanho, por braço, por controle) antes de somar — coisa que um
sumário por célula já não permite. `.aggregate` sobrevive como o resumo auto-contido de um
artefacto lido isoladamente, e é o que o `test_glossary` usa para enumerar as chaves emitidas.

### O peso não é o que se supõe

O peso de `weighted` é `n_traces` (o tamanho da família em **processos**), enquanto `a_i` é
calculado sobre **passos de decisão**. Uma família de traços longos contribui com muitos passos
para o seu próprio `a_i`, mas entra na agregação apenas com o seu número de processos.
`weighted` pondera processos, não decisões — se a distribuição de comprimento variar muito entre
famílias, as duas leituras divergem, e a divergência entre `macro` e `weighted` é o sinal de que
isso está a acontecer.

## Os dois baselines

Medidos no **mesmo** conjunto de teste da família:

| baseline | o que é | responde |
|---|---|---|
| `top1_successor` | prever sempre o sucessor mais frequente do estado actual | o traço é previsível sem modelo? |
| `top1_global_model` | um Markov de ordem 3 ajustado na união dos treinos | particionar ajuda? |

## A fórmula

Seja `Π` a partição real, `m` um modelo, `A_w(m, Π)` a acurácia agregada ponderada e `B_w(Π)` a
do baseline global. O ganho bruto é

```
Δ(m, Π) = A_w(m, Π) − B_w(Π)
```

**`Δ` não é o efeito do agrupamento.** Ajustar por família encolhe o suporte de cada modelo: o
alfabeto de `C_i` é um subconjunto do alfabeto global, e prever dentro de um alfabeto menor é
mais fácil. Esse ganho existe mesmo que as famílias sejam arbitrárias — chame-se-lhe **dividendo
da partição**. Ele depende apenas de `K` e da distribuição de tamanhos, não do significado.

Seja `Π~` a partição-controle: mesma `K`, mesma distribuição de tamanhos, mesma população,
pertença permutada (`cluster-control`). Então o ganho bruto decompõe-se:

```
Δ(m, Π)  =  [ A_w(m, Π~) − B_w(Π~) ]  +  [ A_w(m, Π) − A_w(m, Π~) ]  +  [ B_w(Π~) − B_w(Π) ]
             \_______ dividendo _______/   \______ sinal da partição ______/   \___ resíduo ___/
```

O estimando do estudo é o termo do meio:

```
Δ*(m, Π) = A_w(m, Π) − A_w(m, Π~)
```

`Δ* > 0` ⟺ a partição carrega sinal de processo **além da sua forma**. É esta a quantidade a
reportar; `Δ` sozinho não distingue uma partição informativa de uma partição arbitrária com o
mesmo formato.

### `Δ*` é um portão de validade, não um ranking

`Δ*` responde **"esta partição é real?"** — e responde bem: se for positiva, o agrupamento carrega
sinal de processo para além da sua forma. O que `Δ*` **não** responde é *"qual partição é
melhor?"*, e a razão é estrutural.

`Δ*` cresce com o número de famílias. Uma partição mais fina tem mais a ganhar sobre o seu
próprio embaralhamento, porque especializar compensa mais quando as famílias são pequenas: o
alfabeto de cada família encolhe, e o controle — que preserva a forma — não preserva a
*informação* que a granularidade traz. Medido nesta base sobre o alfabeto `unit`, a correlação
entre o número de famílias avaliadas e `Δ*` é quase perfeita, e a ordenação por `Δ*` reproduz
a ordenação por `k` (ver `delta_star_by_clustering` em `results_figures.json`).

Consequências práticas:

- Use `Δ*` como **critério de admissão**: uma partição com `Δ* <= 0` não deve entrar no estudo,
  qualquer que seja a sua validade interna.
- **Não** ordene partições de granularidades diferentes por `Δ*`. Para escolher entre elas existe
  `selection_score`, que pesa desempenho a jusante, cobertura e qualidade.
- Comparações **a `k` emparelhado** continuam válidas — é assim que se comparam dois algoritmos
  ou os dois braços sem que a granularidade decida o resultado.

> O modelo `dfg` apresenta o maior `Δ*` de todos, apesar de ter a pior acurácia absoluta. Um
> grafo de precedência construído sobre uma família incoerente é quase inútil, logo é o modelo
> que mais colapsa no controle e mais ganha numa partição real. É o pior preditor e o melhor
> detector: como estatística barata de coerência de família, o `Δ*` do `dfg` é mais sensível do
> que o de qualquer modelo neural.

### O resíduo é um teste de sanidade grátis

`B_w(Π)` e `B_w(Π~)` medem o **mesmo** modelo global sobre o **mesmo** conjunto de passos de
teste — só muda como esses passos se distribuem pelas famílias e, portanto, os pesos. Se as duas
diferirem de forma apreciável, a ponderação está a fazer trabalho que não devia, e é sinal de
que o desequilíbrio entre famílias merece ser reportado ao lado do resultado.

## Armadilhas

- **`n_clusters` de uma célula ≠ `k` do clustering.** O piso de `min_traces` corta famílias.
  Comparar células sem olhar para `n_clusters` e `n_traces` compara populações diferentes.
- **Modelos indisponíveis não são zero.** Um modelo que não pôde ser ajustado entra como
  `{"skipped": <razão>}` e é **excluído** da agregação, não contado como falha. `n_clusters` por
  modelo diz sobre quantas famílias aquele modelo foi de facto medido.
- **`Δ` sem `Δ*` não é publicável.** É a razão pela qual as células `-shuffled` existem e são
  parte da matriz, e não um extra.
- **O split é por processo, nunca por passo.** Passos do mesmo processo nunca se dividem entre
  treino e teste; se algum dia se dividirem, todas as acurácias sobem e nenhuma vale.
