
from __future__ import annotations

from ..core._stage_base import RunContext, StageMeta
from ..core.registry import stage


@stage(StageMeta(
    name="etl",
    phase="graph",
    question="Macro: qual o grafo de fluxo de cada processo a partir do event log?",
    deterministic=True,
    description="Macro: roda precreate + atividades + timeline + permanencia + situacao em ordem.",
    type="core",
    depends_on=("precreate", "atividades", "timeline", "permanencia", "situacao"),
    modes=("neo4j", "json-emit"),
    estimated_duration="varia conforme volume",
))
def run_etl(ctx: RunContext) -> None:
    return None


@stage(StageMeta(
    name="etl-full",
    phase="graph",
    question="Macro: o pipeline inteiro, das fontes ao catalogo nomeado.",
    deterministic=False,
    nondeterminism="inclui etapas de LLM (parse, evaluate, naming)",
    description="Macro completo: etl + download + parse + ner + embed + similarity + processo-cluster.",
    type="core",
    depends_on=(
        "etl", "download", "parse", "ner-extract", "ner-load",
        "embed", "similarity", "processo-cluster",
    ),
    modes=("neo4j", "json-emit"),
    estimated_duration="varia significativamente; horas para corpus grande",
))
def run_etl_full(ctx: RunContext) -> None:
    return None
