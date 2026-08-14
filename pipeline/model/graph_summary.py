
import argparse
import sys
from datetime import datetime
from pathlib import Path as _Path

_HERE = _Path(__file__).resolve()
_ROOT = next((p.parent for p in _HERE.parents if p.name == "pipeline"), _HERE.parents[2])
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from pipeline.cli import add_standard_args, resolve_settings
from ..core.config import ConfigError
from ..core.logging_setup import configure_logging
from ..core.neo4j_driver import build_driver
from ..core.deployment import ORGAO_SIGLA

log = configure_logging(__name__)


def _sec(title):
    log.info("%s", "─" * 70)
    log.info("  %s", title)
    log.info("%s", "─" * 70)


def _bar(value, max_val, width=30):
    if max_val == 0:
        return ""
    filled = int(value / max_val * width)
    return "█" * filled + "░" * (width - filled)


def _fmt_hours(h):
    if h is None:
        return "—"
    if h < 24:
        return f"{h:.1f}h"
    days = h / 24
    if days < 365:
        return f"{days:.1f}d"
    return f"{days / 365:.1f}a"


def _fmt_date(d):
    if d is None:
        return "—"
    if isinstance(d, str):
        return d[:19]
    if isinstance(d, datetime):
        return d.strftime("%Y-%m-%d %H:%M")
    return str(d)[:19]


def _pct(part, total):
    if total == 0:
        return "—"
    return f"{part / total * 100:.1f}%"


def _orgao_match(alias="p", orgao=None):
    if orgao:
        return f"MATCH ({alias}:Processo)-[:CRIADO_NO_ORGAO]->(o:Orgao {{sigla: $orgao}})"
    return f"MATCH ({alias}:Processo)"


def run_summary(driver, orgao: str | None, top: int):
    with driver.session() as s:
        params = {"orgao": orgao} if orgao else {}
        scope = f" (orgão: {orgao})" if orgao else " (todos)"

        _sec(f"VISÃO GERAL{scope}")

        q = f"""
        {_orgao_match('p', orgao)}
        WITH count(p) AS processos
        MATCH (a:Atividade) WITH processos, count(a) AS atividades_total
        MATCH (d:Documento) WITH processos, atividades_total, count(d) AS docs_total
        MATCH (u:Unidade) WITH processos, atividades_total, docs_total, count(u) AS unidades
        MATCH (o:Orgao) WITH processos, atividades_total, docs_total, unidades, count(o) AS orgaos
        MATCH (usr:Usuario) WITH processos, atividades_total, docs_total, unidades, orgaos, count(usr) AS usuarios
        RETURN processos, atividades_total, docs_total, unidades, orgaos, usuarios
        """
        r = s.run(q, **params).single()
        n_processos = r["processos"]
        log.info("%s", f"  Processos:    {r['processos']:,}")
        log.info("%s", f"  Atividades:   {r['atividades_total']:,}")
        log.info("%s", f"  Documentos:   {r['docs_total']:,}")
        log.info("%s", f"  Unidades:     {r['unidades']:,}")
        log.info("%s", f"  Órgãos:       {r['orgaos']:,}")
        log.info("%s", f"  Usuários:     {r['usuarios']:,}")

        if n_processos == 0:
            log.info("  Nenhum processo encontrado.")
            return

        _sec("DATAS DE CRIAÇÃO DOS PROCESSOS")

        q = f"""
        {_orgao_match('p', orgao)}
        WHERE p.data_criacao IS NOT NULL
        RETURN min(p.data_criacao) AS primeiro,
               max(p.data_criacao) AS ultimo,
               count(p) AS total
        """
        r = s.run(q, **params).single()
        log.info("%s", f"  Primeiro processo:  {_fmt_date(r['primeiro'])}")
        log.info("%s", f"  Último processo:    {_fmt_date(r['ultimo'])}")
        log.info("%s", f"  Com data:           {r['total']:,} / {n_processos:,}")

        q = f"""
        {_orgao_match('p', orgao)}
        WHERE p.data_criacao IS NOT NULL
        WITH p, substring(toString(p.data_criacao), 0, 7) AS mes
        RETURN mes, count(p) AS total
        ORDER BY mes
        """
        records = list(s.run(q, **params))
        if records:
            max_count = max(r["total"] for r in records)
            log.info("  Processos por mês:")
            for r in records:
                log.info("%s", f"    {r['mes']}  {r['total']:>6,}  {_bar(r['total'], max_count, 25)}")

        _sec("ÚLTIMO ANDAMENTO POR PROCESSO")

        q = f"""
        {_orgao_match('p', orgao)}
        MATCH (a:Atividade)-[:DO_PROCESSO]->(p)
        WITH p, max(a.data_hora) AS ultimo_andamento
        RETURN min(ultimo_andamento) AS mais_antigo,
               max(ultimo_andamento) AS mais_recente,
               count(p) AS total
        """
        r = s.run(q, **params).single()
        log.info("%s", f"  Último andamento mais antigo:   {_fmt_date(r['mais_antigo'])}")
        log.info("%s", f"  Último andamento mais recente:  {_fmt_date(r['mais_recente'])}")

        q = f"""
        {_orgao_match('p', orgao)}
        MATCH (a:Atividade)-[:DO_PROCESSO]->(p)
        WITH p, max(a.data_hora) AS ultimo
        WITH p, duration.between(ultimo, datetime()).days AS dias_parado
        RETURN
            count(CASE WHEN dias_parado <= 7 THEN 1 END) AS ate_7d,
            count(CASE WHEN dias_parado > 7 AND dias_parado <= 30 THEN 1 END) AS ate_30d,
            count(CASE WHEN dias_parado > 30 AND dias_parado <= 90 THEN 1 END) AS ate_90d,
            count(CASE WHEN dias_parado > 90 AND dias_parado <= 180 THEN 1 END) AS ate_180d,
            count(CASE WHEN dias_parado > 180 AND dias_parado <= 365 THEN 1 END) AS ate_1a,
            count(CASE WHEN dias_parado > 365 THEN 1 END) AS mais_1a
        """
        r = s.run(q, **params).single()
        buckets = [
            ("≤ 7 dias",     r["ate_7d"]),
            ("8–30 dias",    r["ate_30d"]),
            ("31–90 dias",   r["ate_90d"]),
            ("91–180 dias",  r["ate_180d"]),
            ("181–365 dias", r["ate_1a"]),
            ("> 1 ano",      r["mais_1a"]),
        ]
        max_b = max(v for _, v in buckets) if buckets else 1
        log.info("  Idade do último andamento:")
        for label, val in buckets:
            log.info("%s", f"    {label:<15} {val:>6,}  {_bar(val, max_b, 25)}")

        _sec(f"TIPOS DE PROCEDIMENTO (TOP {top})")

        q = f"""
        {_orgao_match('p', orgao)}
        MATCH (p)-[:TEM_TIPO]->(tp:TipoProcedimento)
        RETURN tp.nome AS tipo, count(p) AS total
        ORDER BY total DESC LIMIT $top
        """
        records = list(s.run(q, top=top, **params))
        if records:
            max_count = records[0]["total"]
            for r in records:
                log.info("%s", f"    {r['total']:>6,}  {_bar(r['total'], max_count, 20)}  {r['tipo']}")

        _sec(f"ÓRGÃOS QUE MAIS CRIARAM PROCESSOS (TOP {top})")

        q = f"""
        {_orgao_match('p', orgao)}
        MATCH (p)-[:CRIADO_NO_ORGAO]->(o2:Orgao)
        RETURN o2.sigla AS orgao_sigla, count(p) AS total
        ORDER BY total DESC LIMIT $top
        """
        records = list(s.run(q, top=top, **params))
        if records:
            max_count = records[0]["total"]
            for r in records:
                log.info("%s", f"    {r['total']:>6,}  {_bar(r['total'], max_count, 20)}  {r['orgao_sigla']}")

        _sec(f"UNIDADES MAIS VISITADAS (TOP {top})")

        q = f"""
        {_orgao_match('p', orgao)}
        MATCH (p)-[r:PASSOU_PELA_UNIDADE]->(u:Unidade)
        RETURN u.sigla AS unidade,
               count(p) AS processos,
               sum(r.visitas) AS total_visitas,
               avg(r.duracao_total_horas) AS avg_permanencia_h
        ORDER BY processos DESC LIMIT $top
        """
        records = list(s.run(q, top=top, **params))
        if records:
            max_count = records[0]["processos"]
            log.info("%s", f"    {'Processos':>10} {'Visitas':>10} {'Perm. média':>12}  Unidade")
            log.info("%s", f"    {'─' * 10} {'─' * 10} {'─' * 12}  {'─' * 35}")
            for r in records:
                log.info("%s", f"    {r['processos']:>10,} {r['total_visitas']:>10,} {_fmt_hours(r['avg_permanencia_h']):>12}  {r['unidade']}")

        _sec(f"UNIDADES QUE MAIS EXECUTARAM AÇÕES (TOP {top})")

        q = f"""
        {_orgao_match('p', orgao)}
        MATCH (a:Atividade)-[:DO_PROCESSO]->(p)
        MATCH (a)-[:EXECUTADO_PELA_UNIDADE]->(u:Unidade)
        RETURN u.sigla AS unidade, count(a) AS acoes
        ORDER BY acoes DESC LIMIT $top
        """
        records = list(s.run(q, top=top, **params))
        if records:
            max_count = records[0]["acoes"]
            for r in records:
                log.info("%s", f"    {r['acoes']:>8,}  {_bar(r['acoes'], max_count, 20)}  {r['unidade']}")

        _sec(f"USUÁRIOS MAIS ATIVOS (TOP {top})")

        q = f"""
        {_orgao_match('p', orgao)}
        MATCH (a:Atividade)-[:DO_PROCESSO]->(p)
        MATCH (a)-[:EXECUTADO_PELO_USUARIO]->(usr:Usuario)
        RETURN usr.nome AS usuario, count(a) AS acoes
        ORDER BY acoes DESC LIMIT $top
        """
        records = list(s.run(q, top=top, **params))
        if records:
            max_count = records[0]["acoes"]
            for r in records:
                log.info("%s", f"    {r['acoes']:>8,}  {_bar(r['acoes'], max_count, 20)}  {r['usuario']}")

        _sec(f"TIPOS DE AÇÃO MAIS FREQUENTES (TOP {top})")

        q = f"""
        {_orgao_match('p', orgao)}
        MATCH (a:Atividade)-[:DO_PROCESSO]->(p)
        MATCH (a)-[:TIPO_ACAO]->(ta:TipoAcao)
        RETURN ta.chave AS tipo_acao, count(a) AS total
        ORDER BY total DESC LIMIT $top
        """
        records = list(s.run(q, top=top, **params))
        if records:
            max_count = records[0]["total"]
            for r in records:
                log.info("%s", f"    {r['total']:>8,}  {_bar(r['total'], max_count, 20)}  {r['tipo_acao']}")

        _sec("GRUPOS DE ATIVIDADE")

        q = f"""
        {_orgao_match('p', orgao)}
        MATCH (a:Atividade)-[:DO_PROCESSO]->(p)
        MATCH (a)-[:TIPO_ACAO]->(ta:TipoAcao)-[:PERTENCE_AO_GRUPO]->(ga:GrupoAtividade)
        RETURN ga.label AS grupo, ga.chave AS chave, count(a) AS total
        ORDER BY total DESC
        """
        records = list(s.run(q, **params))
        if records:
            max_count = records[0]["total"]
            for r in records:
                log.info("%s", f"    {r['total']:>8,}  {_bar(r['total'], max_count, 20)}  {r['grupo'] or r['chave']}")

        _sec("DISTRIBUIÇÃO DE ANDAMENTOS POR PROCESSO")

        q = f"""
        {_orgao_match('p', orgao)}
        MATCH (a:Atividade)-[:DO_PROCESSO]->(p)
        WITH p, count(a) AS n
        RETURN min(n) AS minimo,
               max(n) AS maximo,
               avg(n) AS media,
               percentileCont(n, 0.5) AS mediana,
               percentileCont(n, 0.9) AS p90,
               percentileCont(n, 0.99) AS p99
        """
        r = s.run(q, **params).single()
        log.info("%s", f"  Mínimo:   {r['minimo']}")
        log.info("%s", f"  Máximo:   {r['maximo']}")
        log.info("%s", f"  Média:    {r['media']:.1f}")
        log.info("%s", f"  Mediana:  {r['mediana']:.0f}")
        log.info("%s", f"  P90:      {r['p90']:.0f}")
        log.info("%s", f"  P99:      {r['p99']:.0f}")

        _sec("DISTRIBUIÇÃO DE DOCUMENTOS POR PROCESSO")

        q = f"""
        {_orgao_match('p', orgao)}
        MATCH (p)-[:CONTEM_DOCUMENTO]->(d:Documento)
        WITH p, count(d) AS n
        RETURN min(n) AS minimo,
               max(n) AS maximo,
               avg(n) AS media,
               percentileCont(n, 0.5) AS mediana,
               percentileCont(n, 0.9) AS p90,
               percentileCont(n, 0.99) AS p99
        """
        r = s.run(q, **params).single()
        log.info("%s", f"  Mínimo:   {r['minimo']}")
        log.info("%s", f"  Máximo:   {r['maximo']}")
        log.info("%s", f"  Média:    {r['media']:.1f}")
        log.info("%s", f"  Mediana:  {r['mediana']:.0f}")
        log.info("%s", f"  P90:      {r['p90']:.0f}")
        log.info("%s", f"  P99:      {r['p99']:.0f}")

        _sec("DISTRIBUIÇÃO DE UNIDADES VISITADAS POR PROCESSO")

        q = f"""
        {_orgao_match('p', orgao)}
        MATCH (p)-[:PASSOU_PELA_UNIDADE]->(u:Unidade)
        WITH p, count(u) AS n
        RETURN min(n) AS minimo,
               max(n) AS maximo,
               avg(n) AS media,
               percentileCont(n, 0.5) AS mediana,
               percentileCont(n, 0.9) AS p90
        """
        r = s.run(q, **params).single()
        log.info("%s", f"  Mínimo:   {r['minimo']}")
        log.info("%s", f"  Máximo:   {r['maximo']}")
        log.info("%s", f"  Média:    {r['media']:.1f}")
        log.info("%s", f"  Mediana:  {r['mediana']:.0f}")
        log.info("%s", f"  P90:      {r['p90']:.0f}")

        _sec(f"PROCESSOS COM MAIOR PERMANÊNCIA TOTAL (TOP {top})")

        q = f"""
        {_orgao_match('p', orgao)}
        MATCH (p)-[r:PASSOU_PELA_UNIDADE]->(u:Unidade)
        WITH p, sum(r.duracao_total_horas) AS total_horas
        RETURN p.protocolo_formatado AS protocolo, total_horas
        ORDER BY total_horas DESC LIMIT $top
        """
        records = list(s.run(q, top=top, **params))
        if records:
            max_h = records[0]["total_horas"] if records[0]["total_horas"] else 1
            for r in records:
                log.info("%s", f"    {_fmt_hours(r['total_horas']):>10}  {_bar(r['total_horas'] or 0, max_h, 20)}  {r['protocolo']}")

        _sec(f"PROCESSOS PARADOS HÁ MAIS TEMPO (TOP {top})")

        q = f"""
        {_orgao_match('p', orgao)}
        MATCH (a:Atividade)-[:DO_PROCESSO]->(p)
        WITH p, max(a.data_hora) AS ultimo
        RETURN p.protocolo_formatado AS protocolo,
               ultimo AS ultimo_andamento,
               duration.between(ultimo, datetime()).days AS dias_parado
        ORDER BY ultimo ASC LIMIT $top
        """
        records = list(s.run(q, top=top, **params))
        if records:
            log.info("%s", f"    {'Dias':>8}  {'Último andamento':<20}  Protocolo")
            log.info("%s", f"    {'─' * 8}  {'─' * 20}  {'─' * 30}")
            for r in records:
                log.info("%s", f"    {r['dias_parado']:>8,}  {_fmt_date(r['ultimo_andamento']):<20}  {r['protocolo']}")

        _sec(f"ÓRGÃOS COM MAIOR PERMANÊNCIA MÉDIA (TOP {top})")

        q = f"""
        {_orgao_match('p', orgao)}
        MATCH (p)-[r:PASSOU_PELO_ORGAO]->(org:Orgao)
        RETURN org.sigla AS orgao_sigla,
               count(p) AS processos,
               avg(r.duracao_total_horas) AS avg_h,
               max(r.duracao_total_horas) AS max_h
        ORDER BY avg_h DESC LIMIT $top
        """
        records = list(s.run(q, top=top, **params))
        if records:
            log.info("%s", f"    {'Processos':>10} {'Perm. média':>12} {'Perm. máx':>12}  Órgão")
            log.info("%s", f"    {'─' * 10} {'─' * 12} {'─' * 12}  {'─' * 25}")
            for r in records:
                log.info("%s", f"    {r['processos']:>10,} {_fmt_hours(r['avg_h']):>12} {_fmt_hours(r['max_h']):>12}  {r['orgao_sigla']}")

        _sec(f"FLUXOS DE TRAMITAÇÃO MAIS COMUNS (TOP {top})")

        q = f"""
        {_orgao_match('p', orgao)}
        MATCH (a:Atividade)-[:DO_PROCESSO]->(p)
        WHERE a.tipo_acao = 'PROCESSO-REMETIDO-UNIDADE'
        MATCH (a)-[:REMETIDO_PELA_UNIDADE]->(origem:Unidade)
        MATCH (a)-[:EXECUTADO_PELA_UNIDADE]->(destino:Unidade)
        WHERE origem <> destino
        RETURN origem.sigla AS de, destino.sigla AS para, count(*) AS total
        ORDER BY total DESC LIMIT $top
        """
        records = list(s.run(q, top=top, **params))
        if records:
            max_count = records[0]["total"]
            for r in records:
                log.info("%s", f"    {r['total']:>6,}  {_bar(r['total'], max_count, 15)}  {r['de']}  →  {r['para']}")

        log.info("%s", "=" * 70)


def run_summary_json(emit_dir: _Path, top: int) -> None:
    import json
    from collections import Counter

    if not emit_dir.is_dir():
        log.error("Emit directory not found: %s", emit_dir)
        sys.exit(1)

    log.info("%s", "=" * 70)
    log.info("%s", f"  RESUMO (JSON snapshot — {emit_dir})")
    log.info("%s", "=" * 70)

    nodes_dir = emit_dir / "nodes"
    edges_dir = emit_dir / "edges"
    templates_dir = emit_dir / "templates"

    _sec("1. Counts por label (nodes)")
    if nodes_dir.is_dir():
        node_counts: dict[str, int] = {}
        for f in sorted(nodes_dir.glob("*.ndjson")):
            with f.open("r", encoding="utf-8") as fh:
                node_counts[f.stem] = sum(1 for _ in fh)
        if node_counts:
            mx = max(node_counts.values())
            for label, n in sorted(node_counts.items(), key=lambda x: -x[1]):
                log.info("%s", f"  {label:30s} {n:>8d}  {_bar(n, mx)}")
        else:
            log.info("  (nenhum nó emitido)")
    else:
        log.info("  (diretório nodes/ ausente)")

    _sec("2. Counts por relationship (edges)")
    if edges_dir.is_dir():
        edge_counts: dict[str, int] = {}
        for f in sorted(edges_dir.glob("*.ndjson")):
            with f.open("r", encoding="utf-8") as fh:
                edge_counts[f.stem] = sum(1 for _ in fh)
        if edge_counts:
            mx = max(edge_counts.values())
            for rel, n in sorted(edge_counts.items(), key=lambda x: -x[1]):
                log.info("%s", f"  {rel:30s} {n:>8d}  {_bar(n, mx)}")
        else:
            log.info("  (nenhuma aresta emitida)")
    else:
        log.info("  (diretório edges/ ausente)")

    _sec(f"3. Top {top} tipos de ação (de templates/load_atividades.ndjson)")
    activities_template = templates_dir / "load_atividades.ndjson"
    if activities_template.is_file():
        tipo_counter: Counter = Counter()
        total = 0
        with activities_template.open("r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                rows = rec.get("params", {}).get("rows") or []
                for row in rows:
                    tipo = row.get("tipo_acao")
                    if tipo:
                        tipo_counter[tipo] += 1
                        total += 1
        if total:
            mx = tipo_counter.most_common(1)[0][1]
            for tipo, n in tipo_counter.most_common(top):
                log.info("%s", f"  {tipo:35s} {n:>8d}  ({_pct(n, total)})  {_bar(n, mx)}")
        else:
            log.info("  (sem atividades no snapshot)")
    else:
        log.info("%s", f"  (arquivo {activities_template} ausente)")

    _sec("Não disponível em modo JSON")
    log.info("  As seções abaixo exigem traversal do grafo e só rodam em --mode neo4j:")
    log.info("    - permanência por unidade/órgão (PASSOU_PELA_UNIDADE / PASSOU_PELO_ORGAO)")
    log.info("    - rotas comuns de tramitação")
    log.info("    - processos parados há mais tempo")
    log.info("    - usuários/unidades mais ativos por contagem agregada")
    log.info("  Use: pipeline run resumo --mode neo4j  (após replay do snapshot)")
    log.info("%s", "=" * 70)
