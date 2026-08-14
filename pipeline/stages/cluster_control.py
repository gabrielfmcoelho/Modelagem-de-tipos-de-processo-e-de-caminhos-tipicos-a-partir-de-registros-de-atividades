from __future__ import annotations

import json
import logging
import random
from pathlib import Path

from ..evidence.artifact import write_artifact
from ..core._stage_base import RunContext, StageMeta
from ..core.registry import stage
from ..core.state import now_iso
from ..core.paths import ARTIFACTS

log = logging.getLogger(__name__)

CLUSTERING_ROOT = ARTIFACTS / "clustering"
SHUFFLED_SUFFIX = "-shuffled"


def _default_sources() -> tuple[str, ...]:
    from .matrix import REAL_CELLS
    return tuple(f"{run_id}/{algo}" for run_id, algo in REAL_CELLS)


def shuffle_labels(labels: dict[str, int], seed: int = 42) -> dict[str, int]:
    protocolos = sorted(labels)
    values = [labels[p] for p in protocolos]
    random.Random(seed).shuffle(values)
    return dict(zip(protocolos, values))


def _write(run_id: str, algo: str, labels: dict[str, int], source: str, seed: int) -> Path:
    out = CLUSTERING_ROOT / run_id / algo / "labels.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "meta": {"run_id": run_id, "algo": algo, "generated_at": now_iso(),
                 "n": len(labels), "control": "shuffled", "source": source, "seed": seed},
        "labels": labels,
    }
    write_artifact(payload, out, stage="cluster-control",
                   params={"run_id": run_id, "algo": algo, "source": source, "seed": seed,
                           "control": "shuffled"},
                   inputs=[CLUSTERING_ROOT / source / algo / "labels.json"])
    return out


@stage(StageMeta(
    name="cluster-control",
    phase="clustering",
    question="Quanto do ganho vem do agrupamento e nao apenas do numero e tamanho dos grupos?",
    deterministic='conditional',
    nondeterminism="permutacao pseudoaleatoria, fixada pelo seed registrado em params",
    description="Partição-controle: embaralha os rótulos de um clustering real preservando "
                "contagem e distribuição de tamanhos, para medir quanto do ganho vem do agrupamento.",
    type="op",
    depends_on=("cluster-eval",),
    modes=("neo4j", "fs"),
    can_skip_when_done=False,
    estimated_duration="<1min",
))
def run(ctx: RunContext) -> None:
    seed = int(ctx.flags.get("seed") or 42)
    sources = [s.strip() for s in
               str(ctx.flags.get("sources") or ",".join(_default_sources())).split(",") if s.strip()]

    written = []
    for src in sources:
        run_id, _, algo = src.partition("/")
        path = CLUSTERING_ROOT / run_id / algo / "labels.json"
        if not path.is_file():
            raise FileNotFoundError(
                f"cluster-control: {path} not found — run cluster-eval for {src} first")
        labels = json.loads(path.read_text(encoding="utf-8"))["labels"]
        shuffled = shuffle_labels(labels, seed)
        if shuffled == labels:
            raise RuntimeError(f"cluster-control: shuffling {src} was a no-op")
        moved = sum(1 for p in labels if labels[p] != shuffled[p])
        out = _write(run_id + SHUFFLED_SUFFIX, algo, shuffled, src, seed)
        log.info("cluster-control: %s -> %s (%d/%d processos reassigned)",
                 src, out.parent.name and f"{run_id}{SHUFFLED_SUFFIX}/{algo}", moved, len(labels))
        written.append({"source": src, "target": f"{run_id}{SHUFFLED_SUFFIX}/{algo}",
                        "n": len(labels), "reassigned": moved})

    ctx.cache["cluster_control_summary"] = {"seed": seed, "partitions": written}
    log.info("cluster-control complete: %d control partitions written", len(written))
