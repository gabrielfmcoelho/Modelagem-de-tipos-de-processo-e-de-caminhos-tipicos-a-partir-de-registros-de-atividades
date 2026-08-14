from __future__ import annotations

import logging

log = logging.getLogger(__name__)

CORPUS_CYPHER = "MATCH (p:Processo) RETURN p.protocolo_formatado AS pf"


def canon_protocolo(pf: str) -> str:
    return (pf or "").strip().replace("_", "/")


def corpus_protocolos(settings, driver=None, *, allow_connect: bool = False) -> set[str]:
    own = False
    if driver is None:
        if not allow_connect:
            return set()
        try:
            from .neo4j_driver import build_driver
            driver, own = build_driver(settings), True
        except Exception as exc:
            log.warning("corpus filter unavailable — no graph reachable (%s). Every parsed "
                        "processo will be processed, including documents outside the corpus.",
                        exc)
            return set()
    try:
        with driver.session() as s:
            return {canon_protocolo(r["pf"]) for r in s.run(CORPUS_CYPHER) if r["pf"]}
    except Exception as exc:
        log.warning("corpus filter unavailable — could not read the graph (%s)", exc)
        return set()
    finally:
        if own:
            driver.close()
