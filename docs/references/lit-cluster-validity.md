# Literature: internal cluster validity vs. downstream utility

Support material for the *Artificial Intelligence and Law* submission. Every entry below was
verified to exist: DOIs were resolved against the Crossref REST API
(`api.crossref.org/works/<doi>`) and titles/authors/venues/pages come from that authoritative
record, not from memory. Entries without a DOI (NeurIPS/PMLR/workshop proceedings) were verified
against the official proceedings pages, which are cited in the `note`/`url` field.

**Finding being situated.** 16 clusterings of 5,243 administrative processes; internal/relative
validity indices (DBCV, silhouette, Davies–Bouldin, Calinski–Harabasz on a UMAP-50 embedding) are
essentially uncorrelated with downstream utility of per-cluster sequence models
(Spearman rho: DBCV −0.05, silhouette −0.19). The best-scoring clustering (silhouette 0.981,
DBCV 0.818) is the worst downstream because it fragments into 120 micro-clusters. Three
confounds identified: (i) internal indices exclude HDBSCAN noise, so cross-algorithm comparison
is not like-for-like; (ii) silhouette structurally rewards compact convex clusters, i.e. the
k-means objective; (iii) on a common item set all 16 clusterings fall within 0.0057 accuracy.

Legend: **[+]** supports our argument · **[~]** nuances/qualifies it · **[−]** a referee will
use this against us.

---

## 1. The indices themselves, and known critiques of them

### 1.1 Rousseeuw (1987) — silhouette [+] (primary source)

```bibtex
@article{rousseeuw1987silhouettes,
  author  = {Rousseeuw, Peter J.},
  title   = {Silhouettes: A graphical aid to the interpretation and validation of cluster analysis},
  journal = {Journal of Computational and Applied Mathematics},
  volume  = {20},
  pages   = {53--65},
  year    = {1987},
  doi     = {10.1016/0377-0427(87)90125-7}
}
```
Defines s(i) = (b(i) − a(i)) / max(a(i), b(i)) from a *within-cluster mean distance* a(i) and a
*nearest-other-cluster mean distance* b(i), and averages it. Rousseeuw presents it as a *graphical
aid* to interpretation, explicitly for partitioning methods, not as an objective to be maximised
across algorithm families.

**Use for us:** cite as the definition, and note that the a(i)/b(i) construction is a
centroid-free but still *distance-to-the-bulk* contrast — which is exactly why it rewards compact,
convex, roughly equal-radius clusters. Our confound (ii) is readable straight off the definition,
so we do not need to over-claim; we need only point at the formula plus §1.5–1.7 below.

### 1.2 Davies & Bouldin (1979) [+] (primary source)

```bibtex
@article{davies1979cluster,
  author  = {Davies, David L. and Bouldin, Donald W.},
  title   = {A Cluster Separation Measure},
  journal = {IEEE Transactions on Pattern Analysis and Machine Intelligence},
  volume  = {PAMI-1},
  number  = {2},
  pages   = {224--227},
  year    = {1979},
  doi     = {10.1109/TPAMI.1979.4766909}
}
```
Defines the DB index as the mean over clusters of the worst-case ratio (scatter_i + scatter_j) /
separation(i,j). The paper's own framing states the measure "is assumed to have a data density that
is a decreasing function of distance from a vector characteristic of the cluster" — i.e. it is
*explicitly* built on a unimodal, centroid-like density assumption.

**Use for us:** the strongest single-sentence evidence for confound (ii). DB is not
shape-agnostic *by construction*; the original paper says so. A density-based clustering of
arbitrary shape violates the stated assumption, so a DB comparison of HDBSCAN against k-means is
comparing a k-means-shaped criterion across two different generative hypotheses.

### 1.3 Caliński & Harabasz (1974) [+] (primary source)

```bibtex
@article{calinski1974dendrite,
  author  = {Cali{\'n}ski, Tadeusz and Harabasz, Jerzy},
  title   = {A dendrite method for cluster analysis},
  journal = {Communications in Statistics},
  volume  = {3},
  number  = {1},
  pages   = {1--27},
  year    = {1974},
  doi     = {10.1080/03610927408827101}
}
```
The variance-ratio criterion: between-cluster dispersion over within-cluster dispersion, scaled by
degrees of freedom. It is a direct ANOVA-style trace ratio.

**Use for us:** CH is *literally* a normalised version of the k-means objective (minimise trace of
within-cluster scatter). Reporting CH alongside a k-means run is close to reporting the training
loss. Cite together with 1.2 when we make the "the index optimises what k-means optimises" point.

### 1.4 Milligan & Cooper (1985) [~]

```bibtex
@article{milligan1985examination,
  author  = {Milligan, Glenn W. and Cooper, Martha C.},
  title   = {An Examination of Procedures for Determining the Number of Clusters in a Data Set},
  journal = {Psychometrika},
  volume  = {50},
  number  = {2},
  pages   = {159--179},
  year    = {1985},
  doi     = {10.1007/BF02294245}
}
```
Monte Carlo comparison of 30 stopping rules on synthetic data containing 2–5 well-separated,
non-overlapping clusters, analysed by four hierarchical methods. Finds a very wide spread in the
rules' ability to recover the true k; a few work well, many work poorly.

**Complicates us:** this is the canonical "some indices do work" citation, and CH came out at or
near the top. **But**: the benchmark is *synthetic, non-overlapping, hierarchically generated*
data with a known k in 2–5. It is a benchmark on which compactness criteria are guaranteed to
succeed. Cite it as the origin of the field's confidence in CVIs, then note the benchmark design
does not transfer to 5,243 real administrative traces where k is unknown and cluster shapes are
not controlled.

### 1.5 Arbelaitz et al. (2013) — the standard CVI comparison [~]

```bibtex
@article{arbelaitz2013extensive,
  author  = {Arbelaitz, Olatz and Gurrutxaga, Ibai and Muguerza, Javier and
             P{\'e}rez, Jes{\'u}s M. and Perona, I{\~n}igo},
  title   = {An extensive comparative study of cluster validity indices},
  journal = {Pattern Recognition},
  volume  = {46},
  number  = {1},
  pages   = {243--256},
  year    = {2013},
  doi     = {10.1016/j.patcog.2012.07.021}
}
```
Compares 30 CVIs across a large grid of configurations (synthetic + real, varying dimensionality,
noise, cluster overlap, density) — described by the authors as the most extensive CVI comparison
published. Key result: *no index dominates*; performance is configuration-dependent, and indices
disagree substantially with each other.

**Use for us:** the standard citation for "different indices disagree". **Also a referee's
weapon**: silhouette and its variants score well overall in this study, so a referee can say
"silhouette is a validated index". Our reply is that Arbelaitz et al. evaluate CVIs against
*recovery of a known partition*, not against *task utility*, and almost all their generators
produce compact clusters.

### 1.6 Liu et al. (2010) — what internal measures actually respond to [+]

```bibtex
@inproceedings{liu2010understanding,
  author    = {Liu, Yanchi and Li, Zhongmou and Xiong, Hui and Gao, Xuedong and Wu, Junjie},
  title     = {Understanding of Internal Clustering Validation Measures},
  booktitle = {2010 IEEE International Conference on Data Mining (ICDM)},
  pages     = {911--916},
  year      = {2010},
  doi       = {10.1109/ICDM.2010.35}
}
```
Studies 11 widely used internal measures along five *aspects* — monotonicity, noise, density,
sub-clusters, and skewed distributions — and shows each measure fails on at least one; only S_Dbw
survives all five in their setup.

**Use for us:** the best short citation for "internal indices have *systematic, characterisable*
failure modes, in particular under noise and under sub-cluster structure". Our 120-micro-cluster
pathology is precisely their *sub-cluster* aspect: splitting a real cluster into sub-clusters can
*raise* a compactness-based index while destroying the semantic unit. And their *noise* aspect is
our confound (i).

### 1.7 Vendramin, Campello & Hruschka (2010) — relative validity criteria [+]

```bibtex
@article{vendramin2010relative,
  author  = {Vendramin, Lucas and Campello, Ricardo J. G. B. and Hruschka, Eduardo R.},
  title   = {Relative clustering validity criteria: A comparative overview},
  journal = {Statistical Analysis and Data Mining: The ASA Data Science Journal},
  volume  = {3},
  number  = {4},
  pages   = {209--235},
  year    = {2010},
  doi     = {10.1002/sam.10080}
}
```
Frames silhouette/DB/CH/Dunn etc. as *relative* criteria — instruments for ranking candidate
partitions, not for measuring absolute quality — and shows each has features that make it win on
some problem classes and fail on others.

**Use for us:** gives us the correct vocabulary. What we computed are *relative* validity indices;
the literature never licensed them as absolute measures of usefulness, and our result is a concrete
instance of the class-dependence they document. Also useful for the "our indices are only
meaningful within a fixed representation" argument (cf. Yerbury et al. §2.1).

### 1.8 Jaskowiak et al. (2016) — ensembles of relative criteria [~]

```bibtex
@article{jaskowiak2016strategies,
  author  = {Jaskowiak, Pablo A. and Moulavi, Davoud and Furtado, Antonio C. S. and
             Campello, Ricardo J. G. B. and Zimek, Arthur and Sander, J{\"o}rg},
  title   = {On strategies for building effective ensembles of relative clustering validity criteria},
  journal = {Knowledge and Information Systems},
  volume  = {47},
  number  = {2},
  pages   = {329--354},
  year    = {2016},
  doi     = {10.1007/s10115-015-0851-6}
}
```
Starts from the premise that no single relative criterion captures all aspects of clustering
quality and each fails in particular scenarios, then studies whether *ensembles* of criteria
mitigate this.

**Use for us:** the premise sentence is a clean, citable admission from the DBCV authors' own
group. **Complicates us:** the paper's answer is "combine criteria", i.e. a methodological fix
short of abandoning internal validation. A referee may say we should have aggregated indices
rather than concluded they are uninformative. Pre-empt: an ensemble of criteria that all reward
compactness cannot escape confound (ii), and none of the ensemble members sees the downstream task.

### 1.9 Gagolewski, Bartoszuk & Cena (2021) — "Are cluster validity measures (in)valid?" [+]

```bibtex
@article{gagolewski2021invalid,
  author  = {Gagolewski, Marek and Bartoszuk, Maciej and Cena, Anna},
  title   = {Are cluster validity measures (in)valid?},
  journal = {Information Sciences},
  volume  = {581},
  pages   = {620--636},
  year    = {2021},
  doi     = {10.1016/j.ins.2021.10.004}
}
```
Treats each internal CVI as an objective function and *directly optimises it* (rather than
evaluating pre-computed partitions). The partitions that maximise popular indices frequently
disagree with expert reference labellings — i.e. the index's own optimum is not the partition a
human would call correct.

**Use for us:** the strongest general statement in the literature that maximising an internal
index is not the same as finding a good clustering. It is the direct theoretical analogue of our
empirical result: our silhouette-0.981 clustering is what happens when you get close to the
index's optimum. Supporting material and implementations are in `genieclust`.

### 1.10 Rautenstrauch & Ohler (2026) — silhouette's assumptions, recent and blunt [+]

```bibtex
@article{rautenstrauch2026shortcomings,
  author  = {Rautenstrauch, Pia and Ohler, Uwe},
  title   = {Shortcomings of silhouette in single-cell integration benchmarking},
  journal = {Nature Biotechnology},
  volume  = {44},
  number  = {6},
  pages   = {954--958},
  year    = {2026},
  doi     = {10.1038/s41587-025-02743-4},
  note    = {Published online 30 July 2025}
}
```
Argues that silhouette-based metrics, used as the de facto benchmark scores for single-cell data
integration, cannot reliably assess either batch-effect removal or biological signal conservation,
because silhouette's assumptions (compact, roughly convex, comparable-radius groups) are routinely
violated by the label-defined groups being scored.

**Use for us:** a 2026, high-visibility, *domain-external* demonstration that a whole subfield's
silhouette-based benchmark was measuring the wrong thing. Perfect for showing our finding is not a
quirk of administrative-process data. Also directly supports confound (ii) with a recent citation
rather than only 1979/1987 primary sources.

### 1.11 Hassan et al. (2024) — recent A-to-Z survey [~] (background only)

```bibtex
@article{hassan2024atoz,
  author  = {Hassan, Bryar A. and Tayfor, Noor Bahjat and Hassan, Alla A. and
             Ahmed, Aram M. and Rashid, Tarik A. and Abdalla, Naz N.},
  title   = {From A-to-Z review of clustering validation indices},
  journal = {Neurocomputing},
  volume  = {601},
  pages   = {128198},
  year    = {2024},
  doi     = {10.1016/j.neucom.2024.128198}
}
```
Systematic review of internal and external validation indices: mathematics, ideal values,
sensitivity to input data, and suitability across domains, with a proposed classification.

**Use for us:** a single recent citation to establish that the CVI zoo is large and heterogeneous
and that index selection is itself an open problem. Low argumentative weight; use it only to keep
the related-work paragraph current.

---

## 2. Internal validity does not predict external agreement or task utility

### 2.1 Yerbury et al. (2025) — the closest thing to our result in the literature [+][~]

```bibtex
@article{yerbury2025rvi,
  author  = {Yerbury, Luke W. and Campello, Ricardo J. G. B. and
             Livingston, Jr., G. C. and Goldsworthy, Mark and O'Neil, Lachlan},
  title   = {On the Use of Relative Validity Indices for Comparing Clustering Approaches},
  journal = {ACM Transactions on Knowledge Discovery from Data},
  volume  = {19},
  number  = {8},
  pages   = {1--53},
  year    = {2025},
  doi     = {10.1145/3748726}
}
```
Investigates whether RVIs (silhouette width, Davies–Bouldin, Calinski–Harabasz, …) can be used to
select a *similarity paradigm* — the combination of normalisation, representation, and distance
measure. Over 2.7 million partitions of synthetic and real feature-vector and time-series data.
Result: RVIs are conceptually and empirically unsuitable for this purpose. The authors' explicit
recommendation is to use external validation on high-quality labelled data, or "carefully designed
outcome-oriented criteria informed by dataset characteristics and domain requirements".

**Use for us:** this is the single best citation we have. Their recommended alternative —
*outcome-oriented criteria* — is exactly the downstream-utility protocol we ran. Cite it as
prior methodological support, and cite our numbers as an empirical instance in a new domain.

**But it also complicates us, and a referee will notice.** Yerbury et al. explicitly frame the
*traditional* use of RVIs — "guide the selection of the number of clusters and compare partitions
from different clustering algorithms" — as the established, non-targeted practice, and attack only
the newer similarity-paradigm use. Read literally, they leave algorithm comparison on a fixed
representation intact, which is closer to what we did. See §8.1 for how to answer this.

### 2.2 von Luxburg, Williamson & Guyon (2012) — clustering must be judged by end-use [+]

```bibtex
@inproceedings{vonluxburg2012clustering,
  author    = {von Luxburg, Ulrike and Williamson, Robert C. and Guyon, Isabelle},
  title     = {Clustering: Science or Art?},
  booktitle = {Proceedings of ICML Workshop on Unsupervised and Transfer Learning},
  series    = {Proceedings of Machine Learning Research},
  volume    = {27},
  pages     = {65--79},
  year      = {2012},
  publisher = {PMLR},
  url       = {https://proceedings.mlr.press/v27/luxburg12a.html}
}
```
Asks whether clustering quality can be compared by a general, algorithm-independent, scientifically
sound procedure. Answer: no. "Clustering should not be treated as an application-independent
mathematical problem, but should always be studied in the context of its end-use."

**Use for us:** the philosophical licence for our whole design. Our downstream-utility criterion
*is* the end-use context. Highly quotable in the discussion. Pair with Hennig (2015).

### 2.3 Hennig (2015) — "What are the true clusters?" [+]

```bibtex
@article{hennig2015true,
  author  = {Hennig, Christian},
  title   = {What are the true clusters?},
  journal = {Pattern Recognition Letters},
  volume  = {64},
  pages   = {53--62},
  year    = {2015},
  doi     = {10.1016/j.patrec.2015.04.009}
}
```
Argues from constructivist philosophy of science that "truth" in cluster analysis is
aim-dependent: different applications require different cluster characteristics, and different
methods are good for different aims. Emphasises transparent communication of the cluster concept
in use.

**Use for us:** grounds the claim that "best clustering" is undefined absent a stated aim. It also
justifies our stating the aim up front (usable typical paths per cluster) rather than deferring to
a generic index. Strong for an *AI and Law* audience, where the aim is an institutional one.

### 2.4 Kleinberg (2002) — impossibility [+]

```bibtex
@inproceedings{kleinberg2002impossibility,
  author    = {Kleinberg, Jon},
  title     = {An Impossibility Theorem for Clustering},
  booktitle = {Advances in Neural Information Processing Systems 15 (NIPS 2002)},
  pages     = {463--470},
  year      = {2002},
  url       = {https://proceedings.neurips.cc/paper/2002/hash/43e4e6a6f341e00671e123714de019a8-Abstract.html}
}
```
No clustering function simultaneously satisfies scale-invariance, richness, and consistency;
relaxations expose the trade-offs in single-linkage, k-means, k-median, sum-of-pairs.

**Use for us:** one sentence in the introduction to establish that there is no algorithm-neutral
notion of "correct clustering", so any universal internal criterion is suspect a priori. Do not
overuse — it is about clustering *functions*, not validity indices, and a picky referee will say so.

### 2.5 Färber et al. (2010) — external labels are not a neutral yardstick either [+]

```bibtex
@inproceedings{faerber2010classlabels,
  author    = {F{\"a}rber, Ines and G{\"u}nnemann, Stephan and Kriegel, Hans-Peter and
               Kr{\"o}ger, Peer and M{\"u}ller, Emmanuel and Schubert, Erich and
               Seidl, Thomas and Zimek, Arthur},
  title     = {On Using Class-Labels in Evaluation of Clusterings},
  booktitle = {MultiClust: 1st International Workshop on Discovering, Summarizing and Using
               Multiple Clusterings, held in conjunction with KDD 2010},
  year      = {2010},
  url       = {https://www.dbs.ifi.lmu.de/~zimek/publications/MultiClustAtKDD2010/Faerberetal.pdf}
}
```
Argues that class labels used as ground truth for clustering may not correspond to the structure in
the data nor to the cluster model being evaluated, so external evaluation against labels can be as
misleading as internal evaluation. (Workshop paper; no DOI. Page numbers omitted deliberately —
we did not verify them.)

**Use for us:** protects our flank. We do *not* claim external labels are the answer; we claim a
*task* is. Cite this when explaining why we did not simply switch to ARI/NMI against an
administrative taxonomy.

### 2.6 Jeon et al. (2025) — benchmark datasets themselves may not be valid [+]

```bibtex
@article{jeon2025clm,
  author  = {Jeon, Hyeon and Aupetit, Micha{\"e}l and Shin, DongHwa and Cho, Aeri and
             Park, Seokhyeon and Seo, Jinwook},
  title   = {Measuring the Validity of Clustering Validation Datasets},
  journal = {IEEE Transactions on Pattern Analysis and Machine Intelligence},
  volume  = {47},
  number  = {6},
  pages   = {5045--5058},
  year    = {2025},
  doi     = {10.1109/TPAMI.2025.3548011}
}
```
Introduces *cluster-label matching* (CLM) to quantify how well a benchmark dataset's class labels
align with its actual cluster structure, and shows that widely used validation datasets vary
enormously in CLM — so conclusions drawn from them about which algorithm or index is "best" are
dataset-dependent.

**Use for us:** the meta-level point. Every study that certifies a CVI (Milligan & Cooper,
Arbelaitz, …) certified it on benchmark corpora whose labels may not match the data's structure.
It weakens the "silhouette has been validated" rebuttal at the root.

### 2.7 Halkidi, Batistakis & Vazirgiannis (2001) — the classic survey [~] (background)

```bibtex
@article{halkidi2001validation,
  author  = {Halkidi, Maria and Batistakis, Yannis and Vazirgiannis, Michalis},
  title   = {On Clustering Validation Techniques},
  journal = {Journal of Intelligent Information Systems},
  volume  = {17},
  number  = {2--3},
  pages   = {107--145},
  year    = {2001},
  doi     = {10.1023/A:1012801612483}
}
```
The canonical taxonomy — external / internal / relative validation — plus an approach for
selecting the number of clusters and the best scheme by a quality index.

**Use for us:** required background citation to name our three categories precisely. It is also,
usefully, the paper that established the *aspirational* framing we are pushing back on: validation
as a means to identify "the best clustering scheme" by index value.

### 2.8 Hennig (2022) — nine methods, many indexes, no single winner [+]

```bibtex
@article{hennig2022empirical,
  author  = {Hennig, Christian},
  title   = {An empirical comparison and characterisation of nine popular clustering methods},
  journal = {Advances in Data Analysis and Classification},
  volume  = {16},
  number  = {1},
  pages   = {201--229},
  year    = {2022},
  doi     = {10.1007/s11634-021-00478-z}
}
```
Characterises nine clustering methods on 42 real datasets using several validation indexes that
each measure a *distinct aspect* (small within-cluster distances, separation, closeness to
Gaussian, …); on the 30 datasets with a "true" clustering it also reports similarity to truth.
The methods come out characterised rather than ranked — different methods win on different aspects.

**Use for us:** directly supports our confound (iii) framing: once you fix the comparison
properly, method choice does not sort into a clear winner, and index-based rankings mostly re-state
which aspect the index measures.

### 2.9 Van Mechelen et al. (2023) — benchmarking good practice [+]

```bibtex
@article{vanmechelen2023whitepaper,
  author  = {Van Mechelen, Iven and Boulesteix, Anne-Laure and Dangl, Rainer and Dean, Nema and
             Hennig, Christian and Leisch, Friedrich and Steinley, Douglas and Warrens, Matthijs J.},
  title   = {A white paper on good research practices in benchmarking: The case of cluster analysis},
  journal = {WIREs Data Mining and Knowledge Discovery},
  volume  = {13},
  number  = {6},
  pages   = {e1511},
  year    = {2023},
  doi     = {10.1002/widm.1511}
}
```
Community white paper on how cluster-analysis benchmark studies should be designed and reported:
research question first, then data-generating mechanism, methods, and *criteria chosen to match
the research question*.

**Use for us:** methodological cover for our design. We ran 16 clusterings across 2 text variants
and swept parameters, and evaluated against a criterion matched to the stated aim — this is the
white paper's recommended shape. Cite it when defending the study design in a rebuttal.

### 2.10 Rodriguez et al. (2019) — algorithm choice matters less than expected [~]

```bibtex
@article{rodriguez2019comparative,
  author  = {Rodriguez, Mayra Z. and Comin, Cesar H. and Casanova, Dalcimar and Bruno, Odemir M. and
             Amancio, Diego R. and Costa, Luciano da F. and Rodrigues, Francisco A.},
  title   = {Clustering algorithms: A comparative approach},
  journal = {PLOS ONE},
  volume  = {14},
  number  = {1},
  pages   = {e0210236},
  year    = {2019},
  doi     = {10.1371/journal.pone.0210236}
}
```
Compares clustering algorithms on artificial data with tunable class count, separation, and
dimensionality, and examines parameter sensitivity. Finds performance is dominated by parameter
configuration rather than by algorithm identity, and that default configurations are frequently
suboptimal.

**Use for us:** modest support for confound (iii) — "algorithm choice was immaterial (0.0057
accuracy spread)". Their result is that configuration, not algorithm family, drives outcomes.
**Careful:** they *do* find the spectral approach performs particularly well at defaults, so this
is not a clean "all algorithms are equal" citation. Use it for the parameter-dominance point only.

---

## 3. Evaluating clustering (and unsupervised models generally) by a downstream task

### 3.1 Chang et al. (2009) — the canonical intrinsic-vs-extrinsic inversion [+]

```bibtex
@inproceedings{chang2009teahaves,
  author    = {Chang, Jonathan and Boyd-Graber, Jordan and Gerrish, Sean and
               Wang, Chong and Blei, David M.},
  title     = {Reading Tea Leaves: How Humans Interpret Topic Models},
  booktitle = {Advances in Neural Information Processing Systems 22 (NIPS 2009)},
  pages     = {288--296},
  year      = {2009},
  url       = {https://papers.nips.cc/paper_files/paper/2009/hash/f92586a25bb3145facd64ab20fd554ff-Abstract.html}
}
```
Introduces word-intrusion and topic-intrusion human tasks and shows that the field's consensus
intrinsic metric — held-out likelihood — is *negatively* correlated with human-judged topic
interpretability. Their phrasing: models that perform better on held-out likelihood may infer less
semantically meaningful topics.

**Use for us:** the strongest rhetorical analogue available. A whole subfield's standard intrinsic
metric was found to be anti-correlated with the actual use. Our silhouette rho = −0.19 is the same
shape of result. This is the citation that makes a referee accept the finding as a *known genre*
rather than an artefact.

### 3.2 Schnabel et al. (2015) — intrinsic and extrinsic evaluations rank differently [+]

```bibtex
@inproceedings{schnabel2015evaluation,
  author    = {Schnabel, Tobias and Labutov, Igor and Mimno, David and Joachims, Thorsten},
  title     = {Evaluation methods for unsupervised word embeddings},
  booktitle = {Proceedings of the 2015 Conference on Empirical Methods in Natural Language Processing},
  pages     = {298--307},
  year      = {2015},
  publisher = {Association for Computational Linguistics},
  doi       = {10.18653/v1/D15-1036}
}
```
Systematic study of intrinsic (similarity/analogy) versus extrinsic (downstream-task) evaluation of
unsupervised embeddings. Different evaluations produce different orderings of the same methods,
which "calls into question the common assumption that there is one single optimal vector
representation".

**Use for us:** generalises §3.1 beyond topic models: for unsupervised representations broadly,
intrinsic scores and task scores induce different rankings. Directly parallel to our claim that
DBCV/silhouette rankings and downstream-utility rankings are different orderings.

### 3.3 De Weerdt et al. (2013) — downstream evaluation *in process mining* [+]

```bibtex
@article{deweerdt2013active,
  author  = {De Weerdt, Jochen and vanden Broucke, Seppe and Vanthienen, Jan and Baesens, Bart},
  title   = {Active Trace Clustering for Improved Process Discovery},
  journal = {IEEE Transactions on Knowledge and Data Engineering},
  volume  = {25},
  number  = {12},
  pages   = {2708--2720},
  year    = {2013},
  doi     = {10.1109/TKDE.2013.64}
}
```
Proposes ActiTraC, which clusters traces so as to optimise the *quality of the process models
discovered from each cluster*, rather than optimising a distance-space objective — and evaluates on
four complex real-life event logs by discovered-model quality.

**Use for us:** the domain precedent. It establishes that in process/trace analysis, the accepted
evaluation target is downstream model quality, not an internal index in feature space. It makes our
per-cluster-sequence-model criterion a *continuation* of established practice rather than an
invention. Essential for the AI&Law/administrative-process framing.

### 3.4 Zandkarimi et al. (2020) — trace clustering framework and its evaluation [+]

```bibtex
@inproceedings{zandkarimi2020generic,
  author    = {Zandkarimi, Fareed and Rehse, Jana-Rebecca and Soudmand, Pouya and Hoehle, Hartmut},
  title     = {A Generic Framework for Trace Clustering in Process Mining},
  booktitle = {2020 2nd International Conference on Process Mining (ICPM)},
  pages     = {177--184},
  year      = {2020},
  doi       = {10.1109/ICPM49681.2020.00034}
}
```
Decomposes trace clustering into interchangeable stages (encoding, distance, algorithm, evaluation)
and studies the combinations, with the aim of yielding sublogs whose discovered models are less
complex and more understandable.

**Use for us:** recent, in-domain, and supports two things at once: (a) the field's evaluation
target is model comprehensibility/complexity downstream, and (b) the pipeline stages we swept
(2 text variants × algorithms × parameters) are the recognised design space.

### 3.5 Hennig (2019) — validation by user-relevant characteristics [+]

```bibtex
@incollection{hennig2019validation,
  author    = {Hennig, Christian},
  title     = {Cluster Validation by Measurement of Clustering Characteristics Relevant to the User},
  booktitle = {Data Analysis and Applications 1: Clustering and Regression, Modeling-Estimating,
               Forecasting and Data Mining},
  editor    = {Skiadas, Christos H. and Bozeman, James R.},
  pages     = {1--24},
  publisher = {Wiley},
  year      = {2019},
  doi       = {10.1002/9781119597568.ch1}
}
```
A framework for the decisions in a practical cluster analysis, tying each decision — including
which validation characteristics to measure — to the clustering aim in the given application.

**Use for us:** the constructive counterpart to our negative result. We are not only saying "the
indices failed"; we are saying validation must be measured against the user-relevant
characteristic, which here is the usability of the per-cluster typical path.

---

## 4. Validity computed in a reduced/embedded space

### 4.1 Wang & Ye (2026) — the exact methodological objection, formalised [+]

```bibtex
@article{wang2026deepclustering,
  author  = {Wang, Zeya and Ye, Chenglong},
  title   = {Deep Clustering Evaluation: How to Validate Internal Clustering Validation Measures},
  journal = {Journal of the American Statistical Association},
  volume  = {121},
  number  = {553},
  pages   = {223--236},
  year    = {2026},
  doi     = {10.1080/01621459.2025.2592926}
}
```
Argues that internal validation measures designed for low-dimensional spaces are problematic in
deep clustering for two distinct reasons: the curse of dimensionality if applied to the raw
high-dimensional input, and — critically for us — *unreliable comparison of clustering results when
applied to embedded data from different embedding spaces*, because the embedding varies with
training procedure and parameters. Proposes a framework for applying CVIs to embedded spaces so
that internal validation aligns better with external validation.

**Use for us:** the single best citation for confound relating to our UMAP-50 space. It is peer
reviewed, in JASA, and it says in plain terms that a CVI computed in a learned low-dimensional
embedding measures a property of *the embedding as much as of the partition*. Cite it when we state
that our DBCV/silhouette numbers are not comparable across representations and are inflated
relative to the original space.

### 4.2 Chari & Pachter (2023) — 2-D reduction necessarily distorts [+]

```bibtex
@article{chari2023specious,
  author  = {Chari, Tara and Pachter, Lior},
  title   = {The specious art of single-cell genomics},
  journal = {PLOS Computational Biology},
  volume  = {19},
  number  = {8},
  pages   = {e1011288},
  year    = {2023},
  doi     = {10.1371/journal.pcbi.1011288}
}
```
Shows that extreme dimension reduction (hundreds/thousands of dimensions to 2) inevitably induces
significant distortion of the high-dimensional dataset, and that the resulting embeddings are
nonetheless used for quantitative exploratory claims.

**Use for us:** the high-profile "do not do quantitative analysis on the embedding" citation.
**Nuance to state honestly:** their argument targets reduction to 2–3 dimensions; we reduced to 50,
which is a much weaker distortion regime. We should say so explicitly rather than let a referee
say it — and lean on Wang & Ye (§4.1) for the argument that applies at 50 dimensions too.

### 4.3 Kobak & Linderman (2021) — embedding geometry is an artefact of settings [+]

```bibtex
@article{kobak2021initialization,
  author  = {Kobak, Dmitry and Linderman, George C.},
  title   = {Initialization is critical for preserving global data structure in both t-SNE and UMAP},
  journal = {Nature Biotechnology},
  volume  = {39},
  number  = {2},
  pages   = {156--157},
  year    = {2021},
  doi     = {10.1038/s41587-020-00809-z}
}
```
Shows that the apparent superiority of UMAP over t-SNE at preserving global structure is entirely
attributable to a difference in default initialisation (Laplacian eigenmaps vs. random), not to the
objective.

**Use for us:** short and devastating. The global geometry of a UMAP embedding — precisely the
geometry a silhouette or DB score reads — is contingent on an implementation default. Any
absolute-valued index computed on it inherits that contingency.

### 4.4 Wang, Huang, Rudin & Shaposhnik (2021) — local/global trade-off is structural [+]

```bibtex
@article{wang2021understanding,
  author  = {Wang, Yingfan and Huang, Haiyang and Rudin, Cynthia and Shaposhnik, Yaron},
  title   = {Understanding How Dimension Reduction Tools Work: An Empirical Approach to Deciphering
             t-SNE, UMAP, TriMap, and PaCMAP for Data Visualization},
  journal = {Journal of Machine Learning Research},
  volume  = {22},
  number  = {201},
  pages   = {1--73},
  year    = {2021},
  url     = {https://jmlr.org/papers/v22/20-1061.html}
}
```
Decomposes the loss functions of t-SNE/UMAP/TriMap/PaCMAP and shows empirically that preserving
local structure and preserving global structure are in tension: methods generally achieve one at
the expense of the other.

**Use for us:** explains *why* §4.3 happens. A separation-based index (silhouette, DB, CH) reads
global structure; UMAP is tuned for local structure. So the index reads the part of the geometry
the method does not guarantee. Good for a single technical sentence in the methods discussion.

### 4.5 Allaoui, Kherfi & Cheriet (2020) — the counter-case [−]

```bibtex
@inproceedings{allaoui2020umap,
  author    = {Allaoui, Mebarka and Kherfi, Mohammed Lamine and Cheriet, Abdelhakim},
  title     = {Considerably Improving Clustering Algorithms Using {UMAP} Dimensionality Reduction
               Technique: A Comparative Study},
  booktitle = {Image and Signal Processing (ICISP 2020)},
  series    = {Lecture Notes in Computer Science},
  volume    = {12119},
  pages     = {317--325},
  year      = {2020},
  publisher = {Springer},
  doi       = {10.1007/978-3-030-51935-3_34}
}
```
Reports that applying UMAP before clustering considerably improves the accuracy *and* runtime of
several clustering algorithms across benchmark datasets.

**Argues against us / against a naive reading of §4.1–4.4:** a referee can cite this to say
UMAP-then-cluster is established good practice. Note carefully: it is a *counter to a strawman*.
We do not claim UMAP harms clustering; we claim UMAP-space *validity indices* do not transfer.
Allaoui et al. measure improvement in clustering *accuracy against labels*, i.e. an external
criterion — which is our point, not theirs. Cite it and make this distinction explicitly.

---

## 5. Stability / resampling as an alternative validity criterion

### 5.1 Hennig (2007) — clusterboot [+]

```bibtex
@article{hennig2007clusterwise,
  author  = {Hennig, Christian},
  title   = {Cluster-wise assessment of cluster stability},
  journal = {Computational Statistics \& Data Analysis},
  volume  = {52},
  number  = {1},
  pages   = {258--271},
  year    = {2007},
  doi     = {10.1016/j.csda.2006.11.025}
}
```
Resamples the data under several schemes (bootstrap, subsetting, jittering, replacement of points
by noise), matches each original cluster to its most similar cluster in each resampled clustering
via the Jaccard coefficient, and uses the mean Jaccard similarity as a *per-cluster* stability
index. Implemented as `clusterboot` in the R package `fpc`.

**Use for us:** the standard, citable alternative. Crucially it is *cluster-wise*, which suits our
pathology directly: the 120-micro-cluster solution should show low per-cluster Jaccard stability
even while its global silhouette is 0.981. Recommend this in the "what should be done instead"
paragraph — and note honestly in limitations if we did not run it.

### 5.2 von Luxburg (2010) — the stability literature, surveyed [~]

```bibtex
@article{vonluxburg2010stability,
  author  = {von Luxburg, Ulrike},
  title   = {Clustering Stability: An Overview},
  journal = {Foundations and Trends in Machine Learning},
  volume  = {2},
  number  = {3},
  pages   = {235--274},
  year    = {2010},
  doi     = {10.1561/2200000008}
}
```
Monograph-length survey of stability-based model selection: what it does and does not guarantee,
and in which regimes stability-based k-selection is provably misleading.

**Use for us:** cite alongside §5.1 so we do not appear to be naively promoting stability as a
cure. It is the honest framing: stability is a *different* criterion with its own failure modes,
not a fix.

### 5.3 Ben-David, von Luxburg & Pál (2006) — stability can also fail [−]

```bibtex
@inproceedings{bendavid2006sober,
  author    = {Ben-David, Shai and von Luxburg, Ulrike and P{\'a}l, D{\'a}vid},
  title     = {A Sober Look at Clustering Stability},
  booktitle = {Learning Theory (COLT 2006)},
  series    = {Lecture Notes in Computer Science},
  volume    = {4005},
  pages     = {5--19},
  year      = {2006},
  publisher = {Springer},
  doi       = {10.1007/11776420_4}
}
```
Shows that stability-based selection of the number of clusters can select poor clusterings; in the
large-sample limit stability is governed by the behaviour of the *objective function's* minimiser
rather than by the presence of real structure.

**Argues against a naive "just use stability instead" recommendation.** A referee who accepts our
critique of internal indices will immediately ask what we propose instead; if we say "stability",
this paper is the reply. Pre-empt it: we propose downstream utility as the primary criterion and
stability only as a secondary diagnostic.

### 5.4 Ullmann, Hennig & Boulesteix (2022) — validation on validation data [+]

```bibtex
@article{ullmann2022validation,
  author  = {Ullmann, Theresa and Hennig, Christian and Boulesteix, Anne-Laure},
  title   = {Validation of cluster analysis results on validation data: A systematic framework},
  journal = {WIREs Data Mining and Knowledge Discovery},
  volume  = {12},
  number  = {3},
  pages   = {e1444},
  year    = {2022},
  doi     = {10.1002/widm.1444}
}
```
Systematic framework for validating a clustering by checking on held-out or independently collected
validation data whether it remains stable with respect to cluster membership, internal properties,
external associations, and visual patterns — a use of replication rather than of an index.

**Use for us:** the modern, methodological statement of "validate against something other than an
index". Also gives us a principled description of what a hold-out design for clustering would look
like, which strengthens the limitations/future-work section.

### 5.5 Akhanli & Hennig (2020) — calibrate and aggregate, do not read raw index values [+]

```bibtex
@article{akhanli2020comparing,
  author  = {Akhanli, Serhat Emre and Hennig, Christian},
  title   = {Comparing clusterings and numbers of clusters by aggregation of calibrated
             clustering validity indexes},
  journal = {Statistics and Computing},
  volume  = {30},
  number  = {5},
  pages   = {1523--1544},
  year    = {2020},
  doi     = {10.1007/s11222-020-09958-2}
}
```
Proposes a set of indexes measuring *distinct* clustering aspects, then **calibrates** each index
against a random-clustering baseline before any aggregation, because raw index values from
different indexes (and from clusterings with different k) are not on a comparable scale.

**Use for us:** important technical support for our confound (i) and for the k-dependence problem.
Our silhouette 0.981 at k=120 versus a lower value at small k is not a like-for-like comparison
under this paper's argument — raw index values are not calibrated across k or across algorithms.
Cite this to justify *why* the naive cross-clustering ranking is invalid, independent of the
downstream result.

### 5.6 Monti et al. (2003) — consensus clustering as resampling-based validation [~]

```bibtex
@article{monti2003consensus,
  author  = {Monti, Stefano and Tamayo, Pablo and Mesirov, Jill and Golub, Todd},
  title   = {Consensus Clustering: A Resampling-Based Method for Class Discovery and
             Visualization of Gene Expression Microarray Data},
  journal = {Machine Learning},
  volume  = {52},
  number  = {1--2},
  pages   = {91--118},
  year    = {2003},
  doi     = {10.1023/A:1023949509487}
}
```
Uses repeated subsampling and a consensus matrix both to produce a clustering and to *assess the
stability* of the discovered clusters and choose k.

**Use for us:** relevant because our 16 clusterings include a **consensus** variant. Cite as the
origin of the consensus/stability idea. Be careful: consensus clustering is known to produce
apparently stable structure even in null data, so do not present our consensus run as a validity
argument.

---

## 6. DBCV and density-based validation specifically

### 6.1 Moulavi et al. (2014) — DBCV [+] (primary source)

```bibtex
@inproceedings{moulavi2014dbcv,
  author    = {Moulavi, Davoud and Jaskowiak, Pablo A. and Campello, Ricardo J. G. B. and
               Zimek, Arthur and Sander, J{\"o}rg},
  title     = {Density-Based Clustering Validation},
  booktitle = {Proceedings of the 2014 SIAM International Conference on Data Mining (SDM)},
  pages     = {839--847},
  year      = {2014},
  publisher = {Society for Industrial and Applied Mathematics},
  doi       = {10.1137/1.9781611973440.96}
}
```
Introduces DBCV: a *relative* validity index for density-based, arbitrarily shaped clusters, built
from density-sparseness within clusters and density-separation between them, using all-points-core
distances and minimum spanning trees under mutual reachability.

**Use for us:** the definition, and the source of an important qualifier the authors themselves
apply — DBCV is presented as a **relative** index, i.e. for ranking candidate partitions produced
under comparable conditions, not as an absolute quality score comparable across algorithm families
with different noise handling.

### 6.2 Campello et al. (2015) — HDBSCAN* and the status of noise [+]

```bibtex
@article{campello2015hierarchical,
  author  = {Campello, Ricardo J. G. B. and Moulavi, Davoud and Zimek, Arthur and Sander, J{\"o}rg},
  title   = {Hierarchical Density Estimates for Data Clustering, Visualization, and Outlier Detection},
  journal = {ACM Transactions on Knowledge Discovery from Data},
  volume  = {10},
  number  = {1},
  pages   = {1--51},
  year    = {2015},
  doi     = {10.1145/2733381}
}
```
The full HDBSCAN* framework: a complete density-based clustering hierarchy over all density
thresholds, with integrated outlier detection and visualisation. Noise is a *first-class output* of
the model, not a residue.

**Use for us:** grounds confound (i). If noise is a first-class model output, then scoring only
the non-noise points and comparing that score to a partitional method that assigns every point is
structurally unfair — the density method is being graded on a self-selected easy subset.

### 6.3 Beer et al. (2026) — DISCO: CVIs do not evaluate noise [+] (strongest support for confound (i))

```bibtex
@inproceedings{beer2026disco,
  author    = {Beer, Anna and Krieger, Lena and Weber, Pascal and Ritzert, Martin and
               Assent, Ira and Plant, Claudia},
  title     = {Internal Evaluation of Density-Based Clusterings with Noise},
  booktitle = {International Conference on Learning Representations (ICLR 2026)},
  year      = {2026},
  eprint    = {2503.00127},
  archivePrefix = {arXiv},
  primaryClass  = {cs.LG},
  url       = {https://arxiv.org/abs/2503.00127}
}
```
States that existing cluster validity indices do not capture noise assignments — they merely count
noise points rather than evaluating whether the noise labels are *correct* — and introduces DISCO,
the first CVI to assess noise-assignment quality, adapting the silhouette framework to
density-connectivity so it handles arbitrary shapes.

**Use for us:** this is the citation that turns our confound (i) from an observation into a
literature-backed methodological objection: at ICLR 2026 the field explicitly acknowledged that no
prior CVI evaluates noise, which is exactly why our HDBSCAN-vs-k-means index comparison is
confounded. **Caveat to state:** conference paper, arXiv preprint 2503.00127; verify the final
proceedings pagination before camera-ready.

### 6.4 Chicco et al. (2025) — DBCV defended [−]

```bibtex
@article{chicco2025dbcv,
  author  = {Chicco, Davide and Sabino, Giuseppe and Oneto, Luca and Jurman, Giuseppe},
  title   = {The {DBCV} index is more informative than {DCSI}, {CDbw}, and {VIASCKDE} indices for
             unsupervised clustering internal assessment of concave-shaped and density-based clusters},
  journal = {PeerJ Computer Science},
  volume  = {11},
  pages   = {e3095},
  year    = {2025},
  doi     = {10.7717/peerj-cs.3095}
}
```
Benchmarks DBCV against DCSI, CDbw and VIASCKDE on synthetic data with increasing noise and on
real electronic-health-record datasets. DBCV degrades appropriately with data quality in 26/30
synthetic tests and tracks the Adjusted Rand Index in 9/15 real tests (60%), versus DCSI 46.7%,
VIASCKDE 26.7%, CDbw 0%. Conclusion: DBCV is the most informative of the four.

**Argues against us — the most likely referee citation.** A 2025 paper concluding DBCV is
informative, on EHR data (administratively adjacent), including agreement with an external index.
Answers available: (a) 60% agreement with ARI is itself modest — 6 of 15 tests disagreed;
(b) their comparison is *within* density-based indices on *one* clustering pipeline, not across
algorithm families with differing noise semantics; (c) informativeness about *cluster geometry* is
not the same as predictiveness of *downstream task utility*, which is our claim. Cite it
prominently and answer it, rather than omitting it.

### 6.5 Gagolewski (2022) — benchmark framework [~] (supporting infrastructure)

```bibtex
@article{gagolewski2022framework,
  author  = {Gagolewski, Marek},
  title   = {A framework for benchmarking clustering algorithms},
  journal = {SoftwareX},
  volume  = {20},
  pages   = {101270},
  year    = {2022},
  doi     = {10.1016/j.softx.2022.101270}
}
```
An open benchmark suite for clustering with multiple reference partitions per dataset, precisely
because a single ground truth is often not well defined.

**Use for us:** optional. Its multiple-reference-partitions design reinforces §2.3/§2.5 — there is
often no single correct clustering, only aim-dependent ones.

---

## 7. Strongest 8 citations for our argument

Ranked by how much load each can carry in the paper.

| # | Citation | Carries | Where to place |
|---|---|---|---|
| 1 | **Yerbury et al. (2025)**, TKDD, `10.1145/3748726` | RVIs are empirically unsuitable for selecting between clustering approaches (2.7M partitions); recommends outcome-oriented criteria instead — literally our protocol | Discussion, opening the "why internal indices fail here" argument |
| 2 | **Gagolewski et al. (2021)**, Inf. Sci., `10.1016/j.ins.2021.10.004` | Directly optimising a CVI produces partitions experts reject — the theory behind our silhouette-0.981/worst-utility case | Right after we report the 120-cluster pathology |
| 3 | **Chang et al. (2009)**, NIPS 22 | A field's standard intrinsic metric found *anti*-correlated with actual use; makes our rho = −0.19 a recognised genre, not an anomaly | Introduction and discussion; the framing citation |
| 4 | **Wang & Ye (2026)**, JASA, `10.1080/01621459.2025.2592926` | Peer-reviewed statement that CVIs computed in learned embeddings are unreliable across embedding spaces — covers our UMAP-50 confound at the right dimensionality | Methods/limitations, on the UMAP-50 embedding |
| 5 | **Beer et al. (2026)**, ICLR, arXiv:2503.00127 | No prior CVI evaluates noise assignments — makes confound (i) a literature-recognised defect, not our excuse | Right where we say indices exclude HDBSCAN noise |
| 6 | **von Luxburg, Williamson & Guyon (2012)**, PMLR 27:65–79 | Clustering must be judged in the context of its end-use; no algorithm-independent quality procedure exists | Introduction, motivating the downstream-utility design |
| 7 | **De Weerdt et al. (2013)**, TKDE, `10.1109/TKDE.2013.64` | In-domain precedent: trace clustering evaluated by downstream discovered-model quality | Related work; makes our criterion domain-standard |
| 8 | **Rautenstrauch & Ohler (2026)**, Nat. Biotechnol., `10.1038/s41587-025-02743-4` | Recent, high-visibility demonstration that silhouette's shape assumptions invalidate a whole benchmark suite | Confound (ii), as the modern citation next to Davies & Bouldin (1979) |

Runners-up worth keeping in the bib: Akhanli & Hennig (2020) for index calibration across k;
Hennig (2015) for aim-dependence; Liu et al. (2010) for the sub-cluster/noise failure modes.

---

## 8. Counter-arguments a referee will raise

### 8.1 "Yerbury et al. only attack similarity-paradigm selection; comparing algorithms with RVIs is still fine."

The strongest objection, and it comes from our own best citation. Yerbury et al. describe
"compar[ing] partitions from different clustering algorithms" as the *traditional* RVI use and
target only the newer similarity-paradigm use.

**Answer.** (a) Our 16 clusterings are *not* on one fixed footing — HDBSCAN emits noise and k-means
does not, so the index is computed on different item sets, which is a similarity/comparability
violation in spirit even if not in their letter; cite Beer et al. (2026) and Akhanli & Hennig (2020).
(b) Our claim is narrower and empirical: within *this* study the ranking induced by RVIs does not
predict task utility (rho = −0.05 / −0.19). We are not claiming RVIs are universally invalid.
(c) Yerbury et al.'s constructive recommendation — outcome-oriented criteria — is what we did, so
the paper supports our method even where it does not endorse our full generalisation.

### 8.2 "DBCV is a validated, informative index — see Chicco et al. (2025)."

**Answer.** Chicco et al. compare DBCV against three other density-based indices, within one
pipeline, on geometry recovery. Even there, agreement with ARI is 60% (9/15). Informativeness about
geometry is not predictiveness of downstream utility; that is exactly the gap our study measures.
Do not contest their result — reframe the quantity being measured.

### 8.3 "Silhouette and CH are validated by Milligan & Cooper (1985) and Arbelaitz et al. (2013)."

**Answer.** Both certify indices against *recovery of a known partition* on benchmark corpora
composed largely of compact, well-separated clusters. Jeon et al. (2025) show benchmark corpora
themselves vary in how well their labels match actual cluster structure. Neither study evaluates an
index against a task outcome, which is the criterion at issue.

### 8.4 "Your rho values are computed over only 16 clusterings — that is underpowered."

The most dangerous statistical objection, and it is not answerable by citation. **Answer honestly
in the paper:** report confidence intervals or a permutation p-value for the Spearman rho on n=16,
state that we cannot reject a modest positive association, and rest the argument on the
*mechanistic* case (the 120-micro-cluster example, the noise-exclusion confound, the CH/k-means
objective identity) rather than on the correlation alone. Do not let the rho carry the claim by
itself.

### 8.5 "UMAP before clustering is standard and beneficial — Allaoui et al. (2020)."

**Answer.** We agree, and we did it. Our claim is about computing *validity indices* in that space,
not about clustering in it. Note that Allaoui et al. themselves measure improvement by *external*
accuracy, not by an internal index — which is our position, not a refutation of it. Cite Wang & Ye
(2026), Kobak & Linderman (2021), and Wang et al. (2021) for why the embedding's global geometry —
the only thing separation-based indices can read — is contingent on method and initialisation.

### 8.6 "If internal indices are unreliable, use stability instead — why didn't you?"

**Answer.** Cite Ben-David et al. (2006) and von Luxburg (2010): stability-based selection has its
own documented failure modes and can select poor clusterings. We propose Hennig's *cluster-wise*
bootstrap (2007) as a secondary diagnostic — it would flag the 120-micro-cluster solution — and
Ullmann et al. (2022) as the principled hold-out framework. If we did not run these, say so in
limitations; the omission is defensible, silence about it is not.

### 8.7 "All 16 clusterings within 0.0057 accuracy just means your downstream metric is insensitive."

Not a literature objection but the sharpest methodological one, and it partly undercuts our own
headline: if the downstream criterion barely discriminates, a near-zero correlation with anything
is unsurprising. **Answer in the paper:** report the downstream metric's own spread and
measurement noise, distinguish the common-item-set comparison (0.0057 spread, confound iii) from
the *typical-path usability* judgement on which the 120-cluster solution actually fails, and be
explicit that these are two different downstream quantities. Do not let them be conflated.

### 8.8 "Chari & Pachter is about 2-D; you used 50 dimensions."

**Answer.** Correct, and we should concede it in-text rather than be caught. Lean on Wang & Ye
(2026), whose argument is about *embedded spaces generally* and about non-comparability across
embeddings, not about the 2-D extreme.

---

## 9. Deliberately excluded

- No page numbers are given for Färber et al. (2010) — the MultiClust workshop pagination was not
  verified. Cite without pages or with the PDF URL.
- Beer et al. (2026) is cited from arXiv:2503.00127 plus the ICLR 2026 poster listing; final
  proceedings pagination must be checked before camera-ready.
- Jaskowiak et al. is dated **2016** (KAIS 47(2):329–354); Crossref's `issued` field shows the 2015
  online-first date. Same pattern for Rautenstrauch & Ohler (online 2025, print Nat. Biotechnol.
  44(6), 2026) and Ullmann et al. (online 2021, WIREs 12(3), 2022) — dates given above follow the
  print issue.
- Several plausible-sounding items encountered during the search were **not** included because
  publication could not be confirmed to the standard used here. Nothing above is reconstructed
  from memory.
