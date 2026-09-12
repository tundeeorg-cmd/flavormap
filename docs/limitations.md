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

## Added 2026-08-16 — consequences of HD-1 and HD-2

| # | Limitation | Severity | Statement |
|---|---|---|---|
| L17 | Pattani carries no border country | **MEDIUM** | HD-2 defines borders as **land borders only**. Pattani has no land border with Malaysia and therefore no `border_country`, despite being culturally and linguistically continuous with the Malay-speaking south and having obvious maritime contact. This is a known divergence between the administrative definition and the cultural reality, chosen because "maritime adjacency" has no standard threshold. Any border-based result should be read with Pattani in mind |
| L18 | Twelve provinces are `Transitional` | **MEDIUM** | HD-1 assigns a sixth `Transitional` dialect value to provinces that straddle a boundary rather than forcing them into a majority group. This is more honest than a clean five-way split, but it means ~16% of provinces carry no single linguistic label, and RQ1's linguistic comparison must either report them separately or exclude them in a sensitivity run — never silently absorb them |

## Added 2026-09-12 — official-vs-community dish counts are not directly comparable

| # | Limitation | Severity | Statement |
|---|---|---|---|
| L19 | Two government programmes, two dish granularities | **MEDIUM** | RQ3's official-vs-community arithmetic (`local_food_survey` vs. `one_province_one_menu` dish counts for a shared province) compares raw counts across two programmes with different selection criteria and, plausibly, different dish-naming granularity — one dish written two ways in two programmes counts as two dishes, not a match, under exact-string comparison (`scripts/parse_local_dish_inventory.py --report`). The ~150-vs-3 shape is indicative of a real asymmetry (a curated shortlist versus an open community survey), not a precise measurement of how much the state's list omits. Any overlap count between the two is a **lower bound** on true overlap for the same reason — a real match missed by string mismatch reads as "in neither register," which is exactly the finding RQ3 is built to report, so this cuts toward understating agreement, not overstating it |

## Added 2026-09-12 — two programme years are cohorts, not a time series

| # | Limitation | Severity | Statement |
|---|---|---|---|
| L20 | 2567 and 2568 are not a trend | **HIGH** | The one-province-one-menu programme has now been loaded (or is loadable) across two years, `flavormap_food67.csv` (2567) and the 231-PDF `food68` corpus (2568), tagged `source_programme = 'one_province_one_menu_2567'` / `'_2568'` (migration 024). **These are two cohorts of a curation programme, not two waves of a survey, and must never be read as a time series.** A dish present in one year's shortlist and absent from the other's reflects that year's selection committee, not a change in what anyone cooks — the same reasoning L15 already applies to the institutional corpus generally, restated here specifically because two dated cohorts existing side by side is exactly the setup that invites an unearned "X declined between 2567 and 2568" sentence. The two years also differ in more than year: 2568 covers all 77 provinces at a fixed 3 dishes each (231 by construction); 2567 covers 48 of 77 provinces at an uneven ~7.2 dishes each (345 rows, per the source CSV's own counts) — a different coverage shape, not only a different year, and evidence that the two cohorts may not even share a selection rule (`docs/decisions.md`, Task 1a note). Any year-over-year overlap number this project reports (Task 1d) is a comparison of two committees' choices, stated as exactly that |

## Added 2026-09-12 — the gdcatalog / datago_catalog source-inventory tasks

| # | Limitation | Severity | Statement |
|---|---|---|---|
| L21 | Thai substring matching is a silent-failure extraction hazard | **HIGH** | `flavormap_datago_catalog.csv`'s `province` column carried 106 distinct values against Thailand's 77 real provinces because whatever process produced it matched province names as raw substrings — "น่าน" (Nan) matched inside "น่านน้ำ" (territorial waters), assigning a deep-sea fishing-vessel dataset to landlocked Nan province; "แพร่" (Phrae) matched inside "เผยแพร่" (published) seven times. Thai has no spaces between words, so this is not a data-entry error to catch by inspection — it is a structural property of naive substring matching on unsegmented Thai text, confirmed fixable by word-boundary-aware tokenisation (`src/ingest/thai_province_match.py`, verified against PyThaiNLP `newmm`) but only once someone thinks to check. Worth a sentence in the methods section: anyone building a Thai geographic corpus from free text will hit this, and a plausible-looking wrong value is worse than an obviously missing one because nothing about it looks broken |
| L22 | Neither fieldwork province has dish-level open data, in either national catalogue | **HIGH** | Across `flavormap_gdcatalog_sources_full.csv` (1,893 rows) and `flavormap_datago_catalog.csv` (3,861 rows) — every government open-data source this project has been able to assess — zero rows classify as `local_dish_inventory`, `gi_registration`, or `cultural_heritage` for Nan, and zero classify `local_dish_inventory` or `cultural_heritage` for Surin (Surin's four GI-classified rows are all registrant lists that may never be harvested, not product data — `docs/decisions.md`). **The interviews are not supplementing an existing record for Nan and Surin. They are the record.** This is not a gap in this project's search; it is confirmed absent from ~5,700 assessed open-data entries. It strengthens RQ3's framing rather than weakening it, and should be stated plainly in the methods section rather than left for a reader to discover by noticing what is missing |

---

*First entry: 2026-08-16, seeded from Bible §14 plus the three institutional-corpus entries.*
