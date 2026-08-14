# Literature for the *Artificial Intelligence and Law* submission — legal & governance framing

**Purpose.** `latex/references.bib` is strong on method (process mining, clustering, NLP
anonymisation) and thin on law: its only legal entries are three statutes plus three Brazilian
compliance papers. This file fills that gap. Everything here is **new relative to the existing
bib** unless explicitly marked.

**Verification protocol.** Every DOI below was resolved against the **Crossref REST API**
(`api.crossref.org/works/<doi>`) and the returned title, author list, journal, volume, issue and
page range were compared to the entry. Items *without* a DOI were verified against the publisher's,
the law school repository's, or the issuing institution's own page. Nothing here is written from
memory. **Four candidate DOIs encountered during searching resolved to entirely unrelated papers
and were discarded** rather than reported — that is why the protocol exists, and the near-misses
are documented at the end.

**Read the year field carefully.** Springer journals assign a volume year that often differs from
the Crossref "issued" (online-first) year. Where they differ, the BibTeX below uses the
**volume year**, which is the canonical citation, and the discrepancy is flagged inline.

**Tags.** `[DOCTRINAL]` = legal-doctrinal / normative argument · `[EMPIRICAL]` = data or
study-based · `[CONCEPTUAL]` = framework / critical-theoretical · `[METHOD]` = method or
benchmark contribution. `★ AI&Law` marks papers in the target journal; `☆ ICAIL` marks its sister
conference.

> ## ⚠ Read this first — one finding changes a novelty claim
>
> `references-candidates.md` currently records, as a KEY FINDING, that there is **"no prior work"**
> on the impact of anonymisation on **clustering quality**. That is **no longer safe to assert.**
>
> **Ferrão, Prata & Fazendeiro (2022), *Scientific Data* 9, `10.1038/s41597-022-01561-6`** clusters
> a real administrative cohort, re-clusters it after k-anonymity and differential privacy, and
> compares the solutions using Silhouette, Davies–Bouldin **and Calinski–Harabasz** — three of the
> exact indices in our pipeline. See §4.10. The novelty claim must be **narrowed before submission**
> (see the rewrite offered there). A reviewer who finds this paper after we claim priority is the
> worst possible outcome; finding it ourselves and differentiating precisely is a strength.

---

## Contents

1. [Algorithmic transparency & explainability in public administration](#1)
2. [Efficiency, reasonable duration & the right to good administration](#2)
3. [Auditability, accountability by design & access-to-information](#3)
4. [Anonymisation, re-identification & the privacy–utility trade-off](#4)
5. [Empirical & computational legal studies of procedure](#5)
6. [The venue itself — *Artificial Intelligence and Law*](#6)
7. [Primary legal sources — verified, with one hazard flagged](#7)
8. [How to position this paper for AI&Law reviewers](#8)
9. [Verification ledger](#9)

---

<a name="1"></a>
## 1. Algorithmic transparency & explainability in public administration

The core of this section is a distinction the paper should adopt explicitly: **transparency as
*disclosure* versus transparency as *intelligibility***. The literature is close to unanimous that
disclosure alone fails. That is the argumentative space our catalog occupies.

### 1.1 Ananny & Crawford (2018) — the limits of the transparency ideal `[CONCEPTUAL]`

```bibtex
@article{ananny2018seeing,
  author  = {Ananny, Mike and Crawford, Kate},
  title   = {Seeing without knowing: limitations of the transparency ideal and its
             application to algorithmic accountability},
  journal = {New Media \& Society},
  volume  = {20},
  number  = {3},
  pages   = {973--989},
  year    = {2018},
  doi     = {10.1177/1461444816676645}
}
```

Accountability regimes have historically assumed that *seeing* a system equals *knowing* and
therefore *governing* it. The authors interrogate that assumption, enumerate ten specific limits of
transparency applied to algorithmic systems, and sketch an accountability typology built from
engaging those limits rather than from disclosure alone.

**Use for us.** The canonical warrant for the paper's central move: publishing a normative process
model (or a raw log) is "seeing without knowing"; an as-is catalog of process types with typical
paths is an attempt at *knowing*. Cite the first time the word "transparency" appears.

### 1.2 Wachter, Mittelstadt & Floridi (2017) — no right to explanation `[DOCTRINAL]`

```bibtex
@article{wachter2017right,
  author  = {Wachter, Sandra and Mittelstadt, Brent and Floridi, Luciano},
  title   = {Why a right to explanation of automated decision-making does not exist
             in the {General Data Protection Regulation}},
  journal = {International Data Privacy Law},
  volume  = {7},
  number  = {2},
  pages   = {76--99},
  year    = {2017},
  doi     = {10.1093/idpl/ipx005}
}
```

Widely-repeated claims that the GDPR creates a "right to explanation" rest on a weaker textual
foundation than assumed; what the Regulation secures is closer to a limited right to be informed,
with the stronger formulation confined to a non-binding recital.

**Use for us.** Establishes that *legally compelled* explanation is thin and contested — which is
why voluntarily produced, evidence-based transparency artefacts have independent value.

### 1.3 Selbst & Powles (2017) — the rebuttal `[DOCTRINAL]`

```bibtex
@article{selbst2017meaningful,
  author  = {Selbst, Andrew D. and Powles, Julia},
  title   = {Meaningful information and the right to explanation},
  journal = {International Data Privacy Law},
  volume  = {7},
  number  = {4},
  pages   = {233--242},
  year    = {2017},
  doi     = {10.1093/idpl/ipx022}
}
```

The direct reply: "meaningful information about the logic involved" does create a functional
explanation right, and the dispute turns on what counts as meaningful to a data subject.

**Use for us.** **Cite as a pair with 1.2.** Presenting a live doctrinal dispute rather than picking
a side is the cheapest credibility win available to a technically-led paper at a law venue.

### 1.4 Edwards & Veale (2017) — explanation is the wrong remedy `[DOCTRINAL]` *(no DOI)*

```bibtex
@article{edwards2017slave,
  author  = {Edwards, Lilian and Veale, Michael},
  title   = {Slave to the algorithm? {Why} a `right to an explanation' is probably not
             the remedy you are looking for},
  journal = {Duke Law \& Technology Review},
  volume  = {16},
  number  = {1},
  pages   = {18--84},
  year    = {2017}
}
```

Even granting an explanation right, it is a poor remedy: individual-level explanation is
structurally mismatched to systemic algorithmic harms. The authors redirect to system-level
instruments — impact assessments, privacy by design, portability.

**Use for us.** Their pivot from individual explanation to *system-level, documentation-based*
accountability is exactly the register a process catalog operates in.
**Verified at** `https://scholarship.law.duke.edu/dltr/vol16/iss1/2/`. No DOI on the published
version; SSRN preprint `10.2139/ssrn.2972855` exists but **cite the journal version**.

### 1.5 Cobbe (2019) — administrative law and automated government `[DOCTRINAL]`

```bibtex
@article{cobbe2019administrative,
  author  = {Cobbe, Jennifer},
  title   = {Administrative law and the machines of government: judicial review of
             automated public-sector decision-making},
  journal = {Legal Studies},
  volume  = {39},
  number  = {4},
  pages   = {636--655},
  year    = {2019},
  doi     = {10.1017/lst.2019.9}
}
```

No settled account exists of how administrative law applies to public-sector ML systems. Cobbe
combines administrative law, data protection and a technical account of ADM to set out what a
reviewing court should ask and weigh.

**Use for us.** Grounds the claim that **reviewability of administrative action presupposes an
intelligible record of how it actually proceeded** — the thing our catalog reconstructs.

### 1.6 Oswald (2018) — old doctrine for new tools `[DOCTRINAL]`

```bibtex
@article{oswald2018algorithm,
  author  = {Oswald, Marion},
  title   = {Algorithm-assisted decision-making in the public sector: framing the issues
             using administrative law rules governing discretionary power},
  journal = {Philosophical Transactions of the Royal Society A},
  volume  = {376},
  number  = {2128},
  pages   = {20170359},
  year    = {2018},
  doi     = {10.1098/rsta.2017.0359}
}
```

Long-standing administrative law rules constraining discretionary state power (relevancy,
fettering of discretion, delegation, duty to give reasons) already supply a regulatory vocabulary
for algorithm-assisted public decisions.

**Use for us.** **Direct precedent for our principles-based framing** — evaluate against existing
administrative principles rather than invent bespoke criteria. This is the paper to cite when
justifying *why* we anchor on CF art. 37 instead of on deadlines.

### 1.7 Finck (2020) — ADM and administrative law, comparative `[DOCTRINAL]`

```bibtex
@incollection{finck2020automated,
  author    = {Finck, Mich\`ele},
  title     = {Automated decision-making and administrative law},
  booktitle = {The {Oxford} Handbook of Comparative Administrative Law},
  publisher = {Oxford University Press},
  pages     = {655--676},
  year      = {2020},
  doi       = {10.1093/oxfordhb/9780198799986.013.39}
}
```

Handbook treatment of how ADM interacts with core administrative-law guarantees across
jurisdictions.

**Use for us.** A single citable anchor for the comparative claim — useful because a Brazilian
setting needs a bridge to an international readership. *(Crossref returns no editor list for the
chapter record; add editors from the printed volume if your style demands them.)*

### 1.8 Suksi (2021) — administrative due process and ADM `★ AI&Law` `[DOCTRINAL]`

```bibtex
@article{suksi2021administrative,
  author  = {Suksi, Markku},
  title   = {Administrative due process when using automated decision-making in public
             administration: some notes from a {Finnish} perspective},
  journal = {Artificial Intelligence and Law},
  volume  = {29},
  number  = {1},
  pages   = {87--110},
  year    = {2021},
  doi     = {10.1007/s10506-020-09269-x}
}
```

Argues that due-process provisions designed for human civil servants can become redundant once
decision-making is automated, creating problems for good government, responsibility, liability and
the rule of law. Since the GDPR only acknowledges ADM, most administrative due-process safeguards
must come from national law — and Suksi emphasises **preventive legality safeguards**, not only
reactive complaint procedures.

**Use for us.** **One of the two most important citations in this file.** It is in the target
journal, it is administrative-law-doctrinal, and it proves AI&Law publishes administrative-procedure
work grounded in a single national legal order — the exact shape of our paper. The preventive-
safeguards emphasis is also the natural argument for why the as-is procedure must be made
inspectable *before* anything gets automated.
*(Crossref issues 2020 online-first; volume 29 is 2021.)*

### 1.9 Bibal, Lognoul, de Streel & Frénay (2021) — legal requirements on explainability `★ AI&Law` `[DOCTRINAL]`

```bibtex
@article{bibal2021legal,
  author  = {Bibal, Adrien and Lognoul, Michael and de Streel, Alexandre and Fr\'enay, Benoit},
  title   = {Legal requirements on explainability in machine learning},
  journal = {Artificial Intelligence and Law},
  volume  = {29},
  number  = {2},
  pages   = {149--169},
  year    = {2021},
  doi     = {10.1007/s10506-020-09270-4}
}
```

Black-box models may be unacceptable ethically or legally despite high performance. Surveys legal
interpretability/explainability requirements across private *and public* decision-making, then
translates them into constraints on model choice.

**Use for us.** The citation for why our catalog must be *auditable*: a legal-domain artefact
carries an explainability obligation a purely technical clustering result does not. That is the
argument for our consensus clustering and human-readable named clusters — justify them on **legal**
grounds, not on accuracy.
*(Crossref issues 2020 online-first; volume 29 is 2021.)*

### 1.10 Busuioc (2021) — holding algorithms to account `[CONCEPTUAL]`

```bibtex
@article{busuioc2021accountable,
  author  = {Busuioc, Madalina},
  title   = {Accountable artificial intelligence: holding algorithms to account},
  journal = {Public Administration Review},
  volume  = {81},
  number  = {5},
  pages   = {825--836},
  year    = {2021},
  doi     = {10.1111/puar.13293}
}
```

Maps what algorithmic systems do to *public accountability* specifically — how they disrupt
established accountability relationships in government rather than raising generic ethics concerns.

**Use for us.** The leading public-administration statement that accountability requires an
account-*able* record. Ours operates at the **process** layer rather than the decision layer — make
that distinction explicitly; it is also our defence against "you didn't study automated decisions."

### 1.11 Grimmelikhuijsen (2023) — accessibility vs explainability, experimentally `[EMPIRICAL]`

```bibtex
@article{grimmelikhuijsen2023explaining,
  author  = {Grimmelikhuijsen, Stephan},
  title   = {Explaining why the computer says no: algorithmic transparency affects the
             perceived trustworthiness of automated decision-making},
  journal = {Public Administration Review},
  volume  = {83},
  number  = {2},
  pages   = {241--262},
  year    = {2023},
  doi     = {10.1111/puar.13483}
}
```

Decomposes algorithmic transparency into **accessibility** and **explainability** and tests both in
two experimental scenarios. Explainability affects trust more than accessibility; effects are not
robust across decision contexts. Transparency-as-accessibility is insufficient.

**Use for us.** **Empirical backing for the paper's operational definition of transparency.** When a
reviewer asks "what do you mean by transparency, concretely?", this is the answer with evidence.
Pair with 1.1.
*(Crossref issues 2022 online-first; volume 83 is 2023.)*

### 1.12 Kemper & Kolkman (2019) — transparent to whom? `[CONCEPTUAL]`

```bibtex
@article{kemper2019transparent,
  author  = {Kemper, Jakko and Kolkman, Daan},
  title   = {Transparent to whom? {No} algorithmic accountability without a critical audience},
  journal = {Information, Communication \& Society},
  volume  = {22},
  number  = {14},
  pages   = {2081--2096},
  year    = {2019},
  doi     = {10.1080/1369118X.2018.1477967}
}
```

Asks the question the transparency literature mostly skips — transparent *to whom*? Without an
audience competent to interrogate a disclosure, algorithms cannot be held accountable at all.

**Use for us.** Forces us to name the catalog's addressee (internal control, the state audit court,
the *Ministério Público*, reform units) rather than gesturing at "society". Reviewers reward a
named forum.

### 1.13 Di Porto (2023) — algorithmic disclosure rules `★ AI&Law` `[DOCTRINAL]`

```bibtex
@article{diporto2023algorithmic,
  author  = {Di Porto, Fabiana},
  title   = {Algorithmic disclosure rules},
  journal = {Artificial Intelligence and Law},
  volume  = {31},
  number  = {1},
  pages   = {13--51},
  year    = {2023},
  doi     = {10.1007/s10506-021-09302-7}
}
```

Examines how disclosure obligations can themselves be re-designed and computationally supported,
rather than treated as static publication duties.

**Use for us.** Venue-internal precedent that *disclosure design* is an AI&Law topic — helpful,
since our contribution is essentially a better-designed disclosure artefact.
*(Crossref issues 2021 online-first; volume 31 is 2023.)*

### 1.14 Brożek, Furman, Jakubiec & Kucharzyk (2024) — the black box revisited `★ AI&Law` `[CONCEPTUAL]`

```bibtex
@article{brozek2024black,
  author  = {Bro\.zek, Bartosz and Furman, Micha{\l} and Jakubiec, Marek and Kucharzyk, Bart{\l}omiej},
  title   = {The black box problem revisited: real and imaginary challenges for automated
             legal decision making},
  journal = {Artificial Intelligence and Law},
  volume  = {32},
  number  = {2},
  pages   = {427--440},
  year    = {2024},
  doi     = {10.1007/s10506-023-09356-9}
}
```

Argues the opacity objection to automated legal decision-making is partly misconceived, since human
legal decision-making is itself substantially opaque; separates genuine problems from imagined ones.

**Use for us.** For the limitations paragraph: our artefacts make an *already opaque human process*
more legible. Pre-empts "but your clustering is a black box too" by relocating the comparison
standard.
*(Crossref issues 2023 online-first; volume 32 is 2024.)*

### 1.15 Supporting items (all DOI-verified)

| Key | Reference | Why it helps |
|---|---|---|
| `definelicht2020ai` | de Fine Licht K, de Fine Licht J (2020) Artificial intelligence, transparency, and public decision-making. *AI & Society* 35(4):917–926. `10.1007/s00146-020-00960-w` | Argues *limited* transparency focused on **justifications** suffices for legitimacy — a nuanced middle position that fits an as-is catalog `[CONCEPTUAL]` |
| `peeters2020agency` | Peeters R (2020) The agency of algorithms. *Information Polity* 25(4):507–522. `10.3233/IP-200253` | Design variables that set the *preconditions* for transparency and discretion in administrative decisions `[CONCEPTUAL]` |
| `veale2018fairness` | Veale M, Van Kleek M, Binns R (2018) Fairness and accountability design needs for algorithmic support in high-stakes public sector decision-making. *CHI '18*, 1–14. `10.1145/3173574.3174014` | 27 interviews with public-sector ML practitioners; documents the gap between institutional reality and transparency research `[EMPIRICAL]` |

---

<a name="2"></a>
## 2. Efficiency, reasonable duration & the right to good administration

**Discipline note.** The paper is principles-based and does *not* claim a deadline breach.
Over-citing duration doctrine invites exactly the reviewer question we do not want. Cite enough to
establish duration as a recognised legal value, take the methodological template from §2.5, and
move on.

### 2.1 Craig (2022) — Article 41 CFR, the standard commentary `[DOCTRINAL]`

```bibtex
@incollection{craig2022article41,
  author    = {Craig, Paul},
  title     = {Article 41 -- the right to good administration},
  booktitle = {The {EU} {Charter} of {Fundamental} {Rights}: a Commentary},
  editor    = {Peers, Steve and Hervey, Tamara and Kenner, Jeff and Ward, Angela},
  edition   = {2},
  publisher = {Nomos/Hart},
  pages     = {1125--1152},
  year      = {2022},
  doi       = {10.5771/9783748913245-1125}
}
```

The authoritative English-language commentary on Art. 41, covering its four limbs — impartial, fair
and **within a reasonable time** handling; right to be heard; access to file; duty to give reasons —
and their relation to the pre-Charter general principle of good administration.

**Use for us.** The comparative anchor establishing that "reasonable time" is a *constitutive
element* of good administration, not an add-on. That is precisely the principles-based framing we
need, and it makes CF art. 5 LXXVIII a member of a family rather than a local curiosity.
A first edition exists (2014, `10.5771/9783845259055_1112`) — **cite the 2022 second edition**.

### 2.2 Bousta (2013) — the critical counterweight `[DOCTRINAL]`

```bibtex
@article{bousta2013goodadministration,
  author  = {Bousta, Rhita},
  title   = {Who said there is a `right to good administration'? {A} critical analysis of
             {Article} 41 of the {Charter} of {Fundamental} {Rights} of the {European Union}},
  journal = {European Public Law},
  volume  = {19},
  number  = {3},
  pages   = {481--488},
  year    = {2013},
  doi     = {10.54648/euro2013030}
}
```

Argues that Art. 41, though labelled a *right*, is in substance drafted as a set of **duties imposed
on the administration** rather than subjective individual rights.

**Use for us.** **This is more useful than it first appears.** It licenses framing our catalog as
evidence about whether the administration is *discharging its duties* — not as an allegation that
some individual's right was violated. That is exactly our non-accusatory stance, given doctrinal
backing. Cite alongside 2.1, never instead of it.

### 2.3 Hofmann & Mihaescu (2013) — good administration in composite procedures `[DOCTRINAL]`

```bibtex
@article{hofmann2013goodadministration,
  author  = {Hofmann, Herwig C. H. and Mihaescu, C.},
  title   = {The relation between the {Charter's} fundamental rights and the unwritten
             general principles of {EU} law: good administration as the test case},
  journal = {European Constitutional Law Review},
  volume  = {9},
  number  = {1},
  pages   = {73--101},
  year    = {2013},
  doi     = {10.1017/S1574019612001046}
}
```

Uses good administration to test how codified Charter rights relate to unwritten general principles,
arguing the right has real potential to address legitimacy problems in the EU's **integrated /
composite administrative system**, where one procedure runs across several authorities.

**Use for us.** The composite-procedure angle maps directly onto our object: a process crossing many
organisational units where **no single actor owns the total duration**. That is a genuinely
load-bearing doctrinal point for interpreting handoffs and inter-unit waiting in our traces.

### 2.4 Lock (2019) — Article 41, the OUP commentary `[DOCTRINAL]`

```bibtex
@incollection{lock2019article41,
  author    = {Lock, Tobias},
  title     = {Article 41 {CFR} right to good administration},
  booktitle = {The {EU} {Treaties} and the {Charter} of {Fundamental} {Rights}: a Commentary},
  publisher = {Oxford University Press},
  year      = {2019},
  doi       = {10.1093/oso/9780198759393.003.564}
}
```

Establishes that good administration was recognised as a general principle of EU law **before** the
Charter, and that although Art. 41 textually binds only Union institutions, the underlying general
principle reaches Member State authorities implementing EU law.

**Use for us.** The doctrinal bridge for using an EU-derived good-administration standard as a
comparative reference for a *subnational* administration without over-claiming direct
applicability. *(Crossref returns no page range; omit `pages` rather than guessing.)*

### 2.5 Piątek & Potěšil (2021) — ★ the methodological template `[EMPIRICAL]` `[DOCTRINAL]`

```bibtex
@article{piatek2021reasonabletime,
  author  = {Pi\k{a}tek, Wojciech and Pot\v{e}\v{s}il, Luk\'a\v{s}},
  title   = {A right to have one's case heard within a reasonable time before the {Czech}
             and the {Polish} {Supreme} {Administrative} {Courts} -- standards, the reality
             and proposals for the future},
  journal = {Utrecht Law Review},
  volume  = {17},
  number  = {1},
  pages   = {20--32},
  year    = {2021},
  doi     = {10.36633/ulr.586}
}
```

States the international "reasonable time" standards (notably ECHR Art. 6), then measures them
against **actual disposition times and caseloads** in two supreme administrative courts, diagnoses
*structural* causes, and proposes procedural reform — without attributing blame for individual
breaches.

**Use for us.** **The single most useful item in this section.** It is the exact rhetorical structure
our paper needs: *state the normative standard → report observed durations → reason structurally →
propose reform*, explicitly stopping short of breach findings. Peer-reviewed, open access,
administrative. Cite it as methodological precedent for the stance, not just for the content.

### 2.6 Perlingeiro (2016) — Brazilian administrative due process, in English `[DOCTRINAL]`

```bibtex
@article{perlingeiro2016dueprocess,
  author  = {Perlingeiro, Ricardo},
  title   = {Due process prior to administrative decisions and effective judicial protection
             in {Brazil}: a new perspective?},
  journal = {ICL Journal},
  volume  = {10},
  number  = {1},
  pages   = {30--62},
  year    = {2016},
  doi     = {10.1515/icl-2016-0104}
}
```

Re-examines the 1988 Constitution's administrative due-process guarantees through a comparative
Anglo-Saxon/Continental lens; distinguishes administrative *procedures* from *proceedings*, and
addresses impartiality without structural independence and the scope of review of discretion.

**Use for us.** **This closes most of the "Brazilian administrative law in English" gap.**
Peer-reviewed, DOI-bearing, English-language, and precisely on the constitutional guarantees our
framing invokes. Previously the hardest citation to source.

### 2.7 Perlingeiro (2014) — the institutional description `[DOCTRINAL]`

```bibtex
@article{perlingeiro2014adminjustice,
  author  = {Perlingeiro, Ricardo},
  title   = {{Brazil's} administrative justice system in a comparative context},
  journal = {Revista de Investiga\c{c}\~oes Constitucionais},
  volume  = {1},
  number  = {3},
  pages   = {33--58},
  year    = {2014},
  doi     = {10.5380/rinc.v1i3.40517}
}
```

Descriptive analysis of Brazilian administrative process and its judicial system, situating Brazil
relative to the continental-European and US systems that shaped it.

**Use for us.** The background-section citation that lets a non-Brazilian AI&Law reviewer understand
the institutional setting. Open access, English, DOI — everything the Background section needs.

### 2.8 Moynihan, Herd & Harvey (2015) — the administrative burden canon `[CONCEPTUAL]` `[EMPIRICAL]`

```bibtex
@article{moynihan2015adminburden,
  author  = {Moynihan, Donald and Herd, Pamela and Harvey, Hope},
  title   = {Administrative burden: learning, psychological, and compliance costs in
             citizen-state interactions},
  journal = {Journal of Public Administration Research and Theory},
  volume  = {25},
  number  = {1},
  pages   = {43--69},
  year    = {2015},
  doi     = {10.1093/jopart/muu009}
}
```

Introduces administrative burden as learning, psychological and compliance costs borne by citizens,
and argues burden is a **deliberate political choice** rather than accident — a "hidden politics"
that escapes public scrutiny.

**Use for us.** **The key to giving duration normative weight without a breach claim.** It connects
observed process friction directly to CF art. 5 XXXIV "a" (right of petition) and art. 5 LXXVIII,
via costs to the citizen rather than via violated deadlines.

### 2.9 Halling & Baekgaard (2024) — the current systematic review `[CONCEPTUAL]`

```bibtex
@article{halling2024adminburden,
  author  = {Halling, Aske and Baekgaard, Martin},
  title   = {Administrative burden in citizen--state interactions: a systematic literature review},
  journal = {Journal of Public Administration Research and Theory},
  volume  = {34},
  number  = {2},
  pages   = {180--195},
  year    = {2024},
  doi     = {10.1093/jopart/muad023}
}
```

Synthesises 119 articles and shows burdens are consequential, distributive, and **constructed
through both formal policy and implementation practice** — frontline delivery, communication — not
policy alone. Calls for comparative work across policy contexts.

**Use for us.** The "constructed through implementation practice, not just formal policy" finding is
the burden-literature statement of **our core claim**: the normative process description and the
enacted process diverge. Its call for comparative work is an explicit opening for a Brazilian case.

### 2.10 Bozeman, Reed & Scott (1992) — measured elapsed time as a construct `[EMPIRICAL]`

```bibtex
@article{bozeman1992redtape,
  author  = {Bozeman, Barry and Reed, Pamela N. and Scott, Patrick},
  title   = {Red tape and task delays in public and private organizations},
  journal = {Administration \& Society},
  volume  = {24},
  number  = {3},
  pages   = {290--322},
  year    = {1992},
  doi     = {10.1177/009539979202400302}
}
```

Operationalises red tape as the *elapsed time required to complete core organisational tasks*,
establishing measured duration — not perceived burden — as a legitimate empirical construct.

**Use for us.** Direct precedent for treating measured elapsed process time as a valid object of
study. Useful precisely because it predates and is independent of the process-mining literature.

### 2.11 Supporting items

| Key | Reference | Why it helps |
|---|---|---|
| `lipsky2010streetlevel` | Lipsky M (2010) *Street-Level Bureaucracy: Dilemmas of the Individual in Public Services*, 30th Anniversary Expanded edn. Russell Sage Foundation. ISBN 9780871545442 | The foundational reason an emergent data-derived catalog is **not redundant** with the official one: policy as delivered differs from policy as declared `[CONCEPTUAL]` — verified at russellsage.org |
| `reneual2017modelrules` | Craig P, Hofmann HCH, Schneider J-P, Ziller J (eds) (2017) *ReNEUAL Model Rules on EU Administrative Procedure*. OUP. ISBN 9780198795308 | An academically-drafted normative template for what a well-ordered administrative procedure looks like `[DOCTRINAL]`. **⚠ Do not cite a specific rule number** — the official PDF would not parse and no rule on time limits was confirmed |
| `gomes2021brazilreform` | Gomes RC, Lisboa EF (2021) Public management reform in Brazil (2002–2019). *Public Management Review* 23(2):159–167. `10.1080/14719037.2020.1752037` | Every administration 2002–2019 pursued administrative reform — the practical backdrop to the constitutional efficiency principle `[CONCEPTUAL]` |
| `halperin2011lawinbooks` | Halpérin J-L (2011) Law in books and law in action: the problem of legal change. *Maine Law Review* 64(1):45 | Rigorous restatement of Pound, separating "courts departing from text" from "doctrine vs **empirical data** about law" — the second sense is our gap `[CONCEPTUAL]`. **⚠ End page unconfirmed; sources disagree on 2011 vs 2012.** Cite as `64 Me. L. Rev. 45 (2011)` or verify |

> ### ⚠ Confirmed gap — worth stating in the paper
>
> **Two independent searches failed to find peer-reviewed, English-language, DOI-bearing scholarship
> specifically on the Brazilian constitutional efficiency principle (CF art. 37 caput / EC 19/1998).**
> That literature is overwhelmingly Portuguese-language and in books or non-indexed journals.
> Because two independent searches agree, this is a reasonably robust finding rather than a search
> failure.
>
> **Recommended handling:** cite the constitutional text directly (§7 gives verified wording — this
> is what a Brazilian legal reader expects anyway), use Perlingeiro (2.6, 2.7) for the
> English-language administrative-law grounding, and use Craig/Bousta (2.1, 2.2) for the comparative
> normative argument. If the TCC/ABNT version needs Portuguese doctrine, add a standard
> *Direito Administrativo* manual verified by hand from a physical or publisher copy.

---

<a name="3"></a>
## 3. Auditability, accountability by design & access-to-information

### 3.1 Bovens (2007) — the accountability framework everything builds on `[CONCEPTUAL]`

```bibtex
@article{bovens2007analysing,
  author  = {Bovens, Mark},
  title   = {Analysing and assessing accountability: a conceptual framework},
  journal = {European Law Journal},
  volume  = {13},
  number  = {4},
  pages   = {447--468},
  year    = {2007},
  doi     = {10.1111/j.1468-0386.2007.00378.x}
}
```

Defines accountability narrowly and usably: a relationship between an **actor** and a **forum** in
which the actor must explain and justify conduct, the forum can question and judge, and consequences
may follow.

**Use for us.** **The definitional backbone of the legal framing.** It lets us say precisely what a
catalog is for: it supplies the *explain-and-justify* content a forum needs to pose questions.
Structure one paragraph naming actor, forum, criteria and consequences in our setting.
*(Crossref's stored title carries a stray footnote marker; the form above is correct.)*

### 3.2 Raji et al. (2020) — internal algorithmic auditing `[CONCEPTUAL]` `[METHOD]`

```bibtex
@inproceedings{raji2020closing,
  author    = {Raji, Inioluwa Deborah and Smart, Andrew and White, Rebecca N. and
               Mitchell, Margaret and Gebru, Timnit and Hutchinson, Ben and
               Smith-Loud, Jamila and Theron, Daniel and Barnes, Parker},
  title     = {Closing the {AI} accountability gap: defining an end-to-end framework for
               internal algorithmic auditing},
  booktitle = {Proceedings of the 2020 Conference on Fairness, Accountability, and
               Transparency (FAT* '20)},
  pages     = {33--44},
  publisher = {ACM},
  year      = {2020},
  doi       = {10.1145/3351095.3372873}
}
```

External post-hoc audits catch harms too late. Proposes an **internal**, lifecycle-wide framework in
which each stage produces documents that together compose an audit report, assessed against the
organisation's **own stated principles**.

**Use for us.** **The closest methodological analogue to our contribution.** Accountability produced
by an auditable artefact evaluated against the organisation's own declared commitments *is* the
as-is-catalog-versus-declared-model structure. If we cite one thing to explain what kind of object
our catalog is, cite this.

### 3.3 Wieringa (2020) — systematic review of algorithmic accountability `[CONCEPTUAL]`

```bibtex
@inproceedings{wieringa2020account,
  author    = {Wieringa, Maranke},
  title     = {What to account for when accounting for algorithms: a systematic literature
               review on algorithmic accountability},
  booktitle = {Proceedings of the 2020 Conference on Fairness, Accountability, and
               Transparency (FAT* '20)},
  pages     = {1--18},
  publisher = {ACM},
  year      = {2020},
  doi       = {10.1145/3351095.3372833}
}
```

PRISMA review of 242 articles (93 core), organised around Bovens's five accountability components.

**Use for us.** A ready-made scaffold for stating who accounts, to whom, on what criteria. Pairs with
3.1. *(Crossref stores the short title without the subtitle; the full form above is correct.)*

### 3.4 Brauneis & Goodman (2018) — FOI requests as empirical method `[EMPIRICAL]` *(no DOI)*

```bibtex
@article{brauneis2018algorithmic,
  author  = {Brauneis, Robert and Goodman, Ellen P.},
  title   = {Algorithmic transparency for the smart city},
  journal = {Yale Journal of Law \& Technology},
  volume  = {20},
  pages   = {103--176},
  year    = {2018}
}
```

The authors filed **42 open-records requests across 23 states** about six government predictive-
algorithm programs. Most agencies could not produce adequate documentation. Trade secrecy was a
*smaller* obstacle than expected — the deeper problem is that governments **never generated the
records**.

**Use for us.** **The strongest possible support for our core claim.** Access-to-information regimes
deliver transparency only when the underlying record exists; our catalog is exactly the kind of
record whose absence they document empirically. This converts "we built a nice artefact" into "we
built the artefact FOI regimes presuppose and rarely find."
**Verified at** `https://yjolt.org/algorithmic-transparency-smart-city`; cite form
`20 Yale J.L. & Tech. 103 (2018)`. SSRN preprint `10.2139/ssrn.3012499`; cite the journal version.

### 3.5 Janssen, Charalabidis & Zuiderwijk (2012) — publication is not use `[EMPIRICAL]`

```bibtex
@article{janssen2012benefits,
  author  = {Janssen, Marijn and Charalabidis, Yannis and Zuiderwijk, Anneke},
  title   = {Benefits, adoption barriers and myths of open data and open government},
  journal = {Information Systems Management},
  volume  = {29},
  number  = {4},
  pages   = {258--268},
  year    = {2012},
  doi     = {10.1080/10580530.2012.716740}
}
```

Punctures five "myths"; central finding is that a simplistic view prevails which **automatically
equates publicising data with use and benefit**.

**Use for us.** The cleanest citation for why dumping the raw event log is not transparency, and why
the *interpretive* layer (types + typical paths) is the contribution rather than a convenience.

### 3.6 Metcalf et al. (2021) — impacts are constructed, not found `[CONCEPTUAL]`

```bibtex
@inproceedings{metcalf2021algorithmic,
  author    = {Metcalf, Jacob and Moss, Emanuel and Watkins, Elizabeth Anne and
               Singh, Ranjit and Elish, Madeleine Clare},
  title     = {Algorithmic impact assessments and accountability: the co-construction of impacts},
  booktitle = {Proceedings of the 2021 ACM Conference on Fairness, Accountability, and
               Transparency (FAccT '21)},
  pages     = {735--746},
  publisher = {ACM},
  year      = {2021},
  doi       = {10.1145/3442188.3445935}
}
```

"Impacts" are an evaluative construct, not a natural fact; impact assessments risk producing
*organisationally legible metrics inappropriately distant from the harms people actually experience*.

**Use for us.** **Engage as a challenge, not as support.** It presses us to justify why mining actual
traces stays closer to lived administrative experience than declared indicators. Addressing it
head-on in Discussion is a strong move.

### 3.7 Diakopoulos (2015) — inferring behaviour from outputs `[EMPIRICAL]` `[CONCEPTUAL]`

```bibtex
@article{diakopoulos2015algorithmic,
  author  = {Diakopoulos, Nicholas},
  title   = {Algorithmic accountability: journalistic investigation of computational
             power structures},
  journal = {Digital Journalism},
  volume  = {3},
  number  = {3},
  pages   = {398--415},
  year    = {2015},
  doi     = {10.1080/21670811.2014.976411}
}
```

Proposes algorithmic accountability reporting and analyses five reverse-engineering case studies.

**Use for us.** Establishes the epistemic tradition of *inferring how an opaque system actually
behaves from its observable traces* — the same move our pipeline performs on administrative process.

### 3.8 Liebwald (2015) — transparent law and accessible legal information `★ AI&Law` `[DOCTRINAL]`

```bibtex
@article{liebwald2015transparent,
  author  = {Liebwald, Doris},
  title   = {On transparent law, good legislation and accessibility to legal information:
             towards an integrated legal information system},
  journal = {Artificial Intelligence and Law},
  volume  = {23},
  number  = {3},
  pages   = {301--314},
  year    = {2015},
  doi     = {10.1007/s10506-015-9172-z}
}
```

Legal transparency requires more than publication — it requires accessibility, comprehensibility and
integration.

**Use for us.** Venue-internal precedent that "transparency" is an AI&Law topic in its own right, and
that the disclosure-vs-intelligibility distinction is already at home in this journal.

### 3.9 Magnini, Not, Stock & Strapparava (2000) — NLP for public administration `★ AI&Law` `[EMPIRICAL]`

```bibtex
@article{magnini2000natural,
  author  = {Magnini, Bernardo and Not, Elena and Stock, Oliviero and Strapparava, Carlo},
  title   = {Natural language processing for transparent communication between public
             administration and citizens},
  journal = {Artificial Intelligence and Law},
  volume  = {8},
  number  = {1},
  pages   = {1--34},
  year    = {2000},
  doi     = {10.1023/A:1008394902165}
}
```

An early AI&Law paper applying NLP to make administrative communication intelligible to citizens.

**Use for us.** Historical venue precedent that **NLP + public administration + transparency** is a
long-standing AI&Law thread, not an intrusion from another field. A cheap, effective venue-fit
signal.

### 3.10 Supporting items (all DOI-verified)

| Key | Reference | Why it helps |
|---|---|---|
| `bannister2011trouble` | Bannister F, Connolly R (2011) The trouble with transparency. *Policy & Internet* 3(1):1–30. `10.2202/1944-2866.1076` | ICT-enabled transparency can be *inimical* to good governance; the e-gov counterpart to Ananny & Crawford `[CONCEPTUAL]` |
| `meijer2009understanding` | Meijer A (2009) Understanding modern transparency. *Int. Rev. Admin. Sci.* 75(2):255–269. `10.1177/0020852309104175` | *Unidirectional, decontextualised* transparency can erode trust — supports our contextualised catalog `[CONCEPTUAL]` |
| `ruijer2017open` | Ruijer E, Grimmelikhuijsen S, Meijer A (2017) Open data for democracy. *Gov. Inf. Q.* 34(1):45–52. `10.1016/j.giq.2017.01.001` | Open data platforms largely failed democratically because design ignores differing use needs `[EMPIRICAL]` |
| `cobbe2023supply` | Cobbe J, Veale M, Singh J (2023) Understanding accountability in algorithmic supply chains. *FAccT '23*, 1186–1197. `10.1145/3593013.3594073` | The "accountability horizon" across distributed actors — relevant since our processes cross organisational units `[CONCEPTUAL]` |

---

<a name="4"></a>
## 4. Anonymisation, re-identification & the privacy–utility trade-off

The existing bib covers text-anonymisation NLP (TAB, Lison, Lothritz, Ben Cheikh Larbi, Dernoncourt,
Stubbs, Presidio). Missing: (a) the **legal** concept of anonymisation, (b) **re-identification
risk** foundations, (c) **privacy–utility work inside process mining**, and (d) — critically — the
**prior work that already measures anonymisation's effect on clustering**.

### 4.1 Article 29 Working Party (2014) — the regulatory yardstick `[DOCTRINAL]`

```bibtex
@techreport{a29wp2014anonymisation,
  author      = {{Article 29 Data Protection Working Party}},
  title       = {Opinion 05/2014 on anonymisation techniques},
  institution = {European Commission},
  number      = {WP216},
  address     = {Brussels},
  year        = {2014},
  note        = {Ref. 0829/14/EN, adopted 10 April 2014},
  url         = {https://ec.europa.eu/justice/article-29/documentation/opinion-recommendation/files/2014/wp216_en.pdf}
}
```

Assesses anonymisation techniques against three residual risks — **singling out, linkability,
inference** — and holds that a technique failing to defeat all three does not yield anonymous data.
Explicitly rejects equating pseudonymisation with anonymisation.

**Use for us.** The canonical yardstick against which our NER-based PII removal must be **honestly
characterised as pseudonymisation-grade, not legally "anonymous."** Making that concession
explicitly is a credibility move, and it is precisely why the residual-utility question matters.
*(Verified from the primary PDF cover page, which prints "0829/14/EN / WP216 ... Adopted on
10 April 2014".)*

### 4.2 Finck & Pallas (2020) — the anonymisation spectrum `[DOCTRINAL]` `[CONCEPTUAL]`

```bibtex
@article{finck2020identified,
  author  = {Finck, Mich{\`e}le and Pallas, Frank},
  title   = {They who must not be identified---distinguishing personal from non-personal
             data under the {GDPR}},
  journal = {International Data Privacy Law},
  volume  = {10},
  number  = {1},
  pages   = {11--36},
  year    = {2020},
  doi     = {10.1093/idpl/ipz026}
}
```

The personal/non-personal boundary under GDPR Art. 4(1) and Recital 26 is inherently **relative and
risk-based** ("means reasonably likely to be used"), not a property of a dataset. This collides with
WP216's stricter demand, producing legal uncertainty; the authors conclude perfect anonymisation is
impossible and residual risk must be *managed*.

**Use for us.** The doctrinal licence for treating anonymisation as a **dial we can turn and then
measure the cost of**, rather than a switch that is legally on or off. This is the precise legal
counterpart of LGPD art. 12's "esforços razoáveis" standard (§7.3).

### 4.3 Weitzenboeck, Lison, Cyndecka & Langford (2022) — ★ anonymising unstructured text costs 80–96% `[DOCTRINAL]` `[EMPIRICAL]`

```bibtex
@article{weitzenboeck2022unstructured,
  author  = {Weitzenboeck, Emily M. and Lison, Pierre and Cyndecka, Malgorzata and Langford, Malcolm},
  title   = {The {GDPR} and unstructured data: is anonymization possible?},
  journal = {International Data Privacy Law},
  volume  = {12},
  number  = {3},
  pages   = {184--206},
  year    = {2022},
  doi     = {10.1093/idpl/ipac008}
}
```

Asks whether GDPR-grade anonymisation of unstructured data is achievable at all. Using case studies
on **court documents** and medical images, finds that preventing linkage to source data requires
masking roughly **80–96% of the content**, destroying utility. Concludes a risk-based reading is the
only workable one.

**Use for us.** **The single best cite for "anonymisation costs analytical utility, and in free text
the cost is severe."** It is also co-authored by Lison, whom the bib already cites — tying our legal
and NLP anchors to one another. Use it to set the expectation our results then test.

### 4.4 Rocher, Hendrickx & de Montjoye (2019) — sampling is not protection `[EMPIRICAL]`

```bibtex
@article{rocher2019estimating,
  author  = {Rocher, Luc and Hendrickx, Julien M. and de Montjoye, Yves-Alexandre},
  title   = {Estimating the success of re-identifications in incomplete datasets using
             generative models},
  journal = {Nature Communications},
  volume  = {10},
  number  = {1},
  pages   = {3069},
  year    = {2019},
  doi     = {10.1038/s41467-019-10933-3}
}
```

A copula-based generative method estimating per-individual re-identification likelihood from heavily
incomplete releases, validated on 210 populations (AUC 0.84–0.97). Headline: **99.98% of Americans
would be correctly re-identified** using 15 demographic attributes. Concludes the results "seriously
challenge the technical and legal adequacy of the de-identification release-and-forget model."

**Use for us.** Kills the defence "our sample is only 5,243 records, so re-identification is
infeasible." **Sampling is not protection** — which is precisely why anonymisation is worth its
utility cost.

### 4.5 Núñez von Voigt et al. (2020) — ★ event logs are themselves quasi-identifiers `[EMPIRICAL]`

```bibtex
@inproceedings{nunezvonvoigt2020quantifying,
  author    = {Nu{\~n}ez von Voigt, Saskia and Fahrenkrog-Petersen, Stephan A. and
               Janssen, Dominik and Koschmider, Agnes and Tschorsch, Florian and
               Mannhardt, Felix and Landsiedel, Olaf and Weidlich, Matthias},
  title     = {Quantifying the re-identification risk of event logs for process mining},
  booktitle = {Advanced Information Systems Engineering (CAiSE 2020), LNCS},
  pages     = {252--267},
  publisher = {Springer},
  year      = {2020},
  doi       = {10.1007/978-3-030-49435-3_16}
}
```

Empirically quantifies individual uniqueness in real event logs, showing that **activity sequence
plus timestamps** makes cases highly unique and re-identifiable, and that identifier removal alone
is insufficient.

**Use for us.** **The event-log analogue of Narayanan & Shmatikov, and directly on point.** It is the
evidence that an administrative process trace is a quasi-identifier in its own right — which
justifies our design decision to anonymise the *text* rather than merely strip name fields, and
flags a residual risk our own approach does *not* eliminate. Report that limitation honestly.

### 4.6 Sweeney (2002) — k-anonymity `[CONCEPTUAL]`

```bibtex
@article{sweeney2002kanonymity,
  author  = {Sweeney, Latanya},
  title   = {k-anonymity: a model for protecting privacy},
  journal = {International Journal of Uncertainty, Fuzziness and Knowledge-Based Systems},
  volume  = {10},
  number  = {5},
  pages   = {557--570},
  year    = {2002},
  doi     = {10.1142/S0218488502001648}
}
```

Defines k-anonymity and establishes quasi-identifiers — not just explicit identifiers — as the real
re-identification vector.

**Use for us.** Supplies the formal vocabulary (quasi-identifiers, generalisation, suppression) that
the process-mining sanitisation literature builds on.

### 4.7 Narayanan & Shmatikov (2008) — de-anonymising sparse data `[EMPIRICAL]`

```bibtex
@inproceedings{narayanan2008robust,
  author    = {Narayanan, Arvind and Shmatikov, Vitaly},
  title     = {Robust de-anonymization of large sparse datasets},
  booktitle = {2008 IEEE Symposium on Security and Privacy},
  pages     = {111--125},
  publisher = {IEEE},
  year      = {2008},
  doi       = {10.1109/SP.2008.33}
}
```

The Netflix Prize de-anonymisation: sparse high-dimensional data is re-identifiable from little
auxiliary information.

**Use for us.** Relevant precisely because **event logs are sparse and high-dimensional**.

### 4.8 El Emam, Jonker, Arbuckle & Malin (2011) — the honest counterweight `[EMPIRICAL]`

```bibtex
@article{elemam2011systematic,
  author  = {El Emam, Khaled and Jonker, Elizabeth and Arbuckle, Luk and Malin, Bradley},
  title   = {A systematic review of re-identification attacks on health data},
  journal = {PLoS ONE},
  volume  = {6},
  number  = {12},
  pages   = {e28071},
  year    = {2011},
  doi     = {10.1371/journal.pone.0028071}
}
```

Reviews published re-identification attacks and their measured success rates, finding rates are far
lower for *properly* de-identified data than headline demonstrations suggest.

**Use for us.** **The necessary counterweight to 4.4 and 4.7.** It lets us argue the utility cost of
anonymisation should be judged against *realistic*, not worst-case, risk. Citing both directions is
what separates analysis from advocacy — and AI&Law reviewers notice.

### 4.9 Gadotti, Rocher, Houssiau, Creţu & de Montjoye (2024) — the current state of the art `[CONCEPTUAL]`

```bibtex
@article{gadotti2024anonymization,
  author  = {Gadotti, Andrea and Rocher, Luc and Houssiau, Florimond and
             Cre{\c{t}}u, Ana-Maria and de Montjoye, Yves-Alexandre},
  title   = {Anonymization: the imperfect science of using data while preserving privacy},
  journal = {Science Advances},
  volume  = {10},
  number  = {29},
  pages   = {eadn7053},
  year    = {2024},
  doi     = {10.1126/sciadv.adn7053}
}
```

Reviews the whole landscape — de-identification, query-based systems, synthetic data, differential
privacy — and concludes **no perfect solution exists**; best practice is to apply modern techniques
while *auditing their guarantees against attacks*, noting the trade-off is especially hard for
high-dimensional data.

**Use for us.** The most current, most citable statement that anonymisation is an **empirical
engineering trade-off requiring measurement** — which is exactly what we do, on high-dimensional
free text.

### 4.10 ★★ Ferrão, Prata & Fazendeiro (2022) — the prior work that narrows our novelty claim `[EMPIRICAL]`

```bibtex
@article{ferrao2022utility,
  author  = {Ferr{\~a}o, Maria Eug{\'e}nia and Prata, Paula and Fazendeiro, Paulo},
  title   = {Utility-driven assessment of anonymized data via clustering},
  journal = {Scientific Data},
  volume  = {9},
  number  = {1},
  pages   = {456},
  year    = {2022},
  doi     = {10.1038/s41597-022-01561-6}
}
```

Clusters an entire Portuguese cohort of higher-education Law students, then re-clusters versions
anonymised under k-anonymity and (ε, δ)-differential privacy, comparing solutions with
**Silhouette, Davies–Bouldin and Calinski–Harabasz** plus group-composition and relative-risk
measures. Finds that "for low dimensionality/cardinality datasets the anonymization procedure easily
jeopardizes the clustering endeavor," and that anonymised data yields *biased* estimates.

**Use for us — read carefully.** This is **the closest published analogue to our experimental
design**: anonymise, re-cluster, compare cluster solutions on a real administrative cohort, using
three of the same validity indices. It means the "no prior work on anonymisation impact on
clustering quality" claim in `references-candidates.md` **cannot stand as written.**

**Suggested narrowed claim** (defensible against this paper):

> Prior work has measured anonymisation's effect on clustering for **structured, low-dimensional
> tabular microdata** under formal privacy models (Ferrão et al. 2022), and on **control-flow**
> event-log structure under k-anonymity and differential privacy (Fahrenkrog-Petersen et al. 2019,
> 2023; Mannhardt et al. 2019). To our knowledge, no prior work measures the effect of
> **NER-based free-text PII removal** on **embedding-based clustering of administrative process
> documents**.

That claim is narrower, still novel, and now survives contact with the literature. It also
strengthens the paper: Ferrão et al. report utility loss on low-dimensional data, so our
high-dimensional text result becomes a **contrast** rather than an isolated observation.

### 4.11 Elkoumy et al. (2021) — the process-mining privacy agenda `[CONCEPTUAL]`

```bibtex
@article{elkoumy2021privacy,
  author  = {Elkoumy, Gamal and Fahrenkrog-Petersen, Stephan A. and Fani Sani, Mohammadreza and
             Koschmider, Agnes and Mannhardt, Felix and Nu{\~n}ez von Voigt, Saskia and
             Rafiei, Majid and von Waldthausen, Leopold},
  title   = {Privacy and confidentiality in process mining: threats and research challenges},
  journal = {ACM Transactions on Management Information Systems},
  volume  = {13},
  number  = {1},
  pages   = {1--17},
  year    = {2021},
  doi     = {10.1145/3468877}
}
```

The field's agenda-setting paper: enumerates privacy threats specific to event data, presents a
framework, identifies open gaps, and states plainly that privacy is a prerequisite for applying
process mining under regulation.

**Use for us.** **The one citation positioning our anonymisation arm inside an existing research
programme** rather than as institutional compliance.

### 4.12 Fahrenkrog-Petersen, van der Aa & Weidlich (2019, 2023) — sanitise then measure `[METHOD]` `[EMPIRICAL]`

```bibtex
@inproceedings{fahrenkrogpetersen2019pretsa,
  author    = {Fahrenkrog-Petersen, Stephan A. and van der Aa, Han and Weidlich, Matthias},
  title     = {{PRETSA}: event log sanitization for privacy-aware process discovery},
  booktitle = {2019 International Conference on Process Mining (ICPM)},
  pages     = {1--8},
  publisher = {IEEE},
  year      = {2019},
  doi       = {10.1109/ICPM.2019.00012}
}

@article{fahrenkrogpetersen2023optimal,
  author  = {Fahrenkrog-Petersen, Stephan A. and van der Aa, Han and Weidlich, Matthias},
  title   = {Optimal event log sanitization for privacy-preserving process mining},
  journal = {Data \& Knowledge Engineering},
  volume  = {145},
  pages   = {102175},
  year    = {2023},
  doi     = {10.1016/j.datak.2023.102175}
}
```

PRETSA sanitises logs to satisfy k-anonymity on control flow and t-closeness on sensitive
attributes via a prefix-tree formulation that **introduces no new behaviour** — unlike noise-based
methods. The 2023 DKE paper generalises this and evaluates the sanitisation-vs-utility frontier.

**Use for us.** The flagship "sanitise then measure what survives" line, and group-based rather than
noise-based — which parallels our choice to *remove* PII rather than perturb the corpus. The 2023
paper is the formal statement of privacy–utility as a measurable trade-off in process mining.

### 4.13 Mannhardt et al. (2019) — utility loss depends on heterogeneity `[EMPIRICAL]`

```bibtex
@article{mannhardt2019privacy,
  author  = {Mannhardt, Felix and Koschmider, Agnes and Baracaldo, Nathalie and
             Weidlich, Matthias and Michael, Judith},
  title   = {Privacy-preserving process mining: differential privacy for event logs},
  journal = {Business \& Information Systems Engineering},
  volume  = {61},
  number  = {5},
  pages   = {595--614},
  year    = {2019},
  doi     = {10.1007/s12599-019-00613-3}
}
```

Instantiates differential privacy for process discovery. The result is explicitly
**structure-dependent**: highly structured processes with few variants suffer little error, while
logs with many infrequent variants degrade materially.

**Use for us.** The "how much utility you lose depends on how heterogeneous your corpus is" result —
directly relevant, since 5,243 administrative processes with 182 discovered types is exactly the
long-tail, many-variants case. **Cite this when interpreting our own utility numbers.**

### 4.14 Anonymisation of public and judicial records (all verified)

| Key | Reference | Why it helps |
|---|---|---|
| `terzidou2023automated` ☆ ICAIL | Terzidou K (2023) Automated anonymization of court decisions. *ICAIL '23*, 297–305. `10.1145/3594536.3595151` | **Anonymisation as the *enabler* of transparency**, not a compliance tax — courts can publish "more plentifully, faster, and regularly." Our institutional argument, in the sister venue `[DOCTRINAL]`/`[EMPIRICAL]` |
| `allard2021publication` | Allard T, Béziaud L, Gambs S (2021) Publication of court records: circumventing the privacy-transparency trade-off. LNCS, 298–312. `10.1007/978-3-030-89811-3_21` | Names the privacy–transparency trade-off as a *design problem* rather than a policy slogan `[CONCEPTUAL]` |
| `nyffenegger2024anonymity` | Nyffenegger A, Stürmer M, Niklaus J (2024) Anonymity at risk? Findings of NAACL 2024, 2433–2462. `10.18653/v1/2024.findings-naacl.157` | Adversarial LLM re-identification on Swiss Supreme Court decisions — even strong LLMs struggle on real court text, so residual risk is low. The honest counterpoint `[EMPIRICAL]` |
| `anselmo2025pseudonymization` | Anselmo M, Ribas BC (2025) Pseudonymization in legal texts according to the LGPD: a NER approach. LNCS *Intelligent Systems*, 309–323. `10.1007/978-3-031-79032-4_22` | **The Brazilian/Portuguese peer-reviewed precedent for NER-based PII removal under LGPD** — establishes our stack is domain-appropriate, and leaves the downstream-utility question (our contribution) open `[EMPIRICAL]`. ⚠ Crossref shows only LNCS "Intelligent Systems" 2025; secondary sources say BRACIS 2024 — confirm the edition and LNCS volume from the front matter |
| `elkoumy2021mineme` | Elkoumy G, Pankova A, Dumas M (2021) Mine me but don't single me out. *ICPM 2021*, 80–87. `10.1109/ICPM53251.2021.9576852` | Ties a technical guarantee directly to WP216's **"singling out"** criterion — a neat bridge between our legal and empirical sections `[EMPIRICAL]` |

### 4.15 Ohm (2010) — broken promises of privacy `[DOCTRINAL]` *(no DOI)*

```bibtex
@article{ohm2010broken,
  author  = {Ohm, Paul},
  title   = {Broken promises of privacy: responding to the surprising failure of anonymization},
  journal = {UCLA Law Review},
  volume  = {57},
  pages   = {1701--1777},
  year    = {2010}
}
```

Argues reidentification research has invalidated the legal assumption that removing identifiers
produces safe data — a "fundamental misunderstanding [that] pervades nearly every information
privacy law" — and introduces the framing that data can be useful or perfectly anonymous, never both.

**Use for us.** The canonical statement of the tension our experiment operationalises.
**Verified** at the author's own publication list (`https://www.paulohm.com/pub/`, vol. 57, p. 1701)
and against the full text, confirming terminal page 1777. No DOI exists — US law reviews are poorly
indexed in Crossref.

### 4.16 CJEU, *EDPS v SRB* (2025) — identifiability is contextual `[DOCTRINAL]`

```bibtex
@misc{cjeu2025edpssrb,
  author       = {{Court of Justice of the European Union}},
  title        = {Judgment of the Court (First Chamber) of 4 September 2025, Case C-413/23~P,
                  {European Data Protection Supervisor v Single Resolution Board}},
  year         = {2025},
  howpublished = {Press Release No 107/25, Luxembourg},
  url          = {https://curia.europa.eu/site/upload/docs/application/pdf/2025-09/cp250107en.pdf}
}
```

Set aside the General Court's judgment but **confirmed** that pseudonymised data "must not be
regarded as constituting, in all cases and for every person, personal data" — pseudonymisation may,
depending on circumstances, prevent identification by parties other than the controller.

**Use for us.** Very recent authority that identifiability is **contextual and relative** — the basis
for saying our anonymised corpus sits at a different risk point for downstream analysts than for the
originating secretariat.
**⚠ Caveat:** the ECLI is widely reported as `ECLI:EU:C:2025:645` but **could not be confirmed from a
primary CURIA/EUR-Lex source** (both block automated access). Confirm before printing the ECLI. The
press-release PDF itself was verified.

---

<a name="5"></a>
## 5. Empirical & computational legal studies of procedure

### 5.1 ★★ Unger et al. (2021) — process mining on a Brazilian court's own records `☆ ICAIL` `[EMPIRICAL]`

```bibtex
@inproceedings{unger2021jurimetrics,
  author    = {Unger, Adriana Jacoto and dos Santos Neto, Jos\'e Francisco and
               Fantinato, Marcelo and Peres, Sarajane Marques and
               Trecenti, Julio and Hirota, Renata},
  title     = {Process mining-enabled jurimetrics: analysis of a {Brazilian} court's judicial
               performance in the business law processing},
  booktitle = {Proceedings of the Eighteenth International Conference on Artificial
               Intelligence and Law (ICAIL '21)},
  pages     = {240--244},
  publisher = {ACM},
  year      = {2021},
  doi       = {10.1145/3462757.3466137}
}
```

Builds an event log from business-law lawsuits at the São Paulo State Court of Justice (TJSP) and
applies process mining to characterise judicial performance. Finds lawsuits follow an **ad hoc
sequence flow rather than a designed one**, yet process mining still recovers frequent activities
and locates bottlenecks and their root causes.

**Use for us.** **The closest published precedent to our whole enterprise** — Brazilian, event-log-
based, in the AI&Law community's own conference, and explicitly about reconstructing what actually
happens versus what the procedural rules prescribe. It also establishes *jurimetria* as the accepted
Brazilian term. **This must be cited and differentiated in Related Work.** Our differentiation:
judicial vs administrative process, 5 activities vs a discovered 182-type catalog, and we add the
anonymisation arm.
*(Crossref stores only the short title "Process mining-enabled jurimetrics"; the full subtitle
appears in the ACM DL record.)*

### 5.2 ★ Nai et al. (2026) — legal process mining of administrative procedure `[EMPIRICAL]` `[METHOD]`

```bibtex
@article{nai2026procurement,
  author  = {Nai, Roberto and Sulis, Emilio and Audrito, Davide and
             Trifiletti, Vittoria Margherita Sofia and Di Caro, Luigi and Genga, Laura},
  title   = {Legal process mining for the analysis of public procurement workflows},
  journal = {Computer Law \& Security Review},
  volume  = {61},
  pages   = {106283},
  year    = {2026},
  doi     = {10.1016/j.clsr.2026.106283}
}
```

Reconstructs event logs from the official EU Tenders Electronic Daily dataset (five countries,
2016–2022), uses LLMs to extract case attributes from legal texts, and applies process discovery to
recover the actual sequence of tendering activities. Domain experts validated the output for
compliance monitoring and timeliness.

**Use for us.** The **direct administrative-procedure analogue**, in a law venue, making the
transparency case explicitly — automated process analysis helps citizens understand what procedures
contain and increases trust. Extremely close to our framing; cite and differentiate on scope
(procurement vs general administrative process) and on the discovery-of-types contribution.

### 5.3 ★ Nickerson, Varshney & Muntermann (2013) — how to build a taxonomy defensibly `[METHOD]`

```bibtex
@article{nickerson2013taxonomy,
  author  = {Nickerson, Robert C. and Varshney, Upkar and Muntermann, Jan},
  title   = {A method for taxonomy development and its application in information systems},
  journal = {European Journal of Information Systems},
  volume  = {22},
  number  = {3},
  pages   = {336--359},
  year    = {2013},
  doi     = {10.1057/ejis.2012.26}
}
```

Shows taxonomy development has been largely ad hoc, then defines the taxonomy problem formally and
presents an iterative method alternating empirical-to-conceptual and conceptual-to-empirical passes,
with explicit **ending conditions** and quality criteria (conciseness, robustness, comprehensiveness,
extendibility, explanatoriness).

**Use for us.** **This is the citation that converts "we clustered documents and named the clusters"
into a defensible taxonomy-construction procedure with stated stopping rules.** Expect a reviewer to
demand exactly this of an "auditable catalog of emergent process types". One of the highest-value
additions in this file, and it costs one paragraph in Method.

### 5.4 Frankenreiter & Livermore (2020) — computational legal analysis as legal scholarship `[METHOD]`

```bibtex
@article{frankenreiter2020computational,
  author  = {Frankenreiter, Jens and Livermore, Michael A.},
  title   = {Computational methods in legal analysis},
  journal = {Annual Review of Law and Social Science},
  volume  = {16},
  number  = {1},
  pages   = {39--57},
  year    = {2020},
  doi     = {10.1146/annurev-lawsocsci-052720-121843}
}
```

Surveys how digitisation plus NLP, text mining, network analysis and ML created new forms of legal
scholarship, from textual interpretation through quantitative causal estimation.

**Use for us.** The canonical citation for "computational legal studies is a legitimate mode of legal
scholarship" — use it in the Introduction to establish the method's standing *before* defending the
constitutional framing.

### 5.5 Yeung & Azevedo (2011) — the Brazilian evidentiary gap, stated from within `[EMPIRICAL]`

```bibtex
@article{yeung2011efficiency,
  author  = {Yeung, Luciana L. and Azevedo, Paulo F.},
  title   = {Measuring efficiency of {Brazilian} courts with data envelopment analysis ({DEA})},
  journal = {IMA Journal of Management Mathematics},
  volume  = {22},
  number  = {4},
  pages   = {343--356},
  year    = {2011},
  doi     = {10.1093/imaman/dpr002}
}
```

Observes that Brazilian court inefficiency has been acknowledged for decades but never measured, and
that "almost all legal research carried out in Brazil has been subjective, relying entirely on
conventional wisdom and anecdotal evidence." Uses DEA across all 27 state courts, finding management
quality — not resource scarcity — explains most variation.

**Use for us.** **The best available statement, from inside the Brazilian literature, of the exact
evidentiary gap our paper addresses.** That quotation is close to an ideal epigraph for the
Introduction. Also precedent for building performance claims from an institution's own
administrative statistics.

### 5.6 Supporting items (all DOI-verified)

| Key | Reference | Why it helps |
|---|---|---|
| `epstein2002rules` | Epstein L, King G (2002) The rules of inference. *University of Chicago Law Review* 69(1):1–133. `10.2307/1600349` | The founding methodological reference of empirical legal studies; supplies the standards (provenance, uncertainty, replicability) our auditability argument must meet `[METHOD]` |
| `copus2019bigdata` | Copus R, Hübert R, Laqueur H (2019) Big data, machine learning, and the credibility revolution in empirical legal studies. In *Law as Data*, SFI Press, 21–57. `10.37911/9781947864085.02` | The honest framing for what an unsupervised descriptive study can claim — a credible *description*, not a causal estimate `[METHOD]` |
| `lagefreitas2022predicting` | Lage-Freitas A, Allende-Cid H, Santana O, Oliveira-Lage L (2022) Predicting Brazilian court decisions. *PeerJ Computer Science* 8:e904. `10.7717/peerj-cs.904` | Scale-and-provenance norm for Brazilian legal-corpus work (4,043 cases); the natural contrast case — they predict outcomes, we describe procedure `[EMPIRICAL]` |

---

<a name="6"></a>
## 6. The venue itself — *Artificial Intelligence and Law*

All items verified as carrying `container-title: Artificial Intelligence and Law` and the
`10.1007/s10506-` prefix.

### 6.1 ★★ Branting et al. (2025) — government records + transparency law + a deployed tool `[EMPIRICAL]`

```bibtex
@article{branting2025sensitive,
  author  = {Branting, Karl and Brown, Bradford and Giannella, Chris and Van Guilder, James and
             Harrold, Jeff and Howell, Sarah and Baron, Jason R.},
  title   = {Decision support for detecting sensitive text in government records},
  journal = {Artificial Intelligence and Law},
  volume  = {33},
  number  = {1},
  pages   = {171--197},
  year    = {2025},
  doi     = {10.1007/s10506-023-09383-6}
}
```

Starts from the premise that freedom-of-information laws promote transparency but require exemptions,
and that deliberative-language detection is the most burdensome exemption — driving cost and delay in
open-records responses. Presents a detection model embedded in the *FOIA Assistant* system, designed
through human-factors studies and in operational testing at multiple US federal agencies.

**Use for us.** **The closest AI&Law paper to ours in *object*** — administrative government records,
transparency obligations, and a tool intended for real agency use. It demonstrates the journal
expects the transparency-law rationale stated up front and the deployment context reported honestly.
*(Crossref issues 2023 online-first; volume 33 is 2025.)*

### 6.2 ★★ Tinarrage et al. (2025) — Brazilian, empirical, efficiency-framed `[EMPIRICAL]`

```bibtex
@article{tinarrage2025empirical,
  author  = {Tinarrage, Rapha\"el and Ennes, Henrique and Resck, Lucas and Gomes, Lucas T. and
             Ponciano, Jean R. and Poco, Jorge},
  title   = {Empirical analysis of binding precedent efficiency in {Brazilian} {Supreme Court}
             via case classification},
  journal = {Artificial Intelligence and Law},
  year    = {2025},
  doi     = {10.1007/s10506-025-09458-6}
}
```

Uses case classification over Brazilian Supreme Court decisions to assess how efficiently *súmulas
vinculantes* actually operate. Deliberately two-sided: an NLP comparison **and** a legal analysis of
why binding precedents fail to reduce repetitive demand.

**Use for us.** **The single best venue-fit citation available.** Brazilian corpus, empirical method,
efficiency framing, recent, in AI&Law. Direct proof the journal accepts Brazilian data-driven
institutional analysis. Its two-sided structure is also the structure our paper should imitate.
*(Online-first; no volume/pages assigned at verification — check before submission.)*

### 6.3 ★ Vianna, de Moura & da Silva (2024) — the methodological sibling `[METHOD]`

```bibtex
@article{vianna2024topic,
  author  = {Vianna, Daniela and de Moura, Edleno Silva and da Silva, Altigran Soares},
  title   = {A topic discovery approach for unsupervised organization of legal document collections},
  journal = {Artificial Intelligence and Law},
  volume  = {32},
  number  = {4},
  pages   = {1045--1074},
  year    = {2024},
  doi     = {10.1007/s10506-023-09371-w}
}
```

Uncovers hidden topics in growing legal document collections, combining preprocessing variants with
learned vector representations (Doc2Vec, BERT-family). Validated on four datasets of short and long
**Brazilian Portuguese** legal documents; a team of **legal specialists** assessed the discovered
topics as unique and relevant and as accelerating their labelling work.

**Use for us.** **The template to imitate**: embeddings + unsupervised structure discovery on a
Portuguese-language legal corpus, **with human legal-expert validation of the resulting labels**.
Cite as the direct methodological antecedent and *match its validation design* — that expert
validation is the part our cluster-naming currently lacks.
*(Crossref issues 2023 online-first; volume 32 is 2024.)*

### 6.4 ★ Medvedeva, Wieling & Vols (2023) — the field's self-critique `[METHOD]`

```bibtex
@article{medvedeva2023rethinking,
  author  = {Medvedeva, Masha and Wieling, Martijn and Vols, Michel},
  title   = {Rethinking the field of automatic prediction of court decisions},
  journal = {Artificial Intelligence and Law},
  volume  = {31},
  number  = {1},
  pages   = {195--212},
  year    = {2023},
  doi     = {10.1007/s10506-021-09306-3}
}
```

Distinguishes three routinely-conflated tasks — outcome *identification*, outcome-based
*categorisation*, and genuine *forecasting* — and shows published studies misclassify themselves.
Argues that what the legal data actually contains determines which task is even performable.

**Use for us.** **Cite defensively and prominently.** It is the venue's own statement that
methodological honesty is a publication condition, and the strongest available argument that
descriptive, discipline-serving analysis beats another prediction benchmark. Use it to pre-empt "why
didn't you predict something?" and to justify our refusal to make breach claims.
*(Companion empirical anchor, also verified: Medvedeva, Vols & Wieling (2020), AI&Law 28(2):237–266,
`10.1007/s10506-019-09255-y`.)*

### 6.5 Further venue precedents (all DOI-verified)

| Key | Reference | What it establishes |
|---|---|---|
| `chen2019judicial` | Chen DL (2019) Judicial analytics and the great transformation of American law. *AI&Law* 27(1):15–42. `10.1007/s10506-018-9237-x` | The journal publishes work measuring institutional behaviour from records **and then arguing the normative consequence** — the technical result is never the endpoint `[EMPIRICAL]`/`[DOCTRINAL]` |
| `nunes2022quantitative` | Nunes JL, Hartmann IA (2022) A quantitative approach to ranking corporate law precedents in the Brazilian Superior Court of Justice. *AI&Law* 30(1):117–145. `10.1007/s10506-021-09290-8` | Brazilian institutional study at our scale (282,040 opinions); the pipeline that **constructs** the analysable structure from raw text is presented as part of the contribution, plus a qualitative legal reading `[EMPIRICAL]` |
| `bertalan2024attention` | Bertalan VGF, Ruiz EES (2024) Using attention methods to predict judicial outcomes. *AI&Law* 32(1):87–115. `10.1007/s10506-022-09342-7` | Documenting **how the corpus was harvested from official Brazilian electronic legal systems** is a reportable contribution; papers end with an interpretability pass, not a leaderboard `[EMPIRICAL]` |
| `simmler2023smart` | Simmler M, Brunner S, Canova G, Schedler K (2023) Smart criminal justice. *AI&Law* 31(2):213–237. `10.1007/s10506-022-09310-1` | The journal publishes **descriptive institutional** studies whose contribution is an accurate picture of practice plus a normative warning — structurally our move `[EMPIRICAL]` |
| `mohammadi2025topic` | Mohammadi M, Bruijn M, Wieling M, Vols M (2025) Combining topic modelling and citation network analysis... *AI&Law*, advance online. `10.1007/s10506-025-09471-9` | Unsupervised topic structure as a **navigation and organisation** instrument rather than a predictor, validated against a hand-annotated gold subset — a validation strategy to mirror `[METHOD]`/`[EMPIRICAL]` |
| `braun2024disagreement` | Braun D (2024) I beg to differ: how disagreement is handled in the annotation of legal ML data sets. *AI&Law* 32(3):839–862. `10.1007/s10506-023-09369-4` | Every surveyed legal ML dataset **erases annotator disagreement** and under-reports gold-standard derivation — directly relevant to how we report cluster naming and validation `[EMPIRICAL]` |
| `bex2025beyond` | Bex FJ (2025) AI, Law and beyond. *AI&Law* 33(1):253–270. `10.1007/s10506-024-09404-y` | IAAIL Presidential Address: the community wants **real AI systems for the legal field, developed and evaluated jointly with legal-domain partners** — an agency-partnered transparency instrument is exactly that `[DOCTRINAL]` |
| `branting2021scalable` | Branting LK, Pfeifer C, Brown B, et al. (2021) Scalable and explainable legal prediction. *AI&Law* 29(2):213–238. `10.1007/s10506-020-09273-1` | Explainability as a design constraint on a legal-domain ML system `[EMPIRICAL]` |
| `mandal2021unsupervised` | Mandal A, Ghosh K, Ghosh S, Mandal S (2021) Unsupervised approaches for measuring textual similarity between legal court case reports. *AI&Law* 29(3):417–451. `10.1007/s10506-020-09280-2` | In-venue precedent for **unsupervised similarity over legal text**, including embeddings `[EMPIRICAL]` |
| `habernal2024mining` | Habernal I, Faber D, Recchia N, et al. (2024) Mining legal arguments in court decisions. *AI&Law* 32(3):1–38. `10.1007/s10506-023-09361-y` | **The model for interdisciplinary construct validity** — categories over legal material developed *with* legal expertise, not imposed by engineers `[EMPIRICAL]` |

### 6.6 Venue self-description

```bibtex
@article{villata2022thirty,
  author  = {Villata, Serena and Araszkiewicz, Michal and Ashley, Kevin and
             Bench-Capon, Trevor and Branting, L. Karl and Conrad, Jack G. and Wyner, Adam},
  title   = {Thirty years of artificial intelligence and law: the third decade},
  journal = {Artificial Intelligence and Law},
  volume  = {30},
  number  = {4},
  pages   = {561--591},
  year    = {2022},
  doi     = {10.1007/s10506-022-09327-6}
}
```

Surveys the field's third decade and maps which sub-areas the journal considers its own — letting us
site our contribution on the community's own map rather than asserting fit. A companion editor's
introduction is also verified: Bench-Capon T (2022) AI&Law 30(4):475–479,
`10.1007/s10506-022-09325-8`. **The existing bib already has `benchcapon2012history`** — keep it.

---

<a name="7"></a>
## 7. Primary legal sources — verified

Federal texts retrieved from Planalto; Piauí texts from the Assembleia Legislativa do Piauí SAPL
system. Quoted provisions confirmed verbatim.

### 7.1 Constitution — CONFIRMED

- **Art. 37, caput** — "[...] obedecerá aos princípios de legalidade, impessoalidade, moralidade,
  publicidade e **eficiência** [...]" (Redação dada pela EC nº 19, de 1998). *Efficiency was indeed
  added by EC 19/1998; the original 1988 caput listed only four principles.*
- **Art. 5º, LXXVIII** — "a todos, no âmbito judicial e administrativo, são assegurados a razoável
  duração do processo e os meios que garantam a celeridade de sua tramitação." (Incluído pela
  EC nº 45, de 2004).
- **Art. 5º, XXXIV, "a"** — "o direito de petição aos Poderes Públicos em defesa de direitos ou
  contra ilegalidade ou abuso de poder". *Cite the caput of XXXIV alongside "a" — the
  "independentemente do pagamento de taxas" clause lives in the caput, not the alínea.*

URL: `https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm`
Amendments verified separately: EC 19/1998
(`.../constituicao/Emendas/emc/emc19.htm`) and EC 45/2004 (`.../emc45.htm`).

### 7.2 LAI — Lei nº 12.527/2011 — CONFIRMED

Strongest provisions for our argument: **art. 3º, I–II** (publicity as rule, secrecy as exception;
proactive disclosure independent of request) and especially **art. 8º, § 3º, III**: "possibilitar o
acesso automatizado por sistemas externos em formatos abertos, estruturados e **legíveis por
máquina**", with **V** requiring authenticity and integrity.

**Use for us.** Art. 8 § 3 III is the single best statutory hook for **machine auditability** — a
legal duty to make public information machine-processable, exactly the register our artefacts
operate in. **Stronger than the generic LAI reference currently in the bib.**

> **Caveat:** "Lei de Acesso à Informação (LAI)" is the *popular* name and is **not** in the official
> ementa. Write `Lei nº 12.527/2011 (Lei de Acesso à Informação — LAI)`.

URL: `https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2011/lei/l12527.htm`

### 7.3 LGPD — Lei nº 13.709/2018 — CONFIRMED

- **Art. 5º, III** — *dado anonimizado*: "dado relativo a titular que não possa ser identificado,
  considerando a utilização de meios técnicos razoáveis e disponíveis na ocasião de seu tratamento".
- **Art. 5º, XI** — *anonimização*: "utilização de meios técnicos razoáveis e disponíveis no momento
  do tratamento, por meio dos quais um dado perde a possibilidade de associação, direta ou indireta,
  a um indivíduo".
- **Art. 12** — "Os dados anonimizados não serão considerados dados pessoais para os fins desta Lei,
  salvo quando o processo de anonimização [...] for revertido [...] ou quando, com **esforços
  razoáveis**, puder ser revertido."

**Use for us.** **Art. 12 does the legal work for an anonymisation paper and is not currently cited.**
Its "esforços razoáveis" standard is a *risk* standard — pair it directly with Rocher et al. (4.4)
and Finck & Pallas (4.2), which supply the risk-gradient argument that makes it bite.

> **Correction:** the public-sector chapter (Capítulo IV) spans **arts. 23–32** (Seção I, arts. 23–30;
> Seção II, arts. 31–32). Do not label "23–30" as the chapter.

URL: `https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm`

### 7.4 Lei nº 9.784/1999 — CONFIRMED

- **Art. 2º** — principles including legalidade, finalidade, motivação, razoabilidade,
  proporcionalidade, moralidade, ampla defesa, contraditório, segurança jurídica, interesse público
  e eficiência.
- **Art. 49** — "Concluída a instrução de processo administrativo, a Administração tem o prazo de até
  trinta dias para decidir, salvo prorrogação por igual período expressamente motivada."

> **Precision point:** the 30 days run **from the close of the instruction phase**, not from filing.
> Papers routinely get this wrong. Ensure no sentence implies a 30-day limit on the whole process.

URL: `https://www.planalto.gov.br/ccivil_03/leis/l9784.htm`

### 7.5 Piauí — Lei nº 6.782, de 28 de março de 2016 — **CONFIRMED, and stronger than assumed**

Official ementa: *"Regula o processo administrativo no âmbito da Administração Pública do Estado do
Piauí."*

- **Art. 2º** — "O processo administrativo obedecerá, dentre outros, aos princípios da
  **transparência**, legalidade, finalidade, motivação, razoabilidade, proporcionalidade, moralidade,
  ampla defesa, contraditório, segurança jurídica, impessoalidade, **eficiência**, **celeridade**,
  **oficialidade**, publicidade, participação, proteção da confiança legítima e interesse público."

  **All four principles the paper relies on are literally present, and *transparência* is listed
  first** — a genuinely useful detail. The Piauí list is materially broader than the federal art. 2º.

- **Art. 35** — default deadlines: 2 days to docket, 15 to instruct, 10 to decide, each extendable
  once by an equal period on justified request.
- **Art. 36** — unjustified breach generates **disciplinary liability** for the responsible agents
  **without voiding the proceeding**.

URLs (both official ALEPI): `https://sapl.al.pi.leg.br/norma/3878` ·
`https://sapl.al.pi.leg.br/media/sapl/public/normajuridica/2016/3878/3878_texto_integral.pdf`

> **⚠ Transcription caveat.** The ALEPI PDF is a scan of the signed original; its OCR garbles art. 35's
> roman numerals (inciso I as "1 -", inciso III as "II -", "10 (dez)" as "1 O (dez)"). The
> reconstruction is defensible — § 2º cross-references "o prazo previsto no **inciso III** do caput",
> which requires three incisos — but **verify against the PDF page image before submission** and cite
> the page image if challenged.

### 7.6 Piauí — Lei Complementar nº 13/1994, art. 114 — **⚠ HAZARD: DO NOT CITE AS CURRENT LAW**

The law exists (*Estatuto dos Servidores Públicos Civis do Estado do Piauí*), but **art. 114 no
longer says what the draft assumes.**

- **Original 1994 wording**, parágrafo único: requests and reconsideration petitions "deverão ser
  despachados no prazo de 5 (cinco) dias e decididos dentro de **30 (trinta) dias**."
- **Current wording** (redação dada pela **Lei Complementar nº 261, de 25 de outubro de 2021**):
  art. 114 sets a **5-day window for the interested party to appeal** — a deadline on the *citizen*,
  not on the administration.

**That is the opposite of what a process-duration argument wants.** If the manuscript cites
"LC 13/1994, art. 114" for a 30-day administrative decision deadline, that deadline was **replaced in
2021 and is not in force.**

**Recommendation: drop it.** Lei 6.782/2016 art. 35 does the job cleanly, is in force, and concerns
administrative process generally rather than servant discipline. If kept, mark the version:
*"LC 13/1994, art. 114, parágrafo único, redação original, alterada pela LC 261/2021."*

URL: `https://www.al.pi.leg.br/servicos/ouvidoria/Ouvidoria/20250729094712/lei-complementar-13-1994.pdf`

### 7.7 EU Charter art. 41 — text CONFIRMED, pin-cite PARTIAL

Art. 41(1): "Every person has the right to have his or her affairs handled impartially, fairly and
**within a reasonable time** by the institutions, bodies, offices and agencies of the Union."
§2(a) right to be heard; §2(b) access to file; §2(c) duty to give reasons; §3 reparation; §4 language.

Verified at the EU Agency for Fundamental Rights: `https://fra.europa.eu/en/eu-charter/article/41-right-good-administration`,
which shows the **OJ C 303/17, 14.12.2007** reference.

> **⚠** EUR-Lex bot-blocks all automated access. The CELEX id `12012P/TXT` and the commonly-cited
> **2012 consolidated reference OJ C 326/391, 26.10.2012** were **not verified**. Confirm the 2012
> pin-cite manually before printing it, or cite the 2007 OJ reference that was verified.

### 7.8 BibTeX for the statutes

```bibtex
@misc{brasil1988cf,
  author       = {{Brasil}},
  title        = {Constitui\c{c}\~ao da Rep\'ublica Federativa do Brasil de 1988},
  year         = {1988},
  howpublished = {Bras\'ilia, DF: Presid\^encia da Rep\'ublica},
  note         = {Art. 5\textordmasculine, XXXIV, ``a'' e LXXVIII; art. 37, caput.
                  Texto compilado, com as altera\c{c}\~oes das Emendas Constitucionais
                  n\textordmasculine\ 19/1998 e n\textordmasculine\ 45/2004},
  url          = {https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm},
  urldate      = {2026-08-03}
}

@misc{brasil1999lei9784,
  author       = {{Brasil}},
  title        = {Lei n\textordmasculine\ 9.784, de 29 de janeiro de 1999: regula o processo
                  administrativo no \^ambito da Administra\c{c}\~ao P\'ublica Federal},
  year         = {1999},
  howpublished = {Di\'ario Oficial da Uni\~ao, Bras\'ilia, DF},
  url          = {https://www.planalto.gov.br/ccivil_03/leis/l9784.htm},
  urldate      = {2026-08-03}
}

@misc{piaui2016lei6782,
  author       = {{Piau\'i}},
  title        = {Lei n\textordmasculine\ 6.782, de 28 de mar\c{c}o de 2016: regula o processo
                  administrativo no \^ambito da Administra\c{c}\~ao P\'ublica do Estado do Piau\'i},
  year         = {2016},
  howpublished = {Teresina: Assembleia Legislativa do Estado do Piau\'i},
  url          = {https://sapl.al.pi.leg.br/norma/3878},
  urldate      = {2026-08-03}
}
```

`brasil2011lai` and `brasil2018lgpd` are already in `references.bib` — keep those keys, but add a
`note` pinning the specific articles (LAI art. 8 § 3 III; LGPD arts. 5 III, 5 XI, **12**).

---

<a name="8"></a>
## 8. How to position this paper for AI&Law reviewers

### 8.1 The structural problem, stated bluntly

The journal's scope has three baskets: (i) **formal or computational models of legal knowledge,
reasoning and decision-making**; (ii) **in-depth studies of innovative AI systems used in the legal
domain**; (iii) **legal, ethical and social implications of AI in law**.

Basket (i) is the journal's historic core — argumentation frameworks, case-based reasoning, deontic
logic. **Our paper is not in basket (i) and should not pretend to be.** It is a basket (ii) paper
with a basket (iii) argument attached. That is a legitimate and well-populated position — Suksi,
Branting, Di Porto, Liebwald, Vianna, Tinarrage, Nunes & Hartmann, Simmler all sit there — but it
means the burden of demonstrating legal relevance falls **entirely on us**. A formal-models paper
gets that for free.

**The most likely rejection sentence is: *"This is a competent process-mining paper that would be
better placed in an information-systems venue."*** Everything below targets that sentence.

### 8.2 What AI&Law reviewers demand that a purely technical paper omits

Distilled from reading across roughly ninety AI&Law records:

1. **A legal-institutional problem statement before any method.** Papers open with the legal or
   institutional pathology — FOIA processing delays, repetitive demand at the STF, the scarcity of
   Brazilian quantitative legal research — **not** with a dataset or a model gap. Branting (6.1) and
   Yeung (5.5) both do this explicitly.

2. **The law must be load-bearing, not decorative.** `ROTEIRO.md` §3 already states the right test:
   *if a reviewer can delete the word "law" and lose nothing, the framing failed.* Operationally,
   each major design decision needs a sentence tying it to a legal value. Why concluded-only cohorts?
   Why a *typical path* rather than a full model? Why anonymise at all? Each has a legal answer.

3. **Explicit legal grounding by name.** Actual statutes, doctrines and constitutional provisions
   cited and *discussed* — not dropped. Citing CF art. 37 is not legal analysis; legal analysis is:
   here is the principle, here is what it is taken to require, here is the contested reading, here is
   what our artefact contributes. The Wachter/Selbst pair (1.2/1.3) and the Craig/Bousta pair
   (2.1/2.2) exist in this file so you can show a live dispute rather than a settled slogan.

4. **A named forum, not "society".** Bovens (3.1) and Kemper & Kolkman (1.12) both insist
   accountability is a *relationship*. Name who receives the catalog and what they can do with it.
   Vagueness here reads as hand-waving.

5. **Legal-expert validation of computational output.** Vianna's topics, Nunes & Hartmann's
   rankings and Nai's process models were all assessed by domain specialists. Intrinsic metrics
   (silhouette, DBCV, modularity) are treated as necessary but **insufficient**. **Budget for a
   legal-specialist review of the cluster catalog** — this is the most commonly fatal omission.

6. **Task definition treated as a legal question.** Medvedeva (6.4): what task you *can* perform is
   determined by what the legal records actually contain. Expect to argue explicitly that our event
   records support a descriptive typology claim **and no more**.

7. **Explicit scope limits on legal use.** State plainly what the catalog is **not**: not evidence of
   illegality, not a compliance finding, not a basis for disciplinary action against named staff, not
   a decision-support system. Volunteering limits converts a vulnerability into a credibility signal.

8. **Limitations framed as risks *for legal use*, not ML caveats.** Not "we might improve F1 with
   more data" but "what happens if a decision-maker relies on this and it is wrong."

9. **Data provenance reported as a contribution.** Where the corpus came from, what was extracted,
   annotated, discarded, and by whom — Bertalan's crawler, Nunes & Hartmann's citation extraction,
   Braun's argument about disclosing gold-standard derivation. **Document the anonymisation and
   event-record extraction at that level of detail.**

10. **Explainability defended in legal terms.** Bibal (1.9): a legal-domain artefact carries an
    explainability obligation a technical artefact does not. Justify consensus clustering and
    human-readable typical paths on that ground, **not on accuracy**.

11. **Data protection handled as law, not engineering.** Frame the anonymisation arm against LGPD
    art. 12's "esforços razoáveis" standard (§7.3), not as a preprocessing ablation.

12. **Jurisdiction named, universality not claimed.** Papers name the jurisdiction in the title. Ours
    should say Brazilian state administration. Also explain SEI, *protocolo* and *unidade* early —
    reviewers will not be Brazilian administrative lawyers.

### 8.3 The five moves that most improve acceptance odds

**Move 1 — Lead with the *absent record*, not the pipeline.** Brauneis & Goodman (3.4) found
empirically that FOI requests fail mostly because governments *never created the records*. Frame the
contribution as producing the record that transparency law presupposes and rarely finds. This
converts "we applied clustering to government data" into "we built the artefact the
access-to-information regime assumes exists." **The single highest-leverage reframing available.**

**Move 2 — Make disclosure-vs-intelligibility the paper's spine.** Ananny & Crawford (1.1), Janssen
et al. (3.5) and Grimmelikhuijsen (1.11) jointly establish that publication ≠ transparency and that
*explainability* rather than *accessibility* drives the effect. The catalog is an intelligibility
layer over an already-public log. Say that in the abstract.

**Move 3 — Keep the deadline abstinence, and make it an argument.** Convert the restraint from a
limitation into a *methodological virtue*: a deadline claim requires per-process legal qualification
(which provision governs which act, when the clock starts, tolling, extensions) that an event log
cannot supply — precisely the inference Medvedeva et al. (6.4) criticise the prediction literature
for making. Then use Moynihan et al. (2.8) and Halling & Baekgaard (2.9) to give duration normative
weight through **administrative burden** rather than through breach, and take the rhetorical
structure wholesale from Piątek & Potěšil (2.5).

**Move 4 — Narrow the anonymisation novelty claim before a reviewer does it for you.** See §4.10.
Then report the result as a **legal finding**: if anonymisation does not materially degrade
clustering quality, that bears on the LGPD compliance/utility trade-off that Elkoumy et al. (4.11)
frame as an open problem and Fahrenkrog-Petersen et al. (4.12) formalise for control flow. Give it a
legal addressee: agencies can meet data-protection duties without forfeiting analytical value.

**Move 5 — Turn the catalog into a *method*, not a *result*.** Nickerson et al. (5.3) supplies an
established taxonomy-development method with explicit ending conditions and quality criteria. Framing
our 182 types as the output of a stated, stoppable, evaluable procedure — rather than as whatever
HDBSCAN returned — is the difference between "an auditable catalog" and "a clustering run." One
paragraph in Method; disproportionate payoff.

### 8.4 Risks to pre-empt in the manuscript

- **"This is process mining with a legal preface."** Mitigation: the legal framing must appear in the
  *Method* section, not only Introduction and Conclusion. At least one methodological choice should
  be visibly *driven* by a legal requirement rather than retrofitted.
- **"Single organisation, single state, non-generalisable."** Mitigation: claim *transferability of
  method* and treat SEAD-PI as a case study; note SEI is used across much of the Brazilian public
  sector, making the setting a family rather than a singleton. Suksi (1.8) and Simmler (6.5) are
  precedent that a single national context is publishable here.
- **"Your clusters were named by an LLM — on what authority are these legally meaningful types?"**
  The sharpest question you will face. Habernal (6.5) is the venue's model answer; Braun (6.5) shows
  reviewers care about how disagreement was handled. Mitigations: human validation by domain staff,
  inter-rater agreement, and an explicit statement that the types are **descriptive and revisable**,
  not normative classifications.
- **"Related work misses the closest precedent."** Unger et al. (5.1) and Nai et al. (5.2) are the two
  papers a knowledgeable reviewer will expect to see. Both must be cited **and differentiated**.

### 8.5 Minimum viable citation set

If nothing else is added, add these twelve. They cover every gap identified above.

| Purpose | Cite |
|---|---|
| Closest precedent — Brazilian court process mining | `unger2021jurimetrics` |
| Closest precedent — legal process mining of administrative procedure | `nai2026procurement` |
| Venue fit — government records + transparency law, in-venue | `branting2025sensitive` |
| Venue fit — Brazilian + empirical + in-venue | `tinarrage2025empirical` |
| Venue fit — administrative law + ADM, in-venue | `suksi2021administrative` |
| Method sibling — unsupervised legal taxonomy + expert validation | `vianna2024topic` |
| Taxonomy construction as a defensible method | `nickerson2013taxonomy` |
| Transparency ≠ disclosure | `ananny2018seeing` |
| The missing-record argument | `brauneis2018algorithmic` |
| Accountability definition (actor/forum/criteria) | `bovens2007analysing` |
| Methodological honesty, the venue's own standard | `medvedeva2023rethinking` |
| Prior work that narrows our anonymisation claim | `ferrao2022utility` |

---

<a name="9"></a>
## 9. Verification ledger

Counts below were produced mechanically: every DOI string in this file was extracted by regex and
re-resolved against Crossref in a final sweep. **All 88 resolved**, except the single non-resolving
DOI documented in the discard table below.

| Status | Count | Notes |
|---|---|---|
| **Distinct works recommended** | **91** | 62 with full BibTeX + 29 in the supporting tables |
| **— of which DOI-verified via Crossref** | 80 | Every entry carrying a `doi` field |
| **— of which verified without a DOI** | 11 | `edwards2017slave`, `brauneis2018algorithmic`, `ohm2010broken`, `halperin2011lawinbooks` (law reviews, poorly indexed in Crossref); `a29wp2014anonymisation`, `cjeu2025edpssrb` (institutional PDFs); `reneual2017modelrules`, `lipsky2010streetlevel` (ISBN); plus the 3 Brazilian statutes with BibTeX |
| **Additional verified works cited inline** | 2 | Medvedeva et al. (2020) `10.1007/s10506-019-09255-y`; Bench-Capon (2022) editor's introduction `10.1007/s10506-022-09325-8` |
| **Primary law confirmed at official source** | 10 provisions/instruments | CF/1988 (art. 37 caput; art. 5 LXXVIII; art. 5 XXXIV "a") · EC 19/1998 · EC 45/2004 · Lei 9.784/1999 · LAI · LGPD · Piauí Lei 6.782/2016 · Piauí LC 13/1994 · CFR art. 41 |
| **⚠ Hazard flagged** | 1 | Piauí LC 13/1994 art. 114 — the 30-day deadline was **repealed in 2021** |
| **⚠ Novelty claim affected** | 1 | `ferrao2022utility` narrows the "no prior work on anonymisation × clustering" claim (§4.10) |
| **⚠ Partial — confirm before printing** | 5 | CFR art. 41 2012 OJ pin-cite · *EDPS v SRB* ECLI · Halpérin end page/year · Anselmo & Ribas BRACIS edition · Hintze & El Emam end page · no ReNEUAL rule number claimed |
| **Confirmed gap** | 1 | No peer-reviewed **English-language** scholarship on the Brazilian constitutional efficiency principle — two independent searches agree |

### Discarded near-misses (documented so they are not re-introduced)

| Bad DOI | What it actually resolves to |
|---|---|
| `10.1109/ICPM.2019.00030` | Not PRETSA — a different ICPM item. Correct: `10.1109/ICPM.2019.00012` |
| `10.1016/j.is.2021.101908` | "Pattern on demand in transactional distributed databases" (Diop et al.) — unrelated |
| `10.1016/j.is.2023.102232` | A blockchain supply-chain security survey — unrelated. Correct venue for "Optimal event log sanitization" is *Data & Knowledge Engineering* 145:102175 |
| `10.1017/S1867299X00007121` | Does not resolve (404) |

**Sources used for verification:** Crossref REST API · OpenAlex · Semantic Scholar · ACL Anthology ·
Planalto · Assembleia Legislativa do Piauí (SAPL) · EU Agency for Fundamental Rights · CURIA ·
European Commission (WP216 PDF) · Duke Law Scholarship Repository · Yale JOLT · Utrecht Law Review ·
Russell Sage Foundation · paulohm.com.
