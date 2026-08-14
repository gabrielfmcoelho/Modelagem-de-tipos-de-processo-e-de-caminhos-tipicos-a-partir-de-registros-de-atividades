from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ...core.paths import ARTIFACTS, ROOT
from .envelope import NO_ALPHABET, compose, members_block, population_block

FEATURES = ARTIFACTS / "features"
PARSED = ROOT / "parsed_documents"
NER = ROOT / "ner_results"
DOCS = ROOT / "documentos_sead"

NODE_LABELS = ("Processo", "Atividade", "Documento", "Unidade", "Orgao", "Usuario",
               "TipoProcedimento", "TipoAcao", "Ciclo", "CategoriaProcesso", "Coorte")
REL_TYPES = ("DO_PROCESSO", "SEGUIDA_POR", "PRECEDIDA_POR", "INICIOU_PROCESSO",
             "EXECUTADO_PELA_UNIDADE", "PASSOU_PELA_UNIDADE", "PASSOU_PELO_ORGAO",
             "CRIADO_NO_ORGAO", "CONTEM_DOCUMENTO", "REFERENCIA_DOCUMENTO", "SIMILAR_DOC",
             "TEM_TIPO", "EM_ABERTO_NA_UNIDADE", "CATEGORIZADO_COMO", "MEMBRO_DA_COORTE")

STAGE_OF_LABEL = {
    "Processo": "precreate", "Unidade": "precreate", "Orgao": "precreate",
    "Usuario": "precreate", "TipoProcedimento": "precreate", "TipoAcao": "precreate",
    "Atividade": "atividades", "Documento": "atividades",
    "Ciclo": "situacao", "CategoriaProcesso": "processo-cluster", "Coorte": "cohort",
}


def _count(session, query: str) -> int:
    rec = session.run(query).single()
    return int(rec["n"]) if rec and rec["n"] is not None else 0


def _rows(session, query: str) -> list[dict]:
    return [dict(r) for r in session.run(query)]


OPEN_UNIT_DISAGREEMENT_CAP = 500

CONCLUDED_READINGS = {
    "declared_situacao": "p.situacao = 'concluido'",
    "zero_open_units": "coalesce(p.unidades_em_aberto_count, 0) = 0",
    "no_open_unit_edge": "NOT (p)-[:EM_ABERTO_NA_UNIDADE]->()",
}


FLOW_RELS = frozenset({
    "INICIOU_PROCESSO", "SEGUIDA_POR", "PRECEDIDA_POR", "SEGUIDO_INDEPENDENTEMENTE_POR",
    "PASSOU_PELA_UNIDADE", "PASSOU_PELO_ORGAO", "REMETIDO_PELA_UNIDADE",
    "ABERTO_POR", "FECHADO_POR", "ATIVIDADE_MAIS_RECENTE",
})

SCHEMA_TRIPLES_CYPHER = """
MATCH (a)-[r]->(b)
RETURN labels(a)[0] AS src, type(r) AS rel, labels(b)[0] AS dst, count(*) AS n
ORDER BY n DESC, src, rel, dst
"""


def graph_build(driver) -> tuple[Path, dict]:
    nodes, rels = {}, {}
    with driver.session() as s:
        triples = [{"src": r["src"], "rel": r["rel"], "dst": r["dst"], "n": int(r["n"]),
                    "flow": r["rel"] in FLOW_RELS}
                   for r in s.run(SCHEMA_TRIPLES_CYPHER) if r["src"] and r["dst"]]
    with driver.session() as s:
        total_nodes = _count(s, "MATCH (n) RETURN count(n) AS n")
        total_rels = _count(s, "MATCH ()-[r]->() RETURN count(r) AS n")
        for label in NODE_LABELS:
            nodes[label] = _count(s, f"MATCH (n:{label}) RETURN count(n) AS n")
        for rel in REL_TYPES:
            rels[rel] = _count(s, f"MATCH ()-[r:{rel}]->() RETURN count(r) AS n")
        readings = {name: _count(s, f"MATCH (p:Processo) WHERE {expr} RETURN count(p) AS n")
                    for name, expr in CONCLUDED_READINGS.items()}
        concluded = readings["zero_open_units"]
        disagree_expr = " OR ".join(
            f"(({a}) <> ({b}))"
            for a, b in ((CONCLUDED_READINGS["declared_situacao"],
                          CONCLUDED_READINGS["zero_open_units"]),
                         (CONCLUDED_READINGS["zero_open_units"],
                          CONCLUDED_READINGS["no_open_unit_edge"])))
        n_disagreeing = _count(
            s, f"MATCH (p:Processo) WHERE {disagree_expr} RETURN count(p) AS n")
        disagreeing = _rows(
            s, f"MATCH (p:Processo) WHERE {disagree_expr} "
               "RETURN p.protocolo_formatado AS protocolo, p.situacao AS situacao, "
               "p.unidades_em_aberto_count AS unidades_em_aberto, "
               "p.data_conclusao_global AS data_conclusao_global "
               f"ORDER BY protocolo LIMIT {OPEN_UNIT_DISAGREEMENT_CAP}")
        with_tipo = _count(
            s, "MATCH (p:Processo)-[:TEM_TIPO]->(:TipoProcedimento) RETURN count(p) AS n")
        with_features = _count(
            s, "MATCH (p:Processo) WHERE p.cluster_features IS NOT NULL RETURN count(p) AS n")

    by_stage = {}
    for label, stage in STAGE_OF_LABEL.items():
        by_stage.setdefault(stage, {})[label] = nodes.get(label, 0)

    payload = compose(
        scope={"level": "L0", "subject": "graph", "alphabet": NO_ALPHABET},
        population=population_block(
            "corpus", n_cases=nodes.get("Processo", 0),
            definition="the graph as loaded at the moment of the census; every count is a live "
                       "read, not a running total kept by the ETL"),
        members=members_block(NODE_LABELS, [k for k in nodes], allow_missing=True),
        results={
            "totals": {"nodes": total_nodes, "relationships": total_rels},
            "nodes_by_label": nodes,
            "relationships_by_type": rels,
            "schema_triples": triples,
            "flow_relationship_types": sorted(FLOW_RELS),
            "nodes_by_producing_stage": by_stage,
            "processo": {"total": nodes.get("Processo", 0), "concluded": concluded,
                         "open": nodes.get("Processo", 0) - concluded,
                         "with_declared_tipo": with_tipo,
                         "with_cluster_features": with_features},
            "concluded_reconciliation": {
                "readings": readings,
                "predicates": dict(CONCLUDED_READINGS),
                "n_disagreeing": n_disagreeing,
                "disagreeing": disagreeing,
                "truncated": n_disagreeing > len(disagreeing),
                "reading": (
                    "Three independent readings of 'concluded': the situacao our flow rules "
                    "compute from the loaded event log, the open-unit count those same rules "
                    "derive, and the EM_ABERTO_NA_UNIDADE edges the loader writes. The corpus "
                    "is selected upstream in Trino by the gold status field, so on a graph "
                    "loaded that way all three agree by construction and n_disagreeing is 0 — "
                    "that is expected, not a check that passed. The block exists so that a "
                    "processo our rules call open while the source calls it concluded is "
                    "recorded case by case instead of silently dropped, and can be reconciled "
                    "against the estoque-de-processos rules maintained in the other repos."),
            },
        },
    )
    return ARTIFACTS / "stats" / "graph_build.json", payload


def _dir_count(path: Path) -> int:
    return sum(1 for p in path.iterdir() if not p.name.startswith(".")) if path.is_dir() else 0


def _parsed_by_protocolo() -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not PARSED.is_dir():
        return out
    for d in PARSED.iterdir():
        if not d.is_dir():
            continue
        meta = d / "metadata.json"
        pf = ""
        if meta.is_file():
            try:
                pf = (json.loads(meta.read_text(encoding="utf-8")).get("protocolo") or "")
            except Exception:
                pf = ""
        pf = pf.replace("_", "/")
        out[d.name] = {"protocolo": pf,
                       "text": (d / "text.txt").is_file(),
                       "anon": (d / "text_anon.txt").is_file()}
    return out


def _loaded_protocolos(driver) -> set[str]:
    if driver is None:
        return set()
    with driver.session() as s:
        return {r["p"] for r in s.run(
            "MATCH (p:Processo) RETURN p.protocolo_formatado AS p") if r["p"]}


def document_funnel(driver=None) -> tuple[Path, dict]:
    downloaded = _dir_count(DOCS)
    ner = _dir_count(NER)
    docs = _parsed_by_protocolo()
    parsed = len(docs)
    with_text = sum(1 for v in docs.values() if v["text"])
    anon = sum(1 for v in docs.values() if v["anon"])

    loaded = _loaded_protocolos(driver)
    in_corpus = {k: v for k, v in docs.items() if v["protocolo"] and v["protocolo"] in loaded}
    orphan = {k: v for k, v in docs.items() if v["protocolo"] and v["protocolo"] not in loaded}

    graph = {}
    if driver is not None:
        with driver.session() as s:
            graph = {
                "documento_nodes": _count(s, "MATCH (d:Documento) RETURN count(d) AS n"),
                "embedded": _count(
                    s, "MATCH (d:Documento) WHERE d.embedding IS NOT NULL RETURN count(d) AS n"),
                "with_topic": _count(
                    s, "MATCH (d:Documento) WHERE d.topic IS NOT NULL RETURN count(d) AS n"),
            }

    fetched = [
        {"step": "downloaded", "n": downloaded, "source": "documentos_sead/"},
        {"step": "parsed", "n": parsed, "source": "parsed_documents/"},
        {"step": "parsed_with_text", "n": with_text, "source": "parsed_documents/*/text.txt"},
        {"step": "anonymised", "n": anon, "source": "parsed_documents/*/text_anon.txt"},
        {"step": "ner_extracted", "n": ner, "source": "ner_results/"},
    ]
    corpus = [
        {"step": "parsed_in_corpus", "n": len(in_corpus),
         "source": "parsed_documents/ ∩ :Processo"},
        {"step": "with_text", "n": sum(1 for v in in_corpus.values() if v["text"]),
         "source": "parsed_documents/*/text.txt ∩ :Processo"},
        {"step": "anonymised", "n": sum(1 for v in in_corpus.values() if v["anon"]),
         "source": "parsed_documents/*/text_anon.txt ∩ :Processo"},
    ]
    referenced = [{"step": k, "n": v, "source": "neo4j"} for k, v in graph.items()]

    for chain in (fetched, corpus, referenced):
        for i, row in enumerate(chain):
            prev = chain[i - 1]["n"] if i else None
            row["lost_vs_previous"] = (prev - row["n"]) if prev is not None else None

    embedded = graph.get("embedded")
    payload = compose(
        scope={"level": "L0", "subject": "documents", "alphabet": NO_ALPHABET},
        population=population_block(
            "corpus", n_cases=len(in_corpus),
            definition="the corpus is the documents of the processos actually loaded into the "
                       "graph — NOT everything on disk. documentos_sead/ and parsed_documents/ "
                       "accumulate across runs and hold documents of processos outside the "
                       "current load; those are counted separately as `orphan_on_disk` and must "
                       "never be quoted as corpus size"),
        members=members_block(
            [s["step"] for s in fetched + corpus + referenced],
            [s["step"] for s in fetched + corpus + referenced]),
        results={
            "corpus_documents": {
                "population": "opening documents whose processo is present in the graph",
                "funnel": corpus,
                "n_processos_loaded": len(loaded),
                "anonymised_fraction": (
                    round(sum(1 for v in in_corpus.values() if v["anon"]) / len(in_corpus), 4)
                    if in_corpus else None)},
            "fetched_on_disk": {
                "population": "everything the download and parse stages have ever written, over "
                              "any load; a superset of the corpus",
                "funnel": fetched,
                "orphan_on_disk": len(orphan),
                "orphan_note": "parsed documents whose processo is not in the current graph; "
                               "they are residue of a wider or earlier load, not corpus"},
            "referenced_documents": {
                "population": "every :Documento node the event log references, most never fetched",
                "funnel": referenced,
                "embedded_share_of_referenced": (
                    round(embedded / graph["documento_nodes"], 4)
                    if graph.get("documento_nodes") and embedded is not None else None)},
            "note": "three populations, never chained: corpus ⊆ fetched, and referenced is a "
                    "different axis entirely (all documents mentioned, not documents read)",
        },
    )
    return ARTIFACTS / "stats" / "document_funnel.json", payload


def feature_build() -> tuple[Path, dict]:
    arms = {}
    found = []
    if FEATURES.is_dir():
        for npz in sorted(FEATURES.glob("*.npz")):
            run_id = npz.stem
            found.append(run_id)
            try:
                z = np.load(npz, allow_pickle=False)
                protocolos = z["protocolos"]
                features = z["features"]
                entry = {
                    "n_processos": int(protocolos.shape[0]),
                    "dim": int(features.shape[1]) if features.ndim == 2 else None,
                    "dtype": str(features.dtype),
                    "digest": str(z["digest"]) if "digest" in z else "",
                    "text_variant": str(z["text_variant"]) if "text_variant" in z else "",
                }
            except Exception as exc:
                entry = {"unreadable": f"{type(exc).__name__}: {exc}"}
            side = npz.with_name(npz.name + ".meta.json")
            if side.is_file():
                meta = json.loads(side.read_text(encoding="utf-8")).get("_meta", {})
                entry["params"] = meta.get("params")
                entry["sha256"] = json.loads(side.read_text(encoding="utf-8")).get("sha256")
            arms[run_id] = entry

    payload = compose(
        scope={"level": "L0", "subject": "features", "alphabet": NO_ALPHABET},
        population=population_block(
            "corpus",
            definition="every feature matrix on disk; the matrix is what every clustering is "
                       "refit from, so its digest is the reproducibility anchor"),
        members=members_block(found, found),
        results={"n_matrices": len(arms), "matrices": arms},
    )
    return ARTIFACTS / "stats" / "feature_build.json", payload
