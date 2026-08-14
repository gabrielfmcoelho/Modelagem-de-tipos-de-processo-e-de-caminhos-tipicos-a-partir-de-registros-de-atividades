
import argparse
import sys
from datetime import datetime
from pathlib import Path as _Path

_HERE = _Path(__file__).resolve()
_ROOT = next((p.parent for p in _HERE.parents if p.name == "pipeline"), _HERE.parents[2])
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from pipeline.cli import add_standard_args, resolve_settings
from ..model.graph_summary import run_summary, run_summary_json
from ..core.config import ConfigError
from ..core.logging_setup import configure_logging
from ..core.neo4j_driver import build_driver
from ..core.deployment import ORGAO_SIGLA

log = configure_logging(__name__)




















def main():
    parser = argparse.ArgumentParser(description="Statistical summary of the graph (Neo4j or JSON)")
    parser.add_argument("--orgao", default=None,
                        help=f"Filter only processos created in this orgão (e.g. '{ORGAO_SIGLA}'). Neo4j mode only.")
    parser.add_argument("--top", type=int, default=15,
                        help="How many items to show in rankings (default: 15)")
    add_standard_args(parser)
    args = parser.parse_args()

    settings = resolve_settings(args)
    configure_logging(__name__, settings.log_level)

    if settings.emit_json_dir is not None:
        run_summary_json(_Path(settings.emit_json_dir), args.top)
        return
    if settings.read_json_dir is not None:
        run_summary_json(_Path(settings.read_json_dir), args.top)
        return

    try:
        driver = build_driver(settings)
        log.info("Connected to Neo4j: %s", settings.neo4j_uri)
    except ConfigError as e:
        log.error("%s", e)
        sys.exit(2)
    except Exception as e:
        log.error("Failed to connect to Neo4j at %s: %s", settings.neo4j_uri, e)
        sys.exit(1)

    scope = f" — orgão: {args.orgao}" if args.orgao else ""
    log.info("%s", "=" * 70)
    log.info("%s", f"  RESUMO NEO4J{scope}")
    log.info("%s", "=" * 70)

    run_summary(driver, args.orgao, args.top)
    driver.close()


from ..core._stage_base import RunContext, StageMeta
from ..core.registry import stage


@stage(StageMeta(
    name="resumo",
    phase="operations",
    question="Qual o resumo estatistico do grafo carregado?",
    deterministic=True,
    description="Sumário estatístico do grafo. Subset disponível em modo JSON.",
    type="op",
    depends_on=(),
    modes=("neo4j", "json-emit", "json-replay"),
    can_skip_when_done=False,
    estimated_duration="<30s",
))
def run(ctx: RunContext) -> None:
    top = int(ctx.flags.get("top") or 15)
    if ctx.mode in ("json-emit", "json-replay"):
        emit_dir = ctx.flags.get("emit_dir") or ctx.flags.get("read_dir")
        if not emit_dir:
            emit_dir = ctx.settings.emit_json_dir or ctx.settings.read_json_dir
        if not emit_dir:
            raise RuntimeError(
                "resumo em modo JSON requer --emit-dir ou --read-dir"
            )
        run_summary_json(_Path(emit_dir), top)
        ctx.cache["resumo_summary"] = {"mode": ctx.mode, "source": str(emit_dir)}
        return

    driver = ctx.require_driver()
    orgao = ctx.flags.get("orgao")
    scope = f" — orgão: {orgao}" if orgao else ""
    log.info("%s", "=" * 70)
    log.info("%s", f"  RESUMO NEO4J{scope}")
    log.info("%s", "=" * 70)
    run_summary(driver, orgao, top)
    ctx.cache["resumo_summary"] = {"mode": ctx.mode, "orgao": orgao, "top": top}


if __name__ == "__main__":
    main()
