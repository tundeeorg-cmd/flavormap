# FlavorMap — Build Plan for Claude Code

**Version:** 4.0 · **Reconciled:** 2026-08-30 · **Authority:** `FlavorMap_Project_Bible_v4.md`
**Window:** Aug 2026 – Nov 2027 · **Freeze:** 31 March 2027

> **Partially reconciled.** §4 (research questions) and §6 (figures) are v4. The phase
> plan, the gate list and the schema notes still carry v3 numbering and have not been
> re-derived — a v3 RQ number appearing outside those two sections is drift, not a
> reference. Bible §23's "update the five research questions everywhere in the repo" is
> done for the questions themselves; the plumbing that keys off them is not.

> This file is the operational plan. The Bible is the specification. Where the two
> disagree, **the Bible wins** and this file is wrong and should be corrected.
> Superseded plans are in `docs/archive/` — kept, not deleted, because the planning
> trail is part of the authorship evidence (Bible §2).

---

## 0. How to use this document

Spec for an AI coding agent working alongside the student researcher (**the researcher**).

- **[CC]** — Claude Code executes: scaffolding, parsing, wrangling, plumbing, plotting.
- **[HD]** — Human Decision. A judgment only the researcher makes, recorded with its
  reasoning and its alternatives in `docs/decisions.md`. Claude Code implements a decision
  once made; it never makes one, never picks the sensible option and flags it for later,
  and never proceeds past an open gate.

**Twenty gates, ~225 researcher-hours** (Bible §13). That number is what determines
whether the project finishes, and it is the one number that generating code faster does
not reduce.

**Authorship note for the agent:** write clean, idiomatic, documented code. Do not
stylise output to imitate a novice, do not stage commit histories, do not introduce
deliberate errors. The agent builds machinery; the researcher owns every analytical
decision. That only holds if the gates are respected.

---

## 1. Non-negotiable rules

1. **Raw data is immutable.** `raw_*` tables are append-only. Cleaning writes to new tables.
2. **Never fabricate a province.** Attribution failure → `province = NULL`. No
   nearest-neighbour filling, no "probably Central."
3. **Never impute quantities.** ตามชอบ → NULL, `has_quantity = false`.
4. **Never merge canonical ingredients without `[HD]` approval.** Automated similarity
   writes to `alias_candidates`, never to `ingredient_aliases`.
5. **`make figures` regenerates every number and figure** from the database. No
   hand-edited plots, no numbers typed into prose by hand.
6. **Every stochastic operation takes `RANDOM_SEED`** from `src/config.py`.
7. **Respect robots.txt.** 1 req/sec, identifying User-Agent carrying
   `SCRAPER_CONTACT_EMAIL`. Disallowed → source dropped, never worked around. Every
   source audited into `ETHICS.md` **with a date** before a scraper is written.
8. **No personally identifying data enters the database, ever.** No names, contacts,
   addresses, faces, or GPS-tagged photos. Enforced by tests. Filtering at export is too
   late — by then it is in the backups.
9. **Negative results ship.** If a result is null, that is the finding.
10. **Every chart is 2D.** Where a third axis is tempting, use colour, size, or small
    multiples. The single exception is the force-directed network on the public site.

---

## 2. Environment and repo

### 2.1 Stack

| Concern | Choice |
|---|---|
| Python | 3.11, `uv` |
| Database | **PostgreSQL 15 + PostGIS 3.4, local, Docker Compose**. Database `flavormap` |
| Raw pages | **On disk only** (`data/raw/{source_id}/…`), gitignored, never in the database |
| Lint / types / tests | `ruff`, `mypy` on `src/`, `pytest` |
| Migrations | numbered SQL in `db/migrations/`, applied by `scripts/migrate.py`, append-only |
| Scraping | `httpx` + `selectolax`; `playwright` only where JS hydration is confirmed |
| PDF | `pdfplumber`, `pypdf`, `pdftotext -layout` — chosen on evidence per source (see §7.1) |
| LLM | `anthropic` SDK, model pinned in `src/config.py` |
| Analysis | `pandas`, `networkx`, `python-louvain`, `igraph`, `scikit-learn`, `umap-learn`, `scipy`, `geopandas`, `libpysal`, `esda`, `PyThaiNLP` |
| Production serving | **Pre-materialised static JSON.** No live database queries, no API runtime dependency |
| Paper figures | `matplotlib` + `seaborn`, 300 dpi, colourblind-safe, never hand-edited |
| Site | GitHub Pages or Vercel free tier — **Sep–Oct 2027, not before** |

Total infrastructure cost is effectively zero. Nothing needs a GPU. Say so in the paper:
it establishes that the project was constrained by effort and access rather than
resources, which is the profile of a student project done properly.

### 2.2 Makefile targets

```make
setup  db-up  db-down  scrape  ingest  clean  analyze  figures  export  test
all      # clean analyze figures
verify   # fresh-clone reproducibility check
```

`make all` must run end to end from a fresh clone plus a database dump. Checked at the
end of every phase, not once at the end.

---

## 3. Data model

Each table is its own numbered migration. **Migrations are append-only** — a table that
needs changing gets a new forward migration, never an edit to an applied one.

| # | Migration | Contents |
|---|---|---|
| 001 | `sources` | source registry, robots audit, province quality |
| 002 | `raw_recipes` | immutable fetch log — `raw_path`, `content_hash`, `published_at`. **No `raw_html`** |
| 003 | `recipes` | `name_th`, `dish_category`, `occasion`, `endangerment`, `collection_date` |
| 004 | `canonical_ingredients`, `ingredient_aliases`, `ingredient_conflations`, `alias_candidates` | the lexicon and its review queue |
| 005 | `recipe_ingredients` | `raw_text`, `quantity_g` (NULL unless convertible), `acquisition_mode` |
| 006 | `provinces` | 77 rows, ISO codes, region4, dialect_group, centroids, PostGIS geometry |
| 007 | `province_attribution` | four tiers, confidence, rationale |
| 008 | `informants`, `interview_dishes` | fieldwork — **no names, no contacts, ever** |
| 009 | `dish_categories` | RQ5 taxonomy + written inclusion rules. **Seeded empty pending HD-9** |
| 010 | `coverage` | per-province recipe count, labelled fraction, source concentration |
| 011 | `redaction_log` | per-document count of PDPA fields stripped at parse time |
| 012 | `v_recipes_clean` | the analysis view |
| 013 | `provinces.dialect_group` CHECK | HD-1: five groups + `Transitional` |
| 014 | `provinces.border_country` → `TEXT[]` | HD-2: land borders only, multi-border as an array |

**Ordering correction (2026-08-16).** The v2 plan numbered `province_attribution` 006 and
`provinces` 007, with a foreign key pointing from the earlier to the later. That cannot
apply to an empty database. Provinces now comes first. All twelve migrations are verified
to apply from an empty volume via `make db-reset`.

### 3.1 v3 schema changes from v2

- `raw_recipes.raw_html` **removed**. Raw pages live on disk; duplicating them into
  Postgres inflates the database for no benefit.
- `raw_recipes.published_at DATE` **added**. Free to capture now, impossible to backfill
  after the freeze, and it enables any temporal question later. Every scraper must attempt it.
- `recipes.dish_category` is now **load-bearing for RQ5**, backed by a `dish_categories`
  reference table with written inclusion rules.
- `alias_candidates` **added explicitly** — referenced by the canonicalisation plan but
  never defined in the v2 DDL.
- `coverage` **added**. RQ3 is built on it and it ships as a first-class release file.
- `informants` gains `district` and `acquisition_mode` (grown | foraged | market |
  packaged), per Bible §8.

### 3.2 The analysis view

All analysis reads `v_recipes_clean`: attribution confidence in (high, medium),
3–25 mapped ingredients. Low-confidence rows exist for sensitivity analysis only and are
pulled explicitly by `src/analyze/sensitivity.py`. **Tier-4-low never enters the view.**

`source_type` is carried through **every** analysis. Institutional and web-scraped corpora
are never pooled without a source indicator, and any figure mixing them is faceted by source.

---

## 4. The five research questions

**Reconciled to Bible v4 on 2026-08-30.** v4 rewrote the question set completely: four of
the five below are new, and every figure number moved. The set this file carried until
today was v3's, which asked about boundary geometry, network fragility and vernacular
signal — none of which v4 retains as a research question. Where an old question survives
as machinery, that is noted rather than silently dropped.

Each is stated precisely (for the paper) and plainly (for the site, the build log, and
interviews). Each carries a **transferable claim** — what a reader outside Thai food
studies takes away.

> **The risk profile inverted.** This file previously said "All five run on the web
> corpus. **None can be blocked by a cancelled trip.**" Under v4 that is false and
> dangerous to leave standing: **four of five require fieldwork and one requires cooking**
> (Bible §6, "Read together"). A cancelled trip does not degrade the paper, it removes
> questions from it. §22 lists unbooked trips as the top risk for exactly this reason.

### RQ1 — Do the state, the market, and the kitchen agree on what a province eats?
*Plain: does the food the government picks to represent your province match what people there actually cook?*

- **Method** — ingredient-profile distance between the three registers for the same
  province. Cosine distance on normalised ingredient vectors, pairwise:
  official↔commercial, official↔domestic, commercial↔domestic.
- **Output** — triangle plot per province, one vertex per register, edge length =
  disagreement. **Figure 1**.
- **Needs fieldwork** — yes. The domestic register *is* the interviews.
- **A NO looks like** — the three registers agree, meaning official selection and web
  recipes faithfully represent domestic practice. A genuine result in the opposite
  direction, and reassuring for anyone who has ever built on a scraped corpus.
- **Transferable** — cultural corpora carry the selection pressure of whoever assembled
  them. Applies to folk music archives, craft inventories, heritage registers.

This is the spine of the paper. **It is not v3's RQ1**, which asked whether cultural
boundaries are discrete or continuous and answered it with a distance-decay curve. Bible
v4 §1 and §14.5 retire that question and the Mantel and Moran's I tests that served it.

### RQ2 — Is regional identity built from what's included or what's refused?
*Plain: is a region's food about what it uses, or about what it refuses to use?*

- **Method** — decompose each province's distinctiveness into presence-driven and
  absence-driven components. Validate against stated absences from interview Q9.
- **Output** — scatter, presence-driven vs. absence-driven, one point per province,
  diagonal = balanced. **Figure 2** (was Figure 3 under v3).
- **Needs fieldwork** — yes, for validation. Inferred absence is weak evidence; **stated**
  absence is strong.
- **A NO looks like** — distinctiveness is symmetric everywhere. Still a fact nobody had.
- **Why it matters** — every distinctiveness measure in computational humanities (TF-IDF,
  log-odds, Zeta) is a *presence* measure. Absence is structurally invisible to all of
  them. No off-the-shelf measure exists, so it must be defined and defended — **HD-13**.

The only question carried over from v3 substantially unchanged, and still the best
novelty-to-effort ratio in the project.

Interview question 9, to be asked out loud as written:

> **“อะไรที่คนจังหวัดอื่นใส่ในจานนี้ แต่บ้านเราไม่มีวันใส่?”**
> *What do people in other provinces put in this that we would never put in?*

Test the phrasing on the first informant; the wording decides whether the answer is real
or merely polite.

### RQ3 — What does the official record leave out?
*Plain: whose cooking didn't make the government's list?*

- **Method** — the state selected 3 dishes per province. Ask cooks in Nan and Surin what
  they actually cook. Measure overlap at dish level and ingredient level.
- **Output** — table of dishes and ingredients named by cooks that appear in no register;
  overlap bar chart. **Figure 3** (was Figure 1 under v3).
- **Needs fieldwork** — entirely.
- **A NO looks like** — high overlap, validating the state's selection process.
- **Framing** — an **existence claim**, which n≈6 per province fully supports: *six of six
  cooks in Surin named an ingredient no register associates with the province.* Never a
  basis for ranking provinces. That distinction is what makes it unobjectionable.

v3's RQ3 asked how much of the map is legible from public online data and was answered on
2026-08-23 at **1.3%** (`docs/labelled_fraction.md`). That measurement stands and is why
kapook is held as a coverage corpus — but under v4 it is evidence feeding this question,
not the question itself.

### RQ4 — Can you cook a dish from the normalised dataset?
*Plain: after the computer cleans up a recipe, is it still a recipe?*

- **Method** — cook 8 dishes from the **cleaned dataset's** ingredient list, not the
  original source page. Log what was missing, what had to be substituted, what
  normalisation destroyed, whether the result was recognisable.
- **Output** — fidelity matrix, 8 dishes × {quantities, order, technique, specificity,
  completeness}. **Figure 4**.
- **Needs cooking** — entirely. This question cannot be answered any other way.
- **A NO looks like** — everything cooks fine; normalisation is lossless in practice.
  Reassuring, and worth reporting.
- **Transferable** — tokenisation and canonicalisation silently delete information and
  nobody in computational food studies measures how much. A reproducibility argument that
  transfers to any pipeline flattening structured text.

Requires a `cook_along_log` table (Bible §13). In v3 the cooking was narrative colour and
the first thing to cut; here it is the validation layer, and cutting it removes a question.

### RQ5 — Do cooks agree with the state about which dishes are disappearing?
*Plain: the government says these dishes are at risk. Do the people who cook them agree?*

- **Method** — compare the **endangerment level** field in the government PDFs against
  what cooks in Nan and Surin say about the same dishes.
- **Output** — agreement matrix, official level vs. cook-reported status. **Figure 5**.
- **Needs fieldwork** — entirely.
- **A NO looks like** — full agreement, validating the state's assessment process.

> **⚠️ OPEN GATE — do not build against this question yet.** The checkbox extraction it
> depends on works: endangerment recovers on 157 of 231 documents, within 1.3 points of
> the corpus ceiling. But RQ5's sample is the six Nan and Surin documents, four carry a
> level, and **all four carry the same level**. Figure 5's agreement matrix cannot be
> built from one distinct official value. Four options and a recommendation are recorded
> in `docs/decisions.md`; full measurement in `docs/checkbox_extraction.md`. The Decision
> field is empty and no work proceeds past it.
---

## 5. Statistical corrections — Bible §4, verbatim

These are the three a reviewer catches. They are not suggestions.

> **Mantel significance.** Permutation testing, 9,999 permutations. Distance-matrix
> entries are not independent observations; a parametric p-value on them is meaningless
> and a reviewer will say so immediately.

Never `scipy.stats.pearsonr` on flattened matrices. A significant result is also **not
causal** — distance may proxy for shared history, climate, or trade.

> **Moran's I inputs.** Only on interpretable scalars — prevalence of a named ingredient,
> distinctiveness score, recipe count. Never on a UMAP dimension, which has no units and
> no meaning.

Report **both** queen-contiguity and k-nearest weights, or a reviewer will ask. KNN(k=5)
is also the fallback for provinces with no queen neighbours (Phuket). Supporting analysis
inside RQ1, not a headline.

> **UMAP interpretation.** UMAP axes carry no interpretable meaning. Label them
> "UMAP 1 / UMAP 2", caption them as uninterpretable, never quantify from the projection,
> never call an axis geographic or cultural. Use it as a browsing interface on the site,
> not as a result in the paper.

All clustering runs on the full TF-IDF matrix, never on the projection.

**The ordering trap.** The confusion matrix and the heatmap must both be ordered
geographically or by cluster, **never alphabetically**. Alphabetical ordering scatters
real structure into what looks like noise. This single choice is the difference between a
figure that is the result and a figure that says nothing.

---

## 6. Figure specification — Bible §10

Seven figures, specified before implementation, axes named. All 2D. All regenerated by
`make figures`.

| # | Figure | X axis | Y axis | Encoding and purpose |
|---|---|---|---|---|
| 1 | **Register triangle** (RQ1) | — | — | One triangle per province; vertices = official / commercial / domestic; edge length = ingredient-profile distance. Small multiples for the two fieldwork provinces at full size, all others as a two-register line. The paper's signature figure |
| 2 | **Distinctiveness decomposition** (RQ2) | presence-driven | absence-driven | One point per province, diagonal = balanced. Above the line = defines itself by refusal. A chart type reviewers have not seen |
| 3 | **Official-record overlap** (RQ3) | province | count | Stacked bars: dishes named by cooks that are in the official three / in the commercial register / in neither. **The "neither" segment is the finding** |
| 4 | **Pipeline fidelity** (RQ4) | dish | information class | Matrix, 8 dishes × {quantities, order, technique, specificity, completeness}. Cell = survived / degraded / lost. Reads as a table, functions as a figure |
| 5 | **Endangerment agreement** (RQ5) | official level | cook-reported status | Confusion-matrix style; off-diagonal cells are the interesting ones. **Blocked — see the RQ5 gate in §4.** One distinct official value across the fieldwork sample means there is no matrix to draw |
| 6 | **Province × ingredient heatmap** | ingredients (top ~60 by variance) | provinces | Fill = TF-IDF, **faceted by register**. Both axes seriated by clustering, never alphabetical. Good first Results figure because no modelling sits between data and image |
| 7 | **Acquisition mode by province** | province, ordered by distance from Bangkok | share of ingredients | Stacked bars: grown / foraged / market / packaged. Uses a government field directly. Supporting figure, and the most immediately legible in the set |

**The ordering trap.** Any matrix or heatmap must be ordered geographically or by cluster,
**never alphabetically**. Alphabetical ordering scatters real structure into what looks
like noise. This single choice is the difference between a figure that is the result and a
figure that says nothing.

### Built figures that this table no longer lists

Two figures exist in code and do not appear above. Neither is deleted here; what happens
to them is a researcher call, not a reconciliation one.

- **`figures/figure2.png` — regional separation vs. distance.** Specified in
  `docs/figure2_spec.md`, adopted by a decided gate on 2026-08-23, and built:
  `src/viz/figure2.py`, `scripts/make_figure2.py`. It answers v3's RQ1, and Bible v4 §1
  and §14.5 retire that question along with the Mantel and Moran's I tests. v4 §14.5 does
  leave a door open — distance-decay "could return as a supporting analysis" if the
  commercial register grows well past target. **Disposition needed:** supporting analysis,
  appendix, or dropped.
- **`figures/figure4.html` — the ingredient prevalence view.** Built by
  `scripts/make_figure4.py`, and numbered for v3's Figure 4 slot, which v4 gives to
  pipeline fidelity. The v4 figure of that number does not exist yet and needs the
  cook-along log first.

`make figures` still regenerates both, and should keep doing so until their disposition is
settled — Rule 5 is that every figure regenerates from the database, not that every
regenerated figure is in the paper.

---

## 7. Data streams

### 7.1 Web scraping

Target **~2,200 usable after cleaning**, never fewer than four live sources. Sources per
Bible §6 as corrected by `docs/source_audit.md` (9 Aug: `doa.go.th` is dead, `doae.go.th`
is live; `recipe.wongnai.com` does not resolve; `thaifoodrecipe.com` is NXDOMAIN).

Ethics retained in full and without softening: robots.txt and ToS checked **and dated** in
`ETHICS.md` for every site; 1 req/sec; honest User-Agent with contact email; ingredient
lists and province labels stored, never full recipe prose; raw HTML cached locally and
never published.

**Thai PDF extraction.** Direct extraction breaks the sara am — `ประจำปี` comes out as
`ประจ าปี`, `น้ำ` as `น้ า`. Do **not** paper over this with a blanket regex, which will
corrupt legitimately spaced text. Try at least three extractors (`pdfplumber`, `pypdf`,
`pdftotext -layout`), compare on the same ten documents, report which preserves Thai, and
pick on evidence. Normalisation gets a test fixture built from a hand-read document.

### 7.2 Cleaning — still ~40% of total hours

Tokenise with PyThaiNLP `newmm`; normalise to controlled vocabulary; strip quantities and
preparation verbs (หั่น สับ บด ซอย); NFC-normalise; assign province labels from source
page, dish name, or explicit regional claim — **leave unlabelled rather than guessing, and
report the unlabelled fraction**; deduplicate on ingredient-set Jaccard > 0.9; build the
sparse ingredient × recipe matrix.

Dedupe detail worth keeping from the v2 prompts: exact `content_hash` first, then Jaccard
> 0.85 on canonical ingredient sets **and** fuzzy title ratio > 0.8 → flagged for review.
Every retained recipe gets a `cluster_id` (singletons get their own). **That `cluster_id`
is what CV folds group on** — without it the classifier results are inflated.

The controlled vocabulary — 400–700 normalised Thai ingredient entries with variant
mappings — remains the project's most defensible contribution. It does not exist publicly
and cannot be scraped into existence. **~130 hours, cannot be delegated.**

### 7.3 Fieldwork — rescoped

**12–15 interviews across 2 provinces: Nan and Surin.** 60–90 minutes each, 2 trips.
No research question depends on this. Its job is (1) ground-truthing the RQ3 coverage gap
as an *existence claim*, (2) validating the RQ2 measure against stated absences, (3)
authorship evidence.

If only one trip happens, **do Surin** — six interviews beats zero by an enormous margin,
and Surin carries the upper-vs-lower Isaan question that RQ1's linguistic comparison
turns on.

Eight-question protocol retained verbatim from v2, **plus Q9**:

> อะไรที่คนจังหวัดอื่นใส่ในจานนี้ แต่บ้านเราไม่มีวันใส่?
> *What do people in other provinces put in this that we would never put in?*

Q4 captures self-reported boundary markers; Q9 captures **stated absences**, which is what
RQ2 validates against. Inferred absence is weak evidence; stated absence is strong.

Ethics non-negotiable: written one-page Thai consent form in plain language; anonymised by
role and province by default; a parent chaperones every interview and this is stated
plainly in the methods section; reciprocity — every participant receives the finished map
and a printed copy of their own recipe; no recording without explicit permission.

Capture **district**, not just province, and **acquisition mode** (grown / foraged /
market / packaged).

### 7.4 Cook-alongs — eight dishes

Cut from 15, buying back ~14 hours for lexicon work, which is the actual bottleneck. Cook
from the *cleaned dataset's* ingredient list rather than the original web page — the point
is to test the pipeline. Include at least two dishes the classifier gets wrong.

> This is not a cookbook, a food blog, or a YouTube channel. The cooking serves the data.
> The moment it becomes the deliverable, the project has drifted.

### 7.5 Threshold sweep — replaces the fixed minimum

`src/analyze/eligibility.py` computes eligible provinces at **every threshold 5–30**, not
at a single pinned value. Headline results reported at **10 / 15 / 25**. Every
province-level figure caption auto-includes `n = {k} of 77 provinces`.

`PROVINCE_MIN_N` in `src/config.py` is retained only as the default for the caption
helper, not as a gate.

---

## 8. Quality and credibility layer

| Item | Requirement |
|---|---|
| **Second annotator** | **Required**, not optional. 100 recipes independently labelled by a second Thai reader; report Cohen's κ. Cheapest credibility in the project — a few hours of someone's time disposes of the first objection a reviewer raises |
| **Pre-registration** | `docs/hypotheses.md`, dated and committed **before any analysis runs**. Predictions are the researcher's to write. This is what makes the negative-results section read as findings rather than excuses |
| **Negative results** | Full weight in Results, not a footnote |
| **Bias audit** | Quantified, and promoted to a full research question (RQ3) |
| **Decision log** | `docs/decisions.md` — every gate with its reasoning and alternatives |

---

## 9. Human decision gates

Twenty gates, ~225 hours. **Numbering below is a proposal reconciled from the v2 plan to
v3's decision surface — confirm it before it is cited anywhere.**

| Gate | Decision |
|---|---|
| HD-1 | Dialect-group assignment for the five-way split, including the ambiguous provinces |
| HD-2 | Land-border definition — what counts as bordering, and whether coastal proximity counts |
| HD-3 | Source go/no-go: which of the audited sources are worth building scrapers for |
| HD-4 | Read 20 parsed recipes by hand and write the defect list |
| HD-5 | Validate the first 50 LLM extractions before running at volume |
| HD-6 | Author the first 100 canonical ingredients by hand — **the most important gate in the project** |
| HD-7 | Set tier-4 attribution confidence thresholds |
| HD-8 | Centrality / top-20 plausibility check against known Thai cooking |
| HD-9 | The dish-category taxonomy and its written inclusion rules (RQ5 depends on it) |
| HD-10 | The completed ~400-entry lexicon, advisor-reviewed before Phase 3 |
| HD-11 | Code the interview validation responses; decide whether any source is down-weighted |
| HD-12 | Review flagged duplicate pairs; set the source-precedence retention rule |
| HD-13 | Define and defend the RQ2 presence/absence distinctiveness decomposition |
| HD-14 | Choose the competing boundary set for RQ1 and build the linguistic distance matrix |
| HD-15 | The `ที่มา` → acquisition-mode mapping (grown / foraged / market / packaged) |
| HD-16 | Interpret community structure against known Thai culinary geography |
| HD-17 | Decide which distinctiveness findings are real vs. artifacts of source bias |
| HD-18 | Interpret the confusion matrix — which province confusions are meaningful |
| HD-19 | The limitations section — written by the researcher, not generated |
| HD-20 | Final release review: read the full export for anything identifying. Irreversible once public |

Authorship, AI disclosure, and the credit ledger are governed by `CREDITS.md`, not by a gate.

---

## 10. Timeline — Bible §19

Anchored on three fixed dates: **freeze 31 March 2027**, **applications November 2027**,
and the ISB calendar, which puts intensive work in the June–August break rather than term time.

| Window | Build | Fieldwork / cooking | Output |
|---|---|---|---|
| **Aug–Sep 2026** | Three blocking items (§11). Labelled-fraction measurement. Figure 4 signal check. Postgres/PostGIS running. Scrapers 1–3 | Cook the origin dish with family. Book both trips | Repo public. `hypotheses.md` committed. Post 1. **Go/no-go on province-level analysis** |
| **Oct–Dec 2026** | Corpus to ~1,400. Tokenisation and normalisation. Lexicon v0.5. Dish-category taxonomy defined | Trip 1 — Surin, 6 interviews. Cook 2 dishes | Post 2. Lexicon first release. `ETHICS.md` complete |
| **Jan–Mar 2027** | Corpus to ~2,200. Normalisation complete. Category labelling. Second-annotator κ on 100 recipes | Trip 2 — Nan, 6 interviews. Transcription. Cook 3 dishes | Post 3 (failure post). **FREEZE 31 MARCH** |
| **Apr–May 2027** | RQ3 coverage cartography. RQ1 distance-decay + change points. Network, Louvain, backbone | Cook 3 dishes, including ones the classifier gets wrong | Post 4. Figures 1, 2, 7 |
| **Jun–Aug 2027** | RQ2 decomposition. RQ4 fragility. RQ5 classifier + baseline. Full analysis complete | Send results back to participants | Post 5. Figures 3–6. Paper drafted. Dataset packaged |
| **Sep–Oct 2027** | Advisor review. Revisions. Site and quiz built with sister | — | Post 6 (limitations). Journal submission. arXiv + Zenodo DOI. Both HuggingFace repos live |
| **Nov 2027** | Line launch | — | Applications |

Deliberate slack sits in Oct–Dec 2026 and Sep–Oct 2027, both of which collide with
coursework. **School always wins.**

---

## 11. The three blocking items — Bible §21

> Nothing else in this document should proceed until these three are done.

| # | Action | Cost | Why it blocks everything |
|---|---|---|---|
| 1 | ~~Measure the labelled-recipe fraction on a consumer-site pilot corpus.~~ **DONE 2026-08-23 — 1.3%.** See `docs/labelled_fraction.md` | 2 h | Answered: **primarily a coverage paper.** RQ1's province-level form does not survive the number |
| 2 | **Build Figure 4 from real data** — prevalence vs. distance from Bangkok on the same pilot set | 3 h | If pla ra and sticky rice separate at n≈300, the signal is real. If every panel looks like the MSG control, better to know in month 1 than month 8 |
| 3 | **Cook the origin dish** with the family member. Photograph the mise en place. Write down what actually happened, including what contradicts the remembered version. Commit with the real date | 2 h | The one item that cannot be reconstructed later. The essay, the introduction, and every interview answer currently rest on an unfilled bracket |

✅ **Item 1's corpus was resolved and item 1 has run.** The Bible's "~300 SorKorPor
recipes already in hand" do not exist in this repository or on this machine (inventory,
2026-08-16), and "SorKorPor" remains an unresolved source name in the same class as the
`doa.go.th` / `doae.go.th` discrepancy. `cooking.kapook.com` was audited, fetched and
parsed in its place — 2,702 pages, 2,521 with a readable ingredient list — and the
measurement ran on 2026-08-23. **HD-3 for that source was decided on the same day, option
A: keep it, reframed as a coverage corpus.**

**The answer is 1.3%**, against a 35% threshold, confirmed by a researcher-reviewed hand
audit of all 78 candidate pages. Region-level claims reach 6.2%, also far below. So:

- **RQ3 leads.** §4 already said to lead the abstract with it; it is now the spine rather
  than one question of five.
- **RQ1's province-level form is withdrawn.** §4's own constraint fires below 35%.
  Whether it is rebuilt at region level (4–6 units, ~157 pages), rebuilt on fieldwork plus
  the DCP corpus, or dropped is **an open decision** — see `docs/decisions.md`.
- **Item 2 (Figure 4) was built before this ran**, on the DCP corpus rather than the web
  corpus it specifies, and before pre-registration. Both exceptions are recorded in
  `docs/decisions.md`. The real Figure 4 still needs the web corpus.
- **Item 3 (cook the origin dish) is untouched** and is still the one that cannot be
  reconstructed later.

---

## 12. Dataset release — two repos, not one

`OpenFlavorTH-recipes` and `OpenFlavorTH-lexicon`, released separately. Bundling hides the
lexicon's independent value and prevents it being cited on its own. The lexicon is useful
to Thai NLP, recipe parsing, food-safety text mining, and agricultural translation —
people who do not care about regional cuisine at all.

| Artifact | Contents |
|---|---|
| `recipes.parquet` | Recipe ID, normalised ingredients, province (or null), region, dish category, source domain, publication date, collection date. **No recipe prose, no instructions, no copyrighted text** |
| `ingredients_lexicon.csv` | Canonical Thai name, English gloss, all observed variants, category, notes on judgement calls. **The flagship artifact** |
| `coverage.csv` | Recipe count, labelled fraction, source-domain concentration per province |
| `network.gexf` | PMI-weighted co-occurrence network |
| `province_vectors.csv` | TF-IDF vector per qualifying province, with recipe counts |
| `fieldwork.csv` | Anonymised: province, district, role of cook, ingredients, stated substitutions, stated absences, acquisition mode |
| Dataset cards | Motivation, collection method, scraping ethics, known biases, unlabelled fraction, κ, licence, citation, contact |

CC-BY-4.0 data, MIT code, stated in three places. Zenodo DOI. `loading_script` so
`load_dataset` works in one line. English glosses on every lexicon entry. Croissant metadata.

Because all five research questions are answered from the released artifacts, **the
dataset is the paper's reproducibility layer, not a side deliverable.**

---

## 13. Tests

| Test | Asserts |
|---|---|
| `test_raw_immutable` | no UPDATE/DELETE targets `raw_*` anywhere in `src/` |
| `test_pdpa` | no phone, email, or house-number pattern survives into any table |
| `test_canonicalize_deterministic` | same input → same `canonical_id` across runs |
| `test_conflation_guard` | no alias maps across an `ingredient_conflations` pair |
| `test_attribution_precedence` | tier 1 always beats tier 4 |
| `test_clean_view_excludes_low` | zero `confidence='low'` rows in `v_recipes_clean` |
| `test_mantel_recovers_known` | planted r=0.5 on synthetic data → p < 0.01 by permutation |
| `test_no_leakage_recipes` | no `cluster_id` spans two CV folds |
| `test_no_pii` | no table column matches name/phone/email patterns |
| `test_figures_regenerate` | `make figures` produces every file referenced by the manuscript |
| `test_source_type_carried` | no analysis pools institutional and web-scraped rows without a source indicator |

---

## 14. Open question for the researcher

**The image classifier is absent from Bible v3.** v2 scoped an EfficientNet-B0 vision
component over fieldwork photos (`src/vision/`, HD-16, ~400-photo minimum). v3 does not
mention it in the research questions, the feasibility audit, the figure specification, the
technical architecture, or the release artifacts — while explicitly stating that the
methods stack is otherwise "identical."

This reads as a deliberate cut for hour-budget reasons, consistent with every other v3
reduction. But it is not stated as one, and the empty `src/vision/` package is still in the
tree. **Not resolved here.** Until the researcher confirms, vision is treated as out of
scope and no work proceeds on it.

---

## Changelog

- **2026-08-30** — Reconciled to **Bible v4**. Four of the five research questions
  replaced: boundary geometry → three-register agreement (RQ1); coverage legibility →
  what the official record leaves out (RQ3); network fragility → pipeline fidelity, cooked
  (RQ4); vernacular signal → endangerment agreement (RQ5). Only RQ2, presence versus
  absence, survives substantially unchanged. Every figure renumbered, and the figure table
  rewritten to v4 §12. **The risk profile inverted**: this file said all five questions run
  on the web corpus and none could be blocked by a cancelled trip; under v4 four of five
  require fieldwork and one requires cooking. RQ5 marked as an open gate — the checkbox
  extraction works, but the fieldwork sample carries one distinct official value and
  Figure 5 cannot be built from it (`docs/checkbox_extraction.md`). Two built figures that
  v4 no longer lists are recorded with their disposition left open rather than deleted.
  **Partial**: the phase plan, gate list and schema notes still carry v3 numbering.
- **2026-08-23** — §21 blocking item 1 discharged: the labelled-recipe fraction is
  **1.3%** on `cooking.kapook.com`, against a 35% threshold, with a researcher-confirmed
  hand audit behind it. HD-3 decided for that source (option A, coverage corpus). This is
  a coverage paper; RQ1's province-level form is withdrawn pending a separate decision on
  what replaces it. RQ3 marked exploratory — the measurement preceded pre-registration,
  the second such exception in two days.
- **2026-08-16** — Reconciled to Bible v3. RQs rewritten (centrality → distance-decay;
  Louvain-vs-regions → presence/absence decomposition; distinctiveness → coverage
  cartography; Mantel/Moran headline → node-removal fragility; classifier → per-category
  with baseline). Fixed threshold replaced by a 5–30 sweep. Fieldwork cut to 12–15
  interviews across Nan and Surin; cook-alongs to 8. Dataset release split into two HF
  repos. Second annotator and pre-registration promoted to requirements. Figure
  specification and HD-gate list added. Superseded plans archived to `docs/archive/`.
- **2026-08-09** — Database moved from hosted Supabase to local PostgreSQL 15 + PostGIS in
  Docker. `raw_recipes.raw_html` removed in favour of `raw_path`.
