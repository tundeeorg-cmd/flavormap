# RQ1, rebuilt at region level

**Run 2026-08-23** on the kapook corpus, seed 42, 9,999 permutations. Regenerate with
`uv run python -m scripts.rq1_region_level`. Numbers below come from that run;
`data/coverage/rq1_region_signal.json` holds them machine-readable.

## What could not be rebuilt, and why

CLAUDE.md §4 specifies RQ1 as a distance-decay curve — cosine distance on province TF-IDF
against great-circle kilometres — with change-point detection, and a boundary width in
kilometres as the output. **That analysis is not available on this corpus.** At a 1.3%
labelled fraction §4's own constraint collapses the unit from 77 provinces to four
regions, and four units give six pairwise distances. Six points do not support a LOESS
fit or a change point.

The Mantel test fails on the same arithmetic. A 4×4 distance matrix has 4! = 24 distinct
row permutations, so the smallest p-value the permutation scheme can produce is
1/24 ≈ 0.042. The test sits at its floor before it sees data. §5's instruction to use
permutation rather than a parametric p-value is what makes this visible; a parametric
p-value on six pairs would have reported something and meant nothing.

**No boundary width in kilometres is reported, and none can be from this corpus.**

## What was run instead

The question underneath RQ1: does region membership explain ingredient composition at
all? The unit is the recipe, not the region, so n is the number of labelled recipes and
the permutation shuffles recipe labels. This answers a weaker question than §4 asks —
whether there is signal, not where the boundary lies or how wide it is.

161 pages carry an unambiguous region label: 33 from the researcher-confirmed dish
attributions, 128 from an unambiguous region term in the page text. A page whose evidence
points at two regions is left unlabelled.

Because a kapook page may hold one dish or forty-six, three cohorts are reported. The
**single-section cohort is the reported result**; the others show what pooling does.

| cohort | n | Central | North | Northeast | South | within | between | separation | p |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **single** | **58** | 7 | 9 | 28 | 14 | 0.8887 | 0.9475 | **+0.0588** | **0.0001** |
| paired | 76 | 9 | 17 | 33 | 17 | 0.8901 | 0.9422 | +0.0521 | 0.0001 |
| pooled | 161 | 11 | 37 | 73 | 40 | 0.8241 | 0.8705 | +0.0464 | 0.0001 |

Tokenisation is provisional pending **HD-6**: ingredient strings are segmented with
PyThaiNLP `newmm` and filtered against a stoplist of units and preparation verbs. Nothing
was written to `canonical_ingredients`. TF-IDF document frequencies come from all 2,521
pages, not from the labelled 58.

**Label leakage was checked and is absent.** If a region word appeared inside an
ingredient line, the label would partly predict itself. Across the corpus, `อีสาน`,
`ภาคเหนือ`, `ภาคใต้`, `ปักษ์ใต้` and `ล้านนา` occur as ingredient tokens **zero** times.
`กลาง` appears in 101 pages but only in its generic sense (`ไฟกลาง`, medium heat) —
`ภาค` occurs zero times, so the compound that assigns a Central label is never present.

## The result is narrower than the headline

Taking the significant p-value at face value would say Thailand's four regions are
compositionally distinct. The pairwise tests say something much more specific.

| pair | n | separation | p |
|---|---:|---:|---:|
| Northeast vs North | 37 | +0.0803 | **0.0001** |
| Northeast vs Central | 35 | +0.0790 | **0.0003** |
| Northeast vs South | 42 | +0.0592 | **0.0001** |
| North vs South | 23 | +0.0117 | 0.0846 |
| Central vs South | 21 | +0.0019 | 0.4147 |
| Central vs North | 16 | −0.0052 | 0.6738 |

**Every significant pair involves the Northeast.** Removing it removes the finding:

| held out | n | separation | p | |
|---|---:|---:|---:|---|
| without Central | 51 | +0.0612 | 0.0001 | signal |
| without North | 49 | +0.0595 | 0.0001 | signal |
| without South | 44 | +0.0741 | 0.0001 | signal |
| **without Northeast** | **30** | **+0.0050** | **0.2240** | **no signal** |

So the answer to §4's "which boundary is sharpest" is: **the Isan boundary, and on this
corpus only the Isan boundary.** North, Central and South do not separate from one another.

## Two readings, and the corpus cannot choose between them

The tokens driving the Northeast profile are coherent and correct — `ข้าวคั่ว` (toasted
rice powder), `พริกป่น`, `ผักชีฝรั่ง` (culantro), `ปลาร้า`, `สะระแหน่`. That is the
larb–som tam seasoning base, and no one who cooks Thai food would be surprised by it.

*Reading one: the signal is culinary.* Isan cooking really does share a seasoning base
that the other three regions do not, and the measure found it.

*Reading two: the signal is editorial.* `อาหารอีสาน` is a marketing category on Thai
recipe sites, and it attaches to a narrow, tight dish family. What separates may be the
category's dish repertoire rather than the region's cooking. Note the label provenance:
128 of 161 labels came from a region *term* written by an editor, not from a province.

This is exactly the question **HD-17** exists to decide — which distinctiveness findings
are real and which are artifacts of source bias — and it is not resolvable from this
corpus. Fieldwork and the DCP corpus are what would separate the two readings.

## Do not read the non-significant pairs as null results

Central vs North is n=16, with 7 Central recipes in it. Central vs South is n=21. These
tests have very little power, and a separation of zero at n=16 is not evidence that
Central and Northern cooking are compositionally alike — it is evidence that 16 recipes
cannot tell. Rule 9 ships negative results, and this is not one: it is an undetermined
result, which is a different claim and must be written as one.

The Central profile in particular should not be interpreted at all. At n=7, one page's
noise carries visible weight — `เพจ` ("page", from a Facebook credit line) sits among its
top discriminating tokens, which means a non-ingredient line reached an ingredient
section. The parser's 93% coverage is not 100%, and at n=7 the residue is not averaged out.

## Consequences

- **Figure 2 as specified in §6 cannot be built** — it is a distance-decay scatter of
  ~2,900 province pairs, and this corpus supports six region pairs. §6 needs a replacement
  spec for Figure 2, or RQ1 loses its figure. **Open decision, not taken here.**
- **RQ1's output is no longer a number in kilometres.** It is a yes/no on regional signal,
  plus the finding that one boundary carries all of it.
- The result does not depend on the pooling choice: single, paired and pooled cohorts all
  give p = 0.0001 with separations within 0.013 of each other.
