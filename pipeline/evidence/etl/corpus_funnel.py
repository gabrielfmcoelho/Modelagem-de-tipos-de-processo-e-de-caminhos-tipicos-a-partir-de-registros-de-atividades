#!/usr/bin/env python

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone

from ...core.paths import ROOT

from ..artifact import write_artifact
from ...core.config import Settings
from ...core.deployment import ORGAO_SIGLA
from ...core.trino_source import make_trino_conn

_IDENT_RE = re.compile(r"^[A-Za-z0-9_.\-]+$")


def _safe_ident(value: str, what: str) -> str:
    if not _IDENT_RE.match(value or ""):
        raise ValueError(
            f"{what}={value!r} is interpolated into SQL and must be a bare identifier "
            f"matching {_IDENT_RE.pattern}")
    return value

OUT = ROOT / "artifacts" / "stats" / "corpus_funnel.json"
PARSED_DOCS = ROOT / "parsed_documents"

BORN_IN_ORGAO = """
    SELECT DISTINCT protocolo_formatado FROM {t}
    WHERE descricao_replace LIKE 'Processo %gerado%'
      AND split_part(unidade, '/', 1) = '{orgao}'
      AND data_hora >= TIMESTAMP '{y}-01-01 00:00:00'
      AND data_hora <  TIMESTAMP '{n}-01-01 00:00:00'
"""

Q_GENERATED = """
SELECT count(*) FROM ({born})
"""

Q_CORPUS_SET = """
    SELECT protocolo_formatado FROM {gold}
    WHERE protocolo_formatado IN ({born})
      AND status = 'concluido'
      AND dt_ultimo_andamento < TIMESTAMP '{n}-01-01 00:00:00'
"""

Q_CONCLUDED = """
SELECT count(*) FROM (
    SELECT protocolo_formatado
    FROM {t}
    WHERE protocolo_formatado IN ({born})
    GROUP BY protocolo_formatado
    HAVING max(CASE WHEN {concluded} THEN 1 ELSE 0 END) = 1
       AND max(CASE WHEN {concluded} THEN data_hora END) < TIMESTAMP '{n}-01-01 00:00:00'
)
"""

Q_ACTIVITIES = """
SELECT count(*)
FROM {t}
WHERE protocolo_formatado IN (
    SELECT protocolo_formatado
    FROM {t}
    WHERE protocolo_formatado IN ({born})
    GROUP BY protocolo_formatado
    HAVING max(CASE WHEN {concluded} THEN 1 ELSE 0 END) = 1
       AND max(CASE WHEN {concluded} THEN data_hora END) < TIMESTAMP '{n}-01-01 00:00:00'
)
"""

Q_DOCUMENTS = """
SELECT count(DISTINCT regexp_extract(descricao_replace, '{pat}', 1))
FROM {t}
WHERE protocolo_formatado IN ({born})
  AND regexp_extract(descricao_replace, '{pat}', 1) <> ''
  {window}
"""

Q_SPAN = """
SELECT min(data_hora), max(data_hora), count(*) FROM {t}
"""

CONCLUDED_PREDICATE = "lower(descricao_replace) LIKE '%conclus%'"

DOC_NUMBER_PATTERN = r"(\d{7,})\s*\([^@)]+?( \d+)?\)"


def _parsed_in_corpus(born: set[str]) -> int | None:
    if not PARSED_DOCS.is_dir():
        return None
    seen: set[str] = set()
    for p in PARSED_DOCS.iterdir():
        meta = p / "metadata.json"
        if not meta.is_file():
            continue
        try:
            pf = json.loads(meta.read_text(encoding="utf-8")).get("protocolo") or ""
        except (OSError, ValueError):
            continue
        pf = pf.replace("_", "/")
        if pf in born:
            seen.add(pf)
    return len(seen)


def _scalar(cur, sql):
    cur.execute(sql)
    row = cur.fetchone()
    return row[0] if row else None


def build(year: int, table: str, orgao: str, gold_table: str | None = None,
          corpus: set[str] | None = None) -> dict:
    table = _safe_ident(table, "table")
    orgao = _safe_ident(orgao, "orgao")
    gold_table = _safe_ident(
        gold_table or f"{table.split('.')[0]}.sei_gold.processos_metadados", "gold_table")
    fmt = {"t": table, "y": year, "n": year + 1, "concluded": CONCLUDED_PREDICATE,
           "orgao": orgao}
    born = BORN_IN_ORGAO.format(**fmt)
    win = (f"AND data_hora >= TIMESTAMP '{year}-01-01 00:00:00' "
           f"AND data_hora <  TIMESTAMP '{year + 1}-01-01 00:00:00'")
    with make_trino_conn(Settings.from_env()) as conn:
        cur = conn.cursor()
        cur.execute(Q_CORPUS_SET.format(born=born, gold=gold_table, **fmt))
        corpus_from_gold = {r[0] for r in cur.fetchall()}
        corpus_protocolos = corpus if corpus else corpus_from_gold
        corpus_source = "graph" if corpus else "gold_table"
        generated = _scalar(cur, Q_GENERATED.format(born=born))
        concluded = _scalar(cur, Q_CONCLUDED.format(born=born, **fmt))
        activities = _scalar(cur, Q_ACTIVITIES.format(born=born, **fmt))
        docs_all = _scalar(cur, Q_DOCUMENTS.format(
            born=born, t=table, pat=DOC_NUMBER_PATTERN, window=""))
        docs_win = _scalar(cur, Q_DOCUMENTS.format(
            born=born, t=table, pat=DOC_NUMBER_PATTERN, window=win))
        cur.execute(Q_SPAN.format(**fmt))
        span = cur.fetchone()

    parsed_total = (sum(1 for p in PARSED_DOCS.iterdir() if not p.name.startswith("."))
                    if PARSED_DOCS.is_dir() else None)
    parsed = _parsed_in_corpus(corpus_protocolos)

    return {
        "year": year,
        "orgao": orgao,
        "source_table": table,
        "n_documents_all_activity": docs_all,
        "n_documents_activity_within_year": docs_win,
        "n_opening_documents_parsed": parsed,
        "n_parsed_dirs_on_disk": parsed_total,
        "n_corpus_protocolos": len(corpus_protocolos),
        "corpus_source": corpus_source,
        "n_corpus_in_gold_now": len(corpus_from_gold),
        "corpus_source_table": gold_table,
        "document_number_pattern": DOC_NUMBER_PATTERN,
        "concluded_predicate": CONCLUDED_PREDICATE,
        "n_generated": generated,
        "n_conclusion_event_logged_same_year": concluded,
        "n_not_concluded_same_year": (generated - concluded
                                      if None not in (generated, concluded) else None),
        "n_activities_in_concluded": activities,
        "lakehouse_span": {
            "first_event": str(span[0]) if span else None,
            "last_event": str(span[1]) if span else None,
            "n_activities_total": span[2] if span else None,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "caveat": (
            "n_generated counts protocols whose 'Processo gerado' event was executed by a "
            f"{orgao}/... unidade inside the year -- the born-in-orgao definition the article "
            "uses. It is not the SEI autuacao field. n_conclusion_event_logged_same_year applies the "
            "descricao_replace predicate above and is NOT the article's concluded population. "
            "n_corpus_protocolos is PINNED to the corpus the graph actually loaded when corpus_source == 'graph'; n_corpus_in_gold_now re-derives it from the live gold table and will drift, because a case concluded in 2025 can receive a new andamento later and then fail dt_ultimo_andamento < next-year. Report the pinned number: it is what every downstream figure was computed on. "
            "The article's corpus is graph-derived: the situacao stage calls a case concluded "
            "when it has no EM_ABERTO_NA_UNIDADE edge left at year end. The text predicate "
            "used here answers a different question -- 'did a conclusion event get logged' -- "
            "and returns a larger number. Report them as two measures, never as one. "
            "Neither figure is reconcilable with artifacts/traces, which hold a different "
            "slice. "
            "n_documents_all_activity counts distinct document numbers over every activity "
            "of those cases; n_documents_activity_within_year restricts the activity side to "
            "the year, which is the scope the graph load used. The manuscripts' 148,178 is a "
            "Neo4j :Documento node count taken from a graph state and a lakehouse snapshot "
            "that no longer exist; it sits between these two and reproduces as neither. "
            "n_opening_documents_parsed counts parsed_documents/ on disk, the artifact the "
            "12,259 figure refers to. Two counts the article reports and this stage still "
            "does NOT produce -- processos concluded without an embedded opening document, "
            "and opening documents cancelled at source -- live in the document pipeline, not "
            "in sei_atividades."),
    }


def main(argv: list[str] | None = None, corpus: set[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2025)
    ap.add_argument("--table", default=None)
    ap.add_argument("--orgao", default=ORGAO_SIGLA)
    ap.add_argument("--gold-table", default=None,
                    help="gold metadata table that defines the corpus (default "
                         "<catalog>.sei_gold.processos_metadados)")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)

    s = Settings.from_env()
    table = args.table or f"{s.trino_catalog}.{s.trino_schema}.sei_atividades"

    data = build(args.year, table, args.orgao, args.gold_table, corpus=corpus)
    out = write_artifact(data, args.out, stage="corpus-funnel",
                         params={"year": args.year, "table": table, "orgao": args.orgao,
                                 "gold_table": data["corpus_source_table"]})
    print(f"wrote {out}  (generated={data['n_generated']}, "
          f"conclusion_event_logged={data['n_conclusion_event_logged_same_year']}, "
          f"activities={data['n_activities_in_concluded']}, "
          f"documents={data['n_documents_all_activity']}, "
          f"opening_docs_parsed={data['n_opening_documents_parsed']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
