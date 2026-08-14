# LSTM — recorrente com célula de memória

**Pergunta.** A célula de memória do LSTM captura algo que a GRU não captura nestes traces?

`TrueLSTMModel` em `lstm_model.py`. Registrado como `"lstm"`.

```
Embedding(V, 32, padding_idx=0) → LSTM(32, 64, batch_first) → Dropout(0.2) → Linear(64, V)
```

**Idêntico à GRU exceto pela camada recorrente.** `forward` desempacota `(h, c)` e usa
`h[-1]` — o estado oculto final, descartando o estado de célula. Mesmo tamanho de embedding,
mesmo tamanho oculto, mesmo dropout, mesma leitura do último passo.

Essa igualdade é o ponto: a comparação GRU × LSTM é uma comparação de **arquitetura recorrente**
e de mais nada. Se as duas empatam, a porta extra do LSTM não está comprando nada nestes traces
— que é uma conclusão sobre o dado, não sobre as bibliotecas.

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
