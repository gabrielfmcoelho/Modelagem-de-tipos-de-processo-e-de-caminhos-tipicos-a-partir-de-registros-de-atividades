# GCN — convolução de grafo sobre o grafo directly-follows

**Pergunta.** O próximo passo se prevê melhor propagando informação pela *vizinhança* do estado
atual no grafo do processo, em vez de contar apenas as transições que saem dele?

`GcnModel` em `gnn_model.py`. Registrado como `"gnn"` no harness.

## Por que existe

Markov e DFG são estimadores locais: a previsão para o estado `s` usa apenas as transições
observadas a partir de `s`. Um estado raro — visto três vezes na partição — tem uma estimativa
de três amostras, e nada a corrige.

O GCN muda exatamente isto. Duas rodadas de passagem de mensagem fazem a previsão de `s`
incorporar os vizinhos de `s` no grafo, então um estado raro **toma emprestado** de estados
estruturalmente parecidos. É a única família do conjunto que generaliza *pelo grafo* em vez de
pela sequência.

Comportamento observado num caso construído, **nos defaults desta tabela** (200 épocas): com
`E → C` como única transição observada a partir de `E`, o modelo atribui 0,7884 a `C` e
**0,1966 a `D`** — sucessor que nunca seguiu `E`, mas que segue `B`, vizinho estrutural de `E`.
Markov e DFG atribuem 1,0 a `C` e zero a todo o resto.

## Arquitetura

Grafo `G` construído do conjunto de treino: nós são estados, arestas são transições observadas.

1. **Adjacência** `A[i,j]` = contagem de `i → j`, simetrizada (`A + Aᵀ`) e com laços próprios.
2. **Normalização** simétrica `Â = D^-1/2 (A + I) D^-1/2`.
3. **Duas camadas** sem atributos de entrada — a matriz identidade implícita faz de `W₁` uma
   tabela de embeddings: `Z = Â · relu(Â · W₁) · W₂`, com `Z ∈ ℝ^{V×V}`.
4. **Previsão**: `softmax(Z[s])` é a distribuição do próximo estado dado `s`.

Treino por entropia cruzada sobre todos os pares `(i, j)` observados, Adam.

| hiperparâmetro | default |
|---|---|
| `hidden` | 64 |
| `epochs` | 200 |
| `lr` / `weight_decay` | 0.01 / 1e-4 |
| `seed` | 42 |
| `device` | `cpu` — o grafo tem centenas de nós, não milhões |

## Como se encaixa no harness

Herda de `MarkovModel` e sobrescreve **apenas** `fit` e `_counts`. Todo o resto — `predict_next`,
`next_distribution`, `generate`, feixe, amostragem, decodificação restrita — é o mesmo código dos
baselines. Isso é deliberado: a comparação mede a *estimativa*, não a decodificação.

**Estados terminais.** Um estado que nunca apareceu como origem no treino devolve `Counter()`
vazio, como em Markov e DFG. Sem isso o softmax daria massa a sucessores de `<END>` e a geração
não terminaria — foi o primeiro comportamento observado ao integrar o modelo.

## Determinismo

**Condicional**, fixado por `seed=42` — e a reprodutibilidade é *bit a bit*, não aproximada.
Isso exige uma providência que não é óbvia: `fit` fixa `torch.set_num_threads(1)` durante o
treino e restaura depois. Sem isso o GEMM multi-thread soma em ordem variável e duas execuções
idênticas divergem — medido em `1e-6` a `1e-4` nos pesos, o bastante para **trocar a ordem do
top-3** em uma linha em 27. Não é não-determinismo de CUDA: acontece em CPU.

Verificado em grafo de 31 estados e 2.371 transições: três ajustes com a mesma semente dão
matrizes de probabilidade idênticas bit a bit. `test_gnn_model.py` cobre esse tamanho, e não
apenas o grafo de brinquedo — o toy de 5 nós passava mesmo antes da correção.

## Limitações que a leitura precisa carregar

- **Ordem 1 na entrada.** A previsão condiciona no último estado, não na janela. O que ele
  ganha é vizinhança no grafo, não memória de sequência; comparado à GRU ele troca uma coisa
  pela outra.
- **Sem atributos de nó.** `W₁` é uma tabela de embeddings aprendida do zero. Nós com atributos
  (banda documental, tempo médio de posse) são um caminho aberto e não medido.
- **Suavização é uma faca de dois gumes.** A mesma propagação que ajuda um estado raro pode
  atribuir massa a transições que o processo não permite. A decodificação restrita é o que
  impede isso de virar um caminho inválido no catálogo; o custo aparece em `constraint-cost`.
