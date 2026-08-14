# Transformer — atenção sobre a janela

**Pergunta.** Atender a todas as posições da janela, em vez de comprimi-las num estado oculto,
prevê melhor o próximo passo?

`TransformerModel` em `transformer_model.py`. Registrado como `"transformer"`.

```
Embedding(V, 32, padding_idx=0) + Embedding(window, 32)   ← posicional aprendido
  → TransformerEncoder(2 × EncoderLayer(d_model=32, nhead=4, ff=64, dropout=0.2))
  → Linear(32, V)   sobre a ÚLTIMA posição
```

Três diferenças estruturais frente aos recorrentes:

- **Posição é aprendida, não implícita.** `s.pos = nn.Embedding(window, E)` somado ao embedding
  de token. Um recorrente conhece a ordem pela recorrência; aqui a ordem é um parâmetro.
- **Máscara de padding.** `src_key_padding_mask = (x == PAD)` impede que o preenchimento à
  esquerda de prefixos curtos entre na atenção. Sem ela, traces curtos atenderiam a lixo.
- **Sem máscara causal.** Não há `is_causal` nem máscara triangular — mas cada amostra de treino
  é `contexto → próximo`, e o contexto nunca contém o alvo, então não há vazamento. A atenção é
  bidirecional *dentro da janela já observada*, o que é legítimo aqui e não seria num modelo de
  linguagem autoregressivo treinado sobre a sequência inteira.

`d_model` é o **embedding** (32), e `hidden` (64) alimenta apenas o feed-forward interno — a
mesma constante significa coisas diferentes aqui e nos recorrentes.

| hiperparâmetro próprio | default |
|---|---|
| `heads` | 4 |
| `layers` | 2 |

Com `d_model = 32` e `heads = 4`, cada cabeça recebe 8 dimensões.

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
