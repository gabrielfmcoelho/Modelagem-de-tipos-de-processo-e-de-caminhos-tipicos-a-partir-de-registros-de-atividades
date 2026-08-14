
from __future__ import annotations

import typer

from .core.deployment import ORGAO_SIGLA
from . import stages

app = typer.Typer(
    name="pipeline",
    help=f"{ORGAO_SIGLA} processo visualizer pipeline (Trino → Neo4j + documentos + NER).",
    no_args_is_help=False,
    add_completion=False,
)

from .apps import interactive
from .apps import list as list_app
from .apps import run as run_app
from .apps import status as status_app

interactive.register(app)
run_app.register(app)
list_app.register(app)
status_app.register(app)


if __name__ == "__main__":
    app()
