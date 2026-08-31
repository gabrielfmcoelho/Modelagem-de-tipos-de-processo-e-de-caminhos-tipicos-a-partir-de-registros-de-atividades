# Famílias de processo no corpus VIVO — Modelo A (k-means) e Modelo B (random forest)

`scripts/lake_cluster_experiment.py` · run id `exp-lake` ·
saídas em `artifacts/clustering/exp-lake/kmeans/`

> Registro descritivo de um experimento **ad-hoc**. Nada aqui entra no pipeline
> reprodutível do artigo, nenhum número daqui vai para `RESULTS.md`, e `exp-lake`
> não é um braço — não dispara os guards de `_arm_of`.

## A pergunta

O estudo agrupou processos **concluídos em 2025**. A operação precisa de outra
coisa: saber a que família pertence um processo **que ainda está correndo** —
que é justamente aquele cujo trace está incompleto.

## Por que roda neste repositório, e não numa DAG

Tudo de que o experimento precisa já existe aqui, testado e com model card:

| peça | de onde vem |
|---|---|
| varredura de `k` + cotovelo | `pipeline/evidence/clustering/select_k.py` (`sweep_kmeans`, `elbow_index`) |
| nomeação contrastiva em 2 passagens | `pipeline/model/clustering/naming.py` (`name_cluster`, `distinctive_keywords`, `near_duplicate_groups`) |
| truncamento de trace | `processo_features.apply_cutoff` |
| os 6 blocos de feature | `processo_features.build_batch_features` |
| divisão 70/30 estável por processo | `predict.is_train_protocolo` (blake2b do protocolo) |

Reescrever isso do lado do Airflow seriam ~400 linhas reimplementadas para ganhar
o quê. Quando os números se sustentarem, o que vira DAG é só o caminho de
**predição** do Modelo B.

## Fonte dos dados

Trino, direto — o lake já materializou o que o experimento precisa:

| bloco | tabela | observação |
|---|---|---|
| trace (`tipo_acao`, unidade, timestamp) | `sei_silver.processos_atividades` | `tipo_acao` vem PRONTO: são os mesmos 47 padrões ordenados de `pipeline/model/classifier.py`, os dois portados do classificador do dl-api com teste de paridade dos dois lados. **Nenhuma reclassificação.** |
| palavras-chave canônicas | `sei_gold.processos_ia.palavras_chave` | vocabulário controlado do lake (`scripts/ia_keywords.py`), o análogo do stage `keywords` |
| tópico / resumo | `sei_gold.processos_ia.categoria` / `.entendimento_inicial` | análogo direto do que o stage `evaluate` produz |
| embedding do 1º documento | `sei_gold.documentos_texto.embedding` | bge-m3 1024-d, gravado pela task `gera_embeddings` |
| status | `sei_gold.processos_metadados.status` | separa concluídos de em andamento |

Processo sem trace **ou** sem embedding do primeiro documento fica de fora: sem o
bloco semântico ele seria descrito só pelo fluxo e entraria no mesmo espaço com
metade da informação dos outros — pior que ausente.

## Modelo A — k-means com `k` do cotovelo

Ajustado **só nos concluídos com trace completo**. `sweep_kmeans` varre a grade e
`elbow_index` escolhe o `k`; `k_best_silhouette` e `k_combined` saem da mesma
varredura e são reportados para comparação.

O cotovelo é o critério primário, e isso é deliberado. Como diz
[`kmeans.md`](../../pipeline/model/clustering/kmeans/kmeans.md): a silhueta
**favorece estruturalmente** o k-means, porque os dois otimizam a mesma geometria
— compacidade em torno de um centro contra separação entre centros. Os índices
internos entram como *descrição da partição*, nunca como prova de que ela é a
certa. `at_grid_edge` avisa quando o ótimo cai na borda da grade.

Nomeação: as funções de [`naming.md`](../../pipeline/model/clustering/naming.md),
com a amostra vinda do lake. A 2ª passagem (só as colidentes voltam à LLM, agora
com as rivais à vista) é o que impede a família de nomes quase idênticos que
nomear-por-frequência **garante** produzir.

## Modelo B — o prefixo prevê a família

### O problema

Pontuar um processo em andamento com os centróides do Modelo A compara um trace
**parcial** contra um espaço construído com traces **completos**. Um processo
curto-e-correndo fica parecido com um curto-e-terminado, e é atribuído
sistematicamente errado.

### O treino

Cada processo concluído é reconstruído em quatro visões — 25%, 50%, 75% e 100%
dos seus eventos (`apply_cutoff`) — todas **rotuladas com o cluster do trace
completo**. O random forest aprende "com esta evidência parcial, qual família",
não "qual família tem o centróide mais perto".

100% entra na grade porque um processo em andamento pode estar em qualquer ponto
do ciclo, inclusive quase no fim.

**Um único modelo, treinado sobre todos os cortes.** Em produção não se sabe em
que fração do ciclo um processo em andamento está — não há como escolher um
modelo por corte. O preço é acurácia menor no trace completo do que um modelo
dedicado a ele teria; é o preço de funcionar em qualquer prefixo.

### A divisão

70/30 por `is_train_protocolo` (blake2b do protocolo). Como cada processo aparece
em quatro visões, dividir por LINHA poria o mesmo processo dos dois lados e a
acurácia seria fantasia.

## A entrega é a curva, não um número

Acurácia e F1-macro **por corte**, contra dois baselines:

- **classe majoritária** — o piso;
- **centróide-mais-próximo do Modelo A** sobre as MESMAS features truncadas — o
  que o Modelo A faria sozinho.

**Se o random forest não bate o centróide nos cortes truncados, ele não se paga:
pontue por centróide e descarte o Modelo B.**

A comparação vale **só nos cortes truncados**. Em 100% o centróide acerta tudo
*por construção* — foi assim que os rótulos nasceram. Cobrar do random forest que
vença uma tautologia é cobrar a coisa errada. O que 100% dá é uma **âncora de
sanidade**: se o centróide não fecha em 1,0 ali, espaço e rótulos estão
inconsistentes e o resto da tabela não significa nada.

Também sai **recall por cluster**. Cluster pequeno é inaprendível, e a resposta
honesta é um piso de confiança (`--confianca-min`, default 0,35) abaixo do qual
nenhum rótulo é gravado — nunca um chute silencioso.

## Uma limitação conhecida, registrada de propósito

Todas as visões passam por **uma** chamada de `build_batch_features`, porque os
vetorizadores TF-IDF são ajustados lá dentro: visões ajustadas em chamadas
separadas teriam vocabulários e idf diferentes, e o Modelo B precisa exatamente
do contrário — treinar num espaço e predizer no mesmo.

O efeito colateral é que o **idf é calculado sobre a união das visões**, então
estatísticas da população de inferência entram no espaço de treino. São
*features*, não rótulos, e a magnitude é pequena (as visões são truncamentos dos
mesmos processos). O UMAP já é ajustado **só nas visões de trace completo dos
concluídos** e aplicado ao resto, então essa metade já está correta.

**Ao virar produção isto tem de mudar:** ajustar vetorizadores + UMAP sobre os
concluídos, persistir com `joblib` e só TRANSFORMAR o resto. Fica aqui para que
o experimento não passe por leak-free.

## Saídas

| arquivo | o que é |
|---|---|
| `k_sweep.json` | a grade inteira + `k_elbow`, `k_best_silhouette`, `k_combined`, `at_grid_edge` |
| `labels.json` | protocolo → cluster (concluídos, Modelo A) |
| `names.json` | cluster → nome, descrição, marcadores |
| `model_b.json` | a curva por corte, os baselines, o recall por cluster, os avisos |
| `assignments.json` | **o que o lake ingere**: protocolo → cluster + confiança + origem (`kmeans-A` \| `rf-B`) |

O experimento **não escreve no lake**. `assignments.json` é lido do outro lado
por `scripts/load_cluster_labels.py` (em `dlhsead-infra-airflow`), que grava com
`merge_cluster_rows` — um MERGE que toca só as colunas de cluster de
`sei_gold.processos_ia`. A tabela tem dois escritores de IA e o `UPDATE SET` deles
é montado a partir de `COLUMNS` inteiro; um rótulo gravado por aquele caminho
seria apagado na próxima regeneração de IA, e a IA na próxima clusterização.

A separação também é de higiene: o lado que experimenta não precisa de credencial
de escrita, e o lado que escreve não precisa de sklearn/umap.

## Como rodar

```bash
PY=.venv/bin/python

# ensaio: recorte determinístico, sem gastar LLM na nomeação
$PY scripts/lake_cluster_experiment.py --limit 400 --skip-naming

# completo
$PY scripts/lake_cluster_experiment.py --run-id exp-lake

# ingestão, do lado do lake (dlhsead-infra-airflow)
python scripts/load_cluster_labels.py \
    --arquivo .../artifacts/clustering/exp-lake/kmeans/assignments.json --apply
```

Checagem: `pipeline/tests/test_lake_cluster_experiment.py` roda o experimento
inteiro sobre um corpus sintético com **estrutura conhecida** (três famílias com
fluxo, unidades e vocabulário próprios). Se ele não recuperar famílias plantadas
de propósito, também não vai recuperar as reais.
