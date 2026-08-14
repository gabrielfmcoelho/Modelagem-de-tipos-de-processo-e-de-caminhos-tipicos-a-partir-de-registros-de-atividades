# HDBSCAN — agrupamento por densidade, com ruído explícito

**Pergunta.** Que grupos existem quando não se diz quantos existem, e quais casos não pertencem
a grupo nenhum?

`fit(features, **params)` em `hdbscan_model.py`, sobre a biblioteca `hdbscan` de McInnes.
Registrado como `"hdbscan"` no despachante (`_dispatch.py`).

## O que faz

Constrói a hierarquia de densidade dos pontos e extrai dela a partição mais estável. Não recebe
`k`: o número de grupos é consequência da densidade, e pontos em regiões esparsas ficam
**sem grupo** — rótulo `-1`, `NOISE_LABEL`.

Essa é a diferença que separa esta família das outras três do estudo, e é uma diferença de
semântica, não de qualidade: k-means, Leiden e o consenso atribuem **todo** caso a algum grupo,
por construção. HDBSCAN se recusa.

## Parâmetros, como o código os resolve

| parâmetro | default | efeito |
|---|---|---|
| `min_cluster_size` | `20` | menor grupo admissível; abaixo disso os pontos viram ruído |
| `min_samples` | `None` (⇒ igual a `min_cluster_size`) | quão conservadora é a estimativa de densidade |
| `cluster_selection_epsilon` | `0.0` | funde grupos separados por menos que ε; é o que a variante `-hcoarse` usa (ε = 0.5) para produzir uma partição mais grossa |
| `cluster_selection_method` | `"eom"` | *excess of mass*; a alternativa `"leaf"` daria grupos menores e mais numerosos |
| `metric` | `"euclidean"` | **fixo no código** — não é parâmetro |

A métrica merece atenção: as features chegam reduzidas por UMAP com métrica cosseno, e o
agrupamento então corre em **euclidiana** sobre esse espaço reduzido. É a prática usual
(UMAP preserva vizinhança, não ângulo), mas significa que "cosseno" descreve a redução, não o
agrupamento.

## Guarda de corpus pequeno

`n < max(2, min_cluster_size)` devolve tudo como ruído com força zero, sem chamar a biblioteca.
Evita uma exceção da `hdbscan` em partições minúsculas e mantém o contrato de retorno.

## O que devolve

`ClusterResult("hdbscan", labels, strengths, params)`, onde `strengths` é
`clusterer.probabilities_` — a confiança de pertencimento por ponto, entre 0 e 1, **zero para
ruído**. É a única família que produz força de pertencimento real; as outras devolvem `1.0`
para todos.

## Determinismo

**Determinístico** dado o mesmo `.npz` de entrada e os mesmos parâmetros. `cluster-audit`
reajusta o modelo a partir da matriz carimbada e compara com os rótulos gravados.

## A limitação que a leitura precisa carregar

O ruído não é um defeito a corrigir — é o resultado. Mas ele torna a **população avaliada** desta
família menor que a das outras, e duas consequências se seguem:

1. Os índices internos (silhueta, Davies-Bouldin, Calinski-Harabasz) são calculados apenas sobre
   os pontos atribuídos (`cluster_metrics.py`, `mask = labels != -1`), isto é, sobre os pontos
   mais fáceis. Já o **DBCV recebe a matriz inteira** e é multiplicado pela fração atribuída,
   de modo que o valor publicado embute `1 − noise_ratio` como factor.
2. Os casos-ruído somem da avaliação de caminho típico (`normalize_label` mapeia `-1 → None`).

Por isso qualquer comparação com k-means ou Leiden tem de ser lida sobre a população comum —
é o que `compare_algorithms` reporta em `population_accounting`.

## Resolvido em 2026-08-12 — o ruído passa a ser atribuído por omissão

`cluster-eval` agora atribui cada ponto-ruído ao **cluster mais próximo** antes de medir
(`assign_noise_to_nearest`, centróide em espaço `umap50-cosine`, o mesmo das métricas). Por
omissão `--flag assign_noise=true`; passar `assign_noise=false` recupera o comportamento antigo.
`processo-cluster` aplica a mesma política aos rótulos macro que publica, para que o grafo, o
`labels.json` e o `names.json` descrevam uma só partição.

Modo de rótulos congelados (`--flag labels_file=`) **nunca** reatribui: ali o stage avalia uma
partição dada, não produz uma.

Consequência: `labels.json` deixa de conter `-1`, **todos os algoritmos são avaliados sobre os
mesmos casos**, e a comparação entre famílias passa a ser like-for-like. O que HDBSCAN teria
recusado agrupar não se perde — fica legível em `params`, nas chaves
`noise_ratio_before_assignment` (a fração que a densidade recusaria) e `n_reassigned`.

### Porquê — a vantagem medida era em grande parte a abstenção

Os índices internos premiam quem avalia só os casos fáceis. Enquanto HDBSCAN se abstinha e as
outras famílias não, a diferença publicada misturava duas coisas: **qualidade do agrupamento** e
**tamanho da população avaliada**. Recalculando cada partição na população completa, dois efeitos
aparecem — e ambos foram observados nesta base:

1. A vantagem de `hdbscan` sobre Leiden **encolhe**, porque parte dela era a abstenção. E Leiden
   chega ao seu valor **sem se abster**, o que importa para um catálogo entregável que tem de
   classificar todos os casos.
2. A ordem entre parameterizações do próprio HDBSCAN pode **inverter-se**: a variante que parecia
   melhor na sua própria população deixa de o ser na população comum. Um ranking que se inverte
   ao igualar a população nunca estava a medir o que dizia medir.

Os valores de cada célula estão em `artifacts/clustering/<run_id>/<algo>/metrics.json`
(`dbcv`, `silhouette`, `full_population`, e em `meta.params` o que foi reatribuído). Nenhum
número desta base é transcrito aqui: o artefacto é a fonte, e prosa com números envelhece
silenciosamente a cada nova execução.

### O efeito colateral: `noise_ratio` deixou de ser uma variável

Com a atribuição por omissão, `noise_ratio` passa a ser **zero em todas as partições**. Não é
um valor pequeno: é uma constante. Qualquer correlação contra ele fica indefinida, e qualquer
filtro do tipo "só as partições que atribuem tudo" deixa de filtrar — passa a admitir todas,
silenciosamente, sem falhar.

Ambos os casos ocorreram nesta base. A recuperação é usar
**`noise_ratio_before_assignment`**, preservado em `meta.params` de cada agrupamento e exposto
à camada de evidência como `noise_ratio_refused`: aquilo que a densidade **recusaria**. É a
variável que as afirmações sobre abstenção sempre quiseram medir — quanto uma partição se
abstém, e não o que sobrou de uma decisão de política.

> Dois consumidores dependiam de `noise_ratio` para discriminar e foram corrigidos: as
> correlações de `index_mechanism` passaram a usar `noise_ratio_refused`, e os dois portões
> `full_coverage` foram removidos por terem deixado de restringir. A cobertura continua a
> pesar na seleção como **termo pontuado**, onde ainda separa candidatos; o que desapareceu foi
> o portão, não a medida.

> Atribuir ao centróide mais próximo é **uma** escolha defensável; `approximate_predict` do
> próprio HDBSCAN seria outra, e trataria os outliers com mais cuidado. O que não é defensável é
> comparar uma família que avalia 85% com outra que avalia 100% e chamar à diferença qualidade.
