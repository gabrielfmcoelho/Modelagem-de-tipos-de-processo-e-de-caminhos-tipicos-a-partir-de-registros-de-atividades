# Naming — nomear categorias emergentes em duas passagens

**Pergunta:** que nome em linguagem natural descreve cada categoria, de modo que um leitor
consiga **distinguir** categorias vizinhas?

`name_all_clusters` em `naming.py`. Chamado por `processo-cluster` (caminho principal) e pelo
stage `cluster-name`.

> **Qual dos dois usar.** `processo-cluster` só nomeia **HDBSCAN** — recusa qualquer outro
> `algo`, porque constrói a hierarquia macro→micro e usa a probabilidade de pertença do HDBSCAN
> como `confidence`. Para nomear uma partição plana de qualquer algoritmo (k-means, Leiden,
> HDBSCAN) existe o stage **`cluster-name`**, que escreve `names.json` sem tocar no grafo.
> Nomeie **todas** as partições, não apenas a que se julga vencedora: `tab:catalogue` segue o
> agrupamento que `selection_full_coverage` escolher, e se esse não tiver `names.json` a tabela
> sai vazia e o stage `results` falha. Custa segundos por partição. O modelo declarado do SEI (`TipoProcedimento`) **nunca** entra aqui — o
nome emerge do conteúdo e do fluxo observados. Usá-lo tornaria circular a concordância
ARI/NMI-vs-tipo, que é justamente o instrumento externo de avaliação da partição.

## O problema: nomear por frequência produz nomes iguais

Cada categoria era nomeada **isoladamente**, e as palavras-chave enviadas ao modelo eram as
**mais frequentes** da categoria. Dentro de uma mesma família de processos, os termos mais
frequentes são exatamente os **partilhados**. O padrão observado é uma família inteira de
categorias com nomes quase indistinguíveis:

```
Suporte Técnico para Regularização do Sistema de Ponto Eletrônico
Suporte Técnico e Visitas para Regularização de Sistema de Ponto Eletrônico
Suporte Técnico e Manutenção de Ponto Eletrônico
Suporte Técnico e Manutenção de Equipamentos de Ponto Eletrônico
Suporte Técnico e Manutenção de Sistemas de Ponto Eletrônico
```

Nomear por frequência **garante** nomes parecidos para categorias parecidas. E o LLM não podia
diferenciá-las: nunca via as concorrentes.

## Passagem 1 — tema comum + termos distintivos

Cada categoria recebe **dois** conjuntos de palavras-chave:

| conjunto | o que é | papel no prompt |
|---|---|---|
| `top_keywords` | as mais frequentes na categoria | o **tema**, provavelmente partilhado |
| `distinctive_keywords` | as **sobre-representadas** aqui em relação ao resto do corpus | o que **qualifica** o tema |

`distinctive_keywords` compara a probabilidade do termo dentro da categoria com a probabilidade
fora dela, com suavização de Laplace (`alpha=0.5`), e ordena por *lift*:

```
p_in  = (c_cluster + a) / (n_cluster + 2a)
p_out = (c_resto    + a) / (n_resto   + 2a)
lift  = p_in / p_out          # só entram os termos com p_in > p_out
```

Numa família de categorias vizinhas, os termos que **separam** (o subsistema, o modo de
atendimento, o equipamento concreto) alcançam *lift* de ordens de grandeza acima dos termos que
**unem** — que são justamente os mais frequentes. É esse contraste que a passagem 1 explora: os
termos discriminantes deixam de ser abafados pelos partilhados.

## Passagem 2 — renomear apenas as colidentes, com as rivais à vista

Depois da passagem 1, `near_duplicate_groups` agrupa categorias cujos **nomes** se parecem
(Jaccard sobre tokens, sem acentos, sem stopwords). Só os membros desses grupos são renomeados,
agora recebendo `sibling_profiles`: o nome, o tamanho e os termos distintivos de cada rival, com
a instrução explícita de dar um nome que as **distinga**.

Custo: apenas as colidentes voltam ao LLM — uma pequena fração das categorias, não todas.

### O limiar é 0.55, e não é arbitrário

Foi escolhido por varredura sobre os nomes produzidos pela passagem 1, observando o
comportamento do agrupamento e não uma métrica de qualidade:

| limiar | comportamento |
|---|---|
| ≥ 0.60 | **parte** a família de homônimos em subgrupos — cada metade é renomeada sem ver a outra, e as colisões sobrevivem |
| **0.55** | captura a família inteira num só grupo, que é a condição para o LLM poder diferenciá-la |
| ≤ 0.50 | **degenera**: categorias não relacionadas colapsam num grupo único e o prompt perde foco |

A janela útil é estreita porque a similaridade de Jaccard entre nomes curtos salta em degraus.
`max_group` limita quantas rivais entram no prompt. Para repetir a varredura numa base nova,
chame `near_duplicate_groups` sobre o `names.json` da execução.

## Resultado e o que ele revela

A passagem 2 reduz fortemente o número de grupos quase homônimos, mas **não a zero** — e o que
resta é informativo:

```
-> Suporte Técnico e Regularização de Conexão VPN para Sistema de Ponto Eletrônico
-> Suporte Técnico Remoto para Regularização de Batidas de Ponto Eletrônico
-> Suporte Técnico e Diagnóstico de Falhas no Sistema de Ponto Eletrônico
-> (inalterado — "equipamentos" já distinguia)
```

> Quando duas categorias continuam a colidir mesmo com as rivais à vista e com os termos
> distintivos no prompt, isto **deixou de ser** uma falha de nomeação: com o confundidor
> removido, uma colisão que sobrevive é indício de que a **partição** não separa as duas
> categorias. É um sinal sobre o agrupamento, para ser lido junto com a concordância
> ARI/NMI-vs-tipo — não sobre o nomeador.

## Armadilhas

- `_disambiguate_names` resolve apenas nomes **idênticos** (acrescenta um marcador ou `(2)`).
  Não vê quase-homônimos — foi por isso que as cinco categorias passaram.
- A passagem 2 anterior agrupava por igualdade exata de nome em minúsculas; capturava só
  duplicados literais.
- Sem `keywords_by_pf` (o store de `keywords`), ambos os conjuntos ficam vazios e a nomeação
  regride para amostras apenas — categorias vizinhas voltam a receber nomes parecidos.
  O stage `keywords` tem de correr **antes** de `build-arm`, para os dois braços.
