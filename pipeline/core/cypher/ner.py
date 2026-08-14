from __future__ import annotations

NER_SETUP_CONSTRAINTS = [
    "CREATE CONSTRAINT pessoa_fisica_norm IF NOT EXISTS FOR (p:PessoaFisica) REQUIRE p.nome_normalizado IS UNIQUE",
    "CREATE CONSTRAINT pessoa_juridica_norm IF NOT EXISTS FOR (p:PessoaJuridica) REQUIRE p.nome_normalizado IS UNIQUE",
    "CREATE CONSTRAINT cargo_funcao_norm IF NOT EXISTS FOR (c:CargoFuncao) REQUIRE c.nome_normalizado IS UNIQUE",
    "CREATE CONSTRAINT legislacao_referencia IF NOT EXISTS FOR (l:Legislacao) REQUIRE l.referencia IS UNIQUE",
    "CREATE CONSTRAINT contrato_edital_ref IF NOT EXISTS FOR (c:ContratoEdital) REQUIRE c.referencia IS UNIQUE",
]

SET_DOC_PROPERTIES = """
MATCH (d:Documento {numero: $doc_numero})
SET d.tipo_documento_gliner = $tipo_documento,
    d.assunto_gliner = $assunto,
    d.emails_mencionados = $emails,
    d.cpfs_mencionados = $cpfs,
    d.cnpjs_mencionados = $cnpjs,
    d.matriculas_mencionadas = $matriculas,
    d.telefones_mencionados = $telefones,
    d.urls_mencionadas = $urls,
    d.valores_monetarios = $valores,
    d.datas_mencionadas = $datas,
    d.enderecos_mencionados = $enderecos,
    d.objeto_licitacao_gliner = $objeto_licitacao,
    d.vigencia_gliner = $vigencia,
    d.gliner_model = $model,
    d.gliner_extracted_at = $extracted_at
RETURN d.numero AS numero
"""

LINK_PESSOA = """
MATCH (d:Documento {numero: $doc_numero})
UNWIND $items AS item
MERGE (p:PessoaFisica {nome_normalizado: item.norm})
ON CREATE SET p.nome = item.nome
ON MATCH SET p.nome = CASE WHEN size(item.nome) > size(p.nome) THEN item.nome ELSE p.nome END
MERGE (d)-[r:MENCIONA_PESSOA]->(p)
SET r.fonte = coalesce(item.provenance, 'gliner')
"""

LINK_EMPRESA = """
MATCH (d:Documento {numero: $doc_numero})
UNWIND $items AS item
MERGE (e:PessoaJuridica {nome_normalizado: item.norm})
ON CREATE SET e.nome = item.nome
ON MATCH SET e.nome = CASE WHEN size(item.nome) > size(e.nome) THEN item.nome ELSE e.nome END
MERGE (d)-[r:MENCIONA_EMPRESA]->(e)
SET r.fonte = coalesce(item.provenance, 'gliner')
"""

LINK_ORGAO = """
MATCH (d:Documento {numero: $doc_numero})
UNWIND $items AS item
MERGE (o:Orgao {sigla: item.nome})
MERGE (d)-[r:MENCIONA_ORGAO]->(o)
SET r.fonte = coalesce(item.provenance, 'gliner')
"""

LINK_CARGO = """
MATCH (d:Documento {numero: $doc_numero})
UNWIND $items AS item
MERGE (c:CargoFuncao {nome_normalizado: item.norm})
ON CREATE SET c.nome = item.nome
ON MATCH SET c.nome = CASE WHEN size(item.nome) > size(c.nome) THEN item.nome ELSE c.nome END
MERGE (d)-[r:MENCIONA_CARGO]->(c)
SET r.fonte = coalesce(item.provenance, 'gliner')
"""

LINK_LEGISLACAO = """
MATCH (d:Documento {numero: $doc_numero})
UNWIND $items AS item
MERGE (l:Legislacao {referencia: item.ref})
ON CREATE SET l.tipo = item.tipo
MERGE (d)-[r:MENCIONA_LEGISLACAO]->(l)
SET r.fonte = coalesce(item.provenance, 'gliner')
"""

LINK_CONTRATO = """
MATCH (d:Documento {numero: $doc_numero})
UNWIND $items AS item
MERGE (c:ContratoEdital {referencia: item.ref})
MERGE (d)-[r:MENCIONA_CONTRATO]->(c)
SET r.fonte = coalesce(item.provenance, 'gliner')
"""

LINK_CLASSE = """
MATCH (d:Documento {numero: $doc_numero})
UNWIND $items AS item
MERGE (c:ClasseNivel {referencia: item.ref})
MERGE (d)-[r:MENCIONA_CLASSE]->(c)
SET r.fonte = coalesce(item.provenance, 'gliner')
"""

LINK_PESSOA_REL = """
MATCH (d:Documento {numero: $doc_numero})
UNWIND $pairs AS pair
MERGE (p:PessoaFisica {nome: pair.head})
MERGE (p)-[r:{rel_type}]->(d)
SET r.objeto = pair.tail
"""

LINK_ENTITY_REL = """
MATCH (d:Documento {numero: $doc_numero})
UNWIND $pairs AS pair
MERGE (d)-[r:{rel_type}]->(:PessoaFisica {{nome: pair.tail}})
SET r.agente = pair.head
"""

CLEAR_GLINER = [
    "MATCH ()-[r:MENCIONA_PESSOA]->() DELETE r",
    "MATCH ()-[r:MENCIONA_EMPRESA]->() DELETE r",
    "MATCH ()-[r:MENCIONA_ORGAO]->() WHERE NOT EXISTS { MATCH ()-[:PERTENCE_AO_ORGAO]->() } DELETE r",
    "MATCH ()-[r:MENCIONA_CARGO]->() DELETE r",
    "MATCH ()-[r:MENCIONA_LEGISLACAO]->() DELETE r",
    "MATCH ()-[r:MENCIONA_CONTRATO]->() DELETE r",
    "MATCH ()-[r:ASSINOU]->() DELETE r",
    "MATCH ()-[r:AUTORIZOU]->() DELETE r",
    "MATCH ()-[r:SOLICITOU]->() DELETE r",
    "MATCH ()-[r:CONTRATOU]->() DELETE r",
    "MATCH ()-[r:NOMEOU]->() DELETE r",
    "MATCH ()-[r:DESIGNOU]->() DELETE r",
    "MATCH ()-[r:EXONEROU]->() DELETE r",
    "MATCH ()-[r:ENCAMINHOU_PARA_DOC]->() DELETE r",
    "MATCH (p:PessoaFisica) WHERE NOT (p)--() DELETE p",
    "MATCH (p:PessoaJuridica) WHERE NOT (p)--() DELETE p",
    "MATCH (c:CargoFuncao) WHERE NOT (c)--() DELETE c",
    "MATCH (l:Legislacao) WHERE NOT (l)--() DELETE l",
    "MATCH (c:ContratoEdital) WHERE NOT (c)--() DELETE c",
    """MATCH (d:Documento) WHERE d.gliner_model IS NOT NULL
       REMOVE d.tipo_documento_gliner, d.assunto_gliner,
              d.emails_mencionados, d.cpfs_mencionados, d.cnpjs_mencionados,
              d.matriculas_mencionadas, d.telefones_mencionados, d.urls_mencionadas,
              d.valores_monetarios, d.datas_mencionadas, d.enderecos_mencionados,
              d.objeto_licitacao_gliner, d.vigencia_gliner,
              d.gliner_model, d.gliner_extracted_at""",
]
