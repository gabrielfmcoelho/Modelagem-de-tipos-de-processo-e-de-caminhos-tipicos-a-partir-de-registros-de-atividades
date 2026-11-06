---
type: workflow
title: Document Acquisition and Parsing
description: How process documents are fetched from the SEI API and turned into text — the access-unit fallback strategy, the append-only outcome ledger that makes downloads idempotent, the filesystem stores, and the per-format parsers with their native-first PDF quality gate.
tags: [documents, sei-api, download, parsing, pdf, ocr, idempotency, ledger]
verified:
  - by: openwiki/0.5.0
    at: 2026-09-10T12:46:32.229Z
sources:
  - id: openwiki-source-106d8b3be3c2cf8fe0071557
    resource: repo://pipeline/core/doc_store.py
  - id: openwiki-source-46d076c21c138ceb9ec29c20
    resource: repo://pipeline/core/parsed_store.py
  - id: openwiki-source-dc64e3b77ba4721bd421cab9
    resource: repo://pipeline/core/sei_client.py
  - id: openwiki-source-a111ebd82b0d85bea33f64c4
    resource: repo://pipeline/model/parsing/__init__.py
  - id: openwiki-source-573dd6ef75963be6523eb46f
    resource: repo://pipeline/model/parsing/html.py
  - id: openwiki-source-06dcba1fa45b42b13041ff4c
    resource: repo://pipeline/model/parsing/pdf.py
  - id: openwiki-source-c77a737c70969b541c8af745
    resource: repo://pipeline/model/parsing/vision.py
  - id: openwiki-source-6d70ba84897161bc79d3f527
    resource: repo://pipeline/stages/document_funnel.py
  - id: openwiki-source-9e20f5ecb9a20575329d12ba
    resource: repo://pipeline/stages/download.py
  - id: openwiki-source-3317e9ce68b1e232876d6a29
    resource: repo://pipeline/stages/parse.py
generated: { by: "claude-code", at: "2026-09-10T12:46:32.229Z" }
---

# Document Acquisition and Parsing

The event log says *that* a document exists; it does not contain the document.
This workflow retrieves the files from the SEI API and converts them into plain
text that the downstream document, feature and clustering phases consume.

Both stages are honest about their reproducibility. `download` declares
`deterministic='conditional'` because the result depends on whether the document
is still available at call time, and `parse` declares `deterministic=False`
outright, because vision and OCR paths vary between identical runs.

## Acquiring documents

### Authentication

`sei_login` posts credentials and returns a token. Its failure handling is
deliberately blunt: invalid credentials, any non-200 response, and a response
missing the token field each log a specific message and terminate the process.
Transient network errors are the exception — connection and timeout failures
retry three times with linearly increasing backoff before giving up.

### The access-unit problem

A SEI document cannot simply be requested by number. The API serves it *on behalf
of an administrative unit*, and only a unit with access to that document will
succeed. The downloader therefore tries candidate units in order until one works.

`_sort_unidades` computes that order:

1. Candidates are restricted to units belonging to the caller's own agency,
   matched either exactly or by the `agency/` prefix.
2. The document's own creating unit is appended when it belongs to that agency
   and is not already present — it is the unit most likely to hold access.
3. The creator sorts first; the remainder sort by **descending historical success
   count**.

That third point makes the strategy adaptive. `success_stats` is a mutable
dictionary threaded through the run and incremented on every successful
download, so units that have worked before are tried earlier for subsequent
documents. Over a long run the ordering converges on the units that actually hold
access, reducing wasted requests.

### Failure taxonomy

The response body is inspected to distinguish failures that mean different
things:

- A body reporting the document was cancelled raises an internal cancellation
  signal that **abandons the remaining units immediately**. A cancelled document
  is cancelled for everyone, so continuing to try other units would be pure
  waste.
- A body reporting denied access moves to the next unit, recording the one that
  was tried.
- Any other non-200 also moves on, but without the specific classification.

The call returns a status of `ok`, `cancelled` or `failed` alongside the payload,
and the filename is recovered from the `content-disposition` header, falling back
to a synthesised name.

### The outcome ledger

`OutcomeLedger` is an append-only NDJSON log beside the downloaded files. Each
record carries a timestamp, the process and document numbers, the status, the
HTTP code, the units tried and a detail field.

On construction it replays the whole file and builds an in-memory map of
outcomes — but only for statuses it treats as **terminal**, which are `ok` and
`cancelled`. This distinction is the heart of the resumption behaviour:

> A **failed** download is not terminal and will be retried on the next run. A
> **cancelled** one is terminal and is never retried.

That is the correct split. A failure may be transient — the network, a busy
server, a unit ordering that had not yet learned — while a cancellation is a
permanent property of the document.

Writes take a lock, create the parent directory, append one JSON line, and update
the terminal map, so the ledger is safe to share across the worker threads.

### Per-process download

Each process is handled by one function with two independent skip gates: the
document store already holding bytes for that document, and the ledger reporting
it as known-cancelled. A process with no units at all is skipped wholesale with a
warning rather than attempted, and `dry_run` short-circuits after reporting what
would have been attempted.

Processes are downloaded in parallel through a thread pool sized by the
`workers` flag, and each worker opens its own HTTP client.

The stage soft-depends on `atividades`, since the document list is normally read
from the graph — but the dependency is soft because documents can also be named
directly with a process flag.

### The document store

`FsDocumentStore` lays files out as
`<base>/<protocolo>/<doc_numero>/<filename>`, with the protocol's slashes
replaced so it is a valid single directory name. `exists` is true when the
document directory exists **and is non-empty**, so an interrupted write that left
an empty directory does not mask a missing document.

The store is defined behind an abstract `DocumentStore` interface with `exists`
and `put`, which is what lets the download logic be exercised without touching a
real filesystem layout.

## Parsing to text

`parse` walks the downloaded tree and dispatches on file extension. Every parser
returns a `(text, method)` pair, and the method string records *how* the text was
obtained — this becomes the per-document provenance of the extraction. An
unsupported extension returns empty text with an `unsupported` method rather than
raising, so one unexpected file type cannot abort a batch.

| Extension group | Handler |
|---|---|
| `.html`, `.htm` | Boilerplate-stripping HTML parser |
| `.txt` | Direct read |
| `.pdf` | Native extraction with vision fallback |
| Images | Vision transcription |
| `.xlsx`, `.xls`, `.csv` | Spreadsheet serialisation |
| `.doc`, `.docx` | Document extraction |

### PDF: native first, behind a quality gate

The PDF path is the most interesting because it decides between a cheap
deterministic route and an expensive non-deterministic one.

Text is first extracted natively with `pdfplumber`, up to a page cap. That text
is then cleaned by `_strip_garbled_runs`, which removes runs of at least six
consecutive short tokens where half or more are single characters — the
signature of a broken text layer that yields letter-by-letter fragments rather
than words.

`_should_use_native` then applies three conditions, all of which must hold for
the native text to be accepted: at least one page was read, fewer than half the
tokens are single characters, and the text averages at least one hundred
characters per page. Failing any of them, the document is sent to vision
transcription instead.

There is a third outcome. When no model client is available, the native text is
returned regardless of quality, with the distinct method string
`pdf-native-no-client` — so a document parsed without the fallback available is
identifiable afterwards rather than silently indistinguishable from a good
native extraction.

### HTML boilerplate removal

Administrative HTML documents are dominated by letterhead, routing fields, a
dateline, signature blocks and footer addresses. The HTML parser strips these
through a sequence of targeted patterns so that what remains is the document
body. Several of those patterns are built from the deployment constants — the
agency domain in particular — so the boilerplate rules follow the same
configuration seam as the rest of the codebase.

### Vision transcription

The vision path encodes pages or images as base64 and sends them to an
OpenAI-compatible chat completion endpoint with a transcription system prompt.
Images are resized to a maximum dimension before encoding to bound request size,
and separate model settings exist for vision and text so the two can be pointed
at different models.

### The parsed store

Parsed output goes to a per-document directory containing `text.txt` and
`metadata.json`, with the anonymized variant added later alongside it.
`iter_parsed_documents` yields only directories that actually contain the
requested variant file, so a document that failed to parse is simply absent from
the iteration rather than surfacing as an empty or broken entry.

## Measuring attrition

`document-funnel` exists because this pipeline loses documents at every step —
some are cancelled, some fail to download, some parse to nothing, some produce no
entities. The stage counts survivors across downloaded, read, anonymized and
embedded, and writes the result as a stamped artifact with the loss declared at
each step.

Its own description records why: the attrition figures used to be counted by
hand with a shell command at the moment a report was written. Turning that into
a provenance-stamped artifact is the same discipline the artifact contract
imposes everywhere else.

## Related pages

- [Anonymization and Entity Extraction](anonymization-and-entity-extraction.md)
- [Ingest and Knowledge Graph Construction](ingest-and-graph-build.md)
- [Process Features and Clustering](features-and-clustering.md)
