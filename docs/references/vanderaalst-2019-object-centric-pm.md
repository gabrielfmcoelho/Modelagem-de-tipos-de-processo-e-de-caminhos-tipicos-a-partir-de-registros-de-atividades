# van der Aalst 2019 — Object-Centric Process Mining

**Citation.** van der Aalst, W. M. P. (2019). Object-Centric Process Mining: Dealing with Divergence and
Convergence in Event Data. In *SEFM 2019*, LNCS 11724, Springer, 3–25. (See also OCEL 2.0: Berti et al., 2023.)
**Link.** https://doi.org/10.1007/978-3-030-30446-1_1 · **Type.** recent (key conceptual shift) · **Topic.** process mining · case notion

## Why it matters to our work — the *protocolo ≠ process* distinction
**This is the reference for the nuance that a SEI `protocolo` is not always a complete end-to-end "process".**
Classic process mining assumes a **single case notion** — every event belongs to exactly one case, and a case is
a self-contained process instance. Object-centric process mining (OCPM) abandons that: an event relates to
**multiple objects** (documents, sub-protocolos, units), which causes **convergence** (one event counted for many
cases) and **divergence** (repeated activities within a case). A protocolo behaves like an *object* whose journey
may be a fragment, may spawn or join others, and is not guaranteed to be one tidy end-to-end flow.

In our work we **treat each protocolo as a single case** (the trace = its chronological activities) — a
*deliberate simplification* that OCPM lets us name honestly as a threat to validity, and that points to the
natural **future work**: an object-centric extension (OCEL) modeling document↔protocolo relations. It also
justifies our framing that **a protocolo is itself a *type* of process** which we cluster into process families.

## Key takeaways
- Single-case-notion ⇒ convergence/divergence distortions; OCEL/OCPM model events over multiple objects.

## How we cite it
Threats to validity + scope (our single-case simplification), terminology (protocolo as object/process-type),
and future work (object-centric extension).
