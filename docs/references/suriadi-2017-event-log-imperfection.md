# Suriadi 2017 — Event Log Imperfection Patterns

**Citation.** Suriadi, S., Andrews, R., ter Hofstede, A. H. M., & Wynn, M. T. (2017). Event log imperfection
patterns for process mining: Towards a systematic approach to cleaning event logs. *Information Systems*, 64,
132–150.
**Link.** https://doi.org/10.1016/j.is.2016.07.011 · **Type.** classic (data-quality) · **Topic.** event-log quality

## Why it matters to our work
**The data-quality backbone of our methodology section.** It catalogs **11 recurring event-log imperfection
patterns** (e.g. *form-based event capture*, *inadvertent time travel*, *unanchored / scattered events*,
*collateral events*) — precisely the kinds of dirt a low-enforcement SEI produces. It frames event-log cleaning
as a **necessary, systematic** step rather than ad-hoc preprocessing, which legitimizes (and lets us document
honestly) our cleaning choices: parsing/header-scrubbing, the `situacao` open/closed derivation, the
**concluded-only** filter for the timeline models, and the `lane_depth` granularity decision.

## Key takeaways
- Event-log quality is decisive for process-mining validity; a pattern repository makes cleaning reproducible.

## How we cite it
Methodology / threats-to-validity: justifying and documenting our log-cleaning and the concluded-only filter on a
dirty SEI log.
