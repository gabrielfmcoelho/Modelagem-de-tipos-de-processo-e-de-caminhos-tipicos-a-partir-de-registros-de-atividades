---
type: workflow
title: Anonymization and Entity Extraction
description: How document text is stripped of personal data — checksum-validated identifier detection, NER-driven span replacement with deterministic pseudonyms, the raw and anonymized text variants that feed the two experiment arms, and how extracted entities are loaded into the graph.
tags: [anonymization, pii, ner, privacy, gliner, pseudonymization, knowledge-graph]
verified:
  - by: openwiki/0.5.0
    at: 2026-09-10T12:46:32.229Z
sources:
  - id: openwiki-source-c37e321ec9e930656644b57b
    resource: repo://pipeline/core/constants.py
  - id: openwiki-source-b6751b42503d1b300864fa4a
    resource: repo://pipeline/core/cypher/ner.py
  - id: openwiki-source-46d076c21c138ceb9ec29c20
    resource: repo://pipeline/core/parsed_store.py
  - id: openwiki-source-78cb3d35a87f93ebdf4712cb
    resource: repo://pipeline/model/anonymize.py
  - id: openwiki-source-dee5c2604c055c2a84117aad
    resource: repo://pipeline/model/ner/gliner.py
  - id: openwiki-source-fba8db829ee9ed8d365c15b5
    resource: repo://pipeline/stages/anonymize.py
  - id: openwiki-source-c1089d915617e9dde125c0f7
    resource: repo://pipeline/stages/ner_extract.py
  - id: openwiki-source-877fd7aaa8d6a5b55e9d8795
    resource: repo://pipeline/stages/ner_load.py
  - id: openwiki-source-e12cf62e7ad435ff12930f7c
    resource: repo://pipeline/tests/test_anonymize.py
  - id: openwiki-source-6981a9528fa786708564ab18
    resource: repo://pipeline/tests/test_no_comments.py
generated: { by: "claude-code", at: "2026-09-10T12:46:32.229Z" }
---

# Anonymization and Entity Extraction

Administrative process documents are full of personal data: names, national
identifiers, staff registration numbers, addresses. This workflow produces a
second text variant per document in which that data has been replaced by
deterministic typed placeholders, and separately loads the non-personal entities
it finds into the knowledge graph.

The anonymized variant is not a side product. It is what makes the `exp-anon`
experimental arm possible: the same corpus, represented without identifying
detail, so the study can measure what anonymisation costs the downstream
analysis.

## Two detection sources

`anonymize` combines two independent detectors and concatenates their results.

### Validated identifiers

`regex_entities` finds structured identifiers with patterns, but **accepts a
candidate only when its check digits validate**. `cpf_valid` and `cnpj_valid`
implement the Brazilian checksum algorithms and additionally reject
all-same-digit sequences, which are structurally valid but are placeholder
values in practice.

This choice is deliberate precision over recall for bare digit runs: an
eleven-digit protocol number that is not a valid CPF is left in the text rather
than redacted. The test suite pins exactly this — a text containing
`protocolo 12345678901` yields no entities at all.

Both formatted and bare forms are matched, with lookaround guards preventing a
match inside a longer digit run. Email addresses are matched by pattern alone.
Staff registration numbers require the literal keyword `matrícula` in context
*and* at least five digits in the captured span, since the number alone is
indistinguishable from any other identifier.

### Model-proposed spans

`ner_entities` consumes the payload written by `ner-extract` and filters it
through three gates before a span becomes redactable:

1. The raw label must map through `LABEL_TO_KEY` and then `NER_KEY_TO_LABEL` to a
   known placeholder class; anything unrecognised is dropped rather than guessed
   at. The mapping is deliberately wide, folding a long tail of document types
   — RG, CNH, PIS/PASEP, OAB, bank accounts, vehicle plates — into a single
   `DOCUMENTO` class.
2. The span must be at least three characters.
3. **The span must actually occur in the source text**, compared case-folded.
   This is a hallucination guard: a model that proposes an entity not present in
   the document cannot cause a spurious replacement.

## Deterministic pseudonyms

A placeholder looks like `<PESSOA_a1b2c3d4>`: the class name plus the first eight
hex characters of a SHA-256 over `label|canonical_key`.

The canonical key is computed differently per class. Digit-bearing labels are
reduced to their digits plus `X`, uppercased — so `529.982.247-25` and
`52998224725` collapse to one key. Text labels are NFKD-normalised, stripped of
combining marks, whitespace-collapsed and case-folded — so accents, casing and
spacing variations of a name converge.

Two properties follow. The same person receives the **same placeholder across
every document**, which preserves co-occurrence structure for analysis. And
because the mapping is a one-way hash of the canonical form, the placeholder
alone does not recover the original.

## The replacement algorithm

`anonymize_text` does not substitute in document order. It sorts entities by
**descending span length** (then label, then text) and processes them
longest-first, recording each accepted match as a claimed interval. A match that
overlaps an already-claimed interval is skipped.

That ordering is what keeps replacements coherent. If a document contains both a
full name and its surname as separate entities, the full name is claimed first
and the surname match inside it is rejected, rather than a shorter entity
corrupting a longer one.

Each label class gets boundary guards appropriate to it: digit classes assert no
adjacent digit on either side, emails assert their own character class
boundaries, and everything else uses word boundaries. Matching is
case-insensitive. Once all intervals are claimed they are sorted and the output
is assembled in one pass, so the original text is never mutated in place.

## The stage

`anonymize` runs in `fs` mode, hard-depends on `parse` and **soft**-depends on
`ner-extract`. The soft dependency is the design point: the stage runs without
NER results and records that it did.

It writes two files per document beside the parsed text — `text_anon.txt` and
`anon_meta.json` — using the variant filenames that `parsed_store` defines, so
downstream consumers select an arm by asking for the `raw` or `anon` variant
rather than by resolving different directories.

### Content-addressed incrementality

Beyond the stage-level checkpoint, `anonymize` keeps its own per-document skip
rule: a document is reprocessed unless the existing metadata records both the
same source text digest **and** the same NER payload digest. Producing new NER
results therefore regenerates exactly the affected documents on the next run,
without a full-stage force.

### Degradation and self-check

Failures degrade rather than abort. An unreadable or malformed NER payload is
logged and that document proceeds regex-only; a missing NER directory warns once
and puts every document on that path. Each document's metadata records
`ner_available`, and the stage summary counts how many were `degraded`, so a
run's coverage is auditable after the fact.

With `--flag verify=true` the stage re-runs the regex detectors **against its own
anonymized output** and counts residual hits, logging them at error level and
accumulating them in the summary. This is the stage's own check on the guarantee
it exists to provide.

## Entity extraction

`ner-extract` runs GLiNER2 over parsed text. Its labels are not short tags but
natural-language descriptions carrying examples — `"nome completo de pessoa
física, ex: João Silva, Maria de Souza"` — which is how a zero-shot extractor is
steered. The examples interpolate the deployment constants, so the institution
names in the prompts follow the same seam as the rest of the codebase.

Long documents are chunked with overlap so an entity spanning a chunk boundary is
still seen, and results are deduplicated with a merge that keeps the longest
surface form and absorbs entries that are prefixes of one another.

The stage declares `deterministic='conditional'`, with the recorded reason that
output is fixed only while the GLiNER2 model version is unchanged.

> **Maintenance note.** The twenty-one-label taxonomy is defined once in
> `pipeline/core/constants.py` as `LABEL_TO_KEY`, from which `ENTITY_LABELS` is
> derived — and then duplicated as a literal `DEFAULT_LABELS` list in *both*
> `pipeline/model/ner/gliner.py` and `pipeline/stages/ner_extract.py`. The three
> lists are currently identical, but nothing enforces that: the repository's
> registry-coverage invariant test watches the model and alphabet registries, not
> this one.

## Loading entities into the graph

`ner-load` attaches extracted entities to `Documento` nodes. It writes
scalar and list findings — emails, identifiers, monetary values, dates,
addresses, document type and subject — directly as properties, and creates
relationships for the entity classes that deserve their own nodes.

Person, organisation, role, legislation and contract nodes are keyed on a
normalised name with uniqueness constraints, and are merged rather than created.
The merge carries a surface-form rule: on match, the stored display name is
replaced only when the incoming one is **longer**, so an abbreviated mention does
not overwrite a fuller one already recorded.

Each relationship records a `fonte` property defaulting to `gliner`, keeping the
provenance of a graph edge distinguishable from edges built out of the event log.

The stage soft-depends on `atividades`, since the `Documento` nodes it matches
are created by the graph phase — running it first simply matches nothing rather
than failing.

## Related pages

- [Document Acquisition and Parsing](document-acquisition-and-parsing.md)
- [Experiment Arms and Run Identifiers](../concepts/experiment-arms-and-run-ids.md)
- [Configuration and Deployment Seams](../architecture/configuration-and-deployment-seams.md)
