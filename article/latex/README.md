# `latex/` — the manuscript (Springer, double-blind)

`main.tex` = preamble + `\input{sections/*}` + `\input{tables/*}`. Sections are written
separately so they can be drafted and revised independently.

## Building

1. **Overleaf**: upload this whole `article/latex/` folder (New Project → Upload Project) and set
   `main.tex` as the main document. `main.tex` alone will not build — it `\input`s `sections/`
   and `tables/`.
2. **Figures**: `\graphicspath` resolves `../figures/`, which works in a local build but not on
   Overleaf. The manuscript references exactly one figure — copy
   `article/figures/pipeline-macro-en.pdf` into a `figures/` subfolder before uploading.
3. **Compiler**: pdfLaTeX with the Springer Nature `sn-jrnl` class
   (`\documentclass[sn-mathphys-num]{sn-jrnl}`). If Overleaf lacks `sn-jrnl`, comment that first
   `\documentclass` line and uncomment the `article` fallback right below it — the built-in shim
   makes the same source compile.
4. **Run order** is BibTeX-based: pdfLaTeX → BibTeX → pdfLaTeX ×2 (Overleaf does this
   automatically on Recompile). Locally: `latexmk -pdf main.tex`.
5. **Before submission**: resolve the remaining `% TODO verify` in `references.bib`, and keep the
   manuscript anonymized (no institution sigla, no author names) for double-blind review.

The PT-BR/ABNT deliverable is a separate build: `article/latex-ptbr/`, `article` class +
`abntex2cite`, same `latexmk -pdf main.tex`. It is **not** anonymized.

## Binding documents, in order of authority

1. `docs/paper/PAPER-MAP.md` — contributions, RQs, guardrails. **§0 holds the
   forbidden-numbers table**: figures from the retired study (12,257 processos, 182
   clusters, DBCV 0.558, five feature blocks, no controls) must never appear here. They still
   live in git history and in `docs/architecture/algorithms.md` / `docs/research/RESULTS.md`.
2. `docs/research/RESULTS.md` — the only numeric source (20 generated tables)
3. `docs/paper/OUTLINE.md` — structure and word budget
4. `docs/paper/ARGUMENT.md` — claim chains, ordering constraints, counter-arguments
