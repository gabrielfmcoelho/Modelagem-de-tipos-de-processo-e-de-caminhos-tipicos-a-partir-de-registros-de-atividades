# Leemans 2013 — Inductive Miner (block-structured, sound discovery)

**Citation.** Leemans, S. J. J., Fahland, D., & van der Aalst, W. M. P. (2013). Discovering Block-Structured
Process Models from Event Logs Containing Infrequent Behaviour. In *BPM 2013 Workshops*, LNBIP 171, Springer,
66–78.
**Link.** https://doi.org/10.1007/978-3-319-06257-0_6 · **Type.** classic · **Topic.** process discovery

## Why it matters to our work
The dominant process-discovery algorithm and a **direct theoretical mirror of our contribution**. The Inductive
Miner discovers models that are **"sound by construction"** — *no deadlocks*, and *the model always fits the log*.
That is exactly the guarantee our **grammar-constrained decoder** provides at *generation* time: every trace we
emit is structurally valid by construction. We can frame our work as bringing the Inductive Miner's
**soundness-by-construction** ideal from process *discovery* to neural process *generation*.

Its **infrequent-behaviour filtering** (IMf) also parallels our `coverage_floor` — both keep the "80% highway"
and drop noise.

## Key takeaways
- Recursive divide-and-conquer → block-structured, sound, fitting models; robust to noise (IMf).

## How we cite it
Related work (discovery baseline) **and** the framing of our validity guarantee as "soundness for generation".
