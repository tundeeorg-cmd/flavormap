# FlavorMap · แผนที่รสชาติ
## The Project Bible — v5, Research Questions v2 Edition

**Computational Geography of Thai Cuisine** · Three registers of the same cuisine
ISB Bangkok · Grade 10 → Grade 11 · Pillar 2 of the Future Leader Plan · **Supersedes v4** · 5 November 2026

---

> **Why this version exists.** v4 rebuilt the project around the balanced government corpus and three
> registers. Since then four things changed on the ground: fieldwork moved to **Nakhon Ratchasima and
> Buri Ram**; the Korat forms carry no usable endangerment level, which left the old RQ5 resting on three
> Buri Ram dishes; the commercial register grew to **three portals** (Kapook, Sanook, MThai) plus two state
> promotional sources (TAT, Ministry of Culture); and the submission plan became concrete (DH2027, JCSSE,
> one dataset venue, iSAI-NLP). v5 rewrites the research questions to match, adds the statistics a
> data-science reader expects, and replaces the fragile RQ5 with a nationwide question.
>
> The organising idea — **three registers, and the gaps between them are the findings** — is unchanged.

> **The structural position, restated.** v4 made four of five questions depend on fieldwork. v5 reduces
> that to **two** (RQ3 fully; RQ1's three-way comparison and RQ2's validation partly). RQ4 depends only on
> the researcher, and the new RQ5 depends only on data already collected. The degraded-mode plan (§7)
> is now a stronger paper than it was in v4.

---

## Contents

1. What changed (v4 → v5, and v3 → v4)
2. The Fingerprints Problem — retained
3. The Origin Story — still has an open bracket
4. PDPA and Research Ethics — new, non-negotiable
5. The Three Registers
6. The Five Research Questions — v2
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
17. The Papers — venues and structure
18. OpenFlavorTH — two datasets, not one
19. The Public Artifact
20. The Credit Ledger
21. Timeline
22. Risk Register
23. The Next 30 Days
24. Application Language & the TunDee pairing

---

## 1. What Changed

### v4 → v5 (5 November 2026)

| Area | v4 | v5 | Reason |
|---|---|---|---|
| **RQ1** | Register distance only | Register distance **+ permutation baseline + bootstrap CIs** | With 3 official dishes per province, a distance means nothing without a chance baseline |
| **RQ4** | "Can you cook a dish from the normalised dataset?" | **A test of the field's ingredient-list standard** — can you cook the dish without the steps, and what is lost? | Same method; framing now explains *why* the dataset holds only ingredient lists (copyright, comparability, field convention) |
| **RQ5** | Cooks vs. state on endangerment (dish-matched, fieldwork) | **Is the internet preserving or abandoning endangered dishes?** Web presence of state-endangered vs. still-transmitted dishes, nationwide | Korat forms give no usable level; old RQ5 rested on 3 Buri Ram dishes. New RQ5 uses ~157 extracted levels and the commercial corpus. Q10 stays as a qualitative check |
| **Fieldwork provinces** | Nakhon Ratchasima + Buri Ram | **Nakhon Ratchasima + Buri Ram** (HD-32) | Korat is local; only Buri Ram needs travel. Cost: two neighbouring Isaan provinces, no North contrast — stated as a limitation |
| **Commercial register** | ~400–600 scraped recipes, ≥4 sources | **Kapook (1,360) + Sanook + MThai** collected; Wongnai/Cookpad frozen until after 13 Dec | Volume target already exceeded; constraint is labels and balance |
| **State promotional sources** | — | **TAT and Ministry of Culture** pages collected; register assignment is a decision (HD-register) | Possible "other state lists" for RQ3, or reference only |
| **Official register** | 231 PDFs | 231 PDFs + **Nakhon Nayok by manual transcription** (`extraction_method = manual`) | One province had no extractable text layer |
| **Venues** | JCA primary, CHR 2028, arXiv | **DH2027 (20 Nov) · JCSSE 2027 (22 Jan) · LaTeCH-CLfL 2027 or ICWSM 2027 (Jan) · iSAI-NLP 2027 (Aug)** · full paper to arXiv + JCA by 31 Mar 2027 | Concrete plan; see §17 |
| **Impact** | Site + quiz | **Impact track I1–I7** (PyThaiNLP lexicon, endangered-dish list to creators, policy brief, Thai article, community give-back, school kit, academic partnership) | Moves the project from measuring gaps to helping close them |
| **Timeline** | §21 calendar | **`FlavorMap_Timeline_2027.md` (v4) is authoritative**; §21 summarises it | One source of truth for dates |

### v3 → v4 (retained for the record)


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

This is the organising idea of the project. The same cuisine is documented three times by three different actors
with three different motives, and the gaps between them are the findings.

| Register | Source | Size | Represents | Selection pressure |
|---|---|---|---|---|
| **Official** | 231 government PDFs, `food.culture.go.th` | 3 per province × 77 | What the state selects to represent a province | Cultural policy, heritage framing, provincial pride |
| **Commercial** | Kapook, Sanook, MThai recipes | 1,360 Kapook + Sanook + MThai (counts per T1.13a) | What the urban internet cooks and publishes | SEO, photographability, ingredient availability in Bangkok |
| **Domestic** | 12–15 interviews, Nakhon Ratchasima + Buri Ram | ~40–60 dishes | What people actually cook at home | Season, cost, what grows nearby, habit |

Each register is a *sample with a bias*, and each bias is different. No register is the truth. The
comparison is the instrument.

**Every recipe in the database carries a `register` column.** This is the single most important schema
decision in the project and it must be present from the first load, not retrofitted.

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

**Status (Nov 2026).** Endangerment level was extracted for ~157 of 231 forms. The six fieldwork-province
readings must be verified by eye (T0.4); Korat's forms carry no usable level. This is why v5's RQ5 uses the
level **nationwide** against the web corpus rather than against cooks in two provinces.

### State promotional sources (new in v5)

TAT "local food by province" pages and Ministry of Culture / provincial culture office pages were
collected on 7 Oct 2026. They are state records but not the DCP forms, and many are dish lists rather than
recipes. Their role is a decision (HD-register): (a) merge into official — breaks the 3 × 77 balance;
(b) a separate *state-promotional* register usable in RQ3; (c) reference only, for dish-name matching and
province hints. They never enter `recipes` before an ETHICS.md row and that decision exist.

---

## 6. The Five Research Questions · v2 (5 November 2026)

Each question is stated in a short form (site, interviews, slides) and a full form (paper), in Thai and
English, with its **transferable claim** — what a reader outside Thai food studies takes away. The
canonical table lives in `FlavorMap_Research_Questions.md`; this section adds method, outputs and roles.

### Roles in the set

| RQ | Role | Data science interest | Conference fit | Focus order | Value of the answer |
|---|---|---|---|---|---|
| **RQ1** | **Headline** — the spine of every paper | 2 | **1** | **1** | 2 |
| **RQ2** | **Method contribution** — a new measure | **1** | 3 | 3 | 5 |
| **RQ3** | **Authorship evidence** — fieldwork only she can do | 5 | 4 | 5 | 3 |
| **RQ4** | **Validation** — tests the field's standard | 3 | 2 | 2 | 4 |
| **RQ5** | **Public stake** — preservation | 4 | 5 | 4 | **1** |

(1 = highest.)

### RQ1 — State, market, kitchen: real difference or chance?

| | |
|---|---|
| **Short (TH)** | อาหารประจำจังหวัดที่รัฐเลือก สูตรบนเว็บ และอาหารที่คนในจังหวัดทำกินจริง ต่างกันจริง หรือแค่บังเอิญ? |
| **Short (EN)** | How different are the dishes the state chose to represent each province, the recipes on the web, and what people in that province actually cook, and are the differences real or just chance? |
| **Full (EN)** | How far apart are the ingredient profiles of the same province across three sources — the Department of Cultural Promotion's records, recipes on food websites, and the dishes home cooks in that province actually make? Distance is cosine distance between ingredient profiles within each province. Are these differences larger than expected by chance? We compare against a baseline built by randomly shuffling province labels (a permutation test) and report bootstrap confidence intervals. |
| **Method** | Normalised ingredient vectors per region (HD-37; province rows where they exist) per register → pairwise cosine distance → permutation test (HD-44, revised 2026-11-06): primary, register-label shuffle within each region, 9,999 shuffles, empirical p, Holm-adjusted across regions; secondary, region-label shuffle within each register → 95% bias-corrected bootstrap CI (9,999 resamples of recipes within region) → robustness: commercial side per source. The primary test was chosen after trial results were seen (HD-44). Optional second test: a classifier predicting region from ingredients, compared across registers. |
| **Output** | Distance table with n, CI and p; Figure 1 (register triangles for Korat and Buri Ram; two-register lines elsewhere); Figure 6 heatmap. |
| **Needs fieldwork** | Only for the three-way comparison in Korat and Buri Ram. Official↔commercial runs nationwide without it. |
| **A NO looks like** | Registers differ no more than chance. A real result: it would mean state and web records are fair proxies for home cooking. |
| **Transferable** | **Cultural corpora carry the selection pressure of whoever assembled them**, and the effect can be tested against chance. |

### RQ2 — Identity from what's used, or what's refused?

| | |
|---|---|
| **Short (TH)** | อาหารแต่ละภาคมีเอกลักษณ์เพราะวัตถุดิบที่ใส่ หรือเพราะวัตถุดิบที่คนในภาคไม่ใส่? |
| **Short (EN)** | Does a region's food identity come from the ingredients it uses, or from the ingredients it refuses to use? |
| **Full (EN)** | Is each province's culinary distinctiveness driven by ingredients it uses more than the national average, or by ingredients it uses less or never uses? Does this decomposition agree with what home cooks say "we would never put in"? |
| **Method** | Decompose each province's distance from the national mean into presence-driven and absence-driven components (definition = HD-13, hers). Validate the absence component against stated absences from interview Q9. |
| **Output** | Figure 2 (presence vs. absence scatter, diagonal = balanced); `stated_absences.csv`. |
| **Needs fieldwork** | For validation only; without it absences are inferred (weaker, reportable). |
| **A NO looks like** | Distinctiveness is symmetric everywhere. Still a fact nobody had. |
| **Transferable** | **Every standard distinctiveness measure (TF-IDF, log-odds, Zeta) is a presence measure; absence is structurally invisible.** |

Interview Q9, asked as written: **“อะไรที่คนจังหวัดอื่นใส่ในจานนี้ แต่บ้านเราไม่มีวันใส่?”**

### RQ3 — What does the state's list leave out?

| | |
|---|---|
| **Short (TH)** | มีอาหารหรือวัตถุดิบอะไรบ้างที่คนในจังหวัดทำกินจริง แต่ไม่อยู่ในรายชื่ออาหารของรัฐ? |
| **Short (EN)** | Which dishes and ingredients do people actually cook that are missing from the state's list? |
| **Full (EN)** | To what extent do the dishes and ingredients that home cooks in Nakhon Ratchasima and Buri Ram report cooking appear in the state's three-dishes-per-province list and in web recipes, and which appear in neither? |
| **Method** | Set comparison at dish level and ingredient level; raw counts, never percentages; optionally also against TAT / m-culture lists if HD-register option (b). |
| **Output** | Figure 3 (stacked bars: in official / in commercial / in neither); table of "neither" items. |
| **Needs fieldwork** | Entirely. |
| **Framing** | An **existence claim** ("6 of 6 cooks in Buri Ram named an ingredient no register associates with the province"), never a ranking of provinces. |
| **Transferable** | **Heritage designation is a sampling procedure with a bias, and the bias is measurable.** |

### RQ4 — Without the steps, can you still make the dish?

| | |
|---|---|
| **Short (TH)** | นักวิจัยศึกษาอาหารจากรายชื่อวัตถุดิบอย่างเดียว ถ้าไม่มีขั้นตอนการทำ เราจะยังทำอาหารจานนั้นออกมาได้จริงไหม? |
| **Short (EN)** | Researchers study food from ingredient lists alone. Without the cooking steps, can we still actually make the dish? |
| **Full (EN)** | Does the ingredient-list representation of recipes, standard in computational food research, retain enough knowledge to cook the dish, and what information is lost (quantities, order, technique, ingredient specificity)? We test this by cooking eight dishes from state, web and home-cook sources. |
| **Why ingredient lists** | (1) recipe prose is copyrighted and is never stored or redistributed (§4); (2) lists can be normalised and compared across thousands of recipes, steps cannot; (3) the field's convention since Ahn et al. 2011. Nobody has checked whether the convention reconstitutes a meal. |
| **Method** | Cook 8 dishes from the cleaned ingredient list only (≥2 official, ≥2 the pipeline handles badly, ≥1 from an interview). Score each information class 0–2 (survived / degraded / lost); recognisability verdict; one sensory sentence. Optional: give a language model the list, ask for steps, compare with the original — the model is the object tested, never the analyst. |
| **Output** | Figure 4 fidelity matrix; `cook_along_log.csv`. |
| **Needs** | Only the researcher. |
| **Transferable** | **Tokenisation and canonicalisation silently delete information, and nobody in computational food studies measures how much.** |

### RQ5 — Is the internet preserving or abandoning endangered dishes?

| | |
|---|---|
| **Short (TH)** | อินเทอร์เน็ตกำลังช่วยรักษา หรือปล่อยให้เมนูพื้นบ้านที่ใกล้สูญหายหายไป? |
| **Short (EN)** | Is the internet helping to preserve endangered local dishes, or letting them disappear? |
| **Full (EN)** | How widely are recipes for dishes the state classifies as endangered published on food websites, compared with dishes the state classifies as still being passed on? |
| **Why it matters** | The internet is where younger people now learn to cook. A dish with no online recipe has no place to be learned outside the family — so absence online accelerates loss. Presence online may mean the state label is outdated or the web is preserving it. Both are findings. |
| **Method** | Match official dish names to commercial recipes (exact → fuzzy → hand-checked sample; report matching precision/recall; rules = HD-match). Compare web presence of endangered vs. still-transmitted dishes (counts, rate, test controlling for region). Q10 interview answers in Buri Ram as a qualitative check. |
| **Output** | Figure 5 (web presence by official endangerment level); `endangered_web_presence.csv` — the list used by impact tasks I2 and I3. |
| **Needs fieldwork** | No. |
| **A NO looks like** | No difference in web presence — the web neither preserves nor neglects endangered dishes. |
| **Transferable** | **Official risk lists of cultural practice can be checked against where practice is actually transmitted today.** |

### Read together

The same cuisine documented three times produces three different objects, beyond chance (RQ1); identity
lives in refusal as much as in addition (RQ2); official selection leaves measurable gaps (RQ3); the
field's standard representation deletes information nobody has quantified (RQ4); and the state's own
risk list can be checked against where cooking is learned today (RQ5).

For applications: **RQ1 is the story, RQ2 shows original method, RQ4 shows critical thinking, RQ5 shows
impact, RQ3 shows she did it herself.**

---

## 7. Feasibility Audit

| RQ | Verdict | Real cost | Constraint and mitigation |
|---|---|---|---|
| **RQ1** | Yes | ~22 h analysis | Official↔commercial runs nationwide now; three-way only in Korat and Buri Ram. Commercial province labels are sparse → region-level fallback (HD-labelling). Permutation + bootstrap add ~2 h. |
| **RQ2** | Yes | ~18 h (15 thinking, 3 coding) | Cost is definitional. Without Q9 answers, absences are inferred — weaker but reportable. |
| **RQ3** | **Fieldwork-only** | ~12 h + fieldwork | No interviews, no question. Comes almost free if Q9/Q10 and "what do you cook" are asked every time. |
| **RQ4** | Yes | ~8 h + 8 cooking sessions | Fully under her control. Needs lexicon v1.0 first. |
| **RQ5** | **Yes (new)** | ~12 h | Uses data already collected. Risk is dish-name matching quality — measured, not assumed. |

**Total analysis ≈ 72 h. Normalisation (lexicon) ≈ 50 h. Fieldwork ≈ 40 h + one Buri Ram trip** (Korat is local).

### The degraded-mode plan

If fieldwork falls short (<10 interviews by 6 Dec), the paper becomes: **RQ1 (two-register, nationwide,
with baselines) + RQ2 (inferred absences) + RQ4 + RQ5.** Only RQ3 is lost. That is a stronger fallback
than v4's, and it is decided now rather than in December.

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

**Status (Nov 2026).** Collected: **Kapook** (2,702 pages → 1,360 recipes, loaded), **Sanook** and **MThai**
(collected 7 Oct, loading via timeline tasks T1.13a–e). The ~400–600 target is exceeded; the constraints now are
**province labels** (Kapook had none) and **balance across sources** (HD-balance). Wongnai, Cookpad TH and
Krua.co are frozen until after the 13 Dec data freeze. TAT and Ministry of Culture pages are state sources,
handled under HD-register (§5).

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

**12–15 interviews across two provinces — Nakhon Ratchasima and Buri Ram** (HD-32). Six per province minimum. 60–90 minutes each.

**Why these two.** Both Isaan, both far from the commercial register's Bangkok centre of gravity.
Korat is local, so its interviews happen on weekends at home; Buri Ram needs one trip. **Cost:** two
neighbouring provinces give no North–Isaan contrast — stated in the limitations register. If the trip
fails, Korat alone still supports RQ3 as an existence claim.

**Scope.** Depth beats spread. One 90-minute interview with photographs, a cooked dish, and a follow-up
beats four rushed 40-minute conversations. Four interviews per province supports nothing; six supports a
specific, defensible sentence.

**The protocol.** All eight questions from v2 retained verbatim, including Q3 (substitutions — collected
even though the graph analysis is out of scope) and Q8 ("what do restaurants get wrong about it?"). Plus
Q9 from §6 (stated absences, feeding RQ2), and Q10 (a qualitative check for RQ5):

> **“จานนี้ยังมีคนทำอยู่ไหม? ใครทำ? คนรุ่นใหม่ทำเป็นหรือเปล่า?”**
> *Does anyone still make this? Who? Do younger people know how?*

Ask Q10 about the three dishes the government listed for that province. Answers are stored in a separate
table (`dish_status_reports`, HD-Q10) so a Q10 answer never creates a domestic recipe.

**Fields to capture:** district as well as province; ingredient acquisition mode, using the same four
categories as the government forms so the registers are directly comparable.

**Ethics and consent per §4** — unchanged and non-negotiable.

---

## 11. Data Stream 4 — Cook-Alongs, Promoted to a Research Question

**Eight dishes.** In v3 this was narrative colour. Since v4 it is RQ4; in v5 it is framed as a test of the field's ingredient-list standard.

**Protocol.** Cook from the **cleaned dataset's** ingredient list, not the original source page — the
point is to test the pipeline, not the recipe. For each dish log:

- what was missing from the normalised list that the original had
- what had to be substituted and why
- what the normalisation destroyed: quantities, order, technique, ingredient specificity
- whether the result was recognisable as the dish
- one sentence of sensory description
- a 0–2 score for each information class (quantities, order, technique, specificity, completeness)

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
| 1 | **Register triangle** (RQ1) | — | — | One triangle per province; vertices = official / commercial / domestic; edge length = ingredient-profile distance. Small multiples for Korat and Buri Ram at full size, all others as a two-register line with bootstrap CI. Mark distances that beat the permutation baseline. The paper's signature figure. |
| 2 | **Distinctiveness decomposition** (RQ2) | presence-driven | absence-driven | One point per province, diagonal = balanced. Above the line = defines itself by refusal. A chart type reviewers have not seen. |
| 3 | **Official-record overlap** (RQ3) | province | count | Stacked bars: dishes named by cooks that are in the official three / in the commercial register / in neither. The "neither" segment is the finding. |
| 4 | **Pipeline fidelity** (RQ4) | dish | information class | Matrix, 8 dishes × {quantities, order, technique, specificity, completeness}. Cell = survived / degraded / lost. Reads as a table but functions as a figure. |
| 5 | **Endangered dishes online** (RQ5) | official endangerment level | share of dishes with ≥1 web recipe | Bars with counts and 95% CIs; annotate the endangered dishes with zero online recipes. The list behind it feeds the impact track. |
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

**Is the difference real? (v5; test revised 2026-11-06, HD-44).** The unit is the region (HD-37). For
each region, shuffle the official/commercial labels across the region's recipes 9,999 times
(register-label shuffle, the primary test), recompute the distance, and report where the observed value
falls (empirical p-value), Holm-adjusted across the four regions. As a secondary test, shuffle region
labels within each register. Report 95% bias-corrected bootstrap confidence intervals by resampling
recipes within each region (9,999 resamples). The primary test was chosen after trial results were seen;
the paper says so. Repeat the commercial side per source (Kapook, Sanook, MThai) as a robustness check.
Report a null result plainly.

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

### 14.4 Overlap (RQ3)

A set comparison, not a model. Report raw counts, not percentages — with n≈6 per province a percentage
misleads and a count is honest.

### 14.4b Web presence of endangered dishes (RQ5, new in v5)

1. **Dish-name matching** (HD-match): exact match after normalisation → fuzzy match above a threshold →
   hand-check a random sample of ≥100 candidate pairs; report precision and recall.
2. **Presence:** for each official dish, number of matching commercial recipes and a 0/1 "online" flag.
3. **Comparison:** endangered vs. still-transmitted dishes — counts, rates, and a test that controls for
   region (e.g. stratified comparison or logistic regression with region).
4. **Caveat:** endangerment is self-reported by form submitters; say so beside every result.

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
| **Fieldwork is partly load-bearing** | **MEDIUM · v5** | RQ3 depends entirely on 12–15 interviews; RQ1's three-way comparison and RQ2's validation partly. If fieldwork fails, the paper keeps RQ1 (two-register), RQ2 (inferred), RQ4 and RQ5 |
| **Fieldwork n = 12–15** | HIGH | Presented as an existence demonstration and qualitative validation, never as a representative sample and never as a basis for ranking provinces. Two provinces at n≈6, stated as such |
| **Official register is 3 dishes per province** | HIGH · NEW | A sample of three from a population of hundreds, selected by a committee with cultural-policy motives. This is the object of study in RQ3, but it also limits what RQ1 can conclude |
| **Domestic register covers 2 of 77 provinces** | HIGH | RQ1's three-way comparison is only possible for Nakhon Ratchasima and Buri Ram — two neighbouring Isaan provinces, with no North contrast. All other provinces are two-register. Do not present a national three-register map |
| **Register sample sizes are unequal** | MEDIUM · NEW | 3 vs. ~6 vs. ~6. Distance measures are sparsity-sensitive. Report n alongside every distance |
| **Commercial corpus skews urban and Central Thai** | HIGH | Retained from v2 |
| **Normalisation involves judgement calls** | MEDIUM | Retained — and now partly *measured*, by RQ4 |
| **Recipes are not consumption** | MEDIUM | Retained. A documented recipe is not evidence of what people eat |
| **No temporal dimension** | MEDIUM | The corpus is a single time-slice. She can say traditions are undocumented; she cannot say how fast they are vanishing. RQ5 reports *stated* endangerment, not measured rate of loss. Catch this before it reaches an essay |
| **Endangerment level is self-reported** | MEDIUM | The government field reflects the submitter's assessment, not an independent survey. RQ5 compares it with web presence; it is not a measured rate of loss |
| **Dish-name matching error (RQ5)** | MEDIUM · v5 | Thai dish names vary. Precision/recall of matching reported from a hand-checked sample |
| **Commercial register = three portals** | MEDIUM · v5 | Kapook, Sanook, MThai; syndicated duplicates removed (HD-dedup); per-source robustness reported |
| **Mixed provenance in the official register** | LOW · v5 | Nakhon Nayok transcribed by hand (`extraction_method = manual`); sensitivity check excludes it |
| **Dish-category taxonomy** | MEDIUM | Categories are constructed, not natural. Publish the taxonomy and inclusion rules so others can disagree with specific assignments |
| **Single annotator** | LOW-MED → **RESOLVED** | 100 recipes independently double-labelled; Cohen's κ reported. A few hours of a second Thai reader's time — cheapest credibility in the project |
| **Sites excluded for ToS reasons** | LOW | Retained |

---

## 17. The Papers — Venues and Structure

| Priority | Venue | Paper | Deadline | Conference | Est. chance | Focus |
|---|---|---|---|---|---|---|
| 1 | **DH2027** | Short paper, RQ1 + design (1,000–1,250 words) | **20 Nov 2026** | 28 Jun–3 Jul 2027, Galway | ~40–55% | Core |
| 2 | **JCSSE 2027** | Technical: extraction, PDPA at parse time, normalisation, RQ4 | 22 Jan 2027 | 16–18 Jun 2027, Chiang Rai | ~60–75% | Core, safest |
| 3 | **LaTeCH-CLfL 2027** | Dataset paper (OpenFlavorTH) | ~early Jan 2027 | ~spring 2027 | ~40–50% | Pick one (recommended) |
| 4 | **ICWSM 2027** | Dataset paper | 15 Jan 2027 | ~May–Jun 2027, Edinburgh | ~20–30% | Pick one (alternative) |
| 5 | **iSAI-NLP 2027** | The lexicon as a Thai NLP resource | ~Aug 2027 | ~Nov 2027, Thailand | ~55–70% | Core |
| 6 | **JADH 2027** | Research story | ~spring 2027 | ~Sep 2027, Japan | ~50–65% | Backup if DH declines |
| — | **Full paper** | RQ1–RQ5 (~4,600 words) | 31 Mar 2027 | arXiv + Journal of Cultural Analytics | — | Core |

Chances are estimates, not published rates. ECTI-CON (same paper as JCSSE) and CHR 2028 (too late for
applications) are skipped. **Overlap rule:** the dataset paper owns the dataset, JCSSE owns the
extraction method, the full paper owns the findings; each cites the others.

### Full paper structure — ~4,600 words

| Section | Words | Notes |
|---|---|---|
| Introduction | 600 | Opens with the kitchen. The origin story **is** the introduction |
| Related work | 500 | Ahn et al. 2011; computational gastronomy; Thai food studies; critical dataset studies. **State the disagreements:** distinctiveness measures are blind to absence; nobody validates the ingredient-list standard by cooking |
| Data — the three registers | 900 | Sources, PDPA, scraping ethics, cleaning, lexicon, fieldwork protocol |
| Methods | 700 | Register distance with permutation baseline and bootstrap; RQ2 decomposition; cook-along scoring; dish-name matching |
| Results | 1,100 | Negative results at full weight; compare with pre-registered predictions |
| What the record leaves out | 400 | RQ3 — two provinces, ~12 cooks, the "neither" table |
| Limitations | 500 | Lifted from the live register |
| Conclusion | 300 | What next, what she would do differently |

**Authorship rules unchanged and non-negotiable:** she is first author; a faculty advisor is co-author only
for substantive contribution to design or analysis, otherwise acknowledged. The sister is acknowledged by
name for visualisation and design.

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
| `endangered_web_presence.csv` · v5 | Official dish, province, region, official endangerment level, number of matching web recipes, online flag, match method. The RQ5 evidence and the list behind impact tasks I2/I3 |
| `dish_status_reports.csv` · v5 | Q10 answers (anonymised): dish, province, still made?, who makes it, do younger people know? Qualitative check for RQ5 |
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
- Propose the lexicon as a PyThaiNLP corpus (impact task I1) — one honest proposal, not a campaign
- Version it: v1.0 at submission, v1.1 if a second fieldwork round lands
- **Report the real download number at application time.** "340 downloads" is far more credible than "widely used"

---

## 19. The Public Artifact

Thai-first, phone-first, shared through Line. What gets built: the map (tap a province, see its three
dishes, its distinctive ingredients, and — for Nakhon Ratchasima and Buri Ram — the register triangle); the province quiz
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

**`FlavorMap_Timeline_2027.md` (v4) is the authoritative plan** — task IDs, owners, done-when tests,
gates and the impact track. This section is a summary.

| Window | Main work | Output |
|---|---|---|
| **Now → 20 Nov 2026** | Lexicon to ~150 entries; load Sanook/MThai; labelling decision; preliminary RQ1 with permutation + bootstrap; Korat interviews begin | **DH2027 submitted** |
| **21 Nov → 13 Dec** | Korat + Buri Ram interviews (12); lexicon to ~400 with glosses; cook-alongs 1–4; second annotator; dish-category taxonomy | **Data freeze 13 Dec** |
| **14 Dec → 22 Jan** | Cook-alongs 5–8; RQ4 table; RQ2 definition (HD-13); dataset release; JCSSE + dataset paper | **Datasets public; JCSSE + LaTeCH/ICWSM submitted** |
| **23 Jan → 31 Mar** | RQ1–RQ5 full analysis (RQ5 matching); figures 1–7; full paper; mentor review | **arXiv + journal submission** |
| **Apr → Aug 2027** | Camera-ready; talks; site with sister; impact track I1–I7 (any order, as soon as each prerequisite exists) | **Presentations Jun–Jul** |
| **Aug → Nov 2027** | iSAI-NLP lexicon paper; applications | **Applications with real download counts** |

**School always wins.** Exam weeks are zero-hour weeks.

---

## 22. Risk Register

| Risk | Severity | Mitigation |
|---|---|---|
| **Fieldwork falls short** | **MEDIUM** · was HIGH in v4 | Only RQ3 is lost entirely. Korat is local; one Buri Ram trip. Degraded mode (§7): RQ1, RQ2, RQ4, RQ5 |
| **Endangerment readings wrong** | MEDIUM · v5 | Extracted for ~157 of 231 forms; verify a hand-labelled sample (T2.8) and report accuracy. RQ5 v5 uses the level nationwide, so no single province is decisive |
| **DH2027 deadline (20 Nov)** | **HIGH · v5** | Lexicon ≥150 entries + preliminary RQ1 by 8 Nov; if not, DH reports method + region-level descriptives |
| **Dish-name matching too noisy (RQ5)** | MEDIUM · v5 | Hand-checked sample; report precision/recall; restrict to high-confidence matches if needed |
| **Data collected before an ethics check** | MEDIUM · v5 | Sanook/MThai/TAT/m-culture collected 7 Oct: dated retrospective audit; exclude any source whose terms forbid reuse |
| **Buri Ram trip slips** | MEDIUM · v5 | Keep the 13 Dec freeze; Korat alone supports RQ3 as an existence claim |
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

## 23. The Next 30 Days (from 5 November 2026)

| # | Action | Owner | By | Why it blocks everything else |
|---|---|---|---|---|
| 1 | **Confirm Phase 0 and source loading are done** (parser fix merged, backups, 30 PDFs + Nakhon Nayok loaded, Sanook/MThai inventoried with ethics rows) — run the master prompt; it reports status | Claude Code | 7 Nov | Every analysis reads from this database |
| 2 | **Lexicon to ≥150 entries covering ≥80% of mentions** (HD-6 rules first) | Bo | 8 Nov | RQ1 cannot run without it |
| 3 | **Labelling decision** (province vs. region) + preliminary RQ1 with permutation and bootstrap; Figure 6 | Bo → Claude Code | 8 Nov | DH Section 5 |
| 4 | **Write and submit DH2027** — mentor review ~10–12 Nov | Bo | **20 Nov** | First deadline |
| 5 | **Pre-registration** in `docs/hypotheses.md` for RQ v2 (dated amendment if v1 was committed) — before the first interview | Bo | before interview 1 | Makes results credible |
| 6 | **Cook the origin dish**; write it up the same day | Bo + family | before DH draft | The DH opening depends on it |
| 7 | **Book the Buri Ram weekend and the Korat interviews** | Bo + parents | 10 Nov | RQ3 and the three-way RQ1 |

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
