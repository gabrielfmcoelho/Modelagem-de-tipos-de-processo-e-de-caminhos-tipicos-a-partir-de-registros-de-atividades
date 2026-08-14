
from __future__ import annotations

SEI_ATIVIDADES_COLUMNS = frozenset({
    "id", "id_processo", "protocolo_formatado", "data_hora", "id_unidade",
    "unidade", "usuario", "tipo_procedimento", "descricao_replace",
    "id_serie", "data_carga",
})

FIND_PROCESSOS_SQL = """
    SELECT protocolo_formatado, id_processo, data_hora, unidade, usuario, tipo_procedimento
    FROM sei_atividades
    WHERE descricao_replace LIKE 'Processo %gerado%'
    {date_filter}
    {orgao_filter}
    {status_filter}
    ORDER BY data_hora
    {limit_clause}
"""

WINDOW_PROTOCOLOS_SUBQUERY = """
    SELECT protocolo_formatado FROM sei_atividades
    WHERE descricao_replace LIKE 'Processo %gerado%'
    {date_filter}
    {orgao_filter}
    {status_filter}
"""

FIND_DISTINCT_UNIDADES_SQL = """
    SELECT a.unidade AS unidade,
           MAX(u.id_unidade) AS id_unidade,
           MAX(u.descricao) AS descricao
    FROM sei_atividades a
    LEFT JOIN sei_unidades u ON u.unidade = a.unidade
    WHERE a.unidade IS NOT NULL
      AND a.protocolo_formatado IN ({window})
    GROUP BY a.unidade
"""

FIND_REMETIDO_DESCRICOES_SQL = """
    SELECT DISTINCT descricao_replace FROM sei_atividades
    WHERE descricao_replace LIKE 'Processo remetido%'
      AND protocolo_formatado IN ({window})
"""

FIND_USUARIOS_SQL = """
    SELECT usuario, unidade, COUNT(*) AS cnt FROM sei_atividades
    WHERE usuario IS NOT NULL
      AND protocolo_formatado IN ({window})
    GROUP BY usuario, unidade
    ORDER BY usuario, cnt DESC
"""

FETCH_ANDAMENTOS_SQL = """
    SELECT id, protocolo_formatado, data_hora,
           unidade, usuario, tipo_procedimento, descricao_replace
    FROM sei_atividades
    WHERE protocolo_formatado IN ({in_list})
    {date_filter}
    ORDER BY protocolo_formatado, data_hora
"""

COUNT_ATIVIDADES_FOR_IDS_SQL = """
    SELECT COUNT(*) FROM sei_atividades
    WHERE protocolo_formatado IN ({in_list})
    {date_filter}
"""
