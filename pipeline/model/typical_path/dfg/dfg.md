# DFG — grafo directly-follows com piso de suporte

**Pergunta.** Quanto do comportamento se explica só pelas arestas "A é seguido por B" que
sobrevivem a um piso de suporte?

`DfgModel(coverage_floor)` em `dfg_model.py`. É a linha de base **clássica de mineração de
processos** dentro do mesmo harness dos modelos neurais: mesma partição, mesmo split, mesma
decodificação, mesmas métricas.

## O que faz

Subclasse de `MarkovModel(order=1)` com um filtro antes de contar:

1. Para cada aresta `(a, b)`, conta em **quantas traces distintas** ela ocorre — processos, não
   ocorrências. Uma aresta que se repete cinquenta vezes num único processo conta um.
2. Mantém as arestas cuja fração de traces atinge `coverage_floor`.
3. Só então preenche `ctx[1]` com as contagens das arestas sobreviventes.

O conjunto retido fica em `self.edges` e é reaproveitado fora do modelo: `evaluate_cluster`
calcula `edge_coverage`, `edge_usage`, `edge_f1` e `log_fitness` a partir dele.

## O piso é o que faz dele um modelo distinto

| piso | comportamento |
|---|---|
| `0.0` (default do construtor) | nenhuma aresta descartada — **é exatamente `MarkovModel(order=1)`**, verificado: `DfgModel(0.0).ctx[1] == MarkovModel(1).ctx[1]` |
| `0.05` (**usado pelo harness**, `DFG_COVERAGE_FLOOR`) | descarta as arestas raras; deixa de coincidir com a contagem crua |

Em 0.0 este não é um quinto modelo independente: é a linha de base do sucessor mais frequente
sob outro nome, e a contagem de "cinco famílias" incluiria o próprio piso dela. Em 0.05 ele
passa a ser o que o nome promete — um DFG **podado**, que é como as ferramentas de mineração de
processos efetivamente o usam.

O valor é exposto como `--dfg-floor` e gravado em `meta.dfg_coverage_floor` de cada célula, e
`load_cells` o carrega para `cell["dfg_floor"]`, para que a leitura nunca precise adivinhar qual
dos dois modelos produziu um número — e para que um agregado não misture células de pisos
diferentes sem que nada apareça no resultado.

**O piso é parâmetro do modelo, não da célula.** Até 2026-08-11 `evaluate_cluster` usava a mesma
constante para construir o DFG de onde saem `edge_coverage`, `edge_usage`, `edge_f1`,
`n_model_edges` e `log_fitness` — estatísticas da célula, calculadas até numa célula
`--models markov` que nunca instancia este modelo. Consequência: girar o botão de um modelo movia
a fidelidade de todas as outras famílias, e `log_fitness` deixava de ser o replay fitness da
relação directly-follows observada (0,8921 → 0,6929 só pela mudança de definição). Agora o DFG
das métricas de célula é construído com piso **0,0**, sempre; o `--dfg-floor` afeta apenas a
família `dfg`.

## O custo do piso, medido

Numa sonda sintética o piso de 0,05 removeu **71% das arestas** (281 → 82) e deixou o modelo
**sem previsão em 7,8% dos passos de teste**. Onde `_counts` volta vazio, a geração encerra
(contrato herdado de `MarkovModel`), e `suffix_dl` / `typical_path_distance` passam a medir um
sufixo truncado. O piso melhora a fidelidade estrutural e piora as métricas de caminho; ambas as
coisas ao mesmo tempo, e por construção.

## Determinismo

**Determinístico.** Contagens inteiras e um limiar.

## Limitações

- **Ordem 1.** O próximo passo depende só do estado atual. É a suposição que o DFG faz como
  representação, e é também sua patologia documentada como *modelo de processo*.
- **Aninhado no `markov`.** Como `markov` é ordem 3 com recuo até ordem 1, os dois convergem
  onde o contexto longo não se repete — e coincidem por construção no primeiro passo de qualquer
  geração. Não são famílias independentes; são a mesma família em dois pontos.
