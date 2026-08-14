
from __future__ import annotations


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

LOAD_PROCESSO_CLUSTER_FEATURES_CYPHER = """
UNWIND $rows AS r
MATCH (p:Processo {protocolo_formatado: r.protocolo_formatado})
SET p.cluster_features = r.features,
    p.cluster_features_dim = r.dim,
    p.cluster_features_hash = r.hash,
    p.cluster_features_computed_at = datetime(r.computed_at)
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

LOAD_DOC_BAND_CYPHER = """
UNWIND $rows AS r
MATCH (d:Documento {numero: r.numero})
SET d.band_score = r.band_score
"""

LOAD_ATIVIDADE_BAND_CYPHER = """
UNWIND $rows AS r
MATCH (a:Atividade {source_id: r.source_id})
SET a.activity_band_score = r.activity_band_score
"""

LOAD_PROCESSO_BAND_CYPHER = """
UNWIND $rows AS r
MATCH (p:Processo {protocolo_formatado: r.protocolo})
SET p.processo_band_score = r.processo_band_score,
    p.band_imputed = r.band_imputed
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

LOAD_IDEAL_DIRECTLY_FOLLOWS_CYPHER = """
UNWIND $rows AS r
MATCH (a:DfgNode {id: r.from_id})
MATCH (b:DfgNode {id: r.to_id})
MERGE (a)-[rel:IDEAL_DIRECTLY_FOLLOWS]->(b)
SET rel.cohort_id = $cohort_id
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
