
from __future__ import annotations

import logging
import random
import time
from typing import Any

from neo4j import GraphDatabase
from neo4j.exceptions import TransientError

from .config import Settings

log = logging.getLogger(__name__)

MAX_RETRIES = 20
_BASE_BACKOFF_SECONDS = 0.1
_MAX_BACKOFF_SECONDS = 10.0


def build_driver(settings: Settings, *, verify: bool = True) -> Any:
    settings.require_neo4j()
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    if verify:
        driver.verify_connectivity()
    return driver


def run_query(driver: Any, cypher: str, params: dict | None = None) -> list[dict]:
    with driver.session() as session:
        return [dict(r) for r in session.run(cypher, params)]


def run_with_retry(driver: Any, cypher: str, *, max_retries: int = MAX_RETRIES, **params: Any) -> None:
    for attempt in range(1, max_retries + 1):
        try:
            with driver.session() as session:
                session.run(cypher, **params)
            return
        except TransientError:
            if attempt == max_retries:
                raise
            wait = min(_BASE_BACKOFF_SECONDS * (2 ** attempt) + random.uniform(0, 1.0), _MAX_BACKOFF_SECONDS)
            log.debug("Deadlock (attempt %d/%d), retrying in %.1fs", attempt, max_retries, wait)
            time.sleep(wait)
