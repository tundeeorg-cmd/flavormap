# Blocking item 1 — the labelled-recipe fraction

**Measured 2026-08-23 on `cooking.kapook.com`, n = 2,521 pages with a readable ingredient
list.** Regenerate the table with `uv run python -m scripts.measure_labelled_fraction`;
the hand audit below is in `docs/kapook_province_hits_audit.csv` and is not regenerated.

CLAUDE.md §11 makes this the number the project's shape depends on: above 35% a
province-level paper, below it a region-level paper or primarily a coverage paper. §11
also records that the "~300 SorKorPor recipes" the Bible assumed for this measurement do
not exist on this machine. `cooking.kapook.com` was fetched in their place. It is the
right kind of corpus for the question — unlike the DCP forms, which are province-stamped
by construction and would answer ~100%, nothing here obliges an author to say where a
dish is from.

## The answer

**1.3%.** 33 of 2,521 pages carry a province label that is a claim about where the dish
is from. The province-level threshold is 35%.

Region-level claims reach **6.2%**, which is also far below it.

This is a coverage paper. RQ3 — how much of Thailand's culinary map is legible at all
from public online data — is not a section of this project; on this evidence it is the
project. RQ1's distance-decay form cannot be built from a consumer web corpus alone.

## Why one number was not enough

Thai is unspaced, so a province name has no word boundary to anchor on and a bare
substring search is not a measurement but a homograph count. Three matching rules, two
scopes:

| scope | rule | any province | exactly one |
|---|---|---:|---:|
| article | permissive | 2,393 (94.9%) | 2,110 (83.7%) |
| article | **strict** | **89 (3.5%)** | **78 (3.1%)** |
| article | marker | 17 (0.7%) | 17 (0.7%) |
| title | permissive | 39 (1.5%) | 38 (1.5%) |
| title | strict | 15 (0.6%) | 15 (0.6%) |
| title | marker | 0 | 0 |

`permissive` matches any province name as a substring. `strict` requires a `จังหวัด` or
`จ.` marker for names that are also ordinary Thai words. `marker` requires it for all.

The permissive column is not a near-miss on the threshold; it is almost entirely one
word. `เลย` — Loei province, and also the adverb "at all" — appears in 2,384 of the 2,393
pages, overwhelmingly in the phrase `คลิกเลย` ("click here"). `ตาก` (Tak, and also "to
sun-dry") accounts for 185 more. Reporting 94.9% as a labelled fraction would have been a
measurement of a link and a cooking verb.

Ambiguous names, each confirmed by reading its matches rather than assumed from the
dictionary: `เลย` (at all), `ตาก` (to sun-dry), `แพร่` (to spread — `แพร่หลาย`), `น่าน` (a
substring of `ทูน่า`, tuna), `ตราด` (a substring of `ตรา` + brand, e.g. `ตราดอกบัว`),
`กระบี่` (also "sword"), `ยะลา` (a substring of `ขนมเปี๊ยะลาวา`).

## The hand audit

All 78 single-province strict pages were read in context. A name surviving the strict
rule is still not a label — most of the survivors are about something other than the
dish.

| verdict | n | share of the 78 |
|---|---:|---:|
| **`dish`** — a claim about where the dish or its style is from | **33** | 42% |
| `ingredient` — provenance of an ingredient, brand, or cultivar | 19 | 24% |
| `incidental` — biography, shop, advertisement, username, affiliation, weather | 26 | 33% |

Only the first is a province label. **33 / 2,521 = 1.3%.**

The `incidental` class is the instructive one. Six pages match on one contributor's
Pantip username, which ends in `@` plus a province name; two on an author's university
affiliation; one on a shop owner's surname, which likewise ends in a province name; one
on a Bangkok flood; one on the weather; and five on related-article teasers in the page
furniture (`12 ร้านหมูกระทะน่าหม่ำในกรุงเทพฯ`). None of these say anything about a recipe.

The names themselves are not reproduced here. They are real people's, they came off a
public page rather than out of a form, and rule 8's reason for existing does not change
with the source — nor does the fact that this repository is bound for publication. The
PDPA redactor does not catch them: it anchors on `นาย`/`นาง`/`คุณ`, and a bare surname or
a username carries no honorific.

The `ingredient` class is a genuine finding rather than an error: four pages match on the
rice cultivar `ปทุมธานี 1`, three on one soy sauce brand's home town (`ตราจี้แซ จาก
นครสวรรค์`). Consumer recipe writing locates *ingredients* far more readily than it
locates dishes. Whether ingredient provenance is worth its own tier is a question for
HD-7; counting it as a province label would inflate the fraction to 2.1% and would be
attributing a dish to the address of a soy sauce factory.

Eleven further pages match two or more provinces under the strict rule. All are roundup
listicles carrying many dishes, and they are excluded here rather than assigned: which
section a province belongs to is the page-to-recipe segmentation question, still open.

## Region-level claims

157 pages (6.2%) carry at least one region term; 137 carry exactly one.

| region | pages |
|---|---:|
| Northeast | 74 |
| South | 53 |
| North | 38 |
| Central | 15 |

Bare `เหนือ` and `ใต้` mean "above" and "below" and are excluded; only compounded forms
(`ภาคใต้`, `ปักษ์ใต้`, `อาหารเหนือ`, `ล้านนา`, `อีสาน`, `ภาคกลาง`) count. These are much
cleaner than the province matches — of 14 read by hand, 12 were genuine culinary claims
(`อาหารอีสาน`, `รสเด็ดเผ็ดจัดจ้านแบบปักษ์ใต้`, `อาหารพื้นบ้านล้านนา`) and 2 were
incidental. That is a spot check, not a full audit: 137 pages have not been read.

Note what the region distribution is not. Northeast leading at 74 pages is a fact about
how consumer recipe writing labels food — `อาหารอีสาน` is a marketing category — not
evidence that Isan food is better represented. Central, the least *marked* cuisine,
scores lowest precisely because it is the unmarked default.

## What this does not say

The 1.3% is a property of this corpus, not of Thai food. A recipe with no province label
is not a recipe with no province; it is a recipe whose province the site had no reason to
print. The finding is about the legibility of public online data, which is RQ3's question.

Three sources remain unbuilt (`doae`, `tat`, `pantip_food`) and the DCP corpus is
province-stamped at ~100% but institutional and reference-only. Whether any consumer
source does better is untested — but a second consumer source would have to reach roughly
70% to pull a combined corpus to 35%, which no source in the audit looks likely to do.

## For the researcher

This measurement is the evidence for **HD-3** (source go/no-go) and bears on **HD-7**
(attribution tiers) and **HD-4** (the parsed-recipe defect list).

**The audit is confirmed.** The 78 rows were classified by the agent and reviewed by the
researcher on 2026-08-23, who agreed with all 33 `dish` calls. The headline figure is
therefore a researcher-confirmed 1.3%, not an agent estimate. The `ingredient` and
`incidental` classes were not separately contested; nothing turns on the boundary between
them, since neither is a province label.

---

## Label yield on the loaded commercial register (T1.13, 2026-10-12)

**A measurement for HD-Kapook (TIMELINE T1.14), not a labelling.** Nothing was written to
`province_attribution`. Generated by `scripts/measure_kapook_labels.py`, which documents each
rule; rerun it to reproduce every number below.

How this differs from the 1.3% above: the unit is the **1,360 recipes loaded** into
`recipes`, not the 2,521 pages, and only the **title and the site's category path** are
examined, not the article body. TIMELINE T1.13 asks for "explicit province names in
title/category". The body-text measurement above stands as it was.

**Recipes examined:** 1360 (`register = 'commercial'`).

| Rule | Any hit | Unambiguous (one province / region) | Conflicting |
|---|---:|---:|---:|
| `a_permissive` | 10 (0.7%) | 10 (0.7%) | 0 |
| `a_strict` | 3 (0.2%) | 3 (0.2%) | 0 |
| `a_marker` | 0 (0.0%) | 0 (0.0%) | 0 |
| `c_exact` | 0 (0.0%) | 0 (0.0%) | 0 |
| `c_substring` | 9 (0.7%) | 9 (0.7%) | 0 |
| `b_compound` | 22 (1.6%) | 22 (1.6%) | 0 |
| `b_bare` | 24 (1.8%) | 24 (1.8%) | 0 |

**Unambiguous hits per province** (provinces with at least one hit; ordered as `data/reference/provinces.csv`):

| Province | Region | `a_strict` | `a_marker` | `c_exact` | `c_substring` |
|---|---|---:|---:|---:|---:|
| ตราด | Central | 0 | 0 | 0 | 1 |
| นครราชสีมา | Northeast | 2 | 0 | 0 | 0 |
| ชัยภูมิ | Northeast | 0 | 0 | 0 | 7 |
| ราชบุรี | Central | 0 | 0 | 0 | 1 |
| นครปฐม | Central | 1 | 0 | 0 | 0 |
| **Provinces with ≥1** | | 2 | 0 | 0 | 3 |

**Unambiguous hits per region.** The (b) rules count region claims directly; the (a) and (c) columns roll unambiguous province hits up to `region4`:

| Region | `b_compound` | `b_bare` | `a_strict` | `c_substring` |
|---|---:|---:|---:|---:|
| North | 5 | 5 | 0 | 0 |
| Northeast | 9 | 9 | 2 | 7 |
| Central | 0 | 0 | 1 | 2 |
| South | 8 | 10 | 0 | 0 |

**Where two families both give one province, do they agree?**

| Pair | Recipes with one province under both | Same province |
|---|---:|---:|
| `a_strict` and `c_exact` | 0 | 0 |
| `a_strict` and `c_substring` | 0 | 0 |
| `a_marker` and `c_substring` | 0 | 0 |

`c_substring` matched 3 distinct official dish names; 1 of them are 4 characters or fewer, where a substring match is most likely to be generic. The names and per-recipe hits are in `data/coverage/kapook_label_yield.csv` (gitignored, DCP-derived).


### Reading every match (2026-10-12)

The matches are few enough to read in full: 19 recipes matched any province rule, and 2
more appear only under `b_bare`. This is a reading of what each match is, to inform HD-Kapook;
it decides nothing.

- **`a_strict`, 3 recipes.** All three look like genuine claims: two titles use โคราช for
  Nakhon Ratchasima, and one says a dish comes "straight from" Nakhon Pathom.
  `a_permissive`'s 7 extra hits are homographs: เลย ("at all") in 6 titles, and ตราด as a
  substring across two words in 1.
- **`c_substring`, 9 recipes.** **All 7 Chaiyaphum hits come from one official dish name of
  four characters that is also slang for "to eat"** in recipe titles. The other two are a
  generic ingredient name (Ratchaburi) and a common dish name (Trat).
  None of the 9 looks like a claim that the recipe is from that province.
- **`c_exact`, 0.** No kapook title is exactly an official dish name; titles carry
  marketing text after the dish name.
- **`b_bare` adds 2 recipes over `b_compound`.** Both use ใต้ in "southern curry paste"
  (น้ำพริกแกงใต้, น้ำพริกแกงส้มใต้), which reads as a genuine regional claim, not "below".
- **No recipe received a province from two families**, so the agreement check has nothing
  to compare.

**What this says for HD-Kapook,** to weigh rather than to adopt: on titles and
categories, province labels reach at most 3 genuine recipes (0.2%) in 2 provinces. Region
claims reach 22–24 recipes (1.6–1.8%), spread across North, Northeast and South, with none
for Central. The 1.3% body-text figure above is the larger pool, if the decision admits body
text.
