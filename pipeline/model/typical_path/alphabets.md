# Alfabetos de traço — as três leituras da mesma trajetória

**Pergunta.** Um processo deixa uma sequência de eventos. Que sequência exatamente estamos
modelando: o que foi feito, quem fez, ou por onde passou?

Definidos em `pipeline/model/typical_eval.py` (`procedure_alphabet`, `itinerary_alphabet`,
`itinerary_visits`) e aplicados em `run_typical_eval.py`. Todo modelo de caminho típico consome
um destes três.

## O estado bruto

`protocol_traces` monta cada estado como

```python
f"{a['tipo_acao']}@{_lane(a['unidade'], lane_depth)}"
```

— **ação @ unidade**. Os outros dois alfabetos são *projeções* deste: um fica com o que está
antes do `@`, o outro com o que está depois. O bruto é a junção dos dois eixos.

## Os três, sobre a mesma trace

| | transformação | exemplo (mesma trace) | n |
|---|---|---|---|
| **`unit`** | nenhuma | `GERACAO@GAB · ASSINATURA@GAB · REMESSA@GAB · RECEBIMENTO@DGP · ANALISE@DGP · ANALISE@DGP · REMESSA@DGP · RECEBIMENTO@GAB · CONCLUSAO@GAB` | 9 |
| **`procedure`** | `partition("@")[0]`, repetições consecutivas colapsadas | `GERACAO → ASSINATURA → REMESSA → RECEBIMENTO → ANALISE → REMESSA → RECEBIMENTO → CONCLUSAO` | 8 |
| **`itinerary`** | `partition("@")[2]`, repetições consecutivas colapsadas | `GAB → DGP → GAB` | 3 |

`itinerary_visits` guarda também a contagem por visita — `[[GAB, 3], [DGP, 4], [GAB, 2]]` — de
modo que a permanência não se perde, apenas sai do alfabeto.

## O objetivo de cada um

**`unit` — o que foi feito, e por quem.** Resolução máxima. Responde *"qual o próximo passo deste
procedimento?"* sem abstrair nada, e é a previsão mais difícil: o vocabulário é da ordem de
|ações| × |unidades|, e `ANALISE` em duas unidades são dois estados distintos. É o único alfabeto
que preserva o **ritmo** — dois `ANALISE@DGP` seguidos são duas análises, não uma.

**`itinerary` — por onde o caso andou.** Responde *"por quais mesas passa um caso deste tipo, e em
que ordem?"*. Colapsar é o ponto: um caso parado em DGP por quatro eventos é **uma visita**, não
quatro. É o alfabeto do encaminhamento, do handoff e do retrabalho — uma unidade que reaparece
não-consecutivamente (GAB → DGP → GAB) é um retorno de verdade.

**`procedure` — o que foi feito, ignorando quem.** A sequência de atividades pura. Responde
*"qual é o procedimento, abstraído do organograma?"* — a visão mais transferível, porque não
depende dos nomes de unidade desta administração. **Implementado e nunca executado** (ver abaixo).

## Onde eles entram

`run_typical_eval.py --alphabet {unit,procedure,itinerary}`. O diretório de saída codifica a
escolha:

| alfabeto | diretório |
|---|---|
| `unit` | `artifacts/typical/<run_id>/<algo>/unit/` |
| `procedure` | `artifacts/typical/<run_id>/<algo>/procedure/` |
| `itinerary` | `artifacts/typical/<run_id>/<algo>/itinerary/` |

O alfabeto é um **segmento de caminho**, nunca um sufixo no nome do diretório do algoritmo.
Com sufixo, duas células podiam resolver para o mesmo arquivo — o `clusters_index.json` de uma
célula `procedure` sobrescrevia o da célula `unit` — e todo leitor tinha de reconstruir o eixo
por cirurgia de string. `load_cells` recusa uma célula cujo caminho e cujo `meta` discordem.

O stage `matrix` roda os **três**: `ALPHABETS = ALPHABET_NAMES`, a tupla única em
`model/typical_eval.py`, pelo mesmo motivo que `MODEL_NAMES` existe — uma lista literal
paralela é como um alfabeto (ou um modelo) some de metade dos consumidores sem ninguém notar.

## Armadilha de nomenclatura

O alfabeto chamado `unit` **não contém unidades sozinhas** — contém `ação@unidade`. As tabelas o
rotulam `actions` e o manuscrito o chama *action alphabet*. Três nomes, duas camadas:

| no código | nas tabelas / no artigo | o que de fato contém |
|---|---|---|
| `unit` | actions | ação **@** unidade |
| `itinerary` | routing | unidade apenas |
| `procedure` | — | ação apenas |

Renomear `unit → action` no código é seguro: nada publicado depende da string interna.

---

## Falhas conhecidas — leia antes de comparar alfabetos

### 1. A população avaliada **não é a mesma** entre alfabetos

Depois de transformar, `run_typical_eval` descarta traces com menos de dois estados:

```python
traces = {pf: tw for pf, tw in traces.items() if len(tw[1]) >= 2}
```

Um caso tratado **inteiramente dentro de uma unidade** colapsa para um único estado de itinerário
e **é descartado**:

```
unit       n=4  KEPT      GERACAO@GAB · ASSINATURA@GAB · ANALISE@GAB · CONCLUSAO@GAB
procedure  n=4  KEPT      GERACAO → ASSINATURA → ANALISE → CONCLUSAO
itinerary  n=1  DROPPED   GAB
```

Isto não é ruído: é uma exclusão **sistemática e enviesada**. O alfabeto de roteamento remove
exatamente os casos mais simples — os que nunca foram encaminhados a lugar nenhum. E o efeito se
propaga: menos casos por grupo empurra grupos abaixo do piso `min_traces=30`, então o roteamento
também avalia **menos grupos**.

Consequência para a leitura: *"ações ganham X, roteamento ganha Y"* compara dois números medidos
em populações diferentes. A diferença entre eles não é só o alfabeto.

**Resolvido em 2026-08-11 por decisão de escopo, não por filtro.** Os alfabetos medem coisas
diferentes, então **não são comparados**: cada um tem a sua matriz e o seu melhor modelo para o
seu objetivo. Sem a comparação, a assimetria de população deixa de ser um confundidor — passa a
ser apenas a descrição de cada população, e cada célula carrega a sua em
`meta.n_processos_before_min_states` / `meta.n_dropped_by_min_states`.

A alternativa que havia sido construída — restringir todos os alfabetos aos casos multi-unidade
(`artifacts/stats/multiunit_protocolos.json`, a família `_shared_population`) — foi **removida**.
Ela só existia para permitir a comparação que agora não se faz, custava de 1 a 4 h de GPU por
execução, e dependia de um arquivo sem produtor no repositório.

> Um resultado de itinerário é sobre os casos multi-unidade. Não é sobre o corpus. Diga isso ao
> lado do número, e não há nada a corrigir.

### 2. Comprimento muda, e métricas sensíveis a comprimento não são comparáveis

9 → 8 → 3 estados na mesma trace. `suffix_dl`, `suffix_length_ratio` e `typical_path_distance`
dependem do comprimento; entre alfabetos elas medem escalas diferentes. Válidas **dentro** de um
alfabeto, sem sentido **entre** eles.

### 3. Métricas de um alfabeto eram calculadas para todos — **resolvido em 2026-08-11**

`evaluate_cluster` gravava `typical_path_distance_proc` e `typical_path_distance_itin` em
**toda** célula, independentemente do alfabeto. Numa célula de itinerário a distância em "modo
procedimento" era calculada sobre estados que já eram unidades — um número sem referente, que
mesmo assim entrava na matriz.

Pior, e silencioso: `FlowState._split` parte o estado em `tipo@lane`. Num estado de itinerário
(`U1`) não há `@`, o `tipo` nunca casa com `GERACAO`/`REMETIDO`/`RECEBIDO`/`CONCLUSAO`, e
`allows()` cai no `return True` final — a restrição **nunca prende**. `flow_validity_step`,
`flow_validity_trace` e `suffix_dl_c` eram 1,0 (ou iguais ao irrestrito) por construção, e
renderizavam como números legítimos. `unit_coverage` tinha o espelho disso em `procedure`:
`itinerary_alphabet` de um estado sem `@` devolve `""`, então todo o cluster colapsava numa
única "unidade" e `unit_recall` saía 1,0.

O que cada alfabeto carrega está agora declarado num só lugar, `ALPHABET_AXES`:

| alfabeto | estado carrega | emite fluxo | emite métricas de unidade | projeta em outro alfabeto |
|---|---|---|---|---|
| `unit` | ação + unidade | sim | sim | sim (`_proc`, `_itin`) |
| `procedure` | ação | sim (uma raia só) | não | não |
| `itinerary` | unidade | **não** | sim | não |

A regra é: uma métrica é emitida quando o eixo que ela mede existe no alfabeto da célula. Onde
não existe, a chave **não aparece** — ausência é honesta, `1.0` não é.

### 4. Dificuldade desigual

O vocabulário de `unit` é o produto dos dois eixos; o de `itinerary` é o menor dos três. Um top-1
maior em roteamento pode significar apenas que há menos candidatos por passo. Comparar acurácia
entre alfabetos sem normalizar pela dificuldade não diz o que parece dizer.

### 5. `procedure` é alcançável e não exercitado — **resolvido em 2026-08-11**

Era aceito pela CLI, ausente de `matrix.ALPHABETS` e de `compose.lattice.ALPHABETS`, e
*default* do stage `conformance`. Duas consequências silenciosas: uma célula `-proc` era lida
como **algo `kmeans-proc`, alfabeto `unit`**, e o seu `clusters_index.json` sobrescrevia o da
célula `unit` — `write_artifact` usa `force=True` e `kmeans` < `kmeans-proc` na ordenação, então
`procedure` era emitido por último e ganhava.

Agora os três alfabetos são eixo de primeira classe: segmento de caminho próprio, tupla única
`ALPHABET_NAMES`, e cada um com a sua matriz completa de `arm × algoritmo × modelo`. Nenhum
agregado mistura alfabetos — `write_composed` recusa um artefato cujo `scope` não fixe o
alfabeto nem o declare em `aggregated_over`.
