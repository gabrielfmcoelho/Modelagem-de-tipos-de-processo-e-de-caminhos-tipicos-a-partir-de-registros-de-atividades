
from __future__ import annotations

import logging

from ..core.logging_setup import configure_logging


def test_bracketed_messages_do_not_raise():
    log = configure_logging("test.brackets", "INFO")
    log.info("[skip] stage already complete")
    log.warning("Progress [1/84] chunks")
    assert logging.getLogger().handlers


def test_configure_logging_is_idempotent():
    configure_logging("test.a", "INFO")
    before = len(logging.getLogger().handlers)
    configure_logging("test.b", "DEBUG")
    after = len(logging.getLogger().handlers)
    assert after == before
    assert logging.getLogger().level == logging.DEBUG
