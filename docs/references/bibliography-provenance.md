# Bibliography provenance — `article/latex/references.bib`

How every entry in `references.bib` got there and how it was checked. Two passes, newest first.
Neither pass is normative: **the bib file itself is the artifact**; this is the audit trail behind it.

| pass | date | what it did | outcome |
|---|---|---|---|
| **2 — verification** | 2026-08-01 | every entry re-resolved against the Crossref REST API, treating prior `% TODO verify` marks as worthless | 61/61 checked; corrections, manual-retrieval list, one suspected fabrication |
| **1 — candidates** | 2026-07-11 | annotated proposals per topic, each verified against a primary source (ACL Anthology, publisher DOI, Crossref, arXiv, JOSS, LexML, EUR-Lex, planalto) | 27 new + 1 upgrade, absorbed into `references.bib` |

> **Retracted from pass 1.** Pass 1 records as a *KEY FINDING* that there is **"no prior work"**
> on anonymization impact on clustering quality. That claim does **not** hold — see
> `docs/references/lit-ai-law.md`, which states it "cannot stand as written" and supplies the
> prior work. The section is kept below as a record of what was believed in July; do not cite it.

Related: the topic surveys (`lit-*.md`) and the per-reference notes (`<key>.md`) in this folder;
`README.md` is the index.

---

## Pass 2 — full verification (2026-08-01)


**Target venue:** *Artificial Intelligence and Law* (Springer)
**Date of verification:** 2026-08-01
**Entries checked:** 61 / 61 (every entry treated as unverified regardless of prior `% TODO verify` status)

#### Result

| Status | Count |
|---|---|
| VERIFIED | 43 |
| CORRECTED | 18 |
| NOT_FOUND | 0 |
| HALLUCINATED / suspected fabrication | 0 |

**No fabricated references were found.** Every one of the 61 entries corresponds to a real
publication. This includes all the entries that looked riskiest on paper — the 2026-dated
Brazilian journal article, both 2025 Springer chapters, the 2025 EMNLP demo paper, and the
US law review note. All of their DOIs resolve to the claimed work.

The 18 corrections are metadata defects, not invention: missing page ranges, missing LNBIP/LNCS
volume numbers, `and others` truncation, preprint-vs-published title drift, one wrong entry type,
one wrong volume designation, and one DOI that has been withdrawn from the Crossref registry.

##### Methodology note

Publisher sites that block automated fetching (ScienceDirect, IEEE Xplore, ACM DL, Taylor &
Francis, MIT Press, nature.com, eur-lex, and Springer's SSO-redirecting chapter pages) were
routed around via the publisher's own deposited record — Crossref DOI content negotiation at
`api.crossref.org` / `doi.org` — cross-checked against DBLP, the ACL Anthology, arXiv's API,
institutional repositories (TU/e, SDU, QUT), PubMed, or the article PDF's own printed page
headers. No field in this report was inferred, and no DOI, volume, or page range was constructed.

---

#### 1. Summary table

| Citation key | Status | Confidence | Note |
|---|---|---|---|
| `reimers2019sbert` | CORRECTED | high | `@article` with a `booktitle` field — BibTeX silently drops it. Is EMNLP-**IJCNLP** 2019; pages 3982–3992 and DOI were missing |
| `gunther2007fuzzy` | VERIFIED | high | LNCS 4714, pp. 328–343 confirmed |
| `hochreiter1997lstm` | VERIFIED | high | All fields exact |
| `vanderaalst2016processmining` | VERIFIED | high | 2nd edition, DOI confirmed on Springer |
| `pesic2007declare` | CORRECTED | medium | "Helen Schonenberg" is correct. **Page range disputed across sources — omitted**; publisher is IEEE Computer Society |
| `traag2019leiden` | VERIFIED | high | 5233 is an article number, not a page; fine as-is |
| `brasil2018lgpd` | VERIFIED | high | Law nº 13.709/2018, DOU 15.8.2018, URL resolves. "(LGPD)" name added later by Lei 13.853/2019 |
| `pilan2022text` | VERIFIED | high | All six authors + diacritics correct |
| `lothritz2023evaluating` | VERIFIED | high | All nine authors correct; **no DOI exists** — do not add one |
| `benchcapon2012history` | CORRECTED | high | `and others` hides **24 authors**; full list supplied |
| `bukhsh2021processtransformer` | VERIFIED | high | Preprint only — no peer-reviewed venue exists |
| `campello2013hdbscan` | VERIFIED | high | LNCS 7819 (Part II) is correct, pp. 160–172 |
| `chen2024bgem3` | CORRECTED | high | **Title is wrong** (no "BGE" prefix; "Multi-Linguality"). Published at Findings of ACL 2024, pp. 2318–2335 |
| `cho2014gru` | CORRECTED | high | `and others` hides 7 authors; pages 1724–1734 + DOI missing |
| `dumas2018bpm` | VERIFIED | high | 2nd edition DOI correct (1st ed. is a different DOI) |
| `esser2021ekg` | VERIFIED | high | All fields exact |
| `evermann2017predicting` | VERIFIED | high | All fields exact |
| `greco2006clustering` | VERIFIED | high | DOI `10.1109/TKDE.2006.123` does resolve to this paper |
| `guidotti2018survey` | CORRECTED | high | Missing `articleno = {93}`; **year 2018 (online) vs 2019 (issue) ambiguity** |
| `ieee2012manifesto` | CORRECTED | high | **Corporate author is wrong** — canonical record lists 76 individual authors led by van der Aalst. Changes the in-text citation label |
| `lison2021anonymisation` | VERIFIED | high | All fields exact |
| `mcinnes2017hdbscan` | CORRECTED | high | **Was published** at IEEE ICDMW 2017, pp. 33–42 — arXiv-only `@article` drops the real venue |
| `mcinnes2018umap` | VERIFIED | high | Genuinely preprint-only; no venue to add |
| `moulavi2014dbcv` | VERIFIED | high | Author order and pp. 839–847 confirmed |
| `ramamaneiro2023dlppm` | VERIFIED | high | Vol 16(1):739–756 confirmed via DBLP final-issue record |
| `rozinat2008conformance` | VERIFIED | high | All fields exact |
| `song2009trace` | VERIFIED | high | LNBIP 17, pp. 109–120; year 2009 matches publisher |
| `suriadi2017imperfection` | VERIFIED | high | ⚠ A *2026* IS paper shares this exact title — confirm 2017 is intended |
| `tax2017lstm` | VERIFIED | high | LNCS 10253, pp. 477–492 confirmed |
| `vaswani2017attention` | CORRECTED | high | `and others` hides 8 authors; pages 5998–6008 missing; venue is **NIPS** 2017, not NeurIPS |
| `bencheikhlarbi2023clinical` | VERIFIED | high | All fields exact |
| `stubbs2015automated` | VERIFIED | high | Vol 58 (Suppl), pp. S11–S19 confirmed |
| `dernoncourt2017deidentification` | VERIFIED | high | All fields exact |
| `microsoftpresidio` | CORRECTED | high | **Repo 301-redirects out of the Microsoft org**; year 2020 wrong (created 2018); title is a paraphrase |
| `zaratiana2024gliner` | VERIFIED | high | All fields exact |
| `zaratiana2025gliner2` | CORRECTED | high | **Published title differs from the preprint title**; author is **George**, not "Georgi", Hurn-Maloney; DOI missing |
| `blondel2008fast` | VERIFIED | high | All fields exact |
| `rousseeuw1987silhouettes` | VERIFIED | high | Correctly has no issue number |
| `daviesbouldin1979measure` | CORRECTED | high | **Volume is `PAMI-1`**, not `1` |
| `calinski1974dendrite` | VERIFIED | medium | Journal name correct (the split into "Theory and Methods" came in 1976). **Given names unconfirmed — publisher prints initials only** |
| `mcinnes2017hdbscanjoss` | VERIFIED | high | Matches JOSS's own recommended citation |
| `mcinnes2018umapsoftware` | VERIFIED | high | Exact match incl. `Gro{\ss}berger` |
| `strehl2002ensembles` | CORRECTED | high | **DOI is a withdrawn Crossref DOI** — resolves to the deleted-DOI tombstone. Must be removed |
| `fred2005evidence` | VERIFIED | high | All fields exact |
| `limaesilva2026analise` | VERIFIED | high | Real; DOI resolves; all four authors confirmed. Diacritics should be restored |
| `araujo2023mineracao` | CORRECTED | high | Missing `pages = {203--218}`. (The PDF misprints its own DOI as `v14i27`; the entry has the correct resolving one) |
| `delgado2022discovery` | CORRECTED | high | Missing `pages = {1--10}`; subtitle is lowercase "a case study" |
| `racis2025donot` | CORRECTED | high | Missing **LNBIP volume 554**; title is "Do **not** Stay Behind" |
| `trottier2025using` | CORRECTED | high | **`booktitle` missing entirely**; venue is ICPM 2024 Workshops, LNBIP 533, pp. 572–585 |
| `bose2009context` | VERIFIED | high | All fields exact |
| `deleoni2016general` | VERIFIED | high | All fields exact |
| `berti2023abstractions` | VERIFIED | high | LNBIP 492, pp. 427–439. Year 2023 (DBLP/workshop) vs 2024 (Springer imprint) is a style choice |
| `vidgof2023large` | VERIFIED | high | LNBIP 490, pp. 107–123 confirmed |
| `teinemaa2019outcome` | VERIFIED | high | `articleno = {17}` confirmed via DBLP's `17:1--17:57` |
| `rocha2024critical` | VERIFIED | high | Vol 54, art. 106023, all four authors confirmed |
| `brasil2011lai` | VERIFIED | high | DOU publication **was** 18.11.2011, in the *Edição extra*. ⚠ Not cited anywhere in `main.tex` |
| `canedo2022evaluating` | VERIFIED | high | **LNBIP 455 confirmed** — the `% TODO verify series/volume` can be cleared |
| `erickson2019comparative` | VERIFIED | high | Start page 859 confirmed. **End page could not be confirmed** — but start-page-only is correct Bluebook form |
| `eu2016gdpr` | CORRECTED | high | Title contains a literal `...` ellipsis; OJ reference and URL were already correct |
| `kipf2017gcn` | VERIFIED | high | ICLR 2017, OpenReview.net. ⚠ Not cited in `main.tex` |
| `williams1992reinforce` | VERIFIED | high | Vol 8, pp. 229–256. Omitting `number` correctly sidesteps a 3 vs 3-4 source conflict. ⚠ Not cited in `main.tex` |

##### Cross-check against the manuscript

- 58 of the 61 entries are cited in `main.tex`; there are **no dangling `\cite` keys**.
- Uncited: `kipf2017gcn`, `williams1992reinforce` (both documented as intentional in the `.bib`
  header) and **`brasil2011lai`**, which is *not* documented as intentional. Either cite the
  LAI or drop the entry — Springer production will flag an uncited bibliography item.

##### One change that alters the in-text citation string

`ieee2012manifesto` currently renders as **(IEEE Task Force on Process Mining 2012)**. Correcting
the author field makes it render as **(van der Aalst et al. 2012)**. Check the surrounding prose in
`main.tex` before applying — if the sentence reads "the IEEE Task Force's manifesto", the corrected
citation will no longer agree with it. All other corrections leave the author-year label unchanged.

---

#### 2. Corrected BibTeX

Complete replacement file. VERIFIED entries are reproduced unchanged; CORRECTED entries carry a
`%% CORRECTED:` comment naming what was fixed. All `% TODO verify` markers have been resolved and
removed. Diacritics restored where the source prints them.

```bibtex
%% ===================================================================
%% references.bib — bibliography for main.tex
%% Springer author–year (natbib).
%%
%% All 61 entries verified against primary sources 2026-08-01
%% (publisher pages, Crossref DOI records, DBLP, ACL Anthology, arXiv,
%% institutional repositories). See docs/references/bibliography-provenance.md.
%% ===================================================================

%% ---- Core method / process mining ----

%% CORRECTED: @article -> @inproceedings (booktitle was being silently dropped);
%% venue is EMNLP-IJCNLP; added pages + DOI + publisher/address.
@inproceedings{reimers2019sbert,
  author    = {Reimers, Nils and Gurevych, Iryna},
  title     = {Sentence-{BERT}: sentence embeddings using {Siamese} {BERT}-networks},
  booktitle = {Proceedings of the 2019 Conference on Empirical Methods in Natural Language
               Processing and the 9th International Joint Conference on Natural Language
               Processing (EMNLP-IJCNLP)},
  publisher = {Association for Computational Linguistics},
  address   = {Hong Kong, China},
  month     = nov,
  pages     = {3982--3992},
  year      = {2019},
  doi       = {10.18653/v1/D19-1410},
  url       = {https://aclanthology.org/D19-1410/}
}

@inproceedings{gunther2007fuzzy,
  author    = {G{\"u}nther, Christian W. and van der Aalst, Wil M. P.},
  title     = {Fuzzy mining -- adaptive process simplification based on multi-perspective metrics},
  booktitle = {Business Process Management (BPM 2007), LNCS 4714},
  publisher = {Springer},
  pages     = {328--343},
  year      = {2007},
  doi       = {10.1007/978-3-540-75183-0_24}
}

@article{hochreiter1997lstm,
  author  = {Hochreiter, Sepp and Schmidhuber, J{\"u}rgen},
  title   = {Long short-term memory},
  journal = {Neural Computation},
  volume  = {9},
  number  = {8},
  pages   = {1735--1780},
  year    = {1997},
  doi     = {10.1162/neco.1997.9.8.1735}
}

@book{vanderaalst2016processmining,
  author    = {van der Aalst, Wil M. P.},
  title     = {Process mining: data science in action},
  edition   = {2nd},
  publisher = {Springer},
  year      = {2016},
  doi       = {10.1007/978-3-662-49851-4}
}

%% CORRECTED: publisher is the IEEE Computer Society imprint.
%% pages OMITTED DELIBERATELY — DBLP says 287--300, the TU/e repository says
%% 287--298, and IEEE deposited a start-page-only record. Not confirmable;
%% the DOI is a complete locator. See "NEEDS MANUAL RETRIEVAL".
@inproceedings{pesic2007declare,
  author    = {Pesic, Maja and Schonenberg, Helen and van der Aalst, Wil M. P.},
  title     = {{DECLARE}: full support for loosely-structured processes},
  booktitle = {11th IEEE International Enterprise Distributed Object Computing Conference (EDOC 2007)},
  publisher = {IEEE Computer Society},
  year      = {2007},
  doi       = {10.1109/EDOC.2007.14}
}

@article{traag2019leiden,
  author  = {Traag, Vincent A. and Waltman, Ludo and van Eck, Nees Jan},
  title   = {From {Louvain} to {Leiden}: guaranteeing well-connected communities},
  journal = {Scientific Reports},
  volume  = {9},
  pages   = {5233},
  year    = {2019},
  doi     = {10.1038/s41598-019-41695-z}
}

%% CORRECTED: 'and others' expanded to the full 24-author list.
@article{benchcapon2012history,
  author  = {Bench-Capon, Trevor and Araszkiewicz, Micha{\l} and Ashley, Kevin
             and Atkinson, Katie and Bex, Floris and Borges, Filipe
             and Bourcier, Dani{\`e}le and Bourgine, Paul and Conrad, Jack G.
             and Francesconi, Enrico and Gordon, Thomas F. and Governatori, Guido
             and Leidner, Jochen L. and Lewis, David D. and Loui, Ronald P.
             and McCarty, L. Thorne and Prakken, Henry and Schilder, Frank
             and Schweighofer, Erich and Thompson, Paul and Tyrrell, Alex
             and Verheij, Bart and Walton, Douglas N. and Wyner, Adam Z.},
  title     = {A history of {AI} and {Law} in 50 papers: 25 years of the international
               conference on {AI} and {Law}},
  journal   = {Artificial Intelligence and Law},
  volume    = {20},
  number    = {3},
  pages     = {215--319},
  year      = {2012},
  publisher = {Springer},
  doi       = {10.1007/s10506-012-9131-x}
}

%% Preprint only — DBLP indexes it solely as CoRR; no peer-reviewed venue exists.
@misc{bukhsh2021processtransformer,
  author  = {Bukhsh, Zaharah A. and Saeed, Aaqib and Dijkman, Remco M.},
  title   = {{ProcessTransformer}: predictive business process monitoring with transformer network},
  year    = {2021},
  howpublished = {arXiv preprint arXiv:2104.00721},
  url     = {https://arxiv.org/abs/2104.00721}
}

@inproceedings{campello2013hdbscan,
  author    = {Campello, Ricardo J. G. B. and Moulavi, Davoud and Sander, J{\"o}rg},
  title     = {Density-based clustering based on hierarchical density estimates},
  booktitle = {Advances in Knowledge Discovery and Data Mining (PAKDD 2013), Part II, LNCS 7819},
  publisher = {Springer},
  pages     = {160--172},
  year      = {2013},
  doi       = {10.1007/978-3-642-37456-2_14}
}

%% CORRECTED: title had a spurious "BGE" prefix and said "multi-lingual" where the
%% paper says "Multi-Linguality"; it was NOT preprint-only — published at Findings
%% of ACL 2024 with pages and a DOI. First author's given name is "Jianlyu" in the
%% published version ("Jianlv" on arXiv).
@inproceedings{chen2024bgem3,
  author    = {Chen, Jianlyu and Xiao, Shitao and Zhang, Peitian and Luo, Kun
               and Lian, Defu and Liu, Zheng},
  title     = {{M3}-embedding: multi-linguality, multi-functionality, multi-granularity
               text embeddings through self-knowledge distillation},
  booktitle = {Findings of the Association for Computational Linguistics: ACL 2024},
  publisher = {Association for Computational Linguistics},
  address   = {Bangkok, Thailand},
  month     = aug,
  pages     = {2318--2335},
  year      = {2024},
  doi       = {10.18653/v1/2024.findings-acl.137},
  url       = {https://aclanthology.org/2024.findings-acl.137/}
}

%% CORRECTED: 'and others' expanded to 7 authors; added pages + DOI.
@inproceedings{cho2014gru,
  author    = {Cho, Kyunghyun and van Merri{\"e}nboer, Bart and Gulcehre, Caglar
               and Bahdanau, Dzmitry and Bougares, Fethi and Schwenk, Holger
               and Bengio, Yoshua},
  title     = {Learning phrase representations using {RNN} encoder--decoder for
               statistical machine translation},
  booktitle = {Proceedings of the 2014 Conference on Empirical Methods in Natural
               Language Processing (EMNLP)},
  publisher = {Association for Computational Linguistics},
  address   = {Doha, Qatar},
  month     = oct,
  pages     = {1724--1734},
  year      = {2014},
  doi       = {10.3115/v1/D14-1179},
  url       = {https://aclanthology.org/D14-1179/}
}

@book{dumas2018bpm,
  author    = {Dumas, Marlon and La Rosa, Marcello and Mendling, Jan and Reijers, Hajo A.},
  title     = {Fundamentals of business process management},
  edition   = {2nd},
  publisher = {Springer},
  year      = {2018},
  doi       = {10.1007/978-3-662-56509-4}
}

@article{esser2021ekg,
  author  = {Esser, Stefan and Fahland, Dirk},
  title   = {Multi-dimensional event data in graph databases},
  journal = {Journal on Data Semantics},
  volume  = {10},
  number  = {1--2},
  pages   = {109--141},
  year    = {2021},
  doi     = {10.1007/s13740-021-00122-1}
}

@article{evermann2017predicting,
  author  = {Evermann, Joerg and Rehse, Jana-Rebecca and Fettke, Peter},
  title   = {Predicting process behaviour using deep learning},
  journal = {Decision Support Systems},
  volume  = {100},
  pages   = {129--140},
  year    = {2017},
  doi     = {10.1016/j.dss.2017.04.003}
}

@article{greco2006clustering,
  author  = {Greco, Gianluigi and Guzzo, Antonella and Pontieri, Luigi and Sacc{\`a}, Domenico},
  title   = {Discovering expressive process models by clustering log traces},
  journal = {IEEE Transactions on Knowledge and Data Engineering},
  volume  = {18},
  number  = {8},
  pages   = {1010--1027},
  year    = {2006},
  doi     = {10.1109/TKDE.2006.123}
}

%% CORRECTED: added articleno 93 (ACM cites this as Article 93, 42 pages).
%% YEAR AMBIGUITY: online-first 2018-08-22, print issue 2019-09-30; DBLP says 2019.
@article{guidotti2018survey,
  author    = {Guidotti, Riccardo and Monreale, Anna and Ruggieri, Salvatore
               and Turini, Franco and Giannotti, Fosca and Pedreschi, Dino},
  title     = {A survey of methods for explaining black box models},
  journal   = {ACM Computing Surveys},
  volume    = {51},
  number    = {5},
  articleno = {93},
  pages     = {93:1--93:42},
  year      = {2018},
  doi       = {10.1145/3236009}
}

%% CORRECTED: the canonical record does NOT use a corporate author. Crossref and
%% Springer list 76 individual authors led by van der Aalst; the IEEE Task Force is
%% the body that produced the manifesto, credited in the text.
%% !! This changes the in-text citation from (IEEE Task Force...) to (van der Aalst et al.)
@inproceedings{ieee2012manifesto,
  author    = {van der Aalst, Wil and Adriansyah, Arya and Alves de Medeiros, Ana Karla
               and others},
  title     = {Process mining manifesto},
  booktitle = {Business Process Management Workshops (BPM 2011), Part I, LNBIP 99},
  publisher = {Springer},
  pages     = {169--194},
  year      = {2012},
  doi       = {10.1007/978-3-642-28108-2_19}
}

@inproceedings{lison2021anonymisation,
  author    = {Lison, Pierre and Pil{\'a}n, Ildik{\'o} and S{\'a}nchez, David
               and Batet, Montserrat and {\O}vrelid, Lilja},
  title     = {Anonymisation models for text data: state of the art, challenges and
               future directions},
  booktitle = {Proceedings of the 59th Annual Meeting of the Association for Computational
               Linguistics and the 11th International Joint Conference on Natural Language
               Processing (Volume 1: Long Papers)},
  publisher = {Association for Computational Linguistics},
  pages     = {4188--4203},
  year      = {2021},
  doi       = {10.18653/v1/2021.acl-long.323}
}

%% CORRECTED: this was NOT preprint-only. Published at IEEE ICDMW 2017, pp. 33--42.
@inproceedings{mcinnes2017hdbscan,
  author    = {McInnes, Leland and Healy, John},
  title     = {Accelerated hierarchical density based clustering},
  booktitle = {2017 IEEE International Conference on Data Mining Workshops (ICDMW)},
  publisher = {IEEE},
  pages     = {33--42},
  year      = {2017},
  doi       = {10.1109/ICDMW.2017.12}
}

%% Genuinely preprint-only: arXiv reports no journal reference. Distinct from the
%% JOSS software paper (mcinnes2018umapsoftware) — do not merge them.
@misc{mcinnes2018umap,
  author  = {McInnes, Leland and Healy, John and Melville, James},
  title   = {{UMAP}: uniform manifold approximation and projection for dimension reduction},
  year    = {2018},
  howpublished = {arXiv preprint arXiv:1802.03426},
  url     = {https://arxiv.org/abs/1802.03426}
}

@inproceedings{moulavi2014dbcv,
  author    = {Moulavi, Davoud and Jaskowiak, Pablo A. and Campello, Ricardo J. G. B.
               and Zimek, Arthur and Sander, J{\"o}rg},
  title     = {Density-based clustering validation},
  booktitle = {Proceedings of the 2014 SIAM International Conference on Data Mining (SDM)},
  publisher = {SIAM},
  pages     = {839--847},
  year      = {2014},
  doi       = {10.1137/1.9781611973440.96}
}

@article{ramamaneiro2023dlppm,
  author  = {Rama-Maneiro, Efr{\'e}n and Vidal, Juan C. and Lama, Manuel},
  title   = {Deep learning for predictive business process monitoring: review and benchmark},
  journal = {IEEE Transactions on Services Computing},
  volume  = {16},
  number  = {1},
  pages   = {739--756},
  year    = {2023},
  doi     = {10.1109/TSC.2021.3139807}
}

@article{rozinat2008conformance,
  author  = {Rozinat, Anne and van der Aalst, Wil M. P.},
  title   = {Conformance checking of processes based on monitoring real behavior},
  journal = {Information Systems},
  volume  = {33},
  number  = {1},
  pages   = {64--95},
  year    = {2008},
  doi     = {10.1016/j.is.2007.07.001}
}

@inproceedings{song2009trace,
  author    = {Song, Minseok and G{\"u}nther, Christian W. and van der Aalst, Wil M. P.},
  title     = {Trace clustering in process mining},
  booktitle = {Business Process Management Workshops (BPM 2008), LNBIP 17},
  publisher = {Springer},
  pages     = {109--120},
  year      = {2009},
  doi       = {10.1007/978-3-642-00328-8_11}
}

@article{suriadi2017imperfection,
  author  = {Suriadi, Suriadi and Andrews, Robert and ter Hofstede, Arthur H. M.
             and Wynn, Moe T.},
  title   = {Event log imperfection patterns for process mining: towards a systematic
             approach to cleaning event logs},
  journal = {Information Systems},
  volume  = {64},
  pages   = {132--150},
  year    = {2017},
  doi     = {10.1016/j.is.2016.07.011}
}

@inproceedings{tax2017lstm,
  author    = {Tax, Niek and Verenich, Ilya and La Rosa, Marcello and Dumas, Marlon},
  title     = {Predictive business process monitoring with {LSTM} neural networks},
  booktitle = {Advanced Information Systems Engineering (CAiSE 2017), LNCS 10253},
  publisher = {Springer},
  pages     = {477--492},
  year      = {2017},
  doi       = {10.1007/978-3-319-59536-8_30}
}

%% CORRECTED: 'and others' expanded to 8 authors; added pages; the 2017 conference
%% was named NIPS (the rename to NeurIPS happened in 2018). No DOI exists.
@inproceedings{vaswani2017attention,
  author    = {Vaswani, Ashish and Shazeer, Noam and Parmar, Niki
               and Uszkoreit, Jakob and Jones, Llion and Gomez, Aidan N.
               and Kaiser, {\L}ukasz and Polosukhin, Illia},
  title     = {Attention is all you need},
  booktitle = {Advances in Neural Information Processing Systems 30 (NIPS 2017)},
  pages     = {5998--6008},
  year      = {2017},
  note      = {arXiv:1706.03762}
}

%% ---- PII anonymization / de-identification ----

@misc{brasil2018lgpd,
  author       = {{Brasil}},
  title        = {Lei n\textordmasculine{} 13.709, de 14 de agosto de 2018. Lei Geral de
                  Prote\c{c}\~ao de Dados Pessoais (LGPD)},
  year         = {2018},
  howpublished = {Di\'ario Oficial da Uni\~ao, Bras\'ilia, DF, 15 ago. 2018},
  note         = {Disp\~oe sobre a prote\c{c}\~ao de dados pessoais; altera a Lei
                  n\textordmasculine{} 12.965/2014 (Marco Civil da Internet)},
  url          = {https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm}
}

@article{pilan2022text,
  author    = {Pil{\'a}n, Ildik{\'o} and Lison, Pierre and {\O}vrelid, Lilja
               and Papadopoulou, Anthi and S{\'a}nchez, David and Batet, Montserrat},
  title     = {The text anonymization benchmark ({TAB}): a dedicated corpus and evaluation
               framework for text anonymization},
  journal   = {Computational Linguistics},
  volume    = {48},
  number    = {4},
  pages     = {1053--1101},
  year      = {2022},
  publisher = {MIT Press},
  doi       = {10.1162/coli_a_00458},
  url       = {https://aclanthology.org/2022.cl-4.19/}
}

%% No DOI exists for this paper — the ACL Anthology assigns none. Do not add one.
@inproceedings{lothritz2023evaluating,
  author    = {Lothritz, Cedric and Lebichot, Bertrand and Allix, Kevin and Ezzini, Saad
               and Bissyand{\'e}, Tegawend{\'e} and Klein, Jacques and Boytsov, Andrey
               and Lefebvre, Cl{\'e}ment and Goujon, Anne},
  title     = {Evaluating the impact of text de-identification on downstream {NLP} tasks},
  booktitle = {Proceedings of the 24th Nordic Conference on Computational Linguistics (NoDaLiDa)},
  publisher = {University of Tartu Library},
  address   = {T{\'o}rshavn, Faroe Islands},
  month     = may,
  pages     = {10--16},
  year      = {2023},
  url       = {https://aclanthology.org/2023.nodalida-1.2/}
}

@inproceedings{bencheikhlarbi2023clinical,
  author    = {Ben Cheikh Larbi, Iyadh and Burchardt, Aljoscha and Roller, Roland},
  title     = {Clinical text anonymization, its influence on downstream {NLP} tasks and
               the risk of re-identification},
  booktitle = {Proceedings of the 17th Conference of the European Chapter of the Association
               for Computational Linguistics: Student Research Workshop},
  publisher = {Association for Computational Linguistics},
  pages     = {105--111},
  year      = {2023},
  doi       = {10.18653/v1/2023.eacl-srw.11},
  url       = {https://aclanthology.org/2023.eacl-srw.11/}
}

@article{stubbs2015automated,
  author  = {Stubbs, Amber and Kotfila, Christopher and Uzuner, {\"O}zlem},
  title   = {Automated systems for the de-identification of longitudinal clinical narratives:
             overview of 2014 i2b2/{UTH}ealth shared task track 1},
  journal = {Journal of Biomedical Informatics},
  volume  = {58},
  pages   = {S11--S19},
  year    = {2015},
  doi     = {10.1016/j.jbi.2015.06.007}
}

@article{dernoncourt2017deidentification,
  author  = {Dernoncourt, Franck and Lee, Ji Young and Uzuner, {\"O}zlem and Szolovits, Peter},
  title   = {De-identification of patient notes with recurrent neural networks},
  journal = {Journal of the American Medical Informatics Association},
  volume  = {24},
  number  = {3},
  pages   = {596--606},
  year    = {2017},
  doi     = {10.1093/jamia/ocw156}
}

%% CORRECTED: github.com/microsoft/presidio now 301-redirects to
%% github.com/data-privacy-stack/presidio (project moved to community governance).
%% Year 2020 was wrong: repo created 2018-05-04, first release v0.1.0 2018-12-18.
%% Title replaced with the project's own name from its README.
@misc{microsoftpresidio,
  author       = {{Microsoft}},
  title        = {Presidio: data protection and de-identification {SDK}},
  howpublished = {\url{https://github.com/data-privacy-stack/presidio}},
  year         = {2018},
  note         = {Open-source (MIT); NER + regex + checksum recognizers. Originally
                  developed by Microsoft, now community-governed under the Data Privacy
                  Stack organization. Accessed 2026-08-01}
}

@inproceedings{zaratiana2024gliner,
  author    = {Zaratiana, Urchade and Tomeh, Nadi and Holat, Pierre and Charnois, Thierry},
  title     = {{GLiNER}: generalist model for named entity recognition using bidirectional
               transformer},
  booktitle = {Proceedings of the 2024 Conference of the North American Chapter of the
               Association for Computational Linguistics: Human Language Technologies
               (Volume 1: Long Papers)},
  publisher = {Association for Computational Linguistics},
  pages     = {5364--5376},
  year      = {2024},
  doi       = {10.18653/v1/2024.naacl-long.300},
  url       = {https://aclanthology.org/2024.naacl-long.300/}
}

%% CORRECTED: the title changed between preprint and publication — the entry cited the
%% arXiv title against an EMNLP booktitle. Author is George, not "Georgi", Hurn-Maloney.
%% Added the confirmed DOI. Pages 130--140 and the EMNLP 2025 Demos venue were correct.
@inproceedings{zaratiana2025gliner2,
  author    = {Zaratiana, Urchade and Pasternak, Gil and Boyd, Oliver
               and Hurn-Maloney, George and Lewis, Ash},
  title     = {{GLiNER2}: schema-driven multi-task learning for structured information extraction},
  booktitle = {Proceedings of the 2025 Conference on Empirical Methods in Natural Language
               Processing: System Demonstrations},
  publisher = {Association for Computational Linguistics},
  address   = {Suzhou, China},
  month     = nov,
  pages     = {130--140},
  year      = {2025},
  doi       = {10.18653/v1/2025.emnlp-demos.10},
  url       = {https://aclanthology.org/2025.emnlp-demos.10/},
  note      = {Preprint: arXiv:2507.18546}
}

%% ---- Graph / clustering algorithms ----

@article{blondel2008fast,
  author  = {Blondel, Vincent D. and Guillaume, Jean-Loup and Lambiotte, Renaud
             and Lefebvre, Etienne},
  title   = {Fast unfolding of communities in large networks},
  journal = {Journal of Statistical Mechanics: Theory and Experiment},
  volume  = {2008},
  number  = {10},
  pages   = {P10008},
  year    = {2008},
  doi     = {10.1088/1742-5468/2008/10/P10008}
}

@article{rousseeuw1987silhouettes,
  author  = {Rousseeuw, Peter J.},
  title   = {Silhouettes: a graphical aid to the interpretation and validation of
             cluster analysis},
  journal = {Journal of Computational and Applied Mathematics},
  volume  = {20},
  pages   = {53--65},
  year    = {1987},
  doi     = {10.1016/0377-0427(87)90125-7}
}

%% CORRECTED: volume is PAMI-1, not 1. IEEE used the PAMI-n designation until it
%% switched to plain numbering.
@article{daviesbouldin1979measure,
  author  = {Davies, David L. and Bouldin, Donald W.},
  title   = {A cluster separation measure},
  journal = {IEEE Transactions on Pattern Analysis and Machine Intelligence},
  volume  = {PAMI-1},
  number  = {2},
  pages   = {224--227},
  year    = {1979},
  doi     = {10.1109/TPAMI.1979.4766909}
}

%% Journal name confirmed correct: the split into "Communications in Statistics -
%% Theory and Methods" happened in 1976, after this 1974 vol. 3 article.
%% Given names left as initials: the publisher record prints initials only and the
%% second author's given name is contested (Jerzy vs Joachim). See report.
@article{calinski1974dendrite,
  author  = {Cali{\'n}ski, T. and Harabasz, J.},
  title   = {A dendrite method for cluster analysis},
  journal = {Communications in Statistics},
  volume  = {3},
  number  = {1},
  pages   = {1--27},
  year    = {1974},
  doi     = {10.1080/03610927408827101}
}

@article{mcinnes2017hdbscanjoss,
  author  = {McInnes, Leland and Healy, John and Astels, Steve},
  title   = {hdbscan: hierarchical density based clustering},
  journal = {Journal of Open Source Software},
  volume  = {2},
  number  = {11},
  pages   = {205},
  year    = {2017},
  doi     = {10.21105/joss.00205}
}

@article{mcinnes2018umapsoftware,
  author  = {McInnes, Leland and Healy, John and Saul, Nathaniel and Gro{\ss}berger, Lukas},
  title   = {{UMAP}: uniform manifold approximation and projection},
  journal = {Journal of Open Source Software},
  volume  = {3},
  number  = {29},
  pages   = {861},
  year    = {2018},
  doi     = {10.21105/joss.00861}
}

%% ---- Cluster ensembles / consensus clustering ----

%% CORRECTED: the DOI was REMOVED. 10.1162/153244303321897735 is a withdrawn Crossref
%% DOI that resolves to crossref.org/deleted_DOI.html. JMLR assigns this article no DOI.
@article{strehl2002ensembles,
  author  = {Strehl, Alexander and Ghosh, Joydeep},
  title   = {Cluster ensembles --- a knowledge reuse framework for combining multiple partitions},
  journal = {Journal of Machine Learning Research},
  volume  = {3},
  pages   = {583--617},
  year    = {2002},
  url     = {https://www.jmlr.org/papers/v3/strehl02a.html}
}

@article{fred2005evidence,
  author  = {Fred, Ana L. N. and Jain, Anil K.},
  title   = {Combining multiple clusterings using evidence accumulation},
  journal = {IEEE Transactions on Pattern Analysis and Machine Intelligence},
  volume  = {27},
  number  = {6},
  pages   = {835--850},
  year    = {2005},
  doi     = {10.1109/TPAMI.2005.113}
}

%% ---- Process mining in public administration / e-government ----

%% Diacritics restored from the published record.
@article{limaesilva2026analise,
  author  = {Lima e Silva, Fernando Jorge Ebrahim and Rocha, Marcelo Lisboa
             and Barbosa, Gentil Veloso and Lisboa, Marcelo da Silva},
  title   = {An{\'a}lise de processos administrativos no setor p{\'u}blico via
             minera{\c{c}}{\~a}o de processos: um estudo de caso no Tribunal Regional
             Eleitoral do Tocantins},
  journal = {Revista DCS},
  volume  = {23},
  number  = {88},
  pages   = {e4864},
  year    = {2026},
  issn    = {2224-4131},
  doi     = {10.54899/dcs.v23i88.4864},
  url     = {https://ojs.revistadcs.com/index.php/revista/article/view/4864}
}

%% CORRECTED: added the missing page range 203--218 (read off the PDF's own page headers).
%% NB the published PDF misprints its own DOI as v14i27.567; v15i27.567 is the DOI
%% actually registered at Crossref and is the one that resolves.
@article{araujo2023mineracao,
  author  = {de Araujo, Renata Mendes and Peres, Sarajane Marques and Fantinato, Marcelo
             and Unger, Adriana Jacoto and Neubauer, Thais Rodrigues},
  title   = {Minera{\c{c}}{\~a}o de processos como ferramenta para promo{\c{c}}{\~a}o da
             transpar{\^e}ncia: oportunidades e desafios},
  journal = {Revista da CGU},
  volume  = {15},
  number  = {27},
  pages   = {203--218},
  year    = {2023},
  doi     = {10.36428/revistadacgu.v15i27.567}
}

%% CORRECTED: added pages 1--10 (HICSS paginates each paper independently from 1).
%% Subtitle is lowercase "a case study" in the source.
@inproceedings{delgado2022discovery,
  author    = {Delgado, Andrea and Calegari, Daniel},
  title     = {Discovery and analysis of e-government business processes with process
               mining: a case study},
  booktitle = {Proceedings of the 55th Hawaii International Conference on System Sciences (HICSS)},
  pages     = {1--10},
  year      = {2022},
  doi       = {10.24251/HICSS.2022.296},
  url       = {http://hdl.handle.net/10125/79629}
}

%% CORRECTED: added the missing LNBIP volume 554; title is "Do not Stay Behind"
%% (lowercase "not"); full conference name supplied.
@inproceedings{racis2025donot,
  author    = {Racis, Serena and Spano, Alessandro},
  title     = {Do not stay behind: embracing process mining in the {Italian} public sector},
  booktitle = {Business Information Systems -- 25th International Conference, BIS 2025,
               Pozna{\'n}, Poland, June 25--27, 2025, Proceedings},
  series    = {Lecture Notes in Business Information Processing},
  volume    = {554},
  publisher = {Springer},
  pages     = {152--164},
  year      = {2025},
  doi       = {10.1007/978-3-031-94193-1_12}
}

%% CORRECTED: booktitle was missing entirely. Venue is the ICPM 2024 Workshops
%% (Revised Selected Papers, published 2025), LNBIP 533, pp. 572--585.
@inproceedings{trottier2025using,
  author    = {Trottier, Jacques and Van Woensel, William and Wang, Xiaoyang
               and Mallur, Kavya and El-Gharib, Najah and Amyot, Daniel},
  title     = {Using process mining with pre- and post-intervention analysis to improve
               digital service delivery: a governmental case study},
  booktitle = {Process Mining Workshops -- ICPM 2024 International Workshops, Lyngby,
               Denmark, October 14--18, 2024, Revised Selected Papers},
  series    = {Lecture Notes in Business Information Processing},
  volume    = {533},
  publisher = {Springer},
  pages     = {572--585},
  year      = {2025},
  doi       = {10.1007/978-3-031-82225-4_42},
  note      = {Preprint: arXiv:2409.05869}
}

%% ---- Trace clustering & LLMs in process mining ----

@inproceedings{bose2009context,
  author    = {Bose, R. P. Jagadeesh Chandra and van der Aalst, Wil M. P.},
  title     = {Context aware trace clustering: towards improving process mining results},
  booktitle = {Proceedings of the 2009 SIAM International Conference on Data Mining (SDM)},
  publisher = {SIAM},
  pages     = {401--412},
  year      = {2009},
  doi       = {10.1137/1.9781611972795.35}
}

@article{deleoni2016general,
  author  = {de Leoni, Massimiliano and van der Aalst, Wil M. P. and Dees, Marcus},
  title   = {A general process mining framework for correlating, predicting and clustering
             dynamic behavior based on event logs},
  journal = {Information Systems},
  volume  = {56},
  pages   = {235--257},
  year    = {2016},
  doi     = {10.1016/j.is.2015.07.003}
}

%% Year 2023 follows DBLP/the workshop date; Springer's imprint year is 2024.
@inproceedings{berti2023abstractions,
  author    = {Berti, Alessandro and Schuster, Daniel and van der Aalst, Wil M. P.},
  title     = {Abstractions, scenarios, and prompt definitions for process mining with
               {LLMs}: a case study},
  booktitle = {Business Process Management Workshops (BPM 2023)},
  series    = {Lecture Notes in Business Information Processing},
  volume    = {492},
  publisher = {Springer},
  pages     = {427--439},
  year      = {2023},
  doi       = {10.1007/978-3-031-50974-2_32},
  note      = {arXiv:2307.02194}
}

@inproceedings{vidgof2023large,
  author    = {Vidgof, Maxim and Bachhofner, Stefan and Mendling, Jan},
  title     = {Large language models for business process management: opportunities and
               challenges},
  booktitle = {Business Process Management Forum (BPM Forum 2023)},
  series    = {Lecture Notes in Business Information Processing},
  volume    = {490},
  publisher = {Springer},
  pages     = {107--123},
  year      = {2023},
  doi       = {10.1007/978-3-031-41623-1_7},
  note      = {arXiv:2304.04309}
}

%% ---- Predictive process monitoring ----

@article{teinemaa2019outcome,
  author    = {Teinemaa, Irene and Dumas, Marlon and La Rosa, Marcello and Maggi, Fabrizio Maria},
  title     = {Outcome-oriented predictive process monitoring: review and benchmark},
  journal   = {ACM Transactions on Knowledge Discovery from Data},
  volume    = {13},
  number    = {2},
  articleno = {17},
  pages     = {1--57},
  year      = {2019},
  publisher = {ACM},
  doi       = {10.1145/3301300}
}

%% ---- Brazilian public administration / LGPD legal context ----

@article{rocha2024critical,
  author  = {Rocha, N{\'u}bia Augusto de Sousa and de Almeida, Alexandre Nascimento
             and Nunes, Andr{\'e} and Angelo, Humberto},
  title   = {Critical points for the processing of personal data by the government:
             an empirical study in {Brazil}},
  journal = {Computer Law \& Security Review},
  volume  = {54},
  pages   = {106023},
  year    = {2024},
  doi     = {10.1016/j.clsr.2024.106023}
}

%% Confirmed: DOU publication was 18.11.2011, same day as signature, Edição extra.
%% NB this entry is NOT cited anywhere in main.tex — cite it or drop it.
@misc{brasil2011lai,
  author       = {{Brasil}},
  title        = {Lei n\textordmasculine{} 12.527, de 18 de novembro de 2011. Lei de Acesso
                  \`a Informa\c{c}\~ao (LAI)},
  year         = {2011},
  howpublished = {Di\'ario Oficial da Uni\~ao, Bras\'ilia, DF, 18 nov. 2011, Edi\c{c}\~ao extra},
  note         = {Regula o acesso a informa\c{c}\~oes previsto na Constitui\c{c}\~ao Federal},
  url          = {https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2011/lei/l12527.htm}
}

%% LNBIP volume 455 CONFIRMED — the previous "% TODO verify series/volume" is resolved.
@incollection{canedo2022evaluating,
  author    = {Canedo, Edna Dias and Ribeiro, Vanessa Coelho and Cerqueira, Anderson Jefferson
               and Gravina, Rog{\'e}rio Machado and Cam{\~o}es, Renato and dos Reis, Vinicius Eloy
               and Mendon{\c{c}}a, F{\'a}bio L{\'u}cio Lopes and de Sousa~J{\'u}nior, Rafael T.},
  title     = {Evaluating and evolving the compliance to the Brazilian general data protection
               law in a federal government agency},
  booktitle = {Enterprise Information Systems: 23rd International Conference, ICEIS 2021,
               Virtual Event, April 26--28, 2021, Revised Selected Papers},
  series    = {Lecture Notes in Business Information Processing},
  volume    = {455},
  publisher = {Springer},
  pages     = {3--27},
  year      = {2022},
  doi       = {10.1007/978-3-031-08965-7_1}
}

%% Start page 859 confirmed. End page deliberately omitted — the repository stores only
%% the first page and the PDF is bot-blocked. Start-page-only is correct Bluebook form
%% for a law review cite anyway.
@article{erickson2019comparative,
  author  = {Erickson, Abigayle},
  title   = {Comparative analysis of the {EU}'s {GDPR} and {Brazil}'s {LGPD}: enforcement
             challenges with the {LGPD}},
  journal = {Brooklyn Journal of International Law},
  volume  = {44},
  number  = {2},
  pages   = {859},
  year    = {2019},
  url     = {https://brooklynworks.brooklaw.edu/bjil/vol44/iss2/9/}
}

%% CORRECTED: the title contained a literal "..." ellipsis and omitted "of 27 April 2016"
%% and "and repealing Directive 95/46/EC". Full official English title supplied.
%% The OJ reference and the ELI URL were already correct.
@misc{eu2016gdpr,
  author       = {{European Parliament and Council of the European Union}},
  title        = {Regulation ({EU}) 2016/679 of the European Parliament and of the Council
                  of 27 April 2016 on the protection of natural persons with regard to the
                  processing of personal data and on the free movement of such data, and
                  repealing Directive 95/46/{EC} (General Data Protection Regulation)},
  year         = {2016},
  howpublished = {Official Journal of the European Union, OJ L 119, 4.5.2016, pp. 1--88},
  url          = {https://eur-lex.europa.eu/eli/reg/2016/679/oj}
}

%% ---- Uncited in main.tex (kept for the .qd reference lists) ----

@inproceedings{kipf2017gcn,
  author    = {Kipf, Thomas N. and Welling, Max},
  title     = {Semi-supervised classification with graph convolutional networks},
  booktitle = {5th International Conference on Learning Representations (ICLR 2017)},
  publisher = {OpenReview.net},
  year      = {2017},
  note      = {arXiv:1609.02907}
}

%% `number` deliberately omitted: Springer's own metadata says issue 3, Crossref says 3-4
%% (combined May 1992 issue). Omitting sidesteps an unresolvable source conflict.
@article{williams1992reinforce,
  author  = {Williams, Ronald J.},
  title   = {Simple statistical gradient-following algorithms for connectionist
             reinforcement learning},
  journal = {Machine Learning},
  volume  = {8},
  pages   = {229--256},
  year    = {1992},
  doi     = {10.1007/BF00992696}
}
```

---

#### 3. NEEDS MANUAL RETRIEVAL

**No entry needs to be retrieved from scratch** — all 61 were located and identified. What
follows are four *individual fields* that could not be confirmed to publication standard, and one
editorial decision that only the author can make. In each case the field has been **omitted rather
than guessed**, which is bibliographically valid.

##### 3.1 `pesic2007declare` — page range (the only genuine source conflict)

Three sources disagree and none is decisive:

| Source | Pages |
|---|---|
| DBLP EDOC 2007 TOC | 287–300 |
| TU/e repository (research.tue.nl) | 287–298 |
| IEEE's own Crossref deposit | 287–287 (start-page-only, standard for IEEE deposits of this era) |

DBLP's TOC is internally contiguous (preceding paper ends 286, following paper starts 301), which
is structural evidence for 287–300, but that is inference, not confirmation. **Omitted.**

- **Searched:** `dblp.org/db/conf/edoc/edoc2007.html`, `api.crossref.org/works/10.1109/EDOC.2007.14`,
  research.tue.nl, `doi.org/10.1109/EDOC.2007.4384001` (301-redirects to `.14`, so `.14` is canonical).
- **Most likely source:** IEEE Xplore document page for DOI `10.1109/EDOC.2007.14` — bot-blocked
  (returns HTTP 202 with empty body), needs a human browser session or institutional access.
- **Action:** either open the Xplore page and read the printed page range, or leave `pages` out.
  The DOI is a complete locator; Springer's style will accept the entry without pages.

##### 3.2 `erickson2019comparative` — end page

Start page 859 is confirmed from the BrooklynWorks record's `bepress_citation_firstpage` and its
own recommended citation. The repository stores no `lastpage`.

- **Searched:** `brooklynworks.brooklaw.edu/bjil/vol44/iss2/9/` (metadata retrieved successfully),
  and the PDF at `/cgi/viewcontent.cgi?article=1941&context=bjil` — returns 403/202-empty to both
  WebFetch and curl.
- **Bounding datum, offered as context only and *not* asserted:** the next article in the same
  issue (Sarokin, `.../bjil/vol44/iss2/10/`) starts at 889.
- **Most likely source:** download the PDF manually from BrooklynWorks in a browser.
- **Action:** none required. Bluebook cites law review articles by start page only, so
  `pages = {859}` is already the correct form for this venue.

##### 3.3 `calinski1974dendrite` — authors' given names

Taylor & Francis prints initials only ("T. Caliński", "J. Harabasz"). "Tadeusz Caliński" is
well-documented (Poznań statistician). The second author's given name is **contested**: "Jerzy"
appears in Wikipedia and common usage, but a competing "Joachim" appears in search results and
neither could be adjudicated from a primary source.

- **Searched:** `doi.org/10.1080/03610927408827101` (publisher deposit, initials only);
  tandfonline.com returns 403 to automated fetch.
- **Most likely source:** the printed 1974 article, or a Poznań University of Life Sciences
  institutional page.
- **Action:** the corrected entry uses initials for both authors. Springer author–year renders
  surnames + initials anyway, so **nothing is lost** and the risk is eliminated. Only chase this if
  you specifically want full given names in the `.bib`.

##### 3.4 `guidotti2018survey` — year: 2018 or 2019?

Not a defect, a genuine ambiguity. Crossref `issued`/online-first = 2018-08-22; `published-print`
for the issue = 2019-09-30; **DBLP records it as 2019**. Both appear widely in the literature.

- **Action, author's call:** the corrected entry keeps 2018 (matching the citekey and your original).
  If AI&Law's style prefers the issue year, change to 2019 — and if you do, rename the citekey or
  the label will read "Guidotti et al. 2018" against a 2019 reference.

The same online-vs-imprint ambiguity, harmlessly, affects `berti2023abstractions` (DBLP/workshop
2023 vs Springer imprint 2024). 2023 is retained; either is defensible.

##### 3.5 Two content decisions worth a glance

- **`suriadi2017imperfection`:** an Information Systems paper from **2026** (vol. 137, art. 102645,
  DOI `10.1016/j.is.2025.102645`) by Andrews & Wynn carries an *identical title*. The 2017 paper is
  almost certainly what you want, but confirm you are not citing the wrong one of a matched pair.
- **`microsoftpresidio`:** the corrected entry keeps `author = {{Microsoft}}` because the pipeline's
  experiments used it as Microsoft Presidio, but the project has since moved to community
  governance under the Data Privacy Stack org. If your experiments were run against a specific
  release, cite that release tag and date instead — more reproducible than citing the repo HEAD.

---

#### 4. SUSPECTED FABRICATION

**None. No entry in this bibliography is suspected of being fabricated.**

This is a stronger result than the file's own header implied. The 25 `% TODO verify` markers and
the "best-effort from general knowledge" disclaimer suggested a real fabrication risk, and the
entries that fit the classic hallucination profile — a 2026-dated article in an obscure
Portuguese-language journal, two 2025 Springer chapters, a 2025 EMNLP demo paper, a US law review
note cited by start page only — were each checked with extra scrutiny. All of them are real, and
all of their DOIs resolve to the claimed work:

| Entry that looked risky | Outcome |
|---|---|
| `limaesilva2026analise` (Revista DCS 2026) | Real. DOI resolves; four authors, vol/issue/article ID all confirmed via the journal's OJS Google Scholar meta tags and Crossref |
| `araujo2023mineracao` (Revista da CGU) | Real. DOI resolves; verified down to the article PDF's printed page headers |
| `racis2025donot` (BIS 2025) | Real. DOI resolves; only the LNBIP volume was missing |
| `trottier2025using` (Springer 2025) | Real. DOI resolves; venue is ICPM 2024 Workshops — the entry just never named it |
| `zaratiana2025gliner2` (EMNLP 2025 Demos) | Real. Venue and pages 130–140 were both correct |
| `erickson2019comparative` (Brooklyn J. Int'l L.) | Real. Recommended citation retrieved verbatim from the law school's repository |

##### The one thing that behaves like a fabrication but is not

`strehl2002ensembles` carries `doi = {10.1162/153244303321897735}`. **That DOI does not resolve.**
`https://doi.org/10.1162/153244303321897735` returns 302 → `crossref.org/deleted_DOI.html`, and the
Crossref API record for it has publisher `"Unmaintained records"` and container-title
`"CrossRef Listing of Deleted DOIs"`.

This is *not* a hallucination — it was a genuine MIT Press DOI from the period when JMLR volumes
1–4 had a print run, and it has since been withdrawn from the registry. The article itself is
entirely real and correctly cited otherwise (JMLR vol. 3, pp. 583–617, 2002). JMLR assigns this
article **no DOI at all**, and neither JMLR nor DBLP lists one.

**This is the single field in the bibliography that would fail a reviewer or production check**
(a DOI that resolves to a tombstone page looks exactly like a fabricated DOI). It has been removed
in the corrected BibTeX above, with the canonical JMLR URL retained in its place. **Do not
substitute another DOI** — there is none to substitute.

---

#### Applying this

The corrected block in §2 is a complete drop-in replacement for
`article/latex/references.bib`. Before you paste it, decide the three author-call items:
the `ieee2012manifesto` citation-label change (§1), the `guidotti2018survey` year (§3.4), and
whether `brasil2011lai` gets cited or dropped (§1).

---

## Pass 1 — candidate proposals (2026-07-11)


Target venue: *Artificial Intelligence and Law* (Springer). Compiled 2026-07-11.
Every entry below was verified via WebSearch/WebFetch against a primary source
(ACL Anthology, publisher DOI page, Crossref registration metadata, arXiv, JOSS,
LexML, EUR-Lex, or planalto.gov.br). **No entry is invented.** Where a single
sub-field could only be confirmed from a search snippet rather than a registry
field, it is flagged inline with «verify».

#### How to read this file

- Each entry gives: **BibTeX** (verified) → a **Springer author-year line** ready to
  paste into the article's plain-text reference list (the paper uses Springer
  author-year, not a `.bib` file) → **annotation + target section** → **verified URL**.
- **STATUS tag**: `NEW` = not currently cited; `ALREADY CITED` = present in the
  article's existing 39-entry list (kept here only for completeness / de-dup); or
  `UPGRADE` = already cited but the existing entry has missing/placeholder fields
  that this verified record completes.

#### De-duplication note (IMPORTANT)

The task brief listed only 5 existing references, but the article
(`article-en.qd`, References section) already carries **39** entries. Several
papers requested for this search are therefore **already cited** and should not
be re-added: Bukhsh 2021 (ProcessTransformer), Camargo 2019, Campello 2013
(HDBSCAN), Evermann 2017, Greco 2006, McInnes UMAP-arXiv 2018, Moulavi 2014
(DBCV), Nai 2024 (public procurement), Rama-Maneiro 2023, Song 2009, Tax 2017,
and Silva 2026 (the SEI/TRE-Tocantins case study, currently a placeholder). Those
appear below tagged `ALREADY CITED` / `UPGRADE` so nothing is proposed twice. The
genuinely additive material is tagged `NEW` — **27 new references**.

---

#### TOP 3 MOST CRITICAL TO ADD

The article already has dense process-mining / PPM / clustering coverage but
**zero anonymization references and zero legal-statute grounding** — a striking
gap for a paper submitted to *AI and Law* that anonymizes Brazilian government
PII and stakes its novelty on an anonymization-vs-utility experiment.

1. **Lothritz et al. 2023** (§1) — the single closest prior art to our key claim:
   it empirically measures how anonymization/pseudonymization affects downstream
   NLP and finds the impact "relatively low." Direct support/contrast for our
   raw-vs-anonymized result.
2. **LGPD — Lei nº 13.709/2018** (§6) — the statute that legally *requires* our
   anonymization. Not citing the governing law in an AI & Law submission that
   processes Brazilian public-sector PII is a glaring omission.
3. **Pilán et al. 2022, The Text Anonymization Benchmark (TAB)** (§1) — the
   standard corpus + evaluation framework for text anonymization; anchors the
   legitimacy and vocabulary (direct vs. quasi-identifiers) of our masking layer.

**Also a must-fix method-citation hole:** the pipeline *uses* the Leiden algorithm
but the article never cites it — add **Traag et al. 2019** (§2).

---

#### KEY FINDING — Anonymization impact on CLUSTERING quality: no prior work

> ⚠️ **Retracted.** This claim does not hold. `lit-ai-law.md` states it "cannot stand as
> written" and supplies the prior work. Kept as a record of what was believed on 2026-07-11.

**Verdict: no prior work measures the impact of PII text anonymization /
de-identification on downstream *clustering* quality, nor on next-activity /
process-log prediction.** This strengthens the novelty of the raw-vs-anonymized
result — state it precisely.

What the literature *does* contain:
- **Downstream-impact studies exist, but only for supervised tasks.** Lothritz
  et al. 2023 (9 classification/NER tasks), Ben Cheikh Larbi et al. 2023 (5 NLP
  tasks), and the LOUHI-2020 study "The Impact of De-identification on Downstream
  Named Entity Recognition in Clinical Text" (https://aclanthology.org/2020.louhi-1.1/)
  all measure supervised accuracy — **none evaluate clustering or process
  prediction.**
- **"Clustering" appears in the anonymization literature only as a *mechanism*,
  not a measured downstream task:** k-anonymity-via-clustering for tabular
  microdata; ClustEm4Ano (arXiv:2412.12649) *uses* embedding clustering to build
  generalization hierarchies. Neither measures whether anonymization preserves
  document-clustering quality.
- The nearest "anonymization + clustering" evaluation — "Utility-driven
  assessment of anonymized data via clustering," *Scientific Data* 2022
  (https://www.nature.com/articles/s41597-022-01561-6) — uses clustering to
  *assess tabular microdata* anonymization, not text-PII effect on document
  clustering. Adjacent, not a hit.

Searches tried (WebSearch): `impact of de-identification on downstream NLP
performance clinical text utility`; `impact anonymization on clustering quality
text privacy utility trade-off`; `"anonymization" OR "de-identification" effect on
"clustering" downstream unsupervised text embeddings evaluation`; `does
de-identification degrade document clustering topic model quality anonymized
corpus`. All returned either supervised-task impact studies or tabular
k-anonymity — no text-anonymization-impact-on-clustering study.

**Recommended framing:** "To our knowledge, no prior work measures the effect of
PII anonymization on *unsupervised* downstream tasks (document clustering) or on
next-activity prediction over process logs; existing impact studies cover only
supervised classification/NER (Lothritz et al. 2023; Ben Cheikh Larbi et al. 2023)."

---

### §1 — PII anonymization / pseudonymization for NLP and documents

All `NEW`. This entire area is currently uncited and is the article's biggest gap.

##### 1.1 Lothritz et al. (2023) — impact of de-identification on downstream NLP `NEW`
```bibtex
@inproceedings{lothritz2023evaluating,
  author    = {Lothritz, Cedric and Lebichot, Bertrand and Allix, Kevin and Ezzini, Saad and Bissyand{\'e}, Tegawend{\'e} and Klein, Jacques and Boytsov, Andrey and Lefebvre, Cl{\'e}ment and Goujon, Anne},
  title     = {Evaluating the Impact of Text De-Identification on Downstream {NLP} Tasks},
  booktitle = {Proceedings of the 24th Nordic Conference on Computational Linguistics (NoDaLiDa)},
  pages     = {10--16},
  year      = {2023},
  publisher = {University of Tartu Library},
  url       = {https://aclanthology.org/2023.nodalida-1.2/}
}
```
Author-year: Lothritz C, Lebichot B, Allix K, Ezzini S, Bissyandé T, Klein J, Boytsov A, Lefebvre C, Goujon A (2023) Evaluating the impact of text de-identification on downstream NLP tasks. In: NoDaLiDa 2023. University of Tartu Library, pp 10–16
Contribution/section: **Related work + Discussion.** Closest prior art to our novelty claim — measures six anonymization/pseudonymization strategies across nine downstream NLP tasks and finds impact "relatively low," with random-name pseudonymization preserving utility best. Note it covers only supervised tasks (contrast lever for our clustering/prediction result).
Verified: https://aclanthology.org/2023.nodalida-1.2/

##### 1.2 Ben Cheikh Larbi et al. (2023) — anonymization impact + re-identification `NEW`
```bibtex
@inproceedings{bencheikhlarbi2023clinical,
  author    = {Ben Cheikh Larbi, Iyadh and Burchardt, Aljoscha and Roller, Roland},
  title     = {Clinical Text Anonymization, its Influence on Downstream {NLP} Tasks and the Risk of Re-Identification},
  booktitle = {Proceedings of the 17th Conference of the European Chapter of the ACL: Student Research Workshop},
  pages     = {105--111},
  year      = {2023},
  publisher = {Association for Computational Linguistics},
  doi       = {10.18653/v1/2023.eacl-srw.11},
  url       = {https://aclanthology.org/2023.eacl-srw.11/}
}
```
Author-year: Ben Cheikh Larbi I, Burchardt A, Roller R (2023) Clinical text anonymization, its influence on downstream NLP tasks and the risk of re-identification. In: EACL 2023 Student Research Workshop. ACL, pp 105–111
Contribution/section: **Related work + Discussion.** Measures anonymization's effect on ML across five tasks *and* demonstrates a re-identification attack, framing the exact privacy-utility trade-off our experiment quantifies; its re-id attack motivates our checksum-validated + typed-placeholder masking.
Verified: https://aclanthology.org/2023.eacl-srw.11/

##### 1.3 Pilán et al. (2022) — The Text Anonymization Benchmark (TAB) `NEW`
```bibtex
@article{pilan2022text,
  author    = {Pil{\'a}n, Ildik{\'o} and Lison, Pierre and {\O}vrelid, Lilja and Papadopoulou, Anthi and S{\'a}nchez, David and Batet, Montserrat},
  title     = {The Text Anonymization Benchmark ({TAB}): A Dedicated Corpus and Evaluation Framework for Text Anonymization},
  journal   = {Computational Linguistics},
  volume    = {48},
  number    = {4},
  pages     = {1053--1101},
  year      = {2022},
  publisher = {MIT Press},
  doi       = {10.1162/coli_a_00458},
  url       = {https://aclanthology.org/2022.cl-4.19/}
}
```
Author-year: Pilán I, Lison P, Øvrelid L, Papadopoulou A, Sánchez D, Batet M (2022) The text anonymization benchmark (TAB): a dedicated corpus and evaluation framework for text anonymization. Comput Linguist 48(4):1053–1101
Contribution/section: **Related work + Method.** The definitive corpus/evaluation framework for text anonymization; distinguishes direct vs. quasi-identifiers and defines GDPR-grounded privacy/utility metrics — justifies our typed-placeholder (entity-type) treatment and our evaluation framing.
Verified: https://aclanthology.org/2022.cl-4.19/

##### 1.4 Lison et al. (2021) — anonymisation models for text data (survey) `NEW`
```bibtex
@inproceedings{lison2021anonymisation,
  author    = {Lison, Pierre and Pil{\'a}n, Ildik{\'o} and Sanchez, David and Batet, Montserrat and {\O}vrelid, Lilja},
  title     = {Anonymisation Models for Text Data: State of the Art, Challenges and Future Directions},
  booktitle = {Proceedings of the 59th Annual Meeting of the ACL and the 11th IJCNLP (Volume 1: Long Papers)},
  pages     = {4188--4203},
  year      = {2021},
  publisher = {Association for Computational Linguistics},
  doi       = {10.18653/v1/2021.acl-long.323},
  url       = {https://aclanthology.org/2021.acl-long.323/}
}
```
Author-year: Lison P, Pilán I, Sánchez D, Batet M, Øvrelid L (2021) Anonymisation models for text data: state of the art, challenges and future directions. In: ACL-IJCNLP 2021. ACL, pp 4188–4203
Contribution/section: **Related work.** The reference survey contrasting NLP-based (NER/sequence-labelling) anonymization with privacy-preserving data publishing (k-anonymity) and the GDPR framing — positions our two-layer (regex + NER span-masking) method within the established taxonomy.
Verified: https://aclanthology.org/2021.acl-long.323/

##### 1.5 Stubbs et al. (2015) — 2014 i2b2/UTHealth de-identification shared task `NEW`
```bibtex
@article{stubbs2015automated,
  author  = {Stubbs, Amber and Kotfila, Christopher and Uzuner, {\"O}zlem},
  title   = {Automated Systems for the De-identification of Longitudinal Clinical Narratives: Overview of 2014 i2b2/{UTH}ealth Shared Task Track 1},
  journal = {Journal of Biomedical Informatics},
  volume  = {58},
  pages   = {S11--S19},
  year    = {2015},
  doi     = {10.1016/j.jbi.2015.06.007}
}
```
Author-year: Stubbs A, Kotfila C, Uzuner Ö (2015) Automated systems for the de-identification of longitudinal clinical narratives: overview of 2014 i2b2/UTHealth shared task Track 1. J Biomed Inform 58:S11–S19
Contribution/section: **Related work / Method.** The canonical i2b2/n2c2 de-identification benchmark (best F1 ≈ 0.936 on PHI) — the community reference standard for measuring anonymization span-detection quality.
Verified: https://doi.org/10.1016/j.jbi.2015.06.007

##### 1.6 Dernoncourt et al. (2017) — neural de-identification of patient notes `NEW`
```bibtex
@article{dernoncourt2017deidentification,
  author  = {Dernoncourt, Franck and Lee, Ji Young and Uzuner, {\"O}zlem and Szolovits, Peter},
  title   = {De-identification of Patient Notes with Recurrent Neural Networks},
  journal = {Journal of the American Medical Informatics Association},
  volume  = {24},
  number  = {3},
  pages   = {596--606},
  year    = {2017},
  doi     = {10.1093/jamia/ocw156}
}
```
Author-year: Dernoncourt F, Lee JY, Uzuner Ö, Szolovits P (2017) De-identification of patient notes with recurrent neural networks. J Am Med Inform Assoc 24(3):596–606
Contribution/section: **Method / Related work.** First neural (BiLSTM-CRF) de-identification needing no handcrafted rules — the lineage for our learned NER span-masking layer (GLiNER2/LLM), showing the field's move from regex/rules to neural NER.
Verified: https://academic.oup.com/jamia/article-abstract/24/3/596/2769353 (preprint arXiv:1606.03475)

##### 1.7 Microsoft Presidio — PII de-identification SDK (software) `NEW`
```bibtex
@misc{microsoftpresidio,
  author       = {{Microsoft}},
  title        = {Presidio: {PII} Detection, De-identification and Anonymization {SDK}},
  howpublished = {\url{https://github.com/microsoft/presidio}},
  year         = {2020},
  note         = {Open-source (MIT); NER + regex + checksum recognizers. Accessed 2026-07-11}
}
```
Author-year: Microsoft (2020) Presidio: PII detection, de-identification and anonymization SDK. https://github.com/microsoft/presidio
Contribution/section: **Method.** The de-facto open-source PII framework combining regex/checksum validators with NER recognizers — the closest existing tool to our two-layer design and a natural comparison baseline. Software citation (no canonical peer-reviewed paper; `year` = approx. first release).
Verified: https://github.com/microsoft/presidio

---

### §2 — Graph / clustering algorithms

##### 2.1 Traag et al. (2019) — Leiden algorithm `NEW` (must-fix: currently used but uncited)
```bibtex
@article{traag2019louvain,
  author  = {Traag, V. A. and Waltman, L. and van Eck, N. J.},
  title   = {From Louvain to Leiden: Guaranteeing Well-Connected Communities},
  journal = {Scientific Reports},
  volume  = {9},
  number  = {1},
  pages   = {5233},
  year    = {2019},
  doi     = {10.1038/s41598-019-41695-z}
}
```
Author-year: Traag VA, Waltman L, van Eck NJ (2019) From Louvain to Leiden: guaranteeing well-connected communities. Sci Rep 9:5233
Contribution/section: **Method (Leiden clustering) + Discussion.** Defines the Leiden algorithm we run for graph community detection and motivates it over Louvain (guaranteed connected communities). The pipeline uses Leiden, so this citation is currently missing and should be added.
Verified: https://www.nature.com/articles/s41598-019-41695-z (arXiv:1810.08473)

##### 2.2 Blondel et al. (2008) — Louvain method `NEW`
```bibtex
@article{blondel2008fast,
  author  = {Blondel, Vincent D. and Guillaume, Jean-Loup and Lambiotte, Renaud and Lefebvre, Etienne},
  title   = {Fast Unfolding of Communities in Large Networks},
  journal = {Journal of Statistical Mechanics: Theory and Experiment},
  volume  = {2008},
  number  = {10},
  pages   = {P10008},
  year    = {2008},
  doi     = {10.1088/1742-5468/2008/10/P10008}
}
```
Author-year: Blondel VD, Guillaume J-L, Lambiotte R, Lefebvre E (2008) Fast unfolding of communities in large networks. J Stat Mech 2008(10):P10008
Contribution/section: **Method / Related work.** The modularity-optimization predecessor Leiden improves on — cite alongside Traag et al. to frame the choice of Leiden.
Verified: https://iopscience.iop.org/article/10.1088/1742-5468/2008/10/P10008 (arXiv:0803.0476)

##### 2.3 Rousseeuw (1987) — silhouette index `NEW`
```bibtex
@article{rousseeuw1987silhouettes,
  author  = {Rousseeuw, Peter J.},
  title   = {Silhouettes: A Graphical Aid to the Interpretation and Validation of Cluster Analysis},
  journal = {Journal of Computational and Applied Mathematics},
  volume  = {20},
  pages   = {53--65},
  year    = {1987},
  doi     = {10.1016/0377-0427(87)90125-7}
}
```
Author-year: Rousseeuw PJ (1987) Silhouettes: a graphical aid to the interpretation and validation of cluster analysis. J Comput Appl Math 20:53–65
Contribution/section: **Method (k-selection / cluster validity).** Classic silhouette-width index used as a complementary internal metric and to support k selection for kmeans (the elbow/k-selection sweep in `select_k.py`).
Verified: https://doi.org/10.1016/0377-0427(87)90125-7

##### 2.4 McInnes et al. (2017) — hdbscan software (JOSS) `NEW`
```bibtex
@article{mcinnes2017hdbscan,
  author  = {McInnes, Leland and Healy, John and Astels, Steve},
  title   = {hdbscan: Hierarchical Density Based Clustering},
  journal = {Journal of Open Source Software},
  volume  = {2},
  number  = {11},
  pages   = {205},
  year    = {2017},
  doi     = {10.21105/joss.00205}
}
```
Author-year: McInnes L, Healy J, Astels S (2017) hdbscan: hierarchical density based clustering. J Open Source Softw 2(11):205
Contribution/section: **Method (software citation).** The concrete HDBSCAN implementation we run; cite alongside the already-present Campello et al. 2013 to credit the software.
Verified: https://joss.theoj.org/papers/10.21105/joss.00205

##### 2.5 McInnes et al. (2018) — umap software (JOSS) `NEW`
```bibtex
@article{mcinnes2018umapsoftware,
  author  = {McInnes, Leland and Healy, John and Saul, Nathaniel and Gro{\ss}berger, Lukas},
  title   = {{UMAP}: Uniform Manifold Approximation and Projection},
  journal = {Journal of Open Source Software},
  volume  = {3},
  number  = {29},
  pages   = {861},
  year    = {2018},
  doi     = {10.21105/joss.00861}
}
```
Author-year: McInnes L, Healy J, Saul N, Großberger L (2018) UMAP: uniform manifold approximation and projection. J Open Source Softw 3(29):861
Contribution/section: **Method (software citation).** The UMAP implementation we run; cite alongside the already-present McInnes et al. 2018 arXiv paper to credit the software.
Verified: https://joss.theoj.org/papers/10.21105/joss.00861

##### Already cited in §2 (do not re-add)
- Campello, Moulavi & Sander 2013 (HDBSCAN, PAKDD) — `ALREADY CITED`
- McInnes, Healy & Melville 2018 (UMAP, arXiv:1802.03426) — `ALREADY CITED`
- Moulavi et al. 2014 (DBCV, SDM) — `ALREADY CITED`

---

### §3 — Process mining in public administration / e-government

##### 3.1 Lima e Silva et al. (2026) — SEI process mining, TRE-Tocantins `UPGRADE`
```bibtex
@article{limaesilva2026analise,
  author  = {Lima e Silva, Fernando Jorge Ebrahim and Rocha, Marcelo Lisboa and Barbosa, Gentil Veloso and Lisboa, Marcelo da Silva},
  title   = {An{\'a}lise de processos administrativos no setor p{\'u}blico via minera{\c{c}}{\~a}o de processos: um estudo de caso no Tribunal Regional Eleitoral do Tocantins},
  journal = {Revista DCS},
  volume  = {23},
  number  = {88},
  pages   = {e4864},
  year    = {2026},
  doi     = {10.54899/dcs.v23i88.4864}
}
```
Author-year: Lima e Silva FJE, Rocha ML, Barbosa GV, Lisboa MS (2026) Análise de processos administrativos no setor público via mineração de processos: um estudo de caso no Tribunal Regional Eleitoral do Tocantins. Rev DCS 23(88):e4864
Contribution/section: **Related work + Method/Discussion.** The closest analogue to our work and the only verified *SEI-specific* process-mining case study — mines event logs extracted from SEI, compares against a BPMN reference model, and quantifies rework/cycle-time. **This is the current placeholder "Silva et al (2026) «verify authors/initials»" in the article** — replace it with these verified authors/DOI.
Verified: DOI 10.54899/dcs.v23i88.4864; listing https://ojs.revistadcs.com/index.php/revista/article/view/4864

##### 3.2 de Araujo et al. (2023) — process mining for public-sector transparency (Brazil) `NEW`
```bibtex
@article{araujo2023mineracao,
  author  = {de Araujo, Renata Mendes and Peres, Sarajane Marques and Fantinato, Marcelo and Unger, Adriana Jacoto and Neubauer, Thais Rodrigues},
  title   = {Minera{\c{c}}{\~a}o de Processos como Ferramenta para Promo{\c{c}}{\~a}o da Transpar{\^e}ncia: Oportunidades e Desafios},
  journal = {Revista da CGU},
  volume  = {15},
  number  = {27},
  year    = {2023},
  doi     = {10.36428/revistadacgu.v15i27.567}
}
```
Author-year: de Araujo RM, Peres SM, Fantinato M, Unger AJ, Neubauer TR (2023) Mineração de processos como ferramenta para promoção da transparência: oportunidades e desafios. Rev CGU 15(27)
Contribution/section: **Introduction / Related work.** Positions process mining as an instrument for Brazilian public-sector transparency and accountability (by a leading Brazilian PM group) — grounds the transparency motivation and ties directly to the LGPD-vs-transparency tension in §6.
Verified: https://revista.cgu.gov.br/Revista_da_CGU/article/view/567

##### 3.3 Delgado & Calegari (2022) — e-government process mining case study (HICSS) `NEW`
```bibtex
@inproceedings{delgado2022discovery,
  author    = {Delgado, Andrea and Calegari, Daniel},
  title     = {Discovery and Analysis of E-Government Business Processes with Process Mining: A Case Study},
  booktitle = {Proceedings of the 55th Hawaii International Conference on System Sciences (HICSS)},
  year      = {2022},
  doi       = {10.24251/HICSS.2022.296},
  url       = {http://hdl.handle.net/10125/79629}
}
```
Author-year: Delgado A, Calegari D (2022) Discovery and analysis of e-government business processes with process mining: a case study. In: HICSS 2022
Contribution/section: **Related work / Method.** Methodological e-government case study mining processes implicit in a centralized traceability/information system — directly analogous to extracting logs from SEI, and provides the "processes are implicit in the information system" framing.
Verified: https://scholarspace.manoa.hawaii.edu/items/29ccfd6a-9b42-45d6-a862-fb402b466fad

##### 3.4 Racis & Spano (2025) — process mining adoption in public sector (Italy) `NEW`
```bibtex
@inproceedings{racis2025donot,
  author    = {Racis, Serena and Spano, Alessandro},
  title     = {Do Not Stay Behind: Embracing Process Mining in the {Italian} Public Sector},
  booktitle = {Business Information Systems (BIS 2025)},
  series    = {Lecture Notes in Business Information Processing},
  pages     = {152--164},
  year      = {2025},
  publisher = {Springer},
  doi       = {10.1007/978-3-031-94193-1_12}
}
```
Author-year: Racis S, Spano A (2025) Do not stay behind: embracing process mining in the Italian public sector. In: BIS 2025, LNBIP. Springer, pp 152–164
Contribution/section: **Discussion.** Recent study of barriers/opportunities for adopting process mining in a national public administration — lets us compare our SEAD-PI findings against public-sector adoption challenges elsewhere (data quality, organizational readiness).
Verified: https://link.springer.com/chapter/10.1007/978-3-031-94193-1_12

##### 3.5 Trottier et al. (2024/2025) — government service-delivery process mining `NEW`
```bibtex
@inproceedings{trottier2025using,
  author    = {Trottier, Jacques and Van Woensel, William and Wang, Xiaoyang and Mallur, Kavya and El-Gharib, Najah and Amyot, Daniel},
  title     = {Using Process Mining with Pre- and Post-intervention Analysis to Improve Digital Service Delivery: A Governmental Case Study},
  year      = {2025},
  publisher = {Springer},
  doi       = {10.1007/978-3-031-82225-4_42},
  note      = {Preprint: arXiv:2409.05869}
}
```
Author-year: Trottier J, Van Woensel W, Wang X, Mallur K, El-Gharib N, Amyot D (2025) Using process mining with pre- and post-intervention analysis to improve digital service delivery: a governmental case study. Springer (arXiv:2409.05869)
Contribution/section: **Discussion.** Government (personnel-security-screening) case study using process mining to find bottlenecks/rework and quantify cycle-time gains from interventions — a template for turning discovered inefficiencies into measurable improvement.
Verified: https://arxiv.org/abs/2409.05869 (published version DOI 10.1007/978-3-031-82225-4_42)

##### Already cited / grey literature in §3
- Nai et al. 2024 (process mining on a public-procurement dataset, ECML PKDD workshops) — `ALREADY CITED`
- "Digital transformation initiatives in public administration ... in Brazil" 2021 (Springer) — `ALREADY CITED` (still marked «verify author(s)» in the article)
- Rozinat 2019, "Government Process Mining in the Brazilian Executive Branch" (tf-pm.org / Fluxicon) — **grey literature, not peer-reviewed**; cite only as a practitioner anchor if desired. https://www.tf-pm.org/resources/casestudy/government-process-mining-in-the-brazilian-executive-branch

---

### §4 — Trace clustering & semantic / text-aware process mining; LLMs in PM

##### 4.1 Bose & van der Aalst (2009) — context-aware trace clustering `NEW`
```bibtex
@inproceedings{bose2009context,
  author    = {Bose, R. P. Jagadeesh Chandra and van der Aalst, Wil M. P.},
  title     = {Context Aware Trace Clustering: Towards Improving Process Mining Results},
  booktitle = {Proceedings of the 2009 SIAM International Conference on Data Mining (SDM)},
  pages     = {401--412},
  year      = {2009},
  publisher = {SIAM},
  doi       = {10.1137/1.9781611972795.35}
}
```
Author-year: Bose RPJC, van der Aalst WMP (2009) Context aware trace clustering: towards improving process mining results. In: SDM 2009. SIAM, pp 401–412
Contribution/section: **Method.** Improves trace clustering with context/pattern-aware similarity (generic edit distance) rather than bag-of-activities — the closest classical precedent to our semantic-similarity clustering; motivates embedding-based (bge-m3) similarity as its natural successor.
Verified: https://epubs.siam.org/doi/10.1137/1.9781611972795.35

##### 4.2 de Leoni et al. (2016) — feature-based correlating/predicting/clustering framework `NEW`
```bibtex
@article{deleoni2016general,
  author  = {de Leoni, Massimiliano and van der Aalst, Wil M. P. and Dees, Marcus},
  title   = {A General Process Mining Framework for Correlating, Predicting and Clustering Dynamic Behavior Based on Event Logs},
  journal = {Information Systems},
  volume  = {56},
  pages   = {235--257},
  year    = {2016},
  doi     = {10.1016/j.is.2015.07.003}
}
```
Author-year: de Leoni M, van der Aalst WMP, Dees M (2016) A general process mining framework for correlating, predicting and clustering dynamic behavior based on event logs. Inf Syst 56:235–257
Contribution/section: **Related work.** Frames clustering of traces on derived feature vectors mixing control-flow and case/data attributes — establishes feature/semantic-enriched clustering as a recognized direction our embeddings extend. (Attribute-based rather than strictly text-aware.)
Verified: https://www.sciencedirect.com/science/article/abs/pii/S0306437915001313

##### 4.3 Berti, Schuster & van der Aalst (2023) — process mining with LLMs `NEW`
```bibtex
@inproceedings{berti2023abstractions,
  author    = {Berti, Alessandro and Schuster, Daniel and van der Aalst, Wil M. P.},
  title     = {Abstractions, Scenarios, and Prompt Definitions for Process Mining with {LLMs}: A Case Study},
  booktitle = {Business Process Management Workshops (BPM 2023)},
  series    = {Lecture Notes in Business Information Processing},
  volume    = {492},
  pages     = {427--439},
  year      = {2023},
  publisher = {Springer},
  doi       = {10.1007/978-3-031-50974-2_32},
  note      = {arXiv:2307.02194}
}
```
Author-year: Berti A, Schuster D, van der Aalst WMP (2023) Abstractions, scenarios, and prompt definitions for process mining with LLMs: a case study. In: BPM 2023 Workshops, LNBIP 492. Springer, pp 427–439
Contribution/section: **Related work / Method.** The reference LLM-in-process-mining paper (prompting/abstraction strategies, implemented in pm4py) — positions our vision-LLM parsing and LLM-assisted steps within the emerging LLM-PM literature.
Verified: https://arxiv.org/abs/2307.02194

##### 4.4 Vidgof, Bachhofner & Mendling (2023) — LLMs for BPM (survey/positioning) `NEW`
```bibtex
@inproceedings{vidgof2023large,
  author    = {Vidgof, Maxim and Bachhofner, Stefan and Mendling, Jan},
  title     = {Large Language Models for Business Process Management: Opportunities and Challenges},
  booktitle = {Business Process Management Forum (BPM Forum 2023)},
  series    = {Lecture Notes in Business Information Processing},
  volume    = {490},
  pages     = {107--123},
  year      = {2023},
  publisher = {Springer},
  doi       = {10.1007/978-3-031-41623-1_7},
  note      = {arXiv:2304.04309}
}
```
Author-year: Vidgof M, Bachhofner S, Mendling J (2023) Large language models for business process management: opportunities and challenges. In: BPM Forum 2023, LNBIP 490. Springer, pp 107–123
Contribution/section: **Introduction / Related work.** Maps opportunities/challenges of LLMs across the BPM lifecycle — broad-context citation for the motivation of combining LLMs with process mining.
Verified: https://link.springer.com/chapter/10.1007/978-3-031-41623-1_7

##### Already cited in §4 (do not re-add)
- Greco, Guzzo, Pontieri & Saccà 2006 (IEEE TKDE) — `ALREADY CITED`
- Song, Günther & van der Aalst 2009 (BPM 2008 Workshops) — `ALREADY CITED`

---

### §5 — Next-activity prediction / predictive process monitoring

Almost fully covered already; only one addition.

##### 5.1 Teinemaa et al. (2019) — outcome-oriented PPM review & benchmark `NEW`
```bibtex
@article{teinemaa2019outcome,
  author    = {Teinemaa, Irene and Dumas, Marlon and La Rosa, Marcello and Maggi, Fabrizio Maria},
  title     = {Outcome-Oriented Predictive Process Monitoring: Review and Benchmark},
  journal   = {ACM Transactions on Knowledge Discovery from Data},
  volume    = {13},
  number    = {2},
  articleno = {17},
  pages     = {1--57},
  year      = {2019},
  publisher = {ACM},
  doi       = {10.1145/3301300}
}
```
Author-year: Teinemaa I, Dumas M, La Rosa M, Maggi FM (2019) Outcome-oriented predictive process monitoring: review and benchmark. ACM Trans Knowl Discov Data 13(2):17
Contribution/section: **Related work / Evaluation methodology.** Rigorous review-and-benchmark (taxonomy, 24 datasets, sequence-encoding/bucketing pipeline) supplying an experimental-protocol template — even though its target is outcome- rather than next-activity-oriented.
Verified: https://dl.acm.org/doi/10.1145/3301300

##### Already cited in §5 (do not re-add)
- Tax, Verenich, La Rosa & Dumas 2017 (CAiSE, LSTM) — `ALREADY CITED`
- Camargo, Dumas & González-Rojas 2019 (BPM) — `ALREADY CITED`
- Bukhsh, Saeed & Dijkman 2021 (ProcessTransformer, arXiv) — `ALREADY CITED`
- Evermann, Rehse & Fettke 2017 (Decis Support Syst) — `ALREADY CITED`
- Rama-Maneiro, Vidal & Lama 2023 (IEEE TSC review/benchmark) — `ALREADY CITED`

---

### §6 — Brazilian public administration / LGPD legal context

Entirely uncited today (the article has only Council of Europe 2022, Bench-Capon
2012, Lai 2024 on the legal side) — a major gap for an *AI and Law* submission.

##### 6.1 LGPD — Lei nº 13.709/2018 (primary statute) `NEW`
```bibtex
@misc{brasil2018lgpd,
  author       = {{Brasil}},
  title        = {Lei n\textordmasculine{} 13.709, de 14 de agosto de 2018. Lei Geral de Prote\c{c}\~ao de Dados Pessoais (LGPD)},
  year         = {2018},
  howpublished = {Di\'ario Oficial da Uni\~ao, Bras\'ilia, DF, 15 ago. 2018},
  note         = {Disp\~oe sobre a prote\c{c}\~ao de dados pessoais; altera a Lei n\textordmasculine{} 12.965/2014 (Marco Civil da Internet)},
  url          = {https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm}
}
```
Author-year: Brasil (2018) Lei nº 13.709, de 14 de agosto de 2018 — Lei Geral de Proteção de Dados Pessoais (LGPD). Diário Oficial da União, Brasília
Contribution/section: **Introduction / Legal background.** The statute governing all personal-data processing in Brazil, including by public bodies — the direct legal basis for our anonymization requirement on SEI logs. **Top-3 critical.**
Verified: https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm (cross-confirmed via LexML urn:lex:br:federal:lei:2018-08-14;13709)

##### 6.2 Rocha et al. (2024) — personal-data processing by government in Brazil (empirical) `NEW`
```bibtex
@article{rocha2024critical,
  author  = {Rocha, N{\'u}bia Augusto de Sousa and de Almeida, Alexandre Nascimento and Nunes, Andr{\'e} and Angelo, Humberto},
  title   = {Critical Points for the Processing of Personal Data by the Government: An Empirical Study in {Brazil}},
  journal = {Computer Law \& Security Review},
  volume  = {54},
  pages   = {106023},
  year    = {2024},
  doi     = {10.1016/j.clsr.2024.106023}
}
```
Author-year: Rocha NAS, de Almeida AN, Nunes A, Angelo H (2024) Critical points for the processing of personal data by the government: an empirical study in Brazil. Comput Law Secur Rev 54:106023
Contribution/section: **Related work / Discussion.** Empirical (Delphi) study of the concrete challenges public managers face balancing service delivery, transparency, and privacy under the LGPD — the precise tension our article addresses, and the ideal peer-reviewed English-venue citation for an international AI & Law audience.
Verified: https://www.sciencedirect.com/science/article/abs/pii/S026736492400089X

##### 6.3 LAI — Lei nº 12.527/2011 (primary statute, transparency side) `NEW`
```bibtex
@misc{brasil2011lai,
  author       = {{Brasil}},
  title        = {Lei n\textordmasculine{} 12.527, de 18 de novembro de 2011. Lei de Acesso \`a Informa\c{c}\~ao (LAI)},
  year         = {2011},
  howpublished = {Di\'ario Oficial da Uni\~ao, Bras\'ilia, DF, 18 nov. 2011},
  note         = {Regula o acesso a informa\c{c}\~oes previsto na Constitui\c{c}\~ao Federal},
  url          = {https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2011/lei/l12527.htm}
}
```
Author-year: Brasil (2011) Lei nº 12.527, de 18 de novembro de 2011 — Lei de Acesso à Informação (LAI). Diário Oficial da União, Brasília
Contribution/section: **Legal background.** The statutory mandate for publicity of government-held information — the transparency pole in tension with LGPD's privacy pole; frames why anonymization (not withholding) reconciles publishing SEI process data.
Verified: https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2011/lei/l12527.htm (cross-confirmed via LexML urn:lex:br:federal:lei:2011-11-18;12527)

##### 6.4 Canedo et al. (2022) — LGPD compliance in a federal agency `NEW`
```bibtex
@incollection{canedo2022evaluating,
  author    = {Canedo, Edna Dias and Ribeiro, Vanessa Coelho and Cerqueira, Anderson Jefferson and Gravina, Rog{\'e}rio Machado and Cam{\~o}es, Renato and dos Reis, Vinicius Eloy and Mendon{\c{c}}a, F{\'a}bio L{\'u}cio Lopes and de Sousa~J{\'u}nior, Rafael T.},
  title     = {Evaluating and Evolving the Compliance to the Brazilian General Data Protection Law in a Federal Government Agency},
  booktitle = {Enterprise Information Systems (ICEIS 2021, Revised Selected Papers)},
  series    = {Lecture Notes in Business Information Processing},
  volume    = {455},
  pages     = {3--27},
  year      = {2022},
  publisher = {Springer},
  doi       = {10.1007/978-3-031-08965-7_1}
}
```
Author-year: Canedo ED, Ribeiro VC, Cerqueira AJ et al (2022) Evaluating and evolving the compliance to the Brazilian General Data Protection Law in a federal government agency. In: ICEIS 2021 Revised Selected Papers, LNBIP 455. Springer, pp 3–27
Contribution/section: **Related work.** A case study of operationalizing LGPD compliance inside a Brazilian federal agency — public-sector grounding for the engineering constraints our pipeline must meet. «verify» series/volume (from search snippet; title/authors/pages/DOI confirmed via Crossref).
Verified: https://doi.org/10.1007/978-3-031-08965-7_1

##### 6.5 Erickson (2019) — comparative GDPR/LGPD analysis `NEW`
```bibtex
@article{erickson2019comparative,
  author  = {Erickson, Abigayle},
  title   = {Comparative Analysis of the {EU}'s {GDPR} and {Brazil}'s {LGPD}: Enforcement Challenges with the {LGPD}},
  journal = {Brooklyn Journal of International Law},
  volume  = {44},
  number  = {2},
  pages   = {859},
  year    = {2019}
}
```
Author-year: Erickson A (2019) Comparative analysis of the EU's GDPR and Brazil's LGPD: enforcement challenges with the LGPD. Brooklyn J Int Law 44(2):859
Contribution/section: **Related work / Legal background.** English-language law-review note tracing the LGPD's lineage from the GDPR and critiquing its enforcement design — helps an international audience understand the LGPD's provenance and limits. «verify» end page (start page 859 confirmed).
Verified: https://brooklynworks.brooklaw.edu/bjil/vol44/iss2/9/

##### 6.6 GDPR — Regulation (EU) 2016/679 (comparative anchor, optional) `NEW`
```bibtex
@misc{eu2016gdpr,
  author       = {{European Parliament and Council of the European Union}},
  title        = {Regulation ({EU}) 2016/679 ... on the Protection of Natural Persons with Regard to the Processing of Personal Data (General Data Protection Regulation)},
  year         = {2016},
  howpublished = {Official Journal of the European Union, OJ L 119, 4.5.2016, pp. 1--88},
  url          = {https://eur-lex.europa.eu/eli/reg/2016/679/oj}
}
```
Author-year: European Parliament and Council (2016) Regulation (EU) 2016/679 (General Data Protection Regulation). OJ L 119, 4.5.2016, pp 1–88
Contribution/section: **Introduction / Legal background (optional).** The EU regulation the LGPD is modeled on — a one-line comparative anchor mapping our LGPD framing onto the more widely known GDPR.
Verified: https://eur-lex.europa.eu/eli/reg/2016/679/oj

---

#### Summary of additions (27 new + 1 upgrade)

| § | New refs | Notable |
|---|----------|---------|
| 1 PII anonymization | 7 | Lothritz 2023, Ben Cheikh Larbi 2023, Pilán TAB 2022, Lison 2021, Stubbs 2015, Dernoncourt 2017, Presidio |
| 2 Clustering | 5 | Traag/Leiden 2019 (must-fix), Blondel/Louvain 2008, Rousseeuw 1987, hdbscan+umap JOSS |
| 3 e-gov PM | 4 (+1 upgrade) | Araujo 2023, Delgado 2022, Racis 2025, Trottier 2025; upgrade Silva→Lima e Silva 2026 |
| 4 Trace clustering / LLM-PM | 4 | Bose 2009, de Leoni 2016, Berti 2023, Vidgof 2023 |
| 5 Next-activity | 1 | Teinemaa 2019 |
| 6 LGPD legal | 6 | LGPD 13.709/2018, Rocha 2024, LAI 12.527/2011, Canedo 2022, Erickson 2019, GDPR 2016/679 |

Fields flagged «verify» before submission: Canedo 2022 series/volume; Erickson
2019 end page. Two year caveats: Song 2009 (DBLP dates the entry 2008; LNBIP vol.
17 issued 2009 — already cited) and Berti 2023 (conference 2023; Springer
proceedings issued 2024). Rama-Maneiro TSC issue dated 2023 (online-first 2021).
