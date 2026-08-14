
from __future__ import annotations


CHECK_EMBEDDING_HASH_CYPHER = """
UNWIND $numeros AS n
MATCH (d:Documento {numero: n})
RETURN d.numero AS numero, d.embedding_hash AS hash, d.embedding_modelo AS modelo
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
ORDER BY p.protocolo_formatado
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
ORDER BY p.protocolo_formatado
"""

READ_ALL_CLUSTER_FEATURES_CYPHER = """
MATCH (p:Processo)
WHERE p.cluster_features IS NOT NULL
RETURN p.protocolo_formatado AS protocolo,
       p.cluster_features AS features
ORDER BY p.protocolo_formatado
"""

READ_PROCESSO_TIPO_CYPHER = """
MATCH (p:Processo)
OPTIONAL MATCH (p)-[:TEM_TIPO]->(t:TipoProcedimento)
RETURN p.protocolo_formatado AS protocolo,
       t.nome AS tipo_procedimento
ORDER BY p.protocolo_formatado
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
ORDER BY n.id
"""

READ_DFG_EDGES_CYPHER = """
MATCH (a:DfgNode {cohort_id: $cohort_id})-[r:DIRECTLY_FOLLOWS]->(b:DfgNode {cohort_id: $cohort_id})
RETURN a.state_key AS from_key,
       b.state_key AS to_key,
       r.frequency AS frequency,
       r.n_processos AS n_processos,
       r.mean_intervalo_horas AS mean_intervalo_horas,
       r.mean_contrib_score AS mean_contrib_score
ORDER BY a.id, b.id
"""
