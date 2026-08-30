# FlavorMap · แผนที่รสชาติ
## The Project Bible — v4, Three Registers Edition

**Computational Geography of Thai Cuisine** · Rebuilt around a balanced government corpus
ISB Bangkok · Grade 10 → Grade 11 · Pillar 2 of the Future Leader Plan · **Supersedes v3**

---

> **Why this version exists.** v3 rescoped the project against a real calendar and was right to. But it
> was written before `food.culture.go.th` was found, and that source changes what the project *is*. v3
> assumed a messy scraped corpus with sparse province labels, and built five questions around measuring
> that messiness. The government corpus is balanced, complete-coverage, and already labelled — three
> dishes for every one of Thailand's 77 provinces.
>
> v4 changes the research questions to match the data that actually exists.

> **The structural reversal, stated plainly.** v3's single most important correction was that *no
> research question may depend on fieldwork completing.* **v4 breaks that rule.** Four of the five
> questions below need the interviews. This is a deliberate trade, made because the researcher wants the
> fieldwork and because the register comparison is a better paper than the coverage audit it replaces.
> It is also the single largest risk in this document. See §8 and §20.

---

## Contents

1. What changed from v3, and why
2. The Fingerprints Problem — retained
3. The Origin Story — still has an open bracket
4. PDPA and Research Ethics — new, non-negotiable
5. The Three Registers
6. The Five Research Questions
7. Feasibility Audit
8. Data Stream 1 — The Official Register
9. Data Stream 2 — The Commercial Register
10. Data Stream 3 — The Domestic Register (fieldwork)
11. Data Stream 4 — Cook-alongs, promoted to a research question
12. Figure Specification
13. Technical Architecture
14. Analysis Plan
15. Human Decision Gates & the Claude Code arrangement
16. The Limitations Register
17. The Paper — venue and structure
18. OpenFlavorTH — two datasets, not one
19. The Public Artifact
20. The Credit Ledger
21. Timeline
22. Risk Register
23. The Next 30 Days
24. Application Language & the TunDee pairing

---

## 1. What Changed From v3, and Why

| Area | v3 | v4 | Reason |
|---|---|---|---|
| **Research questions** | Five, built around measuring corpus bias in a messy scrape | Five, built around **comparing three registers** of the same cuisine | The government corpus removed the messiness the v3 questions were designed to measure |
| **Primary source** | Six scraped web sources | `food.culture.go.th` — 231 government PDFs, 3 dishes × 77 provinces | Balanced, complete-coverage, already labelled, with fields fieldwork was supposed to produce |
| **Corpus target** | ~2,200 recipes | **~800** (231 official + ~550 web) | Normalisation falls from ~130 h to ~50 h. Balance beats volume |
| **Province labelling** | Top project risk — unknown fraction, might collapse the paper | **Solved.** Every official record carries province, district, subdistrict | The risk that dominated v3 no longer exists |
| **Fieldwork dependency** | Zero RQs depended on it | **Four of five depend on it** | Deliberate reversal. See the warning above and §20 |
| **Cook-alongs** | 8 dishes, narrative only, "first to cut" | 8 dishes, **promoted to RQ4** | Nobody validates food datasets by cooking from them. It is a real methods contribution |
| **Distance-decay (old RQ1)** | Headline question | **Cut** | 3 recipes per province is too thin for a 2,900-point pairwise curve |
| **Coverage cartography (old RQ3)** | Headline question | **Cut** | The official corpus has complete coverage by construction. The question answers itself |
| **Endangerment level** | Not known to exist | **RQ5 is built on it** | A field in the government forms that nobody has used |
| **PDPA** | Not addressed | **§4, non-negotiable, enforced at parse time** | The source PDFs contain informant names, addresses, and phone numbers |
| **Local path** | `~/Desktop/flavormap` | `~/Desktop/G.9/flavormap` | Moved. Use repo-relative paths so it survives the next move |
| **Methods stack** | NetworkX, TF-IDF, UMAP, K-means, PySAL, Random Forest, PyThaiNLP | **Identical**, minus Mantel and Moran's I | Nothing removed for difficulty. Those two lost their question |

### What v4 gains and what it gives up

**Gains.** A balanced corpus. Solved province labelling. Three genuinely comparable registers. A cooking
question that turns the most enjoyable part of the project into a methods contribution. An endangerment
field nobody else has touched. A fieldwork role that is *central* rather than decorative.

**Gives up.** The distance-decay curve, which was the most quotable single number in v3 ("the food
changes at about 180 km"). The coverage choropleth, which was rhetorically the strongest image. And the
structural safety of a project that could not be destroyed by a cancelled trip.

That last one matters most, and §20 treats it as the top risk rather than burying it.

---

## 2. The Fingerprints Problem — Retained From v2 and v3 · UNCHANGED

The reasoning stands in full and is not restated. The summary: admissions readers discount sophisticated
teen projects steeply because they cannot verify authorship, so **believability is the scarce resource,
not sophistication.** The three signals a reader uses are process visibility, irreplaceable input, and
calibrated claims.

v4 preserves all three mechanisms — public repo from day one, unpolished early notebooks left intact, a
named credit ledger, a limitations register written before anyone asks, and fieldwork only she can do.

v4 strengthens the second signal considerably. In v3 the fieldwork was corroboration; here it is the
input four questions run on. Twelve interviews and eight cooked dishes are not obtainable by a competent
adult with a laptop, which is precisely the point.

---

## 3. The Origin Story — Still Has an Open Bracket · BLOCKING

Every description of the project opens with cooking and arrives at code. The canonical origin paragraph
still has a bracket in it: *the real dish, the real family version.*

**That bracket is still open.** Until it is filled with something that actually happened, the essay, the
paper's introduction, the first build-log post, and every interview answer rest on a placeholder. This is
the one item in the entire document that cannot be reconstructed later — a memory cooked and written down
in month 1 is evidence; the same memory reconstructed in month 14 is a story.

**Action.** Cook the dish with the family member this month. Photograph the mise en place. Write down what
actually happens, including the parts that contradict the remembered version — especially those. Commit
the notes and photos to the repo with the real date. Two hours. See §23.

Voice rules retained: cooking first and method no earlier than the third sentence; first person and
concrete verbs; name the false start; no grand framing verbs; keep the sister visible where she
contributed.

---

## 4. PDPA and Research Ethics · NEW SECTION, NON-NEGOTIABLE

The `food.culture.go.th` submission forms contain **informant personal data**: full name, house number,
road, subdistrict, postcode, and mobile number. Thailand's Personal Data Protection Act applies.

**The rule: strip at parse time, before any database write. Never at export.**

Once a phone number reaches a table it is in the dump, the backup, every Parquet file written from that
table, and any log line that echoed the row. Stripping at export is not compliance; it is hoping nobody
checks the intermediate artifacts.

- Personal data must never reach a table, CSV, Parquet file, log line, or cached intermediate.
- A test asserting that no phone, email, or address value survives into any table is part of the parser's
  **definition of done**, not a follow-up task.
- `data/raw/` holds the original PDFs, is gitignored, and is never published.
- The published dataset carries province, district, dish, and ingredients. It carries no person.

**Fieldwork ethics are unchanged from v2 and v3 and equally non-negotiable:** written one-page Thai
consent form in plain language; default to anonymised publication by role and province; a parent
chaperones every interview and this is stated plainly in the methods section; reciprocity — every
participant receives the finished map and a printed copy of their own recipe as it appears in the
dataset; no recording without explicit permission.

**Scraping ethics** for the commercial register are retained in full and without softening: robots.txt
and ToS checked and dated in `ETHICS.md` for every site; rate-limit 1 request per 1–2 seconds; honest
User-Agent with contact email; ingredient lists and province labels stored, never full recipe prose; raw
HTML cached locally and never published.

For the government source specifically: **check robots.txt first and record the date.** A government
open-data programme does not imply permission by default.

---

## 5. The Three Registers · NEW SECTION

This is the organising idea of v4. The same cuisine is documented three times by three different actors
with three different motives, and the gaps between them are the findings.

| Register | Source | Size | Represents | Selection pressure |
|---|---|---|---|---|
| **Official** | 231 government PDFs, `food.culture.go.th` | 3 per province × 77 | What the state selects to represent a province | Cultural policy, heritage framing, provincial pride |
| **Commercial** | Scraped web recipes | ~400–600 | What the urban internet cooks and publishes | SEO, photographability, ingredient availability in Bangkok |
| **Domestic** | 12–15 interviews, Nan + Surin | ~40–60 dishes | What people actually cook at home | Season, cost, what grows nearby, habit |

Each register is a *sample with a bias*, and each bias is different. No register is the truth. The
comparison is the instrument.

**Every recipe in the database carries a `register` column.** This is the single most important schema
decision in v4 and it must be present from the first load, not retrofitted.

### What the official register contains

Each PDF carries: province, district, subdistrict, dish name, dish category, occasion,
**endangerment level**, ingredient list with quantities, and an **acquisition mode** column
(grown / foraged / market / packaged).

v3 §8 assumed acquisition mode could only come from fieldwork. It is in the government forms. That is a
strictly better source — 231 records instead of 15, collected by people who live there.

**Two known Thai PDF extraction traps**, both of which must be handled and tested:

- **Sara am (ำ) drops and becomes a space** during text extraction. `น้ำปลา` becomes `น้ ปลา`. This
  fails *silently* and corrupts ingredient names rather than throwing an error. A parser can look like it
  is working while poisoning the lexicon.
- **Form checkboxes are Wingdings glyphs** that do not survive text extraction. Dish category and
  **endangerment level** both depend on them — and RQ5 depends on endangerment level. Detect positionally
  or by font, never by character.

If endangerment level cannot be recovered reliably, **RQ5 has no data and must be replaced.** This is the
most likely failure point in the new question set and should be tested in week one.

---

## 6. The Five Research Questions · REWRITTEN

Each question is stated twice: the precise form for the paper, and the plain form for the site, the build
log, and interviews. Each carries the **transferable claim** — what a reader outside Thai food studies
takes away. A question producing only a fact about Thai cuisine gets a poster; one producing a method or
a general claim gets a talk.

### RQ1 — Do the state, the market, and the kitchen agree on what a province eats?

*Plain: does the food the government picks to represent your province match what people there actually cook?*

| | |
|---|---|
| **Method** | Ingredient-profile distance between the three registers for the same province. Cosine distance on normalised ingredient vectors, computed pairwise: official↔commercial, official↔domestic, commercial↔domestic. |
| **Output** | Triangle plot per province, one vertex per register, edge length = disagreement. Figure 1. |
| **Needs fieldwork** | Yes — the domestic register *is* the interviews. |
| **A NO looks like** | The three registers agree. That would mean official selection and web recipes faithfully represent domestic practice — a genuine methodological result in the opposite direction, and reassuring for everyone who has ever built on a scraped corpus. |
| **Transferable** | **Cultural corpora carry the selection pressure of whoever assembled them.** State-curated, commercially-published, and domestically-practised versions of the same tradition are measurably different objects. Applies to folk music archives, craft inventories, heritage registers, and any government-designated cultural list. |

This is the spine of the paper. The finding is a number: how far apart official, commercial, and domestic
Thai food actually are. Nobody has measured it because nobody had all three registers for the same
provinces.

### RQ2 — Is regional identity built from what's included or what's refused?

*Plain: is a region's food about what it uses, or about what it refuses to use?*

| | |
|---|---|
| **Method** | Decompose each province's distinctiveness into presence-driven and absence-driven components. Validate against stated absences from interview Q9. |
| **Output** | Scatter, presence-driven vs. absence-driven, one point per province, diagonal = balanced. Figure 2. |
| **Needs fieldwork** | Yes, for validation. Inferred absence is weak evidence; **stated** absence is strong. |
| **A NO looks like** | Distinctiveness is symmetric everywhere. Still a fact nobody had. |
| **Transferable** | **Every distinctiveness measure in computational humanities — TF-IDF, log-odds, Zeta — is a presence measure. Absence is structurally invisible to all of them.** A decomposition that recovers it is a contribution to measurement, applicable to any corpus where practitioners define themselves against a neighbour. |

Interview question 9, phrased to be asked out loud as written:

> **“อะไรที่คนจังหวัดอื่นใส่ในจานนี้ แต่บ้านเราไม่มีวันใส่?”**
> *What do people in other provinces put in this that we would never put in?*

Test the phrasing on the first informant. The wording determines whether the answer is real or merely
polite.

This remains the most genuinely novel item in the set and costs almost nothing to compute. The cost is
definitional: no off-the-shelf measure exists, so she must define one and defend it. Roughly 15 hours of
thinking and 3 of coding. Best novelty-to-effort ratio in the project.

### RQ3 — What does the official record leave out?

*Plain: whose cooking didn't make the government's list?*

| | |
|---|---|
| **Method** | The state selected 3 dishes per province. Ask cooks in Nan and Surin what they actually cook. Measure overlap at dish level and ingredient level. |
| **Output** | Table of dishes and ingredients named by cooks that appear in no register; overlap bar chart. Figure 3. |
| **Needs fieldwork** | Entirely. |
| **A NO looks like** | High overlap — the official three capture what people cook. That validates the state's selection process, which is itself a finding. |
| **Transferable** | **Heritage designation is a sampling procedure with a bias, and the bias is measurable.** Any national cultural inventory — intangible heritage lists, protected designations, folk archives — is a sample of three from a population of hundreds. |

Framed as an **existence claim**, which n≈6 per province fully supports: *six of six cooks in Surin named
an ingredient no register associates with the province.* Never a basis for ranking provinces. The
distinction is what makes it unobjectionable.

This is the section only she can write, and it states the TunDee thesis in a second domain.

### RQ4 — Can you cook a dish from the normalised dataset?

*Plain: after the computer cleans up a recipe, is it still a recipe?*

| | |
|---|---|
| **Method** | Cook 8 dishes from the **cleaned dataset's** ingredient list, not the original source page. Log what was missing, what had to be substituted, what normalisation destroyed, whether the result was recognisable. |
| **Output** | Fidelity table — 8 dishes × what survived the pipeline. Figure 4. |
| **Needs cooking** | Entirely. This question cannot be answered any other way. |
| **A NO looks like** | Everything cooks fine — normalisation is lossless for practical purposes. Reassuring, and worth reporting. |
| **Transferable** | **Tokenisation and canonicalisation silently delete information, and nobody in computational food studies measures how much.** Quantities, order, technique, and the difference between พริกขี้หนู and พริกขี้หนูสวน all vanish into a bag of tokens. This is a reproducibility argument that transfers to any pipeline that flattens structured text. |

I would push this one hardest. Every paper in the field treats a recipe as a bag of ingredients and never
checks whether the bag reconstitutes a meal. Eight dishes is enough to demonstrate that it does not, and
the demonstration costs eight afternoons.

It also changes what the cooking *is*. In v3 it was narrative colour and the first thing to cut. Here it
is the validation layer, and cutting it removes a research question.

### RQ5 — Do cooks agree with the state about which dishes are disappearing?

*Plain: the government says these dishes are at risk. Do the people who cook them agree?*

| | |
|---|---|
| **Method** | Compare the **endangerment level** field in the government PDFs against what cooks in Nan and Surin say about the same dishes. |
| **Output** | Agreement matrix — official endangerment vs. cook-reported status. Figure 5. |
| **Needs fieldwork** | Entirely. |
| **A NO looks like** | Full agreement, validating the state's assessment process. |
| **Transferable** | **Official risk assessments of cultural practice can be checked against practitioners, and the disagreements are informative.** The cells where the state says "safe" and cooks say "nobody makes this anymore" are the interesting ones. |

Uses a field nobody has noticed, and has the clearest public stake of the five. **Dependent on the
Wingdings checkbox extraction working** — see §5.

### Read together

The five make an argument rather than running a battery of tests. The same cuisine documented three times
by three actors produces three different objects (RQ1); identity lives in refusal as much as in addition
(RQ2); official selection leaves measurable gaps (RQ3); the computational pipeline itself deletes
information nobody has quantified (RQ4); and the state's own risk assessment can be checked against the
people doing the cooking (RQ5).

**Four of five require fieldwork. One requires cooking. This is the point and the risk simultaneously.**

---

## 7. Feasibility Audit

| RQ | Verdict | Real cost | Constraint and mitigation |
|---|---|---|---|
| **RQ1** | Yes | ~20 h analysis | Needs all three registers loaded with a `register` column. If fieldwork fails, degrades to a two-register comparison (official vs. commercial), which still stands as a paper. |
| **RQ2** | Yes, comfortably | ~18 h | Cost is definitional, not computational. Without fieldwork, absences are inferred rather than stated — weaker but reportable. |
| **RQ3** | **Fieldwork-only** | ~12 h + fieldwork | No fieldwork, no question. There is no degraded version. |
| **RQ4** | Yes | ~8 h + 8 cooking sessions | Fully under her control. The only question that depends on nobody else. |
| **RQ5** | **Conditional** | ~10 h + fieldwork | Dies twice over: if the checkbox extraction fails, or if fieldwork fails. Test the extraction in week one. |

**Total analysis: roughly 70 hours**, down from v3's 110, because the corpus is smaller and two
computationally heavy questions were cut.

**Normalisation: roughly 50 hours**, down from ~130, because the corpus is ~800 rather than ~2,200. This
is the change that makes the timeline plausible.

**The bottleneck is no longer normalisation. It is fieldwork logistics** — roughly 85 hours across two
trips, in term time, dependent on other people's availability, a family calendar, and school.

### The degraded-mode plan

If fieldwork does not happen, the honest fallback is a **two-register paper**: official vs. commercial,
RQ1 and RQ2 only, with RQ4 as the methods contribution. That is a real paper and it is worth stating in
advance, because deciding it under pressure in December produces a worse outcome than deciding it now.

---

## 8. Data Stream 1 — The Official Register

231 PDFs at `food68/{region}/{province_index}/{menu_index}.pdf`, three dishes for each of 77 provinces,
2568 programme year.

**Collection.** Enumerate the URL pattern rather than guessing index ranges — discover the actual counts
per region and report them. Rate limit 1 request per 1–2 seconds. Honest User-Agent with contact email.
Download to `data/raw/culture_go_th/`, gitignored, with a manifest recording URL, retrieval timestamp,
HTTP status, and file hash.

**Parsing.** Evaluate at least three extractors — `pdfplumber`, `PyMuPDF`, `pypdf` — on a sample of ~10
PDFs spanning all four regions, and report extraction quality per extractor before committing to one.
Handle the sara am and Wingdings traps from §5 explicitly, with a test for each.

**PDPA stripping at parse time**, per §4, with a passing test as part of the definition of done.

**Load** into Postgres with `register = 'official'`, deduplicated, with provenance columns.

---

## 9. Data Stream 2 — The Commercial Register

Target ~400–600 usable recipes after cleaning, from at least four live sources: Wongnai, Cookpad TH,
Krua.co and magazine archives, provincial tourism pages, regional cookbook OCR, YouTube channel
descriptions.

Scraping ethics per §4, retained in full and without softening.

**Fields to capture — both free now, both unrecoverable later:**

- **Publication / post date** on every scraped recipe. Enables any temporal question later and costs one
  selector per scraper. Impossible to backfill after the freeze.
- **Dish category**, mapped to the same taxonomy the government forms use so the registers are comparable.

**Cleaning pipeline.** Tokenise with PyThaiNLP `newmm`; normalise to the controlled vocabulary; strip
quantities and preparation verbs — *and log what was stripped, because RQ4 measures exactly this loss*;
assign province labels from source page, dish name, or explicit regional claim, leaving unlabelled rather
than guessing; deduplicate on ingredient-set Jaccard above 0.9.

The controlled vocabulary remains the project's most defensible artifact: 400–700 normalised Thai
ingredient entries with variant mappings, a resource that does not exist publicly and cannot be scraped
into existence. Every mapping decision required someone who cooks and reads Thai.

---

## 10. Data Stream 3 — The Domestic Register

**12–15 interviews across two provinces — Nan and Surin.** Six per province minimum. 60–90 minutes each.

**Why these two.** One Northern, one lower-Isaan; both peripheral; both far from the commercial
register's centre of gravity. If only one trip happens, **do Surin.**

**Scope.** Depth beats spread. One 90-minute interview with photographs, a cooked dish, and a follow-up
beats four rushed 40-minute conversations. Four interviews per province supports nothing; six supports a
specific, defensible sentence.

**The protocol.** All eight questions from v2 retained verbatim, including Q3 (substitutions — collected
even though the graph analysis is out of scope) and Q8 ("what do restaurants get wrong about it?"). Plus
Q9 from §6 (stated absences, feeding RQ2), and a new Q10 for RQ5:

> **“จานนี้ยังมีคนทำอยู่ไหม? ใครทำ? คนรุ่นใหม่ทำเป็นหรือเปล่า?”**
> *Does anyone still make this? Who? Do younger people know how?*

Ask Q10 about the three dishes the government listed for that province specifically, so the comparison in
RQ5 is dish-matched rather than general.

**Fields to capture:** district as well as province; ingredient acquisition mode, using the same four
categories as the government forms so the registers are directly comparable.

**Ethics and consent per §4** — unchanged and non-negotiable.

---

## 11. Data Stream 4 — Cook-Alongs, Promoted to a Research Question

**Eight dishes.** In v3 this was narrative colour and the first thing to cut. In v4 it is RQ4.

**Protocol.** Cook from the **cleaned dataset's** ingredient list, not the original source page — the
point is to test the pipeline, not the recipe. For each dish log:

- what was missing from the normalised list that the original had
- what had to be substituted and why
- what the normalisation destroyed: quantities, order, technique, ingredient specificity
- whether the result was recognisable as the dish
- one sentence of sensory description

Include at least two dishes the pipeline handles badly, and at least two from the official register so
the government forms are tested alongside the web recipes. Where a dish came from an interview, cook that
version and send the photograph back to the cook.

Photograph the mise en place, not only the finished dish. The mise en place is the evidence.

**The scope-discipline warning still stands** and matters more now that cooking has a research role: this
is not a cookbook, a food blog, or a YouTube channel. Eight dishes, logged in a structured table. The
moment it becomes the deliverable, the project has drifted.

---

## 12. Figure Specification

Every chart is 2D. Three-dimensional scatter plots lose the ability to read any point's position,
introduce occlusion, and are unreproducible in a paper because the figure depends on a chosen camera
angle. Where a third axis is tempting, use colour, size, or small multiples. The single exception is the
force-directed ingredient network on the website, where 3D is not clearer but is worth spinning.

| # | Figure | X axis | Y axis | Encoding and purpose |
|---|---|---|---|---|
| 1 | **Register triangle** (RQ1) | — | — | One triangle per province; vertices = official / commercial / domestic; edge length = ingredient-profile distance. Small multiples for the two fieldwork provinces at full size, all others as a two-register line. The paper's signature figure. |
| 2 | **Distinctiveness decomposition** (RQ2) | presence-driven | absence-driven | One point per province, diagonal = balanced. Above the line = defines itself by refusal. A chart type reviewers have not seen. |
| 3 | **Official-record overlap** (RQ3) | province | count | Stacked bars: dishes named by cooks that are in the official three / in the commercial register / in neither. The "neither" segment is the finding. |
| 4 | **Pipeline fidelity** (RQ4) | dish | information class | Matrix, 8 dishes × {quantities, order, technique, specificity, completeness}. Cell = survived / degraded / lost. Reads as a table but functions as a figure. |
| 5 | **Endangerment agreement** (RQ5) | official level | cook-reported status | Confusion-matrix style. Off-diagonal cells are the interesting ones. |
| 6 | **Province × ingredient heatmap** | ingredients (top ~60 by variance) | provinces | Fill = TF-IDF, faceted by register. **Both axes seriated by clustering, never alphabetical.** Good first Results figure because no modelling sits between data and image. |
| 7 | **Acquisition mode by province** | province, ordered by distance from Bangkok | share of ingredients | Stacked bars: grown / foraged / market / packaged. Uses a government field directly. Supporting figure, and the most immediately legible in the set. |

**The ordering trap.** Any matrix or heatmap must be ordered geographically or by cluster, never
alphabetically. Alphabetical ordering scatters real structure into what looks like noise. This single
choice is the difference between a figure that is the result and a figure that says nothing.

---

## 13. Technical Architecture

| Component | Choice | Why |
|---|---|---|
| **Working directory** | `~/Desktop/G.9/flavormap` | Moved from `~/Desktop/flavormap`. **Use repo-relative paths** so the next move costs nothing |
| **Database** | Local PostgreSQL 15 + PostGIS in Docker Desktop | Free-tier hosted Postgres pauses after 7 days of inactivity, which collides directly with school-term low-activity periods. Local is faster, free, has no cap, and never pauses |
| **Backups** | Nightly `pg_dump`, gitignored, copied off the machine | Local Postgres has exactly one failure mode: the laptop. A stray `docker compose down -v` destroys the volume. The lexicon is ~50 irreplaceable hours |
| **Raw pages** | On disk, gitignored, **not in the database** | No `raw_html` column. Duplicating pages into Postgres inflates the DB for no benefit |
| **Analysis interface** | Parquet | The database is where the pipeline writes and dedups. Analysis reads Parquet — an 800-row frame fits in RAM with room to spare and needs no SQL |
| **Production API** | Pre-materialised static JSON | Site data never changes after the freeze. Static JSON on a CDN is faster, free, and cannot go down because a container stopped |
| **Language / env** | Python 3.11, local venv, pinned `requirements.txt` | Reproducibility — a reviewer must be able to re-run it |
| **Heavy compute** | None required | Nothing here needs a GPU. **Say so in the paper** — it establishes the project was constrained by effort and access rather than resources, which is the profile of a student project done properly |
| **Thai NLP** | PyThaiNLP | Unchanged |
| **Visualisation** | matplotlib + seaborn for the paper; D3 or Leaflet for the site | Different audiences, different tools |
| **Site hosting** | GitHub Pages or Vercel free tier | Zero cost, zero maintenance |

**Total infrastructure cost: effectively zero.** Real costs are fieldwork travel (~5,000–9,000 THB across
two trips) and cook-along ingredients.

**Schema requirements new in v4:** `register` on every recipe; `endangerment_level`; `acquisition_mode`;
district and subdistrict; `published_at`; `dish_category`; and a `cook_along_log` table for RQ4.

Repository additions: `docs/decisions.md`, `docs/hypotheses.md`, `docs/research_questions.md`,
`data/coverage/`.

---

## 14. Analysis Plan

### 14.1 Register comparison (RQ1)

Build a normalised ingredient vector per province per register. Compute pairwise cosine distance between
registers for the same province. Report the distribution of each pairwise distance across provinces, and
identify the provinces where the registers diverge most and least.

**Trap:** the three registers have very different sample sizes per province — 3 official, ~5–8
commercial, ~6 domestic in two provinces only. Distance measures are sensitive to sparsity. Report
sample sizes alongside every distance, and do not compare a province's official↔domestic distance against
another province's official↔commercial distance without noting the asymmetry.

### 14.2 The distinctiveness decomposition (RQ2)

No off-the-shelf measure exists. She must define one and defend it in the paper. The decomposition splits
a province's distance from the national mean into a component driven by ingredients it uses more than
average, and a component driven by ingredients it uses less. Validate the absence component against
stated absences from interview Q9: agreement is triangulation, disagreement is a discussion section.

This is a human decision gate. The definition is hers, documented in `docs/decisions.md` with the
alternatives she rejected.

### 14.3 The ingredient network

Nodes are normalised ingredients; edges join ingredients appearing in the same recipe; **weight by
pointwise mutual information rather than raw co-occurrence**, or the graph is dominated by fish sauce,
garlic and chilli and tells you nothing. Extract the backbone by disparity filtering before visualising.
Build one network per register and compare — a supporting analysis for RQ1, and the site's main
interactive.

### 14.4 Overlap and agreement (RQ3, RQ5)

Both are set comparisons and contingency tables rather than models. Report raw counts, not just
percentages — with n≈6 per province, a percentage is misleading and a count is honest.

### 14.5 What was cut and why

**Mantel test and Moran's I** are both gone, along with the distance-decay question they served. Neither
was removed for difficulty; they lost their question when the corpus became 3 recipes per province. If
the commercial register grows well past target, distance-decay could return as a supporting analysis on
that register alone — with a permutation-based Mantel, 9,999 permutations, never a parametric p-value.

**UMAP** stays, as a browsing interface on the website only. Its axes carry no interpretable meaning.
Label them "UMAP 1 / UMAP 2", caption them as uninterpretable, never quantify from the projection, and
never call an axis geographic or cultural.

---

## 15. Human Decision Gates & the Claude Code Arrangement

**The arrangement, stated plainly.** Claude Code builds machinery. She owns every analytical decision.
Twenty human decision gates mark the points where the pipeline stops and waits for a judgment only she
can make — and every one is written up in `docs/decisions.md` with its reasoning and its alternatives.

That file is not bookkeeping. It is **interview preparation, methods-section source material, and the
single best answer to "how much help did you have?"** A student who can open a dated file and show two
hundred documented judgment calls is not answering that question defensively.

Representative gates: canonical-vocabulary granularity (are three chillies one ingredient or three?);
province-labelling rules; the RQ2 decomposition definition; the dish-category taxonomy and its mapping
between registers; which eight dishes to cook; which provinces to visit; what counts as "the same dish"
across registers; what goes in the limitations register.

**~180 hours across the twenty gates**, down from v3's ~225 because the corpus is smaller. This is the
number that determines whether the project finishes, and it is the one number that generating code faster
does not reduce.

**AI disclosure is a credibility asset, not a risk.** A line reading *"I used Claude Code to build the
pipeline and to debug the Thai tokeniser; every analytical decision is mine and documented with its
reasoning in docs/decisions.md"* is stronger than silence. Every reader assumes AI assistance was
available; the discriminating question is whether the student is specific about it.

---

## 16. The Limitations Register

Maintained as a live file from month one, not written at the end.

| Entry | Severity | Statement |
|---|---|---|
| **Fieldwork is load-bearing** | **HIGH · NEW** | Four of five questions depend on 12–15 interviews. This reverses v3's structural principle deliberately. If fieldwork fails, the paper degrades to two registers and two questions. Stated in advance, not discovered in December |
| **Fieldwork n = 12–15** | HIGH | Presented as an existence demonstration and qualitative validation, never as a representative sample and never as a basis for ranking provinces. Two provinces at n≈6, stated as such |
| **Official register is 3 dishes per province** | HIGH · NEW | A sample of three from a population of hundreds, selected by a committee with cultural-policy motives. This is the object of study in RQ3, but it also limits what RQ1 can conclude |
| **Domestic register covers 2 of 77 provinces** | HIGH · NEW | RQ1's three-way comparison is only possible for Nan and Surin. All other provinces are two-register. Do not present a national three-register map |
| **Register sample sizes are unequal** | MEDIUM · NEW | 3 vs. ~6 vs. ~6. Distance measures are sparsity-sensitive. Report n alongside every distance |
| **Commercial corpus skews urban and Central Thai** | HIGH | Retained from v2 |
| **Normalisation involves judgement calls** | MEDIUM | Retained — and now partly *measured*, by RQ4 |
| **Recipes are not consumption** | MEDIUM | Retained. A documented recipe is not evidence of what people eat |
| **No temporal dimension** | MEDIUM | The corpus is a single time-slice. She can say traditions are undocumented; she cannot say how fast they are vanishing. RQ5 reports *stated* endangerment, not measured rate of loss. Catch this before it reaches an essay |
| **Endangerment level is self-reported** | MEDIUM · NEW | The government field reflects the submitter's assessment, not an independent survey. RQ5 compares two subjective assessments, which is still interesting but must be described accurately |
| **Dish-category taxonomy** | MEDIUM | Categories are constructed, not natural. Publish the taxonomy and inclusion rules so others can disagree with specific assignments |
| **Single annotator** | LOW-MED → **RESOLVED** | 100 recipes independently double-labelled; Cohen's κ reported. A few hours of a second Thai reader's time — cheapest credibility in the project |
| **Sites excluded for ToS reasons** | LOW | Retained |

---

## 17. The Paper — Venue and Structure

**Working title:** *"Three registers of Thai regional cooking: what the state, the market, and the kitchen
each record"*

| Venue | Track | Assessment |
|---|---|---|
| **Journal of Cultural Analytics** | Primary | The natural home for the RQ1 register claim. With a freeze in early 2027 and applications in November 2027, a review cycle fits comfortably |
| **CHR 2028** | Full paper / poster | Computational Humanities Research is the right community. Suits a post-journal submission or a parallel short paper |
| **arXiv (cs.CY / cs.SI)** | Preprint | Post regardless of venue outcome, before applications. A citable preprint with a DOI is what the Common App honours line actually needs |
| **Thai undergraduate research conference** | Full paper | Realistic and genuine, in Thai or English. Local recognition strengthens the EEF and Chulalongkorn relationships |

### Structure — ~4,600 words

| Section | Words | Notes |
|---|---|---|
| Introduction | 600 | Opens with the kitchen. The origin story **is** the introduction — do not replace it with a literature review |
| Related work | 500 | Ahn et al. 2011 flavour networks; computational gastronomy; Thai food studies; critical dataset studies. **State the disagreement:** standard distinctiveness measures are blind to absence, and no food-computing paper validates its pipeline by cooking |
| Data — the three registers | 900 | Sources, PDPA handling, scraping ethics, cleaning pipeline, the lexicon, the fieldwork protocol. Longest methods subsection, because the data is the contribution |
| Methods | 700 | Justify PMI weighting, the RQ2 decomposition definition, and the register-distance measure explicitly |
| Results | 1,100 | Negative results at full weight, not in a footnote. Compare against the pre-registered expectations |
| **What the official record leaves out** | 400 | The distinctive section. Two provinces, twelve cooks, a table of dishes absent from every register. No other computational gastronomy paper has this |
| Limitations | 500 | Lifted from the live register. Unusually long, deliberately |
| Conclusion | 300 | What she would do next and what she would do differently |

**Authorship rules unchanged and non-negotiable:** she is first author, and if an arrangement would not
permit that, decline the arrangement. A faculty advisor is a co-author only for substantive contribution
to design or analysis — review and advice is an acknowledgement. Getting that boundary right is itself a
mark of research maturity. The sister is acknowledged by name for visualisation and design.

---

## 18. OpenFlavorTH — Two Datasets, Not One

**Release the lexicon separately.** The recipe corpus is competent but modest — comparable public food
datasets run to hundreds of thousands of recipes, and a realistic first-year expectation here is
**150–600 downloads**. The lexicon is a different proposition: useful to Thai NLP, recipe parsing,
food-safety text mining, and agricultural translation — people who do not care about regional cuisine at
all.

Two repos: `OpenFlavorTH-recipes` and `OpenFlavorTH-lexicon`. Bundling them hides the lexicon's
independent value and prevents it being cited on its own.

| Artifact | Contents |
|---|---|
| `recipes.parquet` | Recipe ID, **register**, normalised ingredient list, province, district, region, dish category, **endangerment level**, **acquisition mode**, source domain, publication date, collection date. No recipe prose, no instructions, no copyrighted text, **no personal data** |
| `ingredients_lexicon.csv` | Canonical Thai name, English gloss, all observed variants, category, notes on judgement calls. **The flagship artifact** |
| `stated_absences.csv` · NEW | Province, dish, ingredient named as never used, role of cook. Feeds RQ2. **Exists nowhere else in the world** |
| `cook_along_log.csv` · NEW | Dish, register of origin, what was missing, what was substituted, what normalisation destroyed, recognisability verdict. The RQ4 evidence |
| `endangerment_comparison.csv` · NEW | Dish, province, official endangerment level, cook-reported status. The RQ5 evidence |
| `fieldwork.csv` | Anonymised interview recipes: province, district, role of cook, ingredients, stated substitutions, acquisition mode |
| `network.gexf` | PMI-weighted co-occurrence network, one per register |
| Dataset cards | Motivation, collection method, PDPA handling, scraping ethics, known biases, register definitions, κ, licence, citation, contact |

**Because all five research questions are answered from the released artifacts, the dataset is the
paper's reproducibility layer**, not a side deliverable. A reviewer can re-run every analysis from the
public files. That is a stronger position than most published work in the field, and it should be said in
the dataset card.

### Release checklist

- CC-BY-4.0 for data, MIT for code, stated in three places
- Zenodo DOI via the GitHub link — what makes the Common App honours entry verifiable
- A `loading_script` so `load_dataset` works in one line
- **English glosses on every lexicon entry** — opens it to non-Thai readers, who are most of the potential users
- Croissant metadata file
- One honest post to PyThaiNLP community channels at launch. Not a campaign
- Version it: v1.0 at submission, v1.1 if a second fieldwork round lands
- **Report the real download number at application time.** "340 downloads" is far more credible than "widely used"

---

## 19. The Public Artifact

Thai-first, phone-first, shared through Line. What gets built: the map (tap a province, see its three
dishes, its distinctive ingredients, and — for Nan and Surin — the register triangle); the province quiz
with a shareable result card; the build log linked from the footer; a plain-language methods page linked
from every map view.

**One interactive:** pull an ingredient out of the network and watch it fragment. It is the best demo in
the project and the thing people forward to each other.

**Ship the map, the quiz, and one interactive. Nothing more.** Site builds reliably take triple the
estimate, and this one competes directly with the analysis window.

Deliberately not building: a recipe app or recommendation engine; a native mobile app; user accounts or
saved profiles (collecting personal data from Thai minors creates real obligations for no research
benefit); a restaurant or ingredient-sourcing directory.

---

## 20. The Credit Ledger

Unnamed help looks like hidden help. Naming exactly who did what converts suspicion into confidence.
Published as `CREDITS.md` and reproduced in the paper's acknowledgements.

**Her:** all scraping, parsing, cleaning, lexicon construction, analysis, modelling, writing, fieldwork,
transcription, cooking, and every build-log post.
**Advisor:** named, bounded, hours stated.
**Sister:** named, for visual identity, result-card design, map interface, Line distribution, photography.
**Parents:** chaperoned, transported, made introductions — did not conduct interviews, analyse data, or write.
**Participants:** by role and province, or by name where consent was given.

**Claude Code:** used to build the data pipeline, the scrapers, and the analysis machinery, and to debug
the Thai tokeniser. Every analytical decision — vocabulary granularity, labelling rules, thresholds,
taxonomy, the RQ2 decomposition definition, model choices — is hers and is documented with its reasoning
in `docs/decisions.md`. Claude Code did not choose what to measure, did not interpret any result, and did
not write the paper.

---

## 21. Timeline

Anchored on applications in **November 2027** and the ISB school calendar. **The freeze date is a
decision, not a constraint** — see the note below.

| Window | Build | Fieldwork / cooking | Output |
|---|---|---|---|
| **Sep 2026** | Path migration. Commit local work. Scraper + parser for 231 PDFs. PDPA test passing. **Checkbox extraction test — go/no-go on RQ5** | Cook the origin dish. **Book both trips with real dates** | Repo public. `docs/hypotheses.md` committed. RQ set updated everywhere |
| **Oct 2026** | Commercial register scrape to ~300. Normalisation, lexicon v0.5 | **Trip 1 — Surin, 6 interviews.** Cook 2 dishes | Build-log post 1. `ETHICS.md` complete |
| **Nov 2026** | Corpus to ~800. Normalisation complete. Lexicon v1.0 | **Trip 2 — Nan, 6 interviews.** Cook 3 dishes | Post 2. Lexicon first release |
| **Dec 2026** | All five analyses. Figures 1–7. Second-annotator κ | Cook 3 dishes, including two the pipeline handles badly. Transcription | Post 3 (failure post) |
| **Jan 2027** | Paper draft. Dataset packaged | Send results back to participants | **Draft complete. Both HuggingFace repos live** |
| **Feb–Mar 2027** | *Optional extension window* | *Optional second fieldwork round* | Revisions, or corpus expansion |
| **Apr–Aug 2027** | Advisor review. Site and quiz built with sister | — | Post 4–6. **Journal submission. arXiv preprint + Zenodo DOI** |
| **Sep–Nov 2027** | Line launch, timed to a Thai food moment | — | **Applications. Materials complete** |

**On the January date.** It is self-imposed. Applications are November 2027, which means a January finish
leaves ten months of slack. That slack is genuinely useful for a journal review cycle — but if the two
trips slip, **extending the freeze to March costs nothing and de-risks everything.** The trips are
currently stacked back-to-back in October and November, in term time, which is the tightest part of this
plan. Decide the freeze date deliberately rather than defaulting to January because it was written down
first.

**School always wins.** A strong Grade 10 report matters more to every target programme than a month of
this project.

---

## 22. Risk Register

| Risk | Severity | Mitigation |
|---|---|---|
| **Fieldwork does not happen** | **HIGH** · was MEDIUM in v3 | **Now the top risk, by construction.** Four of five questions depend on it. Mitigation is the degraded-mode plan in §7: a two-register paper with RQ1, RQ2, RQ4. Decide it now, not in December. **Book both trips this week** |
| **Endangerment checkbox unextractable** | **HIGH · NEW** | RQ5 dies with it. Wingdings glyphs do not survive text extraction. **Test in week one**, and have a replacement question ready |
| **Both trips stacked in term time** | HIGH · NEW | October and November are back to back, in Grade 10 coursework. If either slips, both slip. Extend the freeze to March rather than compressing |
| **Origin-story bracket never filled** | HIGH | Two hours that gate the essay, the introduction, and every interview answer. Cannot be reconstructed later. §3 and §23 |
| **Sara am extraction corrupts the lexicon silently** | HIGH · NEW | Fails without throwing. A parser can look correct while poisoning every ingredient name. Explicit test required |
| **PDPA breach** | HIGH · NEW | Personal data reaching any table, dump, or published file. Enforced at parse time with a passing test, per §4 |
| **Normalisation grind stalls the project** | MEDIUM · was HIGH | ~50 hours, down from ~130. Still cannot be delegated. Weekly quota, 50-ingredient batches, every decision logged |
| **Registers are not comparable** | MEDIUM · NEW | Different dish granularity, different naming conventions, different category taxonomies. Map the taxonomies explicitly before comparing, and document the mapping as a decision gate |
| **Grade 10 → 11 workload collision** | MEDIUM | Analysis sits in December break. School wins |
| **Results are null** | MEDIUM | All five questions are framed so a null answer is reportable, and the pre-registration makes the negative result read as a finding |
| **Scope creep into cooking or site-building** | MEDIUM | Cook-alongs capped at 8 and now serve RQ4 — which makes creep *more* tempting, not less. Re-read §11 when it starts feeling like the deliverable |
| **Journal rejection** | LOW-MED | arXiv preprint, Zenodo DOI, and two public datasets already satisfy the honours entry. CHR 2028 remains open |
| **Advisor unavailable** | LOW | Project is completable without one |

---

## 23. The Next 30 Days

| # | Action | Cost | Why it blocks everything else |
|---|---|---|---|
| 1 | **Path migration and audit.** Fix every hardcoded `~/Desktop/flavormap` reference, prefer repo-relative paths, confirm Docker and the test suite still work | 2 hrs | Nothing else can proceed from a broken working directory |
| 2 | **Commit the week of uncommitted work.** Coherent separate commits, honest messages, `.gitignore` verified, personal data checked, pushed | 2 hrs | A week of uncommitted work is a week of authorship evidence that does not exist. The first commit date cannot be created retroactively |
| 3 | **Checkbox extraction test on 10 PDFs.** Can `endangerment_level` and `dish_category` be recovered from the Wingdings glyphs? | 3 hrs | **RQ5 lives or dies here.** Knowable this week, and cheap to know |
| 4 | **Cook the origin dish** with the family member. Photograph the mise en place. Write down what actually happens, including what contradicts the remembered version. Commit with the real date | 2 hrs | The one item that cannot be reconstructed later |
| 5 | **Book both fieldwork trips** into the family calendar with real dates | 1 hr | Four of five questions depend on these two weekends. Unbooked trips are the top risk in §22 |

Then, in the same month: update the five research questions everywhere in the repo; commit
`docs/hypotheses.md` with dated predictions for all five **before any analysis**; write the interview
protocol and the Thai consent form; and start `CREDITS.md`, `LIMITATIONS.md`, and `decisions.md` as
living documents that get appended to all year rather than written at the end.

---

## 24. Application Language & the TunDee Pairing

**Common App activity entry (150 characters):**

> *"Compared Thai regional food across government records, web recipes, and 12 home kitchens. Open dataset + paper."* — 113 characters.

**Interview answers to prepare.** "How much help did you have?" is answered by opening
`docs/decisions.md`. She should be able to name the advisor, the sister, the parents, and the Claude Code
arrangement with bounded roles in twenty seconds without hesitation. Hesitation is what costs.

### The connective tissue with TunDee — say this in every interview

> **The data that exists about a population is not the truth about that population,
> and the gap widens with distance from the centre.**

TunDee closes that gap in scholarship access. FlavorMap measures it in food. One is intervention, one is
measurement, and together they are a coherent research identity rather than two impressive hobbies.

**Put that sentence, verbatim, in both projects' public materials** — the FlavorMap README and the TunDee
site. If a reader meets the same claim twice in two domains, the identity demonstrates itself, and she
never has to assert in an essay that she has one. Asserted, it reads badly; demonstrated, it reads as
inevitable.

**RQ1 and RQ3 sharpen the pairing.** A government list of three dishes per province, and twelve cooks
naming things that are on no list, is the same picture as the scholarship-access gap in a different
domain. That is the slide, and it is the answer to "why does this matter?"

**One caution on weighting.** If FlavorMap is the weaker of the two projects, it should be the supporting
item — one strong activity entry plus a mention inside the TunDee essay — not a second full-strength
narrative competing for the same space. And keep the sister's contribution visible: two named teenage
siblings shipping a Thai-language public tool is a materially harder story to disbelieve than one student
with two impressive projects.

---

> **The test this document is built around.** Hand the finished project to someone who has never met her
> and ask one question: **can you picture a Grade 10 student doing this on weekends?**
>
> With the repository history, six build-log posts, twelve interviews conducted in Thai in two provinces,
> eight dishes cooked and logged against the pipeline, a named credit ledger, a pre-registration written
> before the analysis, two hundred documented decisions, and a limitations register she wrote before
> anyone asked — the answer is yes. The technical work never changed between v1 and v4. Only the evidence
> did, and the evidence was the part that was missing.
