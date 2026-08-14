
from __future__ import annotations

from pathlib import Path

import typer

from .. import stages
from ..core import runner
from ..cli import resolve_settings
from ..core.console import console
from ..core.logging_setup import configure_logging
from ..core.registry import IncompatibleModeError, StageNotFoundError


def _make_settings(
    *,
    neo4j_uri: str | None,
    neo4j_user: str | None,
    neo4j_password: str | None,
    neo4j_database: str | None,
    emit_dir: Path | None,
    read_dir: Path | None,
    log_level: str | None,
    batch_size: int | None,
    workers: int | None,
):
    import argparse
    ns = argparse.Namespace(
        neo4j_uri=neo4j_uri,
        neo4j_user=neo4j_user,
        neo4j_password=neo4j_password,
        neo4j_database=neo4j_database,
        emit_json_dir=emit_dir,
        read_json_dir=read_dir,
        log_level=log_level,
        batch_size=batch_size,
        workers=workers,
    )
    return resolve_settings(ns)


def _parse_flag(flag: str) -> tuple[str, str]:
    if "=" not in flag:
        raise typer.BadParameter(f"--flag requires KEY=VALUE form, got: {flag!r}")
    k, v = flag.split("=", 1)
    return k.strip(), v.strip()


def register(app: typer.Typer) -> None:
    @app.command("run", help="Run one or more stages, resolving dependencies in topological order.")
    def run_cmd(
        stages_arg: list[str] = typer.Argument(..., help="Stage names (one or more). Deps auto-resolved."),
        mode: str | None = typer.Option(None, "--mode", help="neo4j | json-emit | json-replay | fs"),
        emit_dir: Path | None = typer.Option(None, "--emit-dir", "--emit-json"),
        read_dir: Path | None = typer.Option(None, "--read-dir", "--read-json"),
        from_date: str | None = typer.Option(None, "--from"),
        to_date: str | None = typer.Option(None, "--to"),
        workers: int | None = typer.Option(None, "--workers"),
        batch_size: int | None = typer.Option(None, "--batch-size"),
        chunk_size: int | None = typer.Option(None, "--chunk-size"),
        limit: int | None = typer.Option(None, "--limit"),
        force: bool = typer.Option(False, "--force", help="Re-run all selected stages, ignoring checkpoints."),
        force_stage: list[str] = typer.Option([], "--force-stage", help="Re-run only this stage (may repeat)."),
        no_deps: bool = typer.Option(False, "--no-deps", help="Run only the named stage(s); skip dependency resolution."),
        state_dir: Path | None = typer.Option(None, "--state-dir", help="Override .pipeline-state directory."),
        dry_resolve: bool = typer.Option(False, "--dry-resolve", help="Show plan, don't execute."),
        flag: list[str] = typer.Option([], "--flag", help="Stage-specific flag KEY=VALUE (repeatable)."),
        neo4j_uri: str | None = typer.Option(None, "--neo4j-uri"),
        neo4j_user: str | None = typer.Option(None, "--neo4j-user"),
        neo4j_password: str | None = typer.Option(None, "--neo4j-password"),
        neo4j_database: str | None = typer.Option(None, "--neo4j-database"),
        log_level: str | None = typer.Option(None, "--log-level"),
    ) -> None:
        settings = _make_settings(
            neo4j_uri=neo4j_uri,
            neo4j_user=neo4j_user,
            neo4j_password=neo4j_password,
            neo4j_database=neo4j_database,
            emit_dir=emit_dir,
            read_dir=read_dir,
            log_level=log_level,
            batch_size=batch_size,
            workers=workers,
        )
        configure_logging("pipeline", settings.log_level)

        flags: dict = {
            "from_date": from_date,
            "to_date": to_date,
            "workers": workers,
            "batch_size": batch_size,
            "chunk_size": chunk_size,
            "limit": limit,
            "emit_dir": str(emit_dir) if emit_dir else None,
            "read_dir": str(read_dir) if read_dir else None,
        }
        for f in flag:
            k, v = _parse_flag(f)
            flags[k] = v

        try:
            runner.run_stages(
                stages_arg,
                settings=settings,
                mode=mode,
                flags=flags,
                state_dir=state_dir,
                force=force,
                force_stage=set(force_stage),
                no_deps=no_deps,
                dry_resolve=dry_resolve,
                console=console,
            )
        except StageNotFoundError as e:
            console.print(f"[red]Unknown stage: {e}[/red]")
            console.print("Use [bold]pipeline list[/bold] to see available stages.")
            raise typer.Exit(2) from e
        except IncompatibleModeError as e:
            console.print(f"[red]{e}[/red]")
            raise typer.Exit(2) from e
