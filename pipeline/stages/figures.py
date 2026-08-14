from __future__ import annotations

import logging
import runpy
from pathlib import Path

from ..core._stage_base import RunContext, StageMeta
from ..core.registry import stage

log = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parents[2]
GEN_DIR = _ROOT / "article" / "figures"
GRAPH_CENSUS = _ROOT / "artifacts" / "stats" / "graph_build.json"
CAMINHO_METRICS = (_ROOT / "artifacts" / "typical" / "exp-raw-ksil" / "kmeans" / "itinerary"
                   / "metrics.json")

GENERATORS = (
    ("pipeline-diagram", "gen_pipeline_diagram.py", None),
    ("caminho-raias", "gen_caminho_raias.py", CAMINHO_METRICS),
    ("graph-schema", "gen_graph_schema.py", GRAPH_CENSUS),
)
OPTIONAL = (("clusters-umap", "gen_clusters_umap.py"),)


@stage(StageMeta(
    name="figures",
    phase="delivery",
    question="Como as figuras dos manuscritos se derivam dos artefatos?",
    deterministic='conditional',
    nondeterminism="o conteudo e fixo; o PDF embute data de criacao, entao os bytes diferem",
    description="Regenera as figuras que os dois manuscritos incluem, a partir dos geradores "
                "em article/figures/. clusters-umap fica atrás de --flag umap=true: exige "
                "Neo4j e nenhum .tex a inclui.",
    type="op",
    depends_on=("cluster-eval",),
    modes=("neo4j", "fs"),
    can_skip_when_done=False,
    estimated_duration="<1min",
))
def run(ctx: RunContext) -> None:
    only = str(ctx.flags.get("only") or "").strip()
    wanted = [g for g in GENERATORS if not only or g[0] == only]
    if only and not wanted and only not in [n for n, _ in OPTIONAL]:
        raise ValueError(
            f"figures: unknown figure {only!r} — known: "
            f"{', '.join([n for n, _, _ in GENERATORS] + [n for n, _ in OPTIONAL])}")

    written: list[str] = []
    for name, script, needs in wanted:
        path = GEN_DIR / script
        if not path.is_file():
            raise FileNotFoundError(f"figures: generator missing: {path}")
        if needs is not None and not needs.is_file():
            raise RuntimeError(
                f"figures: {name} reads {needs.relative_to(_ROOT)}, which does not exist — "
                "run `pipeline run matrix` first, otherwise the figure would be built from "
                "nothing")
        log.info("figures: %s (%s)", name, script)
        runpy.run_path(str(path), run_name="__main__")
        written.append(name)

    if str(ctx.flags.get("umap") or "").lower() in ("1", "true", "yes"):
        for name, script in OPTIONAL:
            log.info("figures: %s (%s)", name, script)
            runpy.run_path(str(GEN_DIR / script), run_name="__main__")
            written.append(name)

    ctx.cache["figures_summary"] = {"written": written, "out_dir": str(GEN_DIR)}
    log.info("figures: %d generator(s) -> %s", len(written), GEN_DIR)
