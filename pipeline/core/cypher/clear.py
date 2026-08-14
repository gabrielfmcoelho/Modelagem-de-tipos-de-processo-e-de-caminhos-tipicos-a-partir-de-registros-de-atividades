
from __future__ import annotations


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

CLEAR_SIMILAR_DOC_FOR_BATCH_CYPHER = """
UNWIND $numeros AS n
MATCH (a:Documento {numero: n})-[r:SIMILAR_DOC]->()
DELETE r
"""

CLEAR_PROCESSO_CLUSTER_FEATURES_CYPHER = """
UNWIND $protocolos AS pf
MATCH (p:Processo {protocolo_formatado: pf})
REMOVE p.cluster_features,
       p.cluster_features_dim,
       p.cluster_features_hash,
       p.cluster_features_computed_at
"""

CLEAR_CATEGORIA_PROCESSO_CYPHER = """
MATCH (c:CategoriaProcesso)
DETACH DELETE c
"""

CLEAR_COORTE_CYPHER = """
MATCH (c:Coorte {id: $cohort_id})
DETACH DELETE c
"""

CLEAR_DFG_CYPHER = """
MATCH (n:DfgNode {cohort_id: $cohort_id})
DETACH DELETE n
"""

CLEAR_IDEAL_DIRECTLY_FOLLOWS_CYPHER = """
MATCH (:DfgNode {cohort_id: $cohort_id})-[r:IDEAL_DIRECTLY_FOLLOWS]->()
DELETE r
"""

CLEAR_COMUM_CYPHER = """
MATCH (n:ComumNode {cohort_id: $cohort_id})
DETACH DELETE n
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
