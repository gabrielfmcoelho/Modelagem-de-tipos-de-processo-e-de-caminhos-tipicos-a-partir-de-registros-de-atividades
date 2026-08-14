# GRU — recorrente com porta

**Pergunta.** Uma rede recorrente sobre a janela recente prevê melhor que a contagem de Markov?

`LSTMModel` em `gru_model.py` — **o nome da classe é histórico; a arquitetura é GRU**.
Registrado como `"gru"` no harness.

```
Embedding(V, 32, padding_idx=0) → GRU(32, 64, batch_first) → Dropout(0.2) → Linear(64, V)
```

`forward` lê **apenas o último estado oculto** (`h[-1]`), não a sequência de saídas: a janela
inteira é comprimida num vetor de 64 dimensões e a previsão sai dele. É a diferença essencial
para o Transformer, que atende a todas as posições.

## O que os três compartilham — `_TorchSeqModel`

Arquitetura à parte, os três modelos neurais são **o mesmo experimento**: mesma janela, mesmo
laço de treino, mesma tokenização, mesma decodificação. A comparação entre eles isola a camada
que muda.

- **Vocabulário.** Construído do conjunto de treino; `PAD = 0`, `UNK = 1`, estados a partir de 2.
- **Janela.** `_encode` toma os últimos `window` estados e preenche à esquerda com `PAD`. Um
  prefixo mais curto que a janela é preenchido, nunca descartado.
- **Amostras.** Uma por posição `i ≥ 1` de cada trace: contexto → próximo estado.
- **Treino.** Adam, `weight_decay = 1e-4`, entropia cruzada, embaralhamento por época
  (`torch.randperm`), lotes de `batch_size`. `torch.manual_seed(seed)` antes de construir a rede.
- **Dispositivo.** `select_device()` — GPU quando disponível. O harness marca as três famílias
  `requires_gpu=True` e as pula quando não há CUDA.
- **Previsão.** `_next_dist` devolve `softmax(logits)` **descartando PAD e UNK sem
  renormalizar**, então a distribuição destes três modelos soma um pouco menos que 1 — ao
  contrário de markov, dfg e gnn.

| hiperparâmetro | default |
|---|---|
| `embed` / `hidden` | 32 / 64 |
| `window` | 8 estados de contexto |
| `epochs` / `lr` | 30 / 0.01 |
| `batch_size` / `dropout` / `seed` | 2048 / 0.2 / 42 |
| `aux_lambda` | 0.0 — **desligado** |

**Modos que o harness não usa.** `aux_lambda > 0` acrescenta uma perda auxiliar que penaliza
massa em transições que o autômato de fluxo proíbe; `fit_rl` é um ajuste fino REINFORCE que
recompensa validade estrutural. Ambos existem, têm testes, e **nenhum número dos manuscritos
passa por eles** — `default_specs` constrói os três modelos só com `epochs`.

## Determinismo

**Não determinístico.** Treino em GPU: inicialização e não-determinismo de kernels CUDA fazem
execuções idênticas divergirem. O `seed` reduz a variação, não a elimina. (Contraste: o `gnn`
roda em CPU com uma thread e é reprodutível bit a bit.)
