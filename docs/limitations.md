# Limitations register

Maintained as a live file **from month one, not written at the end** (Bible §14). The
limitations section of the paper is lifted from here, and it is deliberately long.

A limitation written before anyone asks reads as calibration. The same limitation written
after review reads as damage control.

**HD-19** is the researcher's final pass over this file for the paper.

---

## Retained from v2

| # | Limitation | Severity | Statement |
|---|---|---|---|
| L1 | Corpus skews urban and Central Thai | **HIGH** | Web recipe sites are written by and for people with reliable internet, disposable income, and an interest in publishing food online. That population is not distributed evenly across Thailand |
| L2 | Province labels sparse and partly inferred | **HIGH** | A substantial share of recipes carry no usable province label. Those that do may carry one inferred from a dish name rather than stated by the author. The unlabelled fraction is reported, never silently dropped |
| L3 | Uneven coverage across 77 provinces | **HIGH** | Some provinces will not clear any sensible inclusion threshold. Province-level claims are made only for provinces that do, and every figure states `n = k of 77` |
| L4 | Small fieldwork n | **MEDIUM** | See L9 — reframed rather than removed |
| L5 | Normalisation involves judgement calls | **MEDIUM** | Whether three chillies are one ingredient or three is a decision, not a fact. Every boundary is recorded in `decisions.md` with its reasoning, and the lexicon is published so others can disagree with specific entries |
| L6 | Recipes are not consumption | **MEDIUM** | A recipe records what someone wrote down, not what anyone ate. Frequency in a corpus is not frequency on a table |
| L7 | Modern recipes flatten historical variation | **MEDIUM** | The corpus is contemporary. It cannot speak to what a province cooked in 1950 |
| L8 | Sites excluded for ToS reasons | **LOW** | Sources whose robots.txt or terms disallow scraping are dropped, not worked around. Their absence is a structured, not random, gap |

## Changed and new in v3

| # | Limitation | Severity | Statement |
|---|---|---|---|
| L9 | Fieldwork n = 12–15 | **MEDIUM** | **Reframed.** Presented as an existence demonstration and qualitative validation — never as a representative sample, and never as a basis for ranking provinces. Two provinces at n≈6 each, stated as such |
| L10 | Dish-category taxonomy | **MEDIUM** *(new)* | Categories are constructed, not natural. The taxonomy and its inclusion rules are published so others can disagree with specific assignments |
| L11 | No temporal dimension | **MEDIUM** *(new)* | The corpus is a single time-slice. It can honestly support "these traditions are undocumented"; it cannot support "these traditions are vanishing at rate X." **Any claim about rate of loss is unsupported — catch this before it reaches an essay** |
| L12 | Linguistic distance matrix | **MEDIUM** *(new)* | Constructed from published ethnolinguistic maps, with judgment calls at every boundary. The matrix is published |
| L13 | Single annotator | **RESOLVED** | No longer a limitation. 100 recipes independently double-labelled by a second Thai reader; Cohen's κ reported |

## Added 2026-08-16 — institutional corpus

| # | Limitation | Severity | Statement |
|---|---|---|---|
| L14 | Institutional corpus is complete by design | **HIGH** | The DCP (`food.culture.go.th`) corpus is province-stamped by construction and covers all 77 provinces. It is the "what should be there" reference layer against which the coverage gap is measured — **it is not evidence that coverage is good** |
| L15 | Institutional corpus is curated for rarity | **HIGH** | The programme deliberately selected dishes *at risk of disappearing*. It therefore systematically over-represents the unusual and is **not a sample of what people cook** |
| L16 | Institutional and web corpora are not poolable | **HIGH** | `source_type` must be carried through every analysis. The two corpora are never pooled without a source indicator, and any figure mixing them is faceted by source. The institutional corpus is also unusable for the labelled-fraction measurement, which would return ~100% and answer nothing |

---

*First entry: 2026-08-16, seeded from Bible §14 plus the three institutional-corpus entries.*
