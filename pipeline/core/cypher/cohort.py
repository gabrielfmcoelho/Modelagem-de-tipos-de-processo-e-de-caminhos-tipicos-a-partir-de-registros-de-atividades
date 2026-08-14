
from __future__ import annotations


COHORT_BASELINE_BORN_ORGAO_CYPHER = """
MATCH (p:Processo)-[:CRIADO_NO_ORGAO]->(:Orgao {sigla: $orgao})
WHERE p.data_criacao >= datetime($from) AND p.data_criacao < datetime($to)
RETURN p.protocolo_formatado AS protocolo,
       toString(p.data_criacao) AS data_criacao,
       coalesce(p.unidades_em_aberto_count, -1) AS unidades_em_aberto_count
ORDER BY protocolo
"""

COHORT_BASELINE_BORN_CREATION_UNIT_CYPHER = """
MATCH (p:Processo)-[:INICIOU_PROCESSO]->(:Atividade)-[:EXECUTADO_PELA_UNIDADE]->(u:Unidade)
WHERE split(u.sigla, '/')[0] = $orgao
  AND p.data_criacao >= datetime($from) AND p.data_criacao < datetime($to)
RETURN p.protocolo_formatado AS protocolo,
       toString(p.data_criacao) AS data_criacao,
       coalesce(p.unidades_em_aberto_count, -1) AS unidades_em_aberto_count
ORDER BY protocolo
"""

COHORT_CLUSTER_MEMBERS_CYPHER = """
UNWIND $cluster_ids AS cid
MATCH (p:Processo)-[:CATEGORIZADO_COMO]->(c:CategoriaProcesso {id: cid})
RETURN DISTINCT p.protocolo_formatado AS protocolo
ORDER BY protocolo
"""

COHORT_PROCESSO_INFO_CYPHER = """
UNWIND $protocolos AS pf
MATCH (p:Processo {protocolo_formatado: pf})
RETURN p.protocolo_formatado AS protocolo,
       toString(p.data_criacao) AS data_criacao,
       coalesce(p.unidades_em_aberto_count, -1) AS unidades_em_aberto_count
ORDER BY protocolo
"""

COHORT_DURATIONS_CYPHER = """
MATCH (p:Processo)-[:MEMBRO_DA_COORTE]->(:Coorte {id: $cohort_id})
RETURN p.protocolo_formatado AS protocolo,
       p.duracao_lifetime_horas AS duracao_lifetime_horas
ORDER BY protocolo
"""

COHORT_DOC_SIMILARITY_CYPHER = """
MATCH (co:Coorte {id: $cohort_id})<-[:MEMBRO_DA_COORTE]-(:Processo)-[:CONTEM_DOCUMENTO]->(d:Documento)
WITH DISTINCT d
OPTIONAL MATCH (d)-[s:SIMILAR_DOC]-(:Documento)
WITH d, collect(s) AS sims
RETURN d.numero AS numero,
       [x IN sims WHERE x.intra_processo = true | x.score] AS intra_scores,
       [x IN sims WHERE x.intra_processo = false | x.score] AS cross_scores
ORDER BY numero
"""

COHORT_ATIVIDADE_DOC_BANDS_CYPHER = """
MATCH (co:Coorte {id: $cohort_id})<-[:MEMBRO_DA_COORTE]-(:Processo)
      <-[:DO_PROCESSO]-(a:Atividade)-[:REFERENCIA_DOCUMENTO]->(d:Documento)
WHERE d.band_score IS NOT NULL
WITH a, collect(d.band_score) AS bands
RETURN a.source_id AS source_id, bands
ORDER BY source_id
"""

COHORT_PROCESSO_DOC_BANDS_CYPHER = """
MATCH (co:Coorte {id: $cohort_id})<-[:MEMBRO_DA_COORTE]-(p:Processo)
OPTIONAL MATCH (p)<-[:DO_PROCESSO]-(a:Atividade)-[:REFERENCIA_DOCUMENTO]->(d:Documento)
WHERE d.band_score IS NOT NULL
WITH p, d, toString(min(a.data_hora)) AS first_seen
WITH p, collect({band: d.band_score, ts: first_seen}) AS docs
RETURN p.protocolo_formatado AS protocolo, docs
ORDER BY protocolo
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
       a.activity_band_score AS activity_band_score,
       a.source_id AS source_id
ORDER BY protocolo, a.data_hora, a.source_id
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
ORDER BY protocolo, from_tipo, to_tipo
"""
