# Markov — cadeia de ordem variável com recuo

**Pergunta.** Quanto do próximo passo se explica contando as sequências curtas que já foram
observadas?

`MarkovModel(order)` em `markov_model.py`. O harness usa **ordem 3**
(`typical_eval.default_specs`). É a linha de base contra a qual todo o resto é lido, e é também
a classe-mãe de `dfg` e `gnn`, que herdam dela toda a decodificação.

## O que faz

`fit` conta, para cada posição da trace, os sufixos de tamanho 1 até `order`:

```
ctx[o][(s_{i-o} … s_{i-1})][s_i] += 1
```

São `order` tabelas simultâneas, não uma só. A previsão (`_counts`) tenta a mais longa que
existe e **recua** até a de ordem 1:

```python
for o in range(min(self.order, len(prefix)), 0, -1):
    c = self.ctx[o].get(tuple(prefix[-o:]))
    if c:
        return c
return Counter()
```

O recuo é o que mantém o modelo utilizável em grupos perto do piso de 30 traces, onde contextos
de ordem 3 quase nunca se repetem.

## Recuo não é suavização — e a distinção é medível

O código devolve o **primeiro contexto não vazio** e para. Não há interpolação entre ordens, nem
desconto, nem massa reservada para o que não foi visto. Um sucessor nunca observado naquele
contexto recebe probabilidade **exatamente zero**.

Consequência medida em dados sintéticos: a cadeia de ordem 3 atribui zero a **54,25%** dos
próximos passos do conjunto de teste (`oov_rate`), contra 6,8% da DFG de ordem 1. O harness
piso-a esses zeros em `1e-6` para calcular NLL, então a coluna `nll` ordena **política de
suavização**, não qualidade de ajuste.

Isso não contamina nenhum número publicado: `nll` e `perplexity` não entram em
`evaluate_matrix`. Mas a leitura de "ordem 3 com recuo" como um modelo probabilístico bem
formado seria errada — ele é um estimador de contagem com seleção de contexto.

## Interface que as subclasses herdam

Tudo passa por `_counts`. `predict_next` ordena por contagem; `next_distribution` normaliza;
`generate` faz busca em feixe com `log(cnt/total)`; `_sample` amostra com temperatura
(`counts[s] ** (1/T)` — invariante a escala, então funciona igual se `_counts` devolver
probabilidades em vez de contagens). Sobrescrever `_counts` sozinho basta para trocar o
estimador mantendo a decodificação — é o que `GcnModel` faz.

`generate` termina quando `is_conclusion(último)` ou quando `_counts` volta vazio. Um estado
nunca visto como origem encerra a geração; é esse contrato que o GCN teve de reproduzir.

## Determinismo

**Determinístico.** Contagens inteiras, decodificação gulosa/feixe. `_sample` depende do `rng`
recebido e é o único caminho estocástico.

## Limitações

- **Primeiro passo é sempre ordem 1.** Em `generate`, o prefixo inicial tem comprimento 1, então
  `min(order, len(prefix)) = 1`: a abertura é, por construção, uma decisão de ordem 1 — idêntica
  à da DFG sem piso.
- `from_counts` constrói com `cls(order=1)` e por isso **quebra nas subclasses**, cujos `__init__`
  não aceitam `order`. Não é usado no pipeline.
