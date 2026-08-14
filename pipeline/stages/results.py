from __future__ import annotations

import json
import logging
from pathlib import Path

from ..evidence.results import results_doc, results_figures, results_tex
from ..evidence.artifact import write_artifact
from ..core._stage_base import RunContext, StageMeta
from ..core.registry import stage
from ..core.state import now_iso

log = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parents[2]
FIGURES_PATH = _ROOT / "artifacts" / "stats" / "results_figures.json"
DOC_PATH = _ROOT / "docs" / "research" / "RESULTS.md"


@stage(StageMeta(
    name="results",
    phase="delivery",
    question="O que os artefatos, juntos, dizem — como tabelas geradas.",
    deterministic=True,
    description="Agrega todos os artefatos em results_figures.json, regenera as tabelas "
                "marcadas de docs/research/RESULTS.md e as tabelas LaTeX em inglês e em "
                "pt-BR. Falha se qualquer um dos três divergir.",
    type="op",
    depends_on=("cluster-eval",),
    modes=("neo4j", "fs"),
    can_skip_when_done=False,
    estimated_duration="<1min",
))
def run(ctx: RunContext) -> None:
    check_only = str(ctx.flags.get("check") or "").lower() in ("1", "true", "yes")
    figures_path = Path(ctx.flags.get("figures") or FIGURES_PATH)
    doc_path = Path(ctx.flags.get("doc") or DOC_PATH)

    figures = results_figures.build()
    if not figures.get("n_cells"):
        raise RuntimeError(
            "results: no matrix cells found under artifacts/typical — run the matrix first "
            "(`pipeline run matrix`), otherwise every generated table would be emptied")

    original = doc_path.read_text(encoding="utf-8") if doc_path.is_file() else ""
    updated, filled = results_doc.render(original, figures)
    missing = sorted(set(results_doc.BLOCKS) - set(filled))
    if missing:
        raise RuntimeError(
            f"results: {doc_path} is missing markers for {missing} — those tables would go "
            "unverified. Add '<!-- fig:NAME -->' / '<!-- /fig:NAME -->' or drop the block.")

    tables_dir = Path(ctx.flags.get("tables") or (_ROOT / "article" / "latex" / "tables"))
    tables_pt_dir = Path(ctx.flags.get("tables_pt")
                         or (_ROOT / "article" / "latex-ptbr" / "tables"))
    rendered = {}
    for name, fn in results_tex.TABLES.items():
        body = fn(figures)
        if not body.strip():
            raise RuntimeError(f"results: LaTeX table {name} rendered empty")
        rendered[(tables_dir, name)] = results_tex.HEADER + body
        for phrase, words in results_tex.untranslated(body).items():
            log.warning("results: pt-BR table %s has no PT entry for %r (untranslated: %s)",
                        name, phrase, ", ".join(words))
        rendered[(tables_pt_dir, name)] = results_tex.HEADER + results_tex.to_pt(body)

    if check_only:
        drifted = [str(d / f"{n}.tex") for (d, n), body in rendered.items()
                   if not (d / f"{n}.tex").is_file()
                   or (d / f"{n}.tex").read_text(encoding="utf-8") != body]
        if updated != original or drifted:
            what = []
            if updated != original:
                what.append(str(doc_path))
            if drifted:
                what.append(f"stale tables: {', '.join(sorted(drifted))}")
            raise RuntimeError(
                "results --check: out of date with the artifacts -- " + "; ".join(what) +
                ". Run `pipeline run results` to regenerate.")
        log.info("results --check: %s and %d LaTeX tables are up to date (%d generated blocks)",
                 doc_path, len(rendered), len(filled))
        ctx.cache["results_summary"] = {
            "checked": True, "blocks": len(filled), "latex_tables": len(rendered)}
        return

    for (d, name), body in rendered.items():
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{name}.tex").write_text(body, encoding="utf-8")
    n_tables = len(rendered)

    figures_path.parent.mkdir(parents=True, exist_ok=True)
    write_artifact(figures, figures_path, stage="results",
                   params={"doc": str(doc_path), "tables": str(tables_dir),
                           "tables_pt": str(tables_pt_dir)})
    doc_path.write_text(updated, encoding="utf-8")

    summary = {
        "figures": str(figures_path), "doc": str(doc_path),
        "blocks": len(filled), "latex_tables": n_tables, "cells": figures.get("n_cells"),
        "models_trained": (figures.get("model_count") or {}).get("models_trained"),
        "clusterings": len((figures.get("cluster_counts") or {})),
    }
    ctx.cache["results_summary"] = summary
    log.info("results: %d markdown tables + %d LaTeX tables, from %d cells (%s models)",
             len(filled), n_tables, summary["cells"], summary["models_trained"])
