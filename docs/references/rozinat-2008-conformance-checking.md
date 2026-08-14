# Rozinat & van der Aalst 2008 — Conformance Checking (de jure vs de facto)

**Citation.** Rozinat, A., & van der Aalst, W. M. P. (2008). Conformance checking of processes based on
monitoring real behavior. *Information Systems*, 33(1), 64–95.
**Link.** https://doi.org/10.1016/j.is.2007.07.001 · **Type.** classic · **Topic.** conformance checking

## Why it matters to our work — norms exist but aren't enforced
**This is the theory of the gap we study.** The SEI has **norms governing the procedural flow, but they are not
technically enforced and do not cover every procedure** — so the *de jure* model (what should happen) and the
*de facto* behavior (what the log shows) diverge. Conformance checking is exactly the discipline that **quantifies
that divergence**: *fitness* (does the observed behavior comply with the model?) and *appropriateness* (does the
model suitably describe reality?).

Two direct connections: (1) we do **as-is** discovery — we model the *de facto* process from the log, not the
prescribed one — which is the only auditable artifact when norms aren't enforced. (2) Our **`FlowState` validity
rules are a minimal de jure model**, and our **`validity_score`** (fraction of a trace's steps that obey them) is
a lightweight **fitness** measure — so our constrained generation closes the conformance gap by *construction*
(generating only fitting traces).

## Key takeaways
- Fitness + appropriateness metrics; Petri-net alignment of log vs model (ProM Conformance Checker).

## How we cite it
Framing (de jure vs de facto), method (validity_score as a fitness analogue), and motivation for as-is modeling.
