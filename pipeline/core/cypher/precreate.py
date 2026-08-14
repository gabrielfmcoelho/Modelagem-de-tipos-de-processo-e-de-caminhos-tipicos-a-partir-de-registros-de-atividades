
from __future__ import annotations


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
