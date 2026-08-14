from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from ...core.paths import ROOT
from ..etl.blocks import fig_corpus_bias
from ..clustering.blocks import _downstream_spread, _spread_interval, fig_ablation, fig_cluster_counts, fig_common_set, fig_coverage, fig_index_mechanism, fig_intrinsic, fig_noise_difficulty, fig_selection, fig_taxonomy
from ..typical_path.blocks import LOWER_IS_BETTER, MODELS, _combo_table, fig_bands, fig_combos, fig_combos_full, fig_controls, fig_dispersion, fig_flow_validity, fig_model_profile, fig_model_vs_medoid, fig_noninferiority, fig_scale, fig_size_trend
from ..shared.doc import _PENDING, _n, _table, fig_glossary


FIGURES = ROOT / "artifacts" / "stats" / "results_figures.json"


RESULTS = ROOT / "docs" / "research" / "RESULTS.md"


BLOCKS = {
    "noninferiority": fig_noninferiority,
    "index_mechanism": fig_index_mechanism,
    "glossary": fig_glossary,
    "flow-validity": fig_flow_validity,
    "taxonomy": fig_taxonomy,
    "selection": fig_selection,
    "combos-full": fig_combos_full,
    "common-set": fig_common_set,
    "noise-difficulty": fig_noise_difficulty,
    "corpus-bias": fig_corpus_bias,
    "combos": fig_combos,
    "model-profile": fig_model_profile,
    "size-trend": fig_size_trend,
    "intrinsic": fig_intrinsic,
    "ablation": fig_ablation,
    "cluster-counts": fig_cluster_counts,
    "model-vs-medoid": fig_model_vs_medoid,
    "controls": fig_controls,
    "bands": fig_bands,
    "dispersion": fig_dispersion,
    "scale": fig_scale,
    "coverage": fig_coverage,
}


def render(doc: str, figures: dict) -> tuple[str, list[str]]:
    filled = []
    for name, fn in BLOCKS.items():
        pattern = re.compile(
            rf"<!-- fig:{re.escape(name)} -->.*?<!-- /fig:{re.escape(name)} -->",
            re.DOTALL)
        if not pattern.search(doc):
            continue
        body = fn(figures)
        doc = pattern.sub(
            lambda m: f"<!-- fig:{name} -->\n{body}\n<!-- /fig:{name} -->".replace("\\", "\\\\"),
            doc)
        filled.append(name)
    return doc, filled


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--figures", default=str(FIGURES))
    ap.add_argument("--doc", default=str(RESULTS))
    ap.add_argument("--check", action="store_true",
                    help="exit non-zero if the doc is out of date instead of rewriting it")
    args = ap.parse_args()

    figures = json.loads(Path(args.figures).read_text(encoding="utf-8"))
    doc_path = Path(args.doc)
    original = doc_path.read_text(encoding="utf-8")
    updated, filled = render(original, figures)

    missing = sorted(set(BLOCKS) - set(filled))
    if args.check:
        if missing:
            print(f"MARKERS MISSING in {doc_path}: {missing} — nothing to verify for those blocks")
            return 1
        if updated != original:
            print(f"OUT OF DATE: {doc_path} does not match {args.figures}")
            return 1
        print(f"up to date ({len(filled)} generated blocks)")
        return 0

    doc_path.write_text(updated, encoding="utf-8")
    print(f"wrote {doc_path}: {len(filled)} blocks regenerated"
          + (f"; markers absent for {missing}" if missing else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
