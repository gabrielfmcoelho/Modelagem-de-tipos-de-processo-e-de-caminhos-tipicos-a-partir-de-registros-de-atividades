# Pesic 2007 — DECLARE: Declarative Process Constraints

**Citation.** Pesic, M., Schonenberg, H., & van der Aalst, W. M. P. (2007). DECLARE: Full Support for
Loosely-Structured Processes. In *EDOC 2007*, IEEE, 287–298.
**Link.** https://doi.org/10.1109/EDOC.2007.14 · **Type.** classic · **Topic.** conformance · declarative constraints

## Why it matters to our work
Our `FlowState` validity machine is, in effect, a small set of **declarative constraints** over administrative
events — *"a RECEBIDO must be preceded by a pending REMETIDO"*, *"exactly one GERAÇÃO"*, *"conclude only an open
lane"*. DECLARE is the canonical formalism for exactly this: rules that an execution must not violate, under an
open-world assumption. It is the BPM-side theoretical grounding for our grammar-constrained decoder.

## Key takeaways
- Constraint templates (existence, response, precedence, …) define *allowed* behavior negatively (what must not
  happen) — our `.allows(state)` predicate is a precedence/existence constraint set.

## How we cite it
Theory: framing `FlowState` as declarative constraints; bridge between conformance checking and constrained
generation.
