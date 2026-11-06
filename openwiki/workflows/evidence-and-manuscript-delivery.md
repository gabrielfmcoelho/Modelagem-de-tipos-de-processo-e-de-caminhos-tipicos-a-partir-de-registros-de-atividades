---
type: workflow
title: Evidence Composition and Manuscript Delivery
description: How stage outputs become the numbers, tables and figures the manuscripts cite — the aggregation envelope that refuses incomplete denominators, the three-way generate-or-verify results gate, bilingual LaTeX table generation, and the blinding that protects the double-blind build.
tags: [evidence, delivery, manuscript, latex, blinding, aggregation, reproducibility]
verified:
  - by: openwiki/0.5.0
    at: 2026-09-10T12:46:32.229Z
sources:
  - id: openwiki-source-291e33cbff67328cc75901ca
    resource: repo://pipeline/evidence/compose/envelope.py
  - id: openwiki-source-29133385fa93ec69c5e2c181
    resource: repo://pipeline/evidence/results/results_doc.py
  - id: openwiki-source-0d9a61c1d74cf55e4097bd27
    resource: repo://pipeline/evidence/results/results_tex.py
  - id: openwiki-source-8ebd8c4acca633813839cbd3
    resource: repo://pipeline/evidence/shared/blind.py
  - id: openwiki-source-f8a01b05a1aa75534536509b
    resource: repo://pipeline/evidence/stage_doc.py
  - id: openwiki-source-b6b9cd1549f53750310779e7
    resource: repo://pipeline/stages/compose_evidence.py
  - id: openwiki-source-a01c40ac0ec64656d7702d41
    resource: repo://pipeline/stages/noninferiority.py
  - id: openwiki-source-d24e90308282cb21e387469a
    resource: repo://pipeline/stages/results.py
generated: { by: "claude-code", at: "2026-09-10T12:46:32.229Z" }
---

# Evidence Composition and Manuscript Delivery

This is the last phase, and the one the whole provenance apparatus exists to
serve: turning per-cell artifacts into the tables, figures and numbers that
appear in two manuscripts. The design principle throughout is that **a number
must be traceable to the artifact that produced it, and an aggregate must be
honest about what it left out**.

## The aggregation envelope

`pipeline/evidence/compose/envelope.py` defines the shape every composed
artifact takes: a `scope` naming its point in the experimental grid, a
`population` naming the case set it covers, a `members` block naming what it
aggregated, and the `results` themselves.

Two of those four are enforced by refusing to build otherwise.

**Members must be complete.** `members_block` compares expected against present
members and raises `IncompleteAggregate` when any are missing, unless the caller
explicitly declares that omission. The message states the failure mode directly:
an aggregate is over all of its level or it declares the omission, because a
silently shorter denominator is how a skipped evaluation cell becomes a headline
number. An interrupted GPU run cannot quietly produce a mean over the cells that
happened to finish.

**Populations must be named and defined.** `population_block` rejects a
population that is neither one of the six declared case sets nor accompanied by
its own definition, on the stated grounds that the population is the most
consequential choice in any comparison here and must not be left implicit in a
key name.

The declared populations are themselves informative. `main-cells`, for instance,
excludes both the shuffled controls and the ablation variants, so that an
arm-versus-arm or model-versus-model difference cannot be confounded with a run
that was deliberately degraded.

`compose-evidence` uses this to derive the composed layers from the raw
evaluation cells — per-arm summaries, agreement between clusterings, per-cluster
indices, per-model and per-alphabet slices, and the cross-cutting comparisons —
each carrying its grid point, population and member list.

## The results gate

`results` is the single stage that renders evidence into publishable form, and it
produces three outputs that must agree:

1. `artifacts/stats/results_figures.json` — the aggregated figures artifact;
2. the generated table blocks inside `docs/research/RESULTS.md`;
3. the LaTeX tables under both `article/latex/tables/` and
   `article/latex-ptbr/tables/`.

It refuses to run at all when no evaluation cells are found, because proceeding
would regenerate every table as empty and silently erase the results.

### Marker discipline

`RESULTS.md` carries paired markers of the form
`<!-- fig:NAME -->` … `<!-- /fig:NAME -->`, and rendering replaces the content
between them. The rendering function fills only the blocks whose markers are
present — and the stage then requires that **every** registered block was filled,
raising with the names of the missing ones.

The effect is that a table cannot be quietly retired by deleting its marker.
Either the marker exists and the block is regenerated and checked, or the block
is removed from the registry deliberately. A LaTeX table that renders empty is
likewise a hard failure rather than an empty tabular in the manuscript.

### Generate or verify

The same stage runs in two modes. By default it writes the figures artifact,
rewrites the markdown blocks, and writes both LaTeX table sets.

With `--flag check=true` it renders everything in memory and compares: if the
markdown would change, or any table file is absent or differs, it raises naming
what is stale and telling the operator to regenerate. Nothing is written. This is
the form used in CI, and it is what makes "the tables are current" a checkable
statement rather than a claim.

Every generated `.tex` file carries a header comment declaring it generated by
this command and not to be edited by hand.

## Two manuscripts, one source of numbers

The repository produces two write-ups of the same study with **opposite identity
requirements** — a double-blind English submission and an identified Portuguese
thesis. Both draw their numbers from the same figures artifact.

### Bilingual tables

Each table body is rendered once and then translated. `to_pt` protects LaTeX
macros and cross-references by replacing them with placeholders, substitutes
known phrases from a translation dictionary, converts numeric formatting to
Portuguese conventions, restores the protected spans, and adjusts layout for
tables registered as wide.

Translation coverage is checked rather than assumed. `untranslated` extracts
captions, header cells and notes, removes every span that has a dictionary entry,
and reports whatever words remain. The stage logs these as warnings — coverage
gaps are surfaced without blocking generation.

### Blinding

`pipeline/evidence/shared/blind.py` protects the double-blind build with two
mechanisms.

A string containing any identifying token — the agency acronym, the state name,
the capital city — is replaced wholesale with an explicit redaction marker.
Otherwise, uppercase acronym tokens that match known administrative unit
acronyms are individually replaced with `[unit]`, preserving the rest of the
string.

The acronym set is not hard-coded. It is derived from the exported traces
artifact by splitting the lane component of each state. And when that artifact is
missing, `_unit_acronyms` **raises rather than proceeding** — the error message
explains exactly why: without it the blind manuscript would be built with the
acronyms intact and nothing would report the failure. This is a control that
fails closed, which is the correct behaviour for an anonymity guarantee.

## Guarding the claims

Several evidence-phase stages exist to test the published claims rather than to
produce them.

`noninferiority` runs a process-by-process paired bootstrap between the raw and
anonymized arms against a **pre-registered** margin, declaring itself
conditionally deterministic with the seed recorded in its artifact parameters.
Pre-registering the margin is what prevents the threshold from being chosen after
seeing the result.

`ablation` and `temporal-holdout` provide the feature-contribution and
out-of-period comparisons, and `cluster-control` supplies the shuffled null that
several tables report alongside the real partition.

The last link is `pipeline/tests/test_manuscript_claims.py`, which asserts that
the numbers actually printed in both manuscripts still match the figures
artifact, including their signs and their required companion figures.

## Generated documentation

`pipeline/evidence/stage_doc.py` generates the stage registry reference from the
live registry. It emits a header declaring the file generated and directing
editors to change the stage and regenerate, then produces the phase view, a full
stage table, and — separately — a **sources of non-determinism** table listing
every stage that is not fully deterministic together with its recorded reason.

That last table is the readable face of the `deterministic` and `nondeterminism`
fields carried through the registry, the ledger and every artifact envelope. The
document also defines the three levels precisely: `true` means byte-identical
output for identical inputs and parameters, `conditional` means deterministic
given the seed the stage records in its artifact, and `false` means the output
varies between runs and therefore informs interpretation without pinning a
number.

## Related pages

- [Artifact Provenance and Audit](../concepts/artifact-provenance-and-audit.md)
- [Experiment Arms and Run Identifiers](../concepts/experiment-arms-and-run-ids.md)
- [Typical Path Discovery and Evaluation](typical-path-discovery.md)
