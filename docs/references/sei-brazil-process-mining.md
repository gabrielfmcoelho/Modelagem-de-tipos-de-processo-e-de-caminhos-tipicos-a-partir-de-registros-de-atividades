# SEI / Brazil — process mining of electronic administrative processes

**Domain anchor for the article.** Our object of study is **protocolos do SEI (Sistema Eletrônico de
Informações)** — the electronic document/process system that runs Brazilian public administration.

## Context (cite as background)
- **SEI** was developed by the **TRF4** (Tribunal Regional Federal da 4ª Região) and is provided free to the
  public administration as the chosen solution of the **Processo Eletrônico Nacional (PEN)** — a national
  infrastructure for electronic administrative processes and documents. *(processoeletronico.gov.br)*
- Adoption is driven by the **Lei de Acesso à Informação — Lei nº 12.527/2011 (LAI)**, which obliges public
  bodies to keep processes/documents available for electronic consultation — a **legal transparency mandate**
  that makes the SEI event log both available and *meant to be auditable*. This is the statutory bridge to
  *Artificial Intelligence and Law*.

## Comparable study (cite as related work)
**Análise de processos administrativos no setor público via mineração de processos: um estudo de caso no
Tribunal Regional Eleitoral do Tocantins.** *Revista DCS.*
**Link.** https://ojs.revistadcs.com/index.php/revista/article/view/4864 · **Type.** recent · Brazilian · SEI

- Extracts event logs **from SEI via SQL** + preprocessing (PowerShell/Python) — the same data path as ours.
- Discovers the **real (as-is) flow**, compares to an **ideal BPMN**, and analyzes performance/conformance.
- Findings: **hidden complexity + significant rework**, cycle time ~**3.38 weeks vs an ideal 8 days**, and
  **compliance deviations** — empirical validation that SEI process mining surfaces actionable transparency/
  efficiency findings.

## Why it matters to our work
This is the closest precedent: process mining of **SEI** administrative processes in a **Brazilian** public body.
It validates our pipeline (SEI log → discovery → as-is vs ideal → conformance) and lets us position our
contribution as a *generalization*: instead of one hand-built ideal BPMN per process, we **cluster** processo
types automatically and learn **validity-constrained generative models** of each — scaling the transparency
instrument across all of an organization's process families.

## How we cite it
Domain/motivation (SEI + PEN + LAI), related work (the TRE-TO case study), and the "what we add" delta
(clustering + learned, rule-valid models vs a single manual BPMN).
