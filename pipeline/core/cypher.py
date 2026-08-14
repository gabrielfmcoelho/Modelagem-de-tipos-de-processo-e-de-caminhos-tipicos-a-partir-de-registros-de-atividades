
from __future__ import annotations

SETUP_CONSTRAINTS: list[str] = [
    "CREATE CONSTRAINT processo_protocolo IF NOT EXISTS FOR (p:Processo) REQUIRE p.protocolo_formatado IS UNIQUE",
    "CREATE CONSTRAINT atividade_source_id IF NOT EXISTS FOR (a:Atividade) REQUIRE a.source_id IS UNIQUE",
    "CREATE CONSTRAINT unidade_sigla IF NOT EXISTS FOR (u:Unidade) REQUIRE u.sigla IS UNIQUE",
    "CREATE CONSTRAINT tipo_procedimento_nome IF NOT EXISTS FOR (tp:TipoProcedimento) REQUIRE tp.nome IS UNIQUE",
    "CREATE CONSTRAINT tipo_acao_chave IF NOT EXISTS FOR (ta:TipoAcao) REQUIRE ta.chave IS UNIQUE",
    "CREATE CONSTRAINT grupo_atividade_chave IF NOT EXISTS FOR (ga:GrupoAtividade) REQUIRE ga.chave IS UNIQUE",
    "CREATE CONSTRAINT orgao_sigla IF NOT EXISTS FOR (o:Orgao) REQUIRE o.sigla IS UNIQUE",
    "CREATE CONSTRAINT usuario_nome IF NOT EXISTS FOR (u:Usuario) REQUIRE u.nome IS UNIQUE",
    "CREATE CONSTRAINT documento_numero IF NOT EXISTS FOR (d:Documento) REQUIRE d.numero IS UNIQUE",
    "CREATE INDEX atividade_data IF NOT EXISTS FOR (a:Atividade) ON (a.data_hora)",
    "CREATE INDEX processo_data_criacao IF NOT EXISTS FOR (p:Processo) ON (p.data_criacao)",
    "CREATE INDEX atividade_seq IF NOT EXISTS FOR (a:Atividade) ON (a.seq)",
    "CREATE CONSTRAINT ciclo_id IF NOT EXISTS FOR (c:Ciclo) REQUIRE c.id IS UNIQUE",
    "CREATE INDEX ciclo_status IF NOT EXISTS FOR (c:Ciclo) ON (c.status)",
    "CREATE INDEX ciclo_entrada IF NOT EXISTS FOR (c:Ciclo) ON (c.entrada)",
    "CREATE INDEX processo_situacao IF NOT EXISTS FOR (p:Processo) ON (p.situacao)",
    """CREATE VECTOR INDEX documento_embedding_idx IF NOT EXISTS
       FOR (d:Documento) ON d.embedding
       OPTIONS { indexConfig: {
           `vector.dimensions`: 1024,
           `vector.similarity_function`: 'cosine'
       }}""",
    "CREATE INDEX similar_doc_tier IF NOT EXISTS FOR ()-[r:SIMILAR_DOC]-() ON (r.tier)",
    "CREATE INDEX similar_doc_intra IF NOT EXISTS FOR ()-[r:SIMILAR_DOC]-() ON (r.intra_processo)",
    "CREATE CONSTRAINT categoria_processo_id IF NOT EXISTS FOR (c:CategoriaProcesso) REQUIRE c.id IS UNIQUE",
    "CREATE INDEX categoria_processo_nivel IF NOT EXISTS FOR (c:CategoriaProcesso) ON (c.nivel)",
    "CREATE CONSTRAINT coorte_id IF NOT EXISTS FOR (c:Coorte) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT dfg_node_id IF NOT EXISTS FOR (n:DfgNode) REQUIRE n.id IS UNIQUE",
    "CREATE INDEX dfg_node_cohort IF NOT EXISTS FOR (n:DfgNode) ON (n.cohort_id)",
    "CREATE INDEX seguida_contrib IF NOT EXISTS FOR ()-[r:SEGUIDA_POR]-() ON (r.contrib_cohort_id)",
    "CREATE INDEX directly_follows_cohort IF NOT EXISTS FOR ()-[r:DIRECTLY_FOLLOWS]-() ON (r.cohort_id)",
    "CREATE CONSTRAINT comum_node_id IF NOT EXISTS FOR (n:ComumNode) REQUIRE n.id IS UNIQUE",
    "CREATE INDEX comum_node_cohort IF NOT EXISTS FOR (n:ComumNode) ON (n.cohort_id)",
]

SEED_TIPOS_CYPHER = """
UNWIND $types AS t
MERGE (ta:TipoAcao {chave: t.chave})
WITH ta, t
MATCH (ga:GrupoAtividade {chave: t.grupo})
MERGE (ta)-[:PERTENCE_AO_GRUPO]->(ga)
"""

PRECREATE_PROCESSOS_CYPHER = """
UNWIND $rows AS r
MERGE (p:Processo {protocolo_formatado: r.protocolo_formatado})
ON CREATE SET p.data_criacao = datetime(r.data_criacao)
SET p.id_processo = r.id_processo
WITH p, r
WHERE r.tipo_procedimento IS NOT NULL
MERGE (tp:TipoProcedimento {nome: r.tipo_procedimento})
MERGE (p)-[:TEM_TIPO]->(tp)
"""

PRECREATE_USUARIOS_CYPHER = """
UNWIND $users AS u
MERGE (usr:Usuario {nome: u.nome})
WITH usr, u
MATCH (o:Orgao {sigla: u.orgao})
MERGE (usr)-[:PERTENCE_AO_ORGAO]->(o)
"""

LOAD_ATIVIDADES_CYPHER = """
UNWIND $rows AS row

MATCH (proc:Processo {protocolo_formatado: row.protocolo_formatado})
MATCH (uni:Unidade {sigla: row.unidade})
MATCH (ta:TipoAcao {chave: row.tipo_acao})
MATCH (usr:Usuario {nome: row.usuario})

MERGE (atv:Atividade {source_id: row.source_id})
ON CREATE SET
    atv.data_hora = datetime(row.data_hora),
    atv.descricao = row.descricao,
    atv.tipo_acao = row.tipo_acao,
    atv.grupo = row.grupo,
    atv.ref_id = row.ref_id,
    atv.seq = row.seq,
    atv.is_start = row.is_start,
    atv.is_conclusion = row.is_conclusion

MERGE (atv)-[:DO_PROCESSO]->(proc)
MERGE (atv)-[:EXECUTADO_PELA_UNIDADE]->(uni)
MERGE (atv)-[:TIPO_ACAO]->(ta)
MERGE (atv)-[:EXECUTADO_PELO_USUARIO]->(usr)
"""

LOAD_ATIVIDADE_NODES_CYPHER = """
UNWIND $rows AS row
MATCH (proc:Processo {protocolo_formatado: row.protocolo_formatado})
MERGE (atv:Atividade {source_id: row.source_id})
ON CREATE SET
    atv.data_hora = datetime(row.data_hora),
    atv.descricao = row.descricao,
    atv.tipo_acao = row.tipo_acao,
    atv.grupo = row.grupo,
    atv.ref_id = row.ref_id,
    atv.seq = row.seq,
    atv.is_start = row.is_start,
    atv.is_conclusion = row.is_conclusion
MERGE (atv)-[:DO_PROCESSO]->(proc)
"""

LOAD_ATIVIDADE_DIM_EDGES_CYPHER = """
UNWIND $rows AS row
MATCH (atv:Atividade {source_id: row.source_id})
MATCH (uni:Unidade {sigla: row.unidade})
MATCH (ta:TipoAcao {chave: row.tipo_acao})
MATCH (usr:Usuario {nome: row.usuario})
MERGE (atv)-[:EXECUTADO_PELA_UNIDADE]->(uni)
MERGE (atv)-[:TIPO_ACAO]->(ta)
MERGE (atv)-[:EXECUTADO_PELO_USUARIO]->(usr)
"""

LOAD_UNIDADE_EDGES_CYPHER = """
UNWIND $rows AS row
MATCH (atv:Atividade {source_id: row.source_id})
MATCH (uni:Unidade {sigla: row.unidade})
MERGE (atv)-[:EXECUTADO_PELA_UNIDADE]->(uni)
WITH atv, row
WHERE row.source_unidade IS NOT NULL
MATCH (su:Unidade {sigla: row.source_unidade})
MERGE (atv)-[:REMETIDO_PELA_UNIDADE]->(su)
"""

LOAD_TIPO_ACAO_EDGES_CYPHER = """
UNWIND $rows AS row
MATCH (atv:Atividade {source_id: row.source_id})
MATCH (ta:TipoAcao {chave: row.tipo_acao})
MERGE (atv)-[:TIPO_ACAO]->(ta)
"""

LOAD_USUARIO_EDGES_CYPHER = """
UNWIND $rows AS row
MATCH (atv:Atividade {source_id: row.source_id})
MATCH (usr:Usuario {nome: row.usuario})
MERGE (atv)-[:EXECUTADO_PELO_USUARIO]->(usr)
"""

LOAD_DOCUMENTO_EDGES_CYPHER = """
UNWIND $rows AS row
MATCH (atv:Atividade {source_id: row.source_id})
MERGE (doc:Documento {numero: row.numero})
ON CREATE SET doc.tipo = row.tipo, doc.serie_id = row.serie_id
MERGE (atv)-[:REFERENCIA_DOCUMENTO]->(doc)
WITH row, doc
MATCH (p:Processo {protocolo_formatado: row.protocolo_formatado})
MERGE (p)-[:CONTEM_DOCUMENTO]->(doc)
"""

LOAD_DOCUMENTO_CYPHER = """
UNWIND $rows AS row
MATCH (atv:Atividade {source_id: row.source_id})
MERGE (doc:Documento {numero: row.numero})
ON CREATE SET doc.tipo = row.tipo,
              doc.serie_id = row.serie_id
MERGE (atv)-[:REFERENCIA_DOCUMENTO]->(doc)
WITH atv, doc
MATCH (atv)-[:DO_PROCESSO]->(p:Processo)
MERGE (p)-[:CONTEM_DOCUMENTO]->(doc)
"""

CLEAR_TIMELINE_EDGES_CYPHER: tuple[tuple[str, str], ...] = (
    ("clear_seguida_por", """
UNWIND $protocolos AS pf
MATCH (:Processo {protocolo_formatado: pf})<-[:DO_PROCESSO]-(:Atividade)-[r:SEGUIDA_POR]->()
DELETE r
"""),
    ("clear_precedida_por", """
UNWIND $protocolos AS pf
MATCH (:Processo {protocolo_formatado: pf})<-[:DO_PROCESSO]-(:Atividade)-[r:PRECEDIDA_POR]->()
DELETE r
"""),
    ("clear_seguido_independente", """
UNWIND $protocolos AS pf
MATCH (:Processo {protocolo_formatado: pf})<-[:DO_PROCESSO]-(:Atividade)-[r:SEGUIDO_INDEPENDENTEMENTE_POR]->()
DELETE r
"""),
)

LOAD_TIMELINE_CYPHER = """
UNWIND $edges AS e
MATCH (a1:Atividade {source_id: e.from_id})
MATCH (a2:Atividade {source_id: e.to_id})
MERGE (a1)-[r:SEGUIDA_POR]->(a2)
SET r.mesma_unidade = e.mesma_unidade,
    r.intervalo_horas = e.intervalo_horas,
    r.intervalo_dias = e.intervalo_dias
MERGE (a2)-[r2:PRECEDIDA_POR]->(a1)
SET r2.mesma_unidade = e.mesma_unidade,
    r2.intervalo_horas = e.intervalo_horas,
    r2.intervalo_dias = e.intervalo_dias
"""

LOAD_PERMANENCIA_UNIDADE_CYPHER = """
UNWIND $rows AS r
MATCH (p:Processo {protocolo_formatado: r.protocolo_formatado})
MATCH (u:Unidade {sigla: r.unidade})
MERGE (p)-[rel:PASSOU_PELA_UNIDADE]->(u)
SET rel.duracao_total_horas = r.duracao_total_horas,
    rel.duracao_acumulada_horas = r.duracao_acumulada_horas,
    rel.duracao_lifetime_horas = r.duracao_lifetime_horas,
    rel.visitas = r.visitas,
    rel.primeira_entrada = datetime(r.primeira_entrada),
    rel.ultima_saida = datetime(r.ultima_saida)
"""

LOAD_PERMANENCIA_ORGAO_CYPHER = """
UNWIND $rows AS r
MATCH (p:Processo {protocolo_formatado: r.protocolo_formatado})
MATCH (o:Orgao {sigla: r.orgao})
MERGE (p)-[rel:PASSOU_PELO_ORGAO]->(o)
SET rel.duracao_total_horas = r.duracao_total_horas,
    rel.duracao_acumulada_horas = r.duracao_acumulada_horas,
    rel.duracao_lifetime_horas = r.duracao_lifetime_horas,
    rel.visitas = r.visitas,
    rel.primeira_entrada = datetime(r.primeira_entrada),
    rel.ultima_saida = datetime(r.ultima_saida)
"""



CLEAR_SITUACAO_FOR_PROTOCOLOS_CYPHER = """
UNWIND $protocolos AS pf
MATCH (p:Processo {protocolo_formatado: pf})
OPTIONAL MATCH (p)<-[:DO_PROCESSO]-(c:Ciclo)
OPTIONAL MATCH (p)-[r1:EM_ABERTO_NA_UNIDADE]->()
OPTIONAL MATCH (p)-[r2:EM_ABERTO_NO_ORGAO]->()
OPTIONAL MATCH (p)-[r3:ULTIMA_ATIVIDADE_EM_ABERTO]->()
OPTIONAL MATCH (p)-[r4:ATIVIDADE_MAIS_RECENTE]->()
DETACH DELETE c
DELETE r1, r2, r3, r4
"""

LOAD_SITUACAO_UNIDADE_CYPHER = """
UNWIND $rows AS r
MATCH (p:Processo {protocolo_formatado: r.protocolo_formatado})
MATCH (u:Unidade {sigla: r.unidade})
MERGE (p)-[rel:SITUACAO_PROCESSO_UNIDADE]->(u)
SET rel.situacao = r.situacao,
    rel.duracao_acumulada_horas = r.duracao_acumulada_horas,
    rel.duracao_lifetime_horas = r.duracao_lifetime_horas,
    rel.visitas = r.visitas,
    rel.primeira_entrada = datetime(r.primeira_entrada),
    rel.ultima_saida = CASE WHEN r.ultima_saida IS NULL THEN null ELSE datetime(r.ultima_saida) END,
    rel.ultima_atividade_id = r.ultima_atividade_id,
    rel.ultima_atividade_data_hora = CASE WHEN r.ultima_atividade_data_hora IS NULL THEN null ELSE datetime(r.ultima_atividade_data_hora) END,
    rel.ultima_atividade_tipo_acao = r.ultima_atividade_tipo_acao,
    rel.dias_sem_atividade = r.dias_sem_atividade
"""

LOAD_EM_ABERTO_UNIDADE_CYPHER = """
UNWIND $rows AS r
MATCH (p:Processo {protocolo_formatado: r.protocolo_formatado})
MATCH (u:Unidade {sigla: r.unidade})
MERGE (p)-[rel:EM_ABERTO_NA_UNIDADE]->(u)
SET rel.desde = datetime(r.desde),
    rel.dias_sem_atividade = r.dias_sem_atividade
"""

LOAD_SITUACAO_ORGAO_CYPHER = """
UNWIND $rows AS r
MATCH (p:Processo {protocolo_formatado: r.protocolo_formatado})
MATCH (o:Orgao {sigla: r.orgao})
MERGE (p)-[rel:SITUACAO_PROCESSO_ORGAO]->(o)
SET rel.situacao = r.situacao,
    rel.unidades_abertas_count = r.unidades_abertas_count,
    rel.duracao_acumulada_horas = r.duracao_acumulada_horas,
    rel.duracao_lifetime_horas = r.duracao_lifetime_horas,
    rel.dias_sem_atividade = r.dias_sem_atividade
"""

LOAD_EM_ABERTO_ORGAO_CYPHER = """
UNWIND $rows AS r
MATCH (p:Processo {protocolo_formatado: r.protocolo_formatado})
MATCH (o:Orgao {sigla: r.orgao})
MERGE (p)-[rel:EM_ABERTO_NO_ORGAO]->(o)
SET rel.desde = datetime(r.desde),
    rel.unidades_abertas_count = r.unidades_abertas_count
"""

LOAD_CICLOS_CYPHER = """
UNWIND $rows AS r
MATCH (p:Processo {protocolo_formatado: r.protocolo_formatado})
MATCH (u:Unidade {sigla: r.unidade})
MERGE (c:Ciclo {id: r.id})
SET c.ordem = r.ordem,
    c.entrada = datetime(r.entrada),
    c.saida = CASE WHEN r.saida IS NULL THEN null ELSE datetime(r.saida) END,
    c.duracao_horas = r.duracao_horas,
    c.status = r.status,
    c.implicit_close = r.implicit_close
MERGE (c)-[:DO_PROCESSO]->(p)
MERGE (c)-[:NA_UNIDADE]->(u)
WITH c, r
WHERE r.abertura_atividade_id IS NOT NULL
MATCH (a_open:Atividade {source_id: r.abertura_atividade_id})
MERGE (c)-[:ABERTO_POR]->(a_open)
"""

LOAD_CICLOS_FECHADO_POR_CYPHER = """
UNWIND $rows AS r
MATCH (c:Ciclo {id: r.id})
MATCH (a_close:Atividade {source_id: r.conclusao_atividade_id})
MERGE (c)-[:FECHADO_POR]->(a_close)
"""

LOAD_ULTIMA_ATIVIDADE_EM_ABERTO_CYPHER = """
UNWIND $rows AS r
MATCH (p:Processo {protocolo_formatado: r.protocolo_formatado})
MATCH (a:Atividade {source_id: r.atividade_id})
MERGE (p)-[:ULTIMA_ATIVIDADE_EM_ABERTO]->(a)
"""

LOAD_ATIVIDADE_MAIS_RECENTE_CYPHER = """
UNWIND $rows AS r
MATCH (p:Processo {protocolo_formatado: r.protocolo_formatado})
MATCH (a:Atividade {source_id: r.atividade_id})
MERGE (p)-[:ATIVIDADE_MAIS_RECENTE]->(a)
"""

LOAD_PROCESSO_SITUACAO_PROPS_CYPHER = """
UNWIND $rows AS r
MATCH (p:Processo {protocolo_formatado: r.protocolo_formatado})
SET p.situacao = r.situacao,
    p.unidades_em_aberto_count = r.unidades_em_aberto_count,
    p.unidades_em_aberto_siglas = r.unidades_em_aberto_siglas,
    p.data_inicio = CASE WHEN r.data_inicio IS NULL THEN null ELSE datetime(r.data_inicio) END,
    p.data_ultima_atividade = CASE WHEN r.data_ultima_atividade IS NULL THEN null ELSE datetime(r.data_ultima_atividade) END,
    p.data_conclusao_global = CASE WHEN r.data_conclusao_global IS NULL THEN null ELSE datetime(r.data_conclusao_global) END,
    p.duracao_lifetime_horas = r.duracao_lifetime_horas,
    p.duracao_lifetime_dias = r.duracao_lifetime_dias,
    p.situacao_computed_at = datetime(r.situacao_computed_at)
"""



CHECK_EMBEDDING_HASH_CYPHER = """
UNWIND $numeros AS n
MATCH (d:Documento {numero: n})
RETURN d.numero AS numero, d.embedding_hash AS hash, d.embedding_modelo AS modelo
"""

LOAD_DOCUMENTO_EMBEDDING_CYPHER = """
UNWIND $rows AS r
MATCH (d:Documento {numero: r.documento_numero})
SET d.embedding = r.embedding,
    d.embedding_modelo = r.modelo,
    d.embedding_hash = r.hash,
    d.embedding_dim = r.dim,
    d.embedding_computed_at = datetime(r.computed_at)
"""

LOAD_DOCUMENTO_EVALUATION_CYPHER = """
UNWIND $rows AS r
MATCH (d:Documento {numero: r.documento_numero})
SET d.topic = r.topic,
    d.summary = r.summary,
    d.evaluation_modelo = r.modelo,
    d.evaluation_status = r.status,
    d.evaluation_computed_at = datetime(r.computed_at)
"""

CLEAR_SIMILAR_DOC_FOR_BATCH_CYPHER = """
UNWIND $numeros AS n
MATCH (a:Documento {numero: n})-[r:SIMILAR_DOC]->()
DELETE r
"""

QUERY_VECTOR_NEIGHBORS_CYPHER = """
CALL db.index.vector.queryNodes('documento_embedding_idx', $k_plus_one, $query_embedding)
YIELD node, score
WHERE node.numero <> $exclude
RETURN node.numero AS numero, score
ORDER BY score DESC
LIMIT $k
"""

LIST_DOCS_PER_PROCESSO_CYPHER = """
MATCH (p:Processo)-[:CONTEM_DOCUMENTO]->(d:Documento)
WHERE d.embedding IS NOT NULL
WITH p, collect({numero: d.numero, embedding: d.embedding}) AS docs
WHERE size(docs) > 1
RETURN p.protocolo_formatado AS protocolo, docs
"""

LOAD_SIMILAR_DOC_CYPHER = """
UNWIND $rows AS r
MATCH (a:Documento {numero: r.from_doc})
MATCH (b:Documento {numero: r.to_doc})
MERGE (a)-[rel:SIMILAR_DOC]->(b)
SET rel.score = r.score,
    rel.tier = r.tier,
    rel.intra_processo = r.intra_processo,
    rel.modelo = r.modelo,
    rel.computed_at = datetime(r.computed_at)
"""



LIST_PROCESSOS_FOR_CLUSTERING_CYPHER = """
MATCH (p:Processo)
OPTIONAL MATCH (a:Atividade)-[:DO_PROCESSO]->(p)
WITH p, collect(a) AS atividades
// Unidade is an EDGE on the activity, not a node property — traverse
// EXECUTADO_PELA_UNIDADE and read u.sigla (the unit key). Reading a
// non-existent a2.unidade property here left the unigram/bigram blocks empty.
OPTIONAL MATCH (a2:Atividade)-[:DO_PROCESSO]->(p)
OPTIONAL MATCH (a2)-[:EXECUTADO_PELA_UNIDADE]->(u2:Unidade)
WITH p, atividades,
     [ev IN collect(DISTINCT {u: u2.sigla, ts: a2.data_hora})
        WHERE ev.u IS NOT NULL] AS unidade_events
OPTIONAL MATCH (p)<-[:DO_PROCESSO]-(a3:Atividade)-[:REFERENCIA_DOCUMENTO]->(d:Documento)
WHERE d.embedding IS NOT NULL
WITH p, atividades, unidade_events,
     collect(DISTINCT {numero: d.numero,
                       embedding: d.embedding,
                       embedding_hash: coalesce(d.embedding_hash, ''),
                       topic: coalesce(d.topic, ''),
                       summary: coalesce(d.summary, ''),
                       first_seen: a3.data_hora}) AS docs_unsorted
RETURN p.protocolo_formatado AS protocolo,
       p.cluster_features_hash AS cluster_features_hash,
       coalesce(p.situacao, '') AS situacao,
       docs_unsorted AS documentos_raw,
       [a IN atividades WHERE a.tipo_acao IS NOT NULL
          | {t: a.tipo_acao, ts: a.data_hora}] AS atividades_raw,
       [ev IN unidade_events | ev.u] AS unidades_visitadas,
       unidade_events AS unidade_events_raw
"""

LOAD_PROCESSO_CLUSTER_FEATURES_CYPHER = """
UNWIND $rows AS r
MATCH (p:Processo {protocolo_formatado: r.protocolo_formatado})
SET p.cluster_features = r.features,
    p.cluster_features_dim = r.dim,
    p.cluster_features_hash = r.hash,
    p.cluster_features_computed_at = datetime(r.computed_at)
"""

CLEAR_PROCESSO_CLUSTER_FEATURES_CYPHER = """
UNWIND $protocolos AS pf
MATCH (p:Processo {protocolo_formatado: pf})
REMOVE p.cluster_features,
       p.cluster_features_dim,
       p.cluster_features_hash,
       p.cluster_features_computed_at
"""

READ_ALL_CLUSTER_FEATURES_CYPHER = """
MATCH (p:Processo)
WHERE p.cluster_features IS NOT NULL
RETURN p.protocolo_formatado AS protocolo,
       p.cluster_features AS features
"""

READ_PROCESSO_TIPO_CYPHER = """
MATCH (p:Processo)
OPTIONAL MATCH (p)-[:TEM_TIPO]->(t:TipoProcedimento)
RETURN p.protocolo_formatado AS protocolo,
       t.nome AS tipo_procedimento
"""

LOAD_CLUSTERING_RUN_CYPHER = """
MERGE (r:ClusteringRun {run_id: $run_id})
SET r.algo = $algo,
    r.dbcv = $dbcv,
    r.silhouette = $silhouette,
    r.noise_ratio = $noise_ratio,
    r.n_macro = $n_macro,
    r.n_micro = $n_micro,
    r.n_processos = $n_processos,
    r.computed_at = datetime($computed_at)
"""

CLEAR_CATEGORIA_PROCESSO_CYPHER = """
MATCH (c:CategoriaProcesso)
DETACH DELETE c
"""

LOAD_CATEGORIA_PROCESSO_CYPHER = """
UNWIND $rows AS r
MERGE (c:CategoriaProcesso {id: r.id})
SET c.nome = r.nome,
    c.descricao = r.descricao,
    c.marcadores = r.marcadores,
    c.nivel = r.nivel,
    c.n_processos = r.n_processos,
    c.centroid = r.centroid,
    c.computed_at = datetime(r.computed_at)
"""

LOAD_SUBCATEGORIA_DE_CYPHER = """
UNWIND $rows AS r
MATCH (child:CategoriaProcesso {id: r.child_id})
MATCH (parent:CategoriaProcesso {id: r.parent_id})
MERGE (child)-[:SUBCATEGORIA_DE]->(parent)
"""

LOAD_CATEGORIZADO_COMO_CYPHER = """
UNWIND $rows AS r
MATCH (p:Processo {protocolo_formatado: r.protocolo_formatado})
MATCH (c:CategoriaProcesso {id: r.categoria_id})
MERGE (p)-[rel:CATEGORIZADO_COMO {nivel: r.nivel}]->(c)
SET rel.reclassificada = r.reclassificada,
    rel.confidence = r.confidence,
    rel.computed_at = datetime(r.computed_at)
"""

SAMPLE_PROCESSOS_FOR_NAMING_CYPHER = """
UNWIND $protocolos AS pf
MATCH (p:Processo {protocolo_formatado: pf})
OPTIONAL MATCH (p)-[:TEM_TIPO]->(tp:TipoProcedimento)
WITH p, tp
OPTIONAL MATCH (p)-[r_uni:PASSOU_PELA_UNIDADE]->(u:Unidade)
WITH p, tp, u, r_uni
ORDER BY r_uni.duracao_acumulada_horas DESC
WITH p, tp, collect(u.sigla)[..3] AS top_unidades

OPTIONAL MATCH (a:Atividade)-[:DO_PROCESSO]->(p)
WITH p, tp, top_unidades, a.tipo_acao AS tipo, count(*) AS cnt
ORDER BY cnt DESC
WITH p, tp, top_unidades, collect(tipo)[..3] AS top_tipos_acao

OPTIONAL MATCH (p)<-[:DO_PROCESSO]-(a_first:Atividade)-[:REFERENCIA_DOCUMENTO]->(d:Documento)
WHERE d.topic IS NOT NULL OR d.embedding IS NOT NULL
WITH p, tp, top_unidades, top_tipos_acao, d, a_first.data_hora AS data_hora
ORDER BY data_hora ASC
WITH p, tp, top_unidades, top_tipos_acao, head(collect(d)) AS first_doc

RETURN p.protocolo_formatado AS protocolo,
       coalesce(tp.nome, '') AS tipo_procedimento,
       coalesce(first_doc.topic, '') AS topic,
       coalesce(first_doc.summary, first_doc.assunto_gliner, '') AS summary,
       top_unidades,
       top_tipos_acao
"""



COHORT_BASELINE_BORN_ORGAO_CYPHER = """
MATCH (p:Processo)-[:CRIADO_NO_ORGAO]->(:Orgao {sigla: $orgao})
WHERE p.data_criacao >= datetime($from) AND p.data_criacao < datetime($to)
RETURN p.protocolo_formatado AS protocolo,
       toString(p.data_criacao) AS data_criacao,
       coalesce(p.unidades_em_aberto_count, -1) AS unidades_em_aberto_count
"""

COHORT_BASELINE_BORN_CREATION_UNIT_CYPHER = """
MATCH (p:Processo)-[:INICIOU_PROCESSO]->(:Atividade)-[:EXECUTADO_PELA_UNIDADE]->(u:Unidade)
WHERE split(u.sigla, '/')[0] = $orgao
  AND p.data_criacao >= datetime($from) AND p.data_criacao < datetime($to)
RETURN p.protocolo_formatado AS protocolo,
       toString(p.data_criacao) AS data_criacao,
       coalesce(p.unidades_em_aberto_count, -1) AS unidades_em_aberto_count
"""

COHORT_CLUSTER_MEMBERS_CYPHER = """
UNWIND $cluster_ids AS cid
MATCH (p:Processo)-[:CATEGORIZADO_COMO]->(c:CategoriaProcesso {id: cid})
RETURN DISTINCT p.protocolo_formatado AS protocolo
"""

COHORT_PROCESSO_INFO_CYPHER = """
UNWIND $protocolos AS pf
MATCH (p:Processo {protocolo_formatado: pf})
RETURN p.protocolo_formatado AS protocolo,
       toString(p.data_criacao) AS data_criacao,
       coalesce(p.unidades_em_aberto_count, -1) AS unidades_em_aberto_count
"""

CLEAR_COORTE_CYPHER = """
MATCH (c:Coorte {id: $cohort_id})
DETACH DELETE c
"""

LOAD_COORTE_CYPHER = """
MERGE (c:Coorte {id: $id})
SET c.label = $label,
    c.orgao_prefix = $orgao_prefix,
    c.from_date = $from_date,
    c.to_date = $to_date,
    c.cap = $cap,
    c.cap_order = $cap_order,
    c.only_concluded = $only_concluded,
    c.n_before_cap = $n_before_cap,
    c.n_after_cap = $n_after_cap,
    c.source_counts_json = $source_counts_json,
    c.computed_at = datetime($computed_at)
"""

LOAD_MEMBRO_DA_COORTE_CYPHER = """
UNWIND $rows AS r
MATCH (p:Processo {protocolo_formatado: r.protocolo})
MATCH (c:Coorte {id: $cohort_id})
MERGE (p)-[rel:MEMBRO_DA_COORTE]->(c)
SET rel.source = r.source,
    rel.confidence = r.confidence,
    rel.computed_at = datetime($computed_at)
"""



COHORT_DURATIONS_CYPHER = """
MATCH (p:Processo)-[:MEMBRO_DA_COORTE]->(:Coorte {id: $cohort_id})
RETURN p.protocolo_formatado AS protocolo,
       p.duracao_lifetime_horas AS duracao_lifetime_horas
"""

LOAD_LINK_SCORE_EDGE_CYPHER = """
UNWIND $rows AS r
MATCH (a:Atividade {source_id: r.from_id})-[rel:SEGUIDA_POR]->(b:Atividade {source_id: r.to_id})
SET rel.advancement_score = r.advancement_score,
    rel.speed_score = r.speed_score,
    rel.rework_flag = r.rework_flag,
    rel.idle_flag = r.idle_flag,
    rel.contrib_score = r.contrib_score,
    rel.contrib_cohort_id = $cohort_id,
    rel.contrib_computed_at = datetime($computed_at)
"""

LOAD_ATIVIDADE_SCORE_CYPHER = """
UNWIND $rows AS r
MATCH (a:Atividade {source_id: r.source_id})
SET a.node_advancement_score = r.node_advancement_score,
    a.node_speed_score = r.node_speed_score,
    a.node_contrib_score = r.node_contrib_score,
    a.contrib_cohort_id = $cohort_id
"""



COHORT_DOC_SIMILARITY_CYPHER = """
MATCH (co:Coorte {id: $cohort_id})<-[:MEMBRO_DA_COORTE]-(:Processo)-[:CONTEM_DOCUMENTO]->(d:Documento)
WITH DISTINCT d
OPTIONAL MATCH (d)-[s:SIMILAR_DOC]-(:Documento)
WITH d, collect(s) AS sims
RETURN d.numero AS numero,
       [x IN sims WHERE x.intra_processo = true | x.score] AS intra_scores,
       [x IN sims WHERE x.intra_processo = false | x.score] AS cross_scores
"""

LOAD_DOC_BAND_CYPHER = """
UNWIND $rows AS r
MATCH (d:Documento {numero: r.numero})
SET d.band_score = r.band_score
"""

COHORT_ATIVIDADE_DOC_BANDS_CYPHER = """
MATCH (co:Coorte {id: $cohort_id})<-[:MEMBRO_DA_COORTE]-(:Processo)
      <-[:DO_PROCESSO]-(a:Atividade)-[:REFERENCIA_DOCUMENTO]->(d:Documento)
WHERE d.band_score IS NOT NULL
WITH a, collect(d.band_score) AS bands
RETURN a.source_id AS source_id, bands
"""

LOAD_ATIVIDADE_BAND_CYPHER = """
UNWIND $rows AS r
MATCH (a:Atividade {source_id: r.source_id})
SET a.activity_band_score = r.activity_band_score
"""

COHORT_PROCESSO_DOC_BANDS_CYPHER = """
MATCH (co:Coorte {id: $cohort_id})<-[:MEMBRO_DA_COORTE]-(p:Processo)
OPTIONAL MATCH (p)<-[:DO_PROCESSO]-(a:Atividade)-[:REFERENCIA_DOCUMENTO]->(d:Documento)
WHERE d.band_score IS NOT NULL
WITH p, d, toString(min(a.data_hora)) AS first_seen
WITH p, collect({band: d.band_score, ts: first_seen}) AS docs
RETURN p.protocolo_formatado AS protocolo, docs
"""

LOAD_PROCESSO_BAND_CYPHER = """
UNWIND $rows AS r
MATCH (p:Processo {protocolo_formatado: r.protocolo})
SET p.processo_band_score = r.processo_band_score,
    p.band_imputed = r.band_imputed
"""



COHORT_ACTIVITIES_FOR_DFG_CYPHER = """
MATCH (co:Coorte {id: $cohort_id})<-[:MEMBRO_DA_COORTE]-(p:Processo)<-[:DO_PROCESSO]-(a:Atividade)
OPTIONAL MATCH (a)-[:EXECUTADO_PELA_UNIDADE]->(u:Unidade)
RETURN p.protocolo_formatado AS protocolo,
       a.tipo_acao AS tipo_acao,
       u.sigla AS unidade,
       coalesce(a.node_contrib_score, 0.0) AS node_contrib_score,
       coalesce(a.node_advancement_score, 0.0) AS node_advancement_score,
       coalesce(a.node_speed_score, 0.0) AS node_speed_score,
       a.activity_band_score AS activity_band_score
"""

COHORT_EDGES_FOR_DFG_CYPHER = """
MATCH (co:Coorte {id: $cohort_id})<-[:MEMBRO_DA_COORTE]-(p:Processo)
MATCH (a:Atividade)-[:DO_PROCESSO]->(p)
MATCH (a)-[r:SEGUIDA_POR]->(b:Atividade)-[:DO_PROCESSO]->(p)
WHERE r.contrib_cohort_id = $cohort_id
OPTIONAL MATCH (a)-[:EXECUTADO_PELA_UNIDADE]->(ua:Unidade)
OPTIONAL MATCH (b)-[:EXECUTADO_PELA_UNIDADE]->(ub:Unidade)
RETURN p.protocolo_formatado AS protocolo,
       a.tipo_acao AS from_tipo,
       b.tipo_acao AS to_tipo,
       ua.sigla AS from_unidade,
       ub.sigla AS to_unidade,
       coalesce(r.contrib_score, 0.0) AS contrib_score,
       coalesce(r.advancement_score, 0.0) AS advancement_score,
       coalesce(r.speed_score, 0.0) AS speed_score,
       r.intervalo_horas AS intervalo_horas
"""

CLEAR_DFG_CYPHER = """
MATCH (n:DfgNode {cohort_id: $cohort_id})
DETACH DELETE n
"""

LOAD_DFG_NODE_CYPHER = """
UNWIND $rows AS r
MERGE (n:DfgNode {id: r.id})
SET n.cohort_id = $cohort_id,
    n.state_key = r.state_key,
    n.tipo_acao = r.tipo_acao,
    n.grupo = r.grupo,
    n.unidade_lane = r.unidade_lane,
    n.frequency = r.frequency,
    n.n_processos = r.n_processos,
    n.is_activation = r.is_activation,
    n.is_conclusion = r.is_conclusion,
    n.features = r.features,
    n.feature_dim = r.feature_dim,
    n.mean_contrib = r.mean_contrib,
    n.mean_advancement = r.mean_advancement,
    n.mean_speed = r.mean_speed,
    n.mean_activity_band = r.mean_activity_band,
    n.computed_at = datetime($computed_at)
WITH n
MATCH (c:Coorte {id: $cohort_id})
MERGE (n)-[:NO_DFG_DA_COORTE]->(c)
"""

LOAD_DIRECTLY_FOLLOWS_CYPHER = """
UNWIND $rows AS r
MATCH (a:DfgNode {id: r.from_id})
MATCH (b:DfgNode {id: r.to_id})
MERGE (a)-[rel:DIRECTLY_FOLLOWS]->(b)
SET rel.cohort_id = $cohort_id,
    rel.frequency = r.frequency,
    rel.n_processos = r.n_processos,
    rel.mean_contrib_score = r.mean_contrib_score,
    rel.mean_advancement = r.mean_advancement,
    rel.mean_speed = r.mean_speed,
    rel.mean_intervalo_horas = r.mean_intervalo_horas
"""



READ_DFG_NODES_CYPHER = """
MATCH (n:DfgNode {cohort_id: $cohort_id})
RETURN n.state_key AS state_key,
       n.tipo_acao AS tipo_acao,
       n.grupo AS grupo,
       n.unidade_lane AS unidade_lane,
       n.frequency AS frequency,
       n.n_processos AS n_processos,
       n.is_activation AS is_activation,
       n.is_conclusion AS is_conclusion,
       n.features AS features,
       n.mean_contrib AS mean_contrib,
       n.mean_advancement AS mean_advancement,
       n.mean_speed AS mean_speed,
       n.mean_activity_band AS mean_activity_band,
       n.gcn_importance AS gcn_importance,
       n.in_ideal_graph AS in_ideal_graph
"""

READ_DFG_EDGES_CYPHER = """
MATCH (a:DfgNode {cohort_id: $cohort_id})-[r:DIRECTLY_FOLLOWS]->(b:DfgNode {cohort_id: $cohort_id})
RETURN a.state_key AS from_key,
       b.state_key AS to_key,
       r.frequency AS frequency,
       r.n_processos AS n_processos,
       r.mean_intervalo_horas AS mean_intervalo_horas,
       r.mean_contrib_score AS mean_contrib_score
"""

LOAD_GCN_NODE_IMPORTANCE_CYPHER = """
UNWIND $rows AS r
MATCH (n:DfgNode {id: r.id})
SET n.gcn_importance = r.gcn_importance,
    n.in_ideal_graph = r.in_ideal_graph,
    n.importance_method = $method
"""

LOAD_DIRECTLY_FOLLOWS_IDEAL_CYPHER = """
UNWIND $rows AS r
MATCH (a:DfgNode {id: r.from_id})-[rel:DIRECTLY_FOLLOWS]->(b:DfgNode {id: r.to_id})
SET rel.in_ideal_graph = r.in_ideal_graph,
    rel.gcn_edge_importance = r.gcn_edge_importance
"""

CLEAR_IDEAL_DIRECTLY_FOLLOWS_CYPHER = """
MATCH (:DfgNode {cohort_id: $cohort_id})-[r:IDEAL_DIRECTLY_FOLLOWS]->()
DELETE r
"""

LOAD_IDEAL_DIRECTLY_FOLLOWS_CYPHER = """
UNWIND $rows AS r
MATCH (a:DfgNode {id: r.from_id})
MATCH (b:DfgNode {id: r.to_id})
MERGE (a)-[rel:IDEAL_DIRECTLY_FOLLOWS]->(b)
SET rel.cohort_id = $cohort_id
"""


CLEAR_COMUM_CYPHER = """
MATCH (n:ComumNode {cohort_id: $cohort_id})
DETACH DELETE n
"""

LOAD_COMUM_NODE_CYPHER = """
UNWIND $rows AS r
MERGE (n:ComumNode {id: r.id})
SET n.cohort_id = $cohort_id,
    n.state_key = r.state_key,
    n.label = r.label,
    n.lane = r.lane,
    n.x = r.x,
    n.coverage = r.coverage,
    n.frequency = r.frequency,
    n.grupo = r.grupo,
    n.on_spine = r.on_spine,
    n.is_start = r.is_start,
    n.is_end = r.is_end,
    n.gcn_kept = r.gcn_kept,
    n.computed_at = datetime($computed_at)
WITH n
MATCH (c:Coorte {id: $cohort_id})
MERGE (n)-[:COMUM_DA_COORTE]->(c)
"""

LOAD_COMUM_EDGE_CYPHER = """
UNWIND $rows AS r
MATCH (a:ComumNode {id: r.from_id})
MATCH (b:ComumNode {id: r.to_id})
MERGE (a)-[rel:COMUM_FLUI_PARA]->(b)
SET rel.cohort_id = $cohort_id,
    rel.coverage = r.coverage,
    rel.frequency = r.frequency,
    rel.mean_interval_h = r.mean_interval_h,
    rel.kind = r.kind,
    rel.on_spine = r.on_spine,
    rel.back_edge = r.back_edge
"""
