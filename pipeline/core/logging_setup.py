
from __future__ import annotations

import logging

from rich.logging import RichHandler

from .console import console

_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(name: str | None = None, level: int | str = logging.INFO) -> logging.Logger:
    if isinstance(level, str):
        level = logging.getLevelName(level.upper())

    root = logging.getLogger()
    if not any(isinstance(h, RichHandler) for h in root.handlers):
        for existing in list(root.handlers):
            root.removeHandler(existing)
        handler = RichHandler(
            console=console,
            show_path=False,
            markup=False,
            rich_tracebacks=False,
            log_time_format=_DATE_FORMAT,
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        root.addHandler(handler)

    root.setLevel(level)
    return logging.getLogger(name) if name else root
