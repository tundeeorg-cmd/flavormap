# FlavorMap — Implementation Timeline 2026–2027

**Version:** v2 · 6 October 2026 · **Supersedes:** v1 of this file and Bible v4 §21 (timeline) and §23 (next 30 days)
**Basis:** `docs/STATUS_2026-10.md` audit (repo `main` at `0aa08a5`; overall ≈18% complete)
**Repo:** `~/Desktop/G.9/flavormap` · GitHub `tundeeorg-cmd/flavormap` · DB: Docker Postgres 15 + PostGIS, host port 5433

> **Goal.** Three conference submissions by **22 Jan 2027** (DH2027, ICWSM 2027, JCSSE 2027), the full research
> paper by **31 Mar 2027**, both OpenFlavorTH datasets public by **15 Jan 2027**, and all three presentations in
> **Jun–Jul 2027**.

---

## 0. How to use this file

This is the operating plan for both the researcher (Bo) and Claude Code. Every task has an ID, an owner, its
dependencies, the files it touches, and a **done-when** test. A task is not done until its done-when is true and
committed.

### Owner tags

| Tag | Who | Meaning |
|---|---|---|
| **[BO]** | Researcher | Analytical judgment, fieldwork, cooking, writing. Cannot be delegated |
| **[CC]** | Claude Code | Machinery: code, migrations, tests, scripts, figures from decided specs, formatting |
| **[BO→CC]** | Both | Bo decides first (logged in `docs/decisions.md`), then Claude Code implements |
| **[FAM]** | Parents | Travel, chaperoning, introductions. Never interviews, analyses or writes |
| **[MEN]** | Mentor | Review and advice → acknowledgement, not authorship, unless substantive design/analysis contribution |

### Rules Claude Code must follow on every task

1. **Read this file, `CLAUDE.md`, and the relevant `docs/decisions.md` entry before starting.**
2. **Stop at every decision gate (HD-x).** If a task needs a judgment that has no *decided* entry in
   `docs/decisions.md`, write the options with evidence into a new entry marked `OPEN`, then stop and report. Never
   pick an option on Bo's behalf. Never write analysis code that hard-codes an undecided choice
   (the audit found `ACQUISITION_HINTS` doing exactly this — see T1.12).
3. **PDPA is non-negotiable.** Personal data never reaches a table, CSV, Parquet, log or dump.
   `tests/test_pdpa.py` and `tests/test_interview.py` must pass before every commit that touches ingest.
4. **Never invent numbers.** Every number in a paper draft, README or dataset card must come from a committed
   script or query whose path is cited next to it. Placeholders are written `[TBD: source]`.
5. **Green before commit:** `pytest -q`, `ruff check`, `mypy` all pass. New behaviour gets a test.
6. **Small, honest commits.** One logical change per commit, conventional-commit prefixes
   (`feat:`, `fix:`, `docs:`, `data:`, `test:`). No work left on side branches — merge or delete within the week.
7. **Migrations are append-only** (next is `025`). Never edit an applied migration.
8. **Raw data stays raw.** `data/raw/` is read-only to pipelines and never committed or published.
9. **Back up after any data change:** `make db-dump`, then `make backup TO=<off-laptop path>`.
10. **Repo-relative paths only.** No `~/Desktop/...` in code.

---

## 1. Submissions

| Venue | Deadline | Paper | Contribution | Presentation |
|---|---|---|---|---|
| **DH2027** | **Fri 20 Nov 2026**, 23:59 AoE | Short paper, 1,000–1,250 words (captions count; table contents and references don't). English. Not anonymous. AI-use disclosure required | Three-registers framing; first official-vs-commercial results; fieldwork design. Theme fit: *Creativity* (cooking as method) | 28 Jun – 3 Jul 2027, University of Galway, Ireland. ~10-min talk. Notification Feb 2027 |
| **ICWSM 2027** | **Fri 15 Jan 2027** (Round 3), 23:59 UTC-12 | Dataset paper | OpenFlavorTH-recipes + OpenFlavorTH-lexicon: collection, PDPA handling, lexicon construction, register statistics, baseline register comparison | Edinburgh, ~May–Jun 2027 (dates TBA) |
| **JCSSE 2027** | **Fri 22 Jan 2027** (Round 2) | Full technical paper (IEEE technical co-sponsor) | Pipeline: Thai PDF extraction (sara am repair, Wingdings checkbox detection), parse-time PDPA stripping, normalisation; evaluated against hand-verified ground truth; RQ4 cook-along fidelity | 16–18 Jun 2027, Mae Fah Luang University, Chiang Rai. Early registration 23 Apr; final manuscript 7 May |
| **Full paper** | **Wed 31 Mar 2027** | Research article, ~4,600 words | RQ1–RQ5 with fieldwork | arXiv preprint + Journal of Cultural Analytics |

**Fallback:** JCSSE Round 1 (Fri 27 Nov 2026) is *not* used — it collides with DH and fieldwork.

**Priority if something must be cut:** DH2027 → JCSSE → full paper → ICWSM. Drop ICWSM first.

### 1.1 Things to verify on each CFP (T1.1, by 19 Oct)

Unverified details that change the plan. Record answers in `docs/venues.md` with the date checked.

- **ICWSM:** dataset-paper page limit and template (AAAI); anonymity rules for dataset papers (can the HF link
  appear?); whether data must be public at submission or at camera-ready; required ethics/FAIR statements;
  preprint policy; exact conference dates.
- **JCSSE:** page limit, IEEE template, anonymity, whether Round 2 has a separate notification date, student
  registration fee, presentation format.
- **DH2027:** bursary scheme for students and its deadline; poster fallback if the short paper is declined.
- **All three:** minimum author age or guardian requirements; registration fees; dual-submission wording.

---

## 2. What each paper uses

| | DH2027 | ICWSM | JCSSE | Full paper |
|---|---|---|---|---|
| Official register (231 DCP PDFs) | ✓ | ✓ (if HD-3 permits) | ✓ | ✓ |
| Commercial register (Kapook) | ✓ | ✓ | ✓ (normalisation only) | ✓ |
| Domestic register (interviews) | design + status | counts only | — | ✓ |
| Lexicon | v0.3 (~150) | v1.0 (~400) | v1.0 | v1.0 |
| RQ1 register distance | two-register, preliminary | baseline stats | — | full, three-register for 2 provinces |
| RQ2 presence/absence | planned | — | — | ✓ |
| RQ3 what the record leaves out | planned | — | — | ✓ |
| RQ4 cook-along fidelity | planned | — | ✓ | ✓ |
| RQ5 endangerment agreement | planned | field description | checkbox accuracy | ✓ (Buri Ram only, see HD-RQ5) |
| Figures | Fig 6 heatmap | Fig 6, Fig 7, network | extraction tables, Fig 4 | Figs 1–7 |

**Overlap rule:** ICWSM and JCSSE are archival. ICWSM owns *the dataset*; JCSSE owns *the extraction method and its
evaluation*; the full paper owns *the findings*. Each cites the others. No paragraph is reused verbatim.

---

## 3. Critical path and go/no-go gates

```
Phase 0 lock-down ─► protocol + consent + Q10 fix ─► pre-registration (24 Oct) ─► interviews (31 Oct → 6 Dec)
                 └─► Kapook labelling decision (1 Nov) ─► lexicon 150 (8 Nov) ─► prelim RQ1 (8 Nov) ─► DH (20 Nov)
lexicon 400 (13 Dec) ─► cook-alongs ─► RQ4 table ─► JCSSE (22 Jan)
lexicon 400 + HD-3 answer + release kit ─► HF live ─► ICWSM (15 Jan)
data freeze (13 Dec) ─► RQ1–RQ5 ─► full paper (31 Mar)
```

| Gate | Date | Question | If NO |
|---|---|---|---|
| **G1** | Sun 12 Oct | Phase 0 done: fix merged, backup off-laptop, 30 PDFs loaded? | Do nothing else until it is |
| **G2** | Sun 26 Oct | Protocol final, consent fixed, Q10 stored separately, predictions committed? | First interview moves; no interview before pre-registration |
| **G3** | Sun 8 Nov | Lexicon ≥150 entries covering ≥80% of ingredient mentions, prelim RQ1 run? | DH paper reports method + region-level descriptive results only |
| **G4** | Sun 6 Dec | ≥10 interviews done? | Freeze anyway; full paper becomes two-register (RQ1, RQ2, RQ4) |
| **G5** | Fri 1 Jan | DCP permission received? | Release lexicon + commercial only; official register described, not redistributed |
| **G6** | Sun 10 Jan | ICWSM draft complete, HF repos ready? | Drop ICWSM; put the time into JCSSE |
| **G7** | Mon 1 Mar | Full-paper draft complete? | Submit arXiv on 31 Mar; journal submission may slip to April |

---

## 4. Capacity budget

| Period | Weeks | Hours/week | Total | Notes |
|---|---|---|---|---|
| 6 Oct – 20 Nov | 6.5 | 15 | ~100 | DH + prep + Korat interviews |
| 21 Nov – 13 Dec | 3 | 15 + trip | ~45 + travel | Fieldwork, lexicon, cooking |
| Winter break | ~3 | 35–40 | ~110 | Two papers + release |
| Jan – Mar (term) | 10 | 10 | ~100 | Full paper |
| **Total** | | | **~355 h** | |

**[BO] T0.7 (by 12 Oct): enter ISB exam weeks, winter-break dates and any fixed school events into this table.**
Exam weeks are planned as 0-hour weeks. If an exam week falls in 7–13 Dec, the data freeze moves to Sun 20 Dec
and Phase 3 compresses by one week (ICWSM is then the first thing dropped).

---

## 5. Phase 0 — Lock down · Tue 6 – Sun 12 Oct 2026 · ~5 h

| ID | Owner | Task | Files / commands | Done when |
|---|---|---|---|---|
| T0.1 | [BO→CC] | Review the unmerged parser fix `b55d02b` (branch `claude/elastic-jemison-170dd6`). Bo reads the diff and the 10→0 section-bleed evidence; decide merge or reject | `src/ingest/dcp_form.py`, `tests/test_ingredient_table.py` | Fix is on `main` (or rejected and DB re-ingested from `main`); worktree branch deleted; suite green |
| T0.2 | [CC] | Dump and back up the database off the laptop | `make db-dump`; `make backup TO=<USB or Drive path>` | A dump dated ≥ T0.1 exists in two places; restore tested once with `scripts/restore*` into a scratch DB |
| T0.3 | [CC] | Load the 30 DCP documents whose province parse failed, including `northeast_5_3.pdf` (Nakhon Ratchasima). Add a test per failure pattern | `src/ingest/dcp_form.py`, `scripts/` ingest, `tests/` | `recipes` has 231 official rows (or each exclusion is listed with a reason in `docs/source_audit.md`); PDPA tests pass |
| T0.4 | [BO] | Verify the 6 fieldwork-province checkbox readings by eye (`northeast_5_1..3`, Buri Ram `northeast_6_1..3`); resolve `northeast_5_3` double tick and `northeast_6_2` occasion/endangerment confusion | `scripts/verify_checkboxes.py` | 6 readings confirmed or corrected in a committed fixture; HD-RQ5 entry written (see §11) |
| T0.5 | [CC] | Commit the fieldwork pack | `FlavorMap_Fieldwork_Pack.pdf` → `docs/fieldwork/` | Tracked; `.gitignore` unchanged |
| T0.6 | [BO] | **Send the DCP permission request (HD-3)** | `docs/dcp_permission_request.md` → email; status line updated | Sent; date recorded in `docs/decisions.md` HD-3 |
| T0.7 | [BO] | Fill the capacity table (§4) with ISB exam and break dates | this file | Dates entered |

---

## 6. Phase 1 — DH2027 sprint + fieldwork prep · Mon 13 Oct – Fri 20 Nov 2026 · ~100 h

### 6.1 Week of 13–19 Oct — admin, protocol, ethics

| ID | Owner | Task | Files | Done when |
|---|---|---|---|---|
| T1.1 | [CC] | Verify the CFP items in §1.1 from the official sites | `docs/venues.md` | Every bullet answered with source URL and date checked |
| T1.2 | [BO] | Finalise the interview protocol: reconcile Q1, Q2, Q4–Q7 with v2 (locate the v2 protocol in `docs/archive/` or past chats); keep Q3, Q8, Q9, Q10 as written in the Bible | `docs/fieldwork/protocol_v4.md` (Thai + English) | Committed; marked FINAL; dated |
| T1.3 | [BO] | Fix the Thai consent form: remove the real-name option (or move named credit outside the database, decided in HD-consent); fix the grade (ม.4 vs ม.5) to match the permission letter | `docs/fieldwork/consent_th.md` | Form promises only what the system does; committed |
| T1.4 | [BO→CC] | **Q10 storage.** Bo decides (HD-Q10); Claude Code adds a separate table, e.g. `dish_status_reports(informant_id, official_recipe_id, still_made, who_makes, young_people_know, notes)`, so Q10 answers about government dishes never create a `domestic` recipe. Loader + tests | migration `025_dish_status_reports.sql`, `src/ingest/interview.py`, `tests/test_interview.py` | A Q10 answer about a dish the cook does not make produces zero `recipes` rows (test); PDPA scan passes |
| T1.5 | [BO+FAM] | Book interview dates: 6 Korat interviews on weekends 31 Oct – 6 Dec; Buri Ram weekend (28–29 Nov or 5–6 Dec). Arrange introductions | `docs/fieldwork/schedule.md` (no names, roles only) | All 12 slots dated; transport confirmed |
| T1.6 | [BO] | Mentor outreach: email Assoc. Prof. Attapol Rutherford (Chula Linguistics) and Dr. Chulanee Thianthai (Chula Sociology & Anthropology); attach the 2-page summary and GitHub link; ask for a 30-min review of the DH draft ~10 Nov | email | Sent; replies logged in `CREDITS.md` draft (role, hours) |
| T1.7 | [CC] | Write the dated interview write-up template + cook-along log template check; one dry-run load with a fake, PII-free interview | `data/interviews/TEMPLATE.toml`, `data/cook_along/TEMPLATE` | Dry run loads, then is deleted; tests green |

### 6.2 By Sun 26 Oct — pre-registration and origin story (Gate G2)

| ID | Owner | Task | Files | Done when |
|---|---|---|---|---|
| T1.8 | [BO] | **Pre-register.** Rewrite `docs/hypotheses.md` for v4: one dated prediction per RQ (direction + rough magnitude) and what a NO looks like. Remove v3 content to `docs/archive/` | `docs/hypotheses.md` | Committed **before the first interview**; commit hash recorded in this file |
| T1.9 | [BO] | Cook the origin dish with the family member; photograph the mise en place; write what actually happened, including what contradicts memory | `docs/notebook.md` (first researcher entry), `data/photos/origin/` (gitignored if faces) | Committed with the real date |
| T1.10 | [CC] | Update docs to v4: README RQ section; `CLAUDE.md` §7.1/§10 (~800 target, not 2,200), §7.3 (fieldwork now load-bearing), gate numbering; create `docs/research_questions.md`; mark Mantel/region-signal code and v3 figures as `archived` (move to `src/analyze/v3/`, `figures/v3/`) | listed files | No v3 RQ text outside `docs/archive/`; suite green |
| T1.11 | [BO] | Amend the Bible: v4.1 note — fieldwork provinces are Nakhon Ratchasima + Buri Ram (HD-32); limitation: two neighbouring Isaan provinces, no North contrast | `FlavorMap_Project_Bible_v4.md` | Committed |
| T1.12 | [BO→CC] | **HD-15 acquisition mode.** Review the existing `ACQUISITION_HINTS` mapping (ที่มา text → grown/foraged/market/packaged). Bo accepts, edits or rejects each mapping; Claude Code then makes the code read the decided table instead of hard-coded hints | `docs/decisions.md` HD-15, `src/ingest/dcp_form.py`, `data/reference/acquisition_map.csv` | No acquisition mode written without a decided mapping; coverage (currently 264/1,132 rows) reported |

### 6.3 Commercial register — by Sun 1 Nov

| ID | Owner | Task | Files | Done when |
|---|---|---|---|---|
| T1.13 | [CC] | Measure the attainable province-label yield on the 1,360 Kapook recipes with three rule families: (a) explicit province names in title/category; (b) explicit regional claims ("อีสาน", "เหนือ", "ใต้", "ภาคกลาง"); (c) dish-name match against official dish names. Report counts per province and region. **Do not write labels yet** | `scripts/measure_kapook_labels.py`, `docs/labelled_fraction.md` | Table of yields by rule committed |
| T1.14 | [BO] | **HD-Kapook.** Choose: province labels (rules accepted), region-level comparison, or both. Also record **HD-sources**: commercial register stays single-source for this cycle (Bible asked for ≥4); stated as a limitation | `docs/decisions.md`, `docs/limitations.md` | Decision logged with rejected alternatives |
| T1.15 | [CC] | Apply the decided labelling into `province_attribution` (confidence + rule recorded per row); "unlabelled" stays unlabelled | migration if needed, `scripts/`, tests | Counts match T1.13 for the chosen rules |

### 6.4 Lexicon v0.3 — 20 Oct to Sun 8 Nov (Gate G3)

| ID | Owner | Task | Files | Done when |
|---|---|---|---|---|
| T1.16 | [BO→CC] | **HD-6 granularity rules** first (e.g. are พริกขี้หนู / พริกขี้หนูสวน one entry or two; how plant parts and processed forms map). Then author entries top-down by frequency | `scripts/lexicon_worklist.py`, `data/reference/ingredients_lexicon.csv`, `scripts/load_lexicon.py` | ≥150 canonical entries; **≥80% of ingredient mentions** (by count) mapped; every non-obvious mapping has a note |
| T1.17 | [CC] | Mention-coverage report after each batch | `scripts/lexicon_coverage.py` → `data/coverage/lexicon_YYYYMMDD.csv` | Weekly snapshot committed |

Weekly quota: **50 entries/week** (Oct 20 → Dec 13 ≈ 8 weeks ≈ 400).

### 6.5 Preliminary analysis — Sat 1 – Sun 8 Nov

| ID | Owner | Task | Files | Done when |
|---|---|---|---|---|
| T1.18 | [CC] | Export analysis Parquet from the DB (no PII) | `scripts/export_parquet.py` → `data/processed/*.parquet` | Parquet regenerated by one command; PDPA scan covers Parquet |
| T1.19 | [CC] | Preliminary RQ1: per province (or region, per HD-Kapook) normalised ingredient vectors per register; official↔commercial cosine distance; n reported beside every value | `src/analyze/rq1_registers.py`, `notebooks/01_rq1_prelim.ipynb` (keep unpolished) | Table of distances + n committed |
| T1.20 | [CC] | Figure 6: province × ingredient TF-IDF heatmap, top ~60 ingredients by variance, both axes seriated by clustering (never alphabetical), faceted by register | `src/viz/figure6.py` → `figures/fig6_heatmap.png` | Figure regenerates from Parquet with one command |
| T1.21 | [BO] | Interpret: which provinces/regions agree most and least; is anything surprising; write 5 bullet observations | `docs/notebook.md` | Committed, dated |

### 6.6 Write and submit DH2027 — Mon 9 – Fri 20 Nov

Follow `DH2027_Short_Paper_Outline.md` (project doc).

| ID | Owner | Task | Done when |
|---|---|---|---|
| T1.22 | [BO] | Draft all sections; Section 5 from T1.19–T1.21 only | 1,000–1,250 words (captions included) |
| T1.23 | [MEN] | 30-min review (~10–12 Nov) | Comments logged |
| T1.24 | [CC] | Number audit: every number in the draft traced to a script/commit; produce `paper/dh2027/numbers.md` | Zero untraced numbers |
| T1.25 | [BO] | Verify all citations; add 2–3 Thai food-studies sources; AI-use disclosure | Reference list checked |
| T1.26 | [BO] | Create ConfTool account (by 13 Nov); submit | **Submitted Fri 20 Nov**; confirmation saved in `paper/dh2027/` |

Parallel through Phase 1: Korat interviews from Sat 31 Oct (T2.1).

---

## 7. Phase 2 — Fieldwork + data freeze · Sat 21 Nov – Sun 13 Dec 2026 · ~45 h + travel

| ID | Owner | Task | Files | Done when |
|---|---|---|---|---|
| T2.1 | [BO+FAM] | 6 Korat interviews (weekends, from 31 Oct, done by 6 Dec). Consent signed first; parent present; Q9 and Q10 asked every time; Q10 about the 3 government dishes for that province | `data/interviews/` (gitignored), loaded via `src/ingest/interview.py` | Each written up **the same day**; loaded; PDPA tests green; backup run |
| T2.2 | [BO+FAM] | Buri Ram trip (28–29 Nov or 5–6 Dec): 6 interviews | as above | as above |
| T2.3 | [BO] | Lexicon to ~400 entries with **English gloss on every entry** | `ingredients_lexicon.csv` | Coverage ≥90% of mentions; glosses 100% |
| T2.4 | [BO→CC] | **HD-9 dish-category taxonomy** + mapping from DCP categories and Kapook site categories | `data/reference/dish_categories.csv`, `docs/decisions.md` | `dish_categories` table populated; every recipe mapped or explicitly "unmapped" |
| T2.5 | [BO] | Choose the 8 cook-along dishes: ≥2 official, ≥2 that the pipeline handles badly, ≥1 from an interview | `docs/decisions.md` (HD-cook) | List committed |
| T2.6 | [BO] | Cook-alongs 1–4 from the **cleaned** ingredient lists; log missing / substituted / destroyed / recognisable + one sensory sentence; photograph mise en place | `data/cook_along/`, `src/ingest/cook_along.py` | 4 rows in `cook_along_log` |
| T2.7 | [BO+second reader] | Second annotator labels 100 recipes (stratified by register and region); Claude Code computes Cohen's κ | `scripts/kappa.py`, `docs/limitations.md` | κ reported per field |
| T2.8 | [BO] | Hand-label checkbox ground truth on ~40 random DCP forms (endangerment + dish category) for JCSSE evaluation | `data/reference/checkbox_truth.csv` | 40 rows; extractor accuracy computable |
| T2.9 | [BO] | Hand-label a ~50-document PDPA evaluation sample (which spans are personal data) | `data/raw/pdpa_eval/` (gitignored) | Precision/recall computable without exposing PII |
| T2.10 | [CC] | **Data freeze Sun 13 Dec:** final ingest, dump, backup, `git tag data-freeze-v1`, coverage snapshot | `data/coverage/` | Tag pushed; dump in two places |

Gate **G4** on Sun 6 Dec (≥10 interviews).

---

## 8. Phase 3 — Two papers + release · Mon 14 Dec 2026 – Fri 22 Jan 2027 · ~110 h

### 8.1 14–24 Dec — RQ4, JCSSE draft, HD-13

| ID | Owner | Task | Done when |
|---|---|---|---|
| T3.1 | [BO] | Cook-alongs 5–8 | 8 rows in `cook_along_log` |
| T3.2 | [CC] | Figure 4 fidelity matrix (8 dishes × quantities/order/technique/specificity/completeness → survived/degraded/lost) | `figures/fig4_fidelity.png` from data |
| T3.3 | [CC] | JCSSE evaluation tables: extractor comparison (pdfplumber/PyMuPDF/pypdf), sara am repair before/after error counts, checkbox accuracy vs T2.8 truth, PDPA precision/recall vs T2.9, normalisation coverage | `paper/jcsse/tables/` regenerate by one command |
| T3.4 | [BO] | JCSSE draft (IEEE template); Claude Code formats LaTeX and figures only | Full draft by 24 Dec |
| T3.5 | [BO] | **HD-13:** define the RQ2 presence/absence decomposition with the rejected alternatives | Decision entry committed |

### 8.2 26 Dec – 12 Jan — ICWSM + HuggingFace release

| ID | Owner | Task | Done when |
|---|---|---|---|
| T3.6 | [CC] | Build `OpenFlavorTH-recipes`: `recipes.parquet` (ID, register, normalised ingredients, province, district, region, dish category, endangerment, acquisition mode, source domain, published date, collection date — **no prose, no PII**); `fieldwork.csv` (anonymised, role + province + district); `cook_along_log.csv`; `endangerment_comparison.csv`; `stated_absences.csv` | Files generate from the frozen DB with one command; PDPA scan on every file |
| T3.7 | [CC] | Build `OpenFlavorTH-lexicon`: `ingredients_lexicon.csv` (canonical Thai, English gloss, variants, category, judgment-call notes) | Validates against schema; 100% glossed |
| T3.8 | [BO→CC] | Dataset cards (motivation, collection, PDPA handling, scraping ethics, register definitions, known biases, κ, licence CC-BY-4.0, citation); `loading_script` so `load_dataset` works in one line; Croissant metadata | Cards reviewed by Bo; loader tested in a clean venv |
| T3.9 | [CC] | Zenodo DOI via GitHub release `v1.0`; `CITATION.cff`; data licence stated in README, dataset cards and `LICENSE-DATA` | DOI resolves |
| T3.10 | [BO] | ICWSM dataset paper draft; Claude Code produces dataset statistics tables and Figures 6, 7 and network figure | Draft by 10 Jan (Gate G6) |
| T3.11 | [BO] | **Gate G5 (1 Jan):** if no DCP permission, release lexicon + commercial + fieldwork-derived files only | Decision logged |
| T3.12 | [BO] | **Submit ICWSM Fri 15 Jan**; datasets public the same day | Confirmation saved |

### 8.3 16–22 Jan — JCSSE

| ID | Owner | Task | Done when |
|---|---|---|---|
| T3.13 | [BO] | Polish JCSSE; check no verbatim overlap with ICWSM; cite the dataset DOI | **Submitted Fri 22 Jan** |

---

## 9. Phase 4 — Full paper · Sat 23 Jan – Wed 31 Mar 2027 · ~100 h

| ID | Owner | Task | Done when |
|---|---|---|---|
| T4.1 | [CC] | RQ1 full: three-register distances for Korat and Buri Ram; two-register for the other provinces; n beside every value | Tables + Figure 1 (register triangles) |
| T4.2 | [CC] | RQ2 per HD-13; validation against stated absences (Q9) | Figure 2 |
| T4.3 | [CC] | RQ3 dish- and ingredient-level overlap; raw counts, not percentages | Figure 3 |
| T4.4 | [CC] | RQ5 agreement matrix (Buri Ram official levels vs. cook reports; Korat reported as "no official level") | Figure 5 |
| T4.5 | [CC] | Ingredient network per register, PMI-weighted, disparity-filter backbone | `network.gexf` per register |
| T4.6 | [CC] | Figure 7 acquisition mode by province, ordered by distance from Bangkok | Figure 7 |
| T4.7 | [BO] | Compare every result with the pre-registered predictions; negative results at full weight | `docs/notebook.md` entries |
| T4.8 | [BO] | Draft (~4,600 words; structure per Bible §17) by **Mon 1 Mar** (Gate G7) | Draft complete |
| T4.9 | [MEN] | Review 2–15 Mar | Comments addressed |
| T4.10 | [BO] | Finalise `CREDITS.md`, `docs/limitations.md`, AI disclosure | Committed |
| T4.11 | [BO] | **31 Mar:** arXiv (cs.CY or cs.SI) + Journal of Cultural Analytics submission | IDs recorded |
| — | [BO] | Feb: DH2027 notification → T5.1 | |

---

## 10. Phase 5 — Present · Apr – Jul 2027

| ID | Owner | Task | Timing |
|---|---|---|---|
| T5.1 | [BO+FAM] | Travel: passports valid 6+ months; check visa requirements for the UK (ICWSM) and Ireland (DH) for Thai passport holders and apply as soon as acceptances arrive; book flights and accommodation; consider one combined UK–Ireland trip if ICWSM dates allow | Feb–Apr |
| T5.2 | [BO] | Apply for DH2027 student bursary and any ICWSM/AAAI student travel support; check ISB funding | per deadlines in `docs/venues.md` |
| T5.3 | [BO] | Camera-ready versions (JCSSE final manuscript **7 May**; early registration **23 Apr**; ICWSM per CFP) | Apr–May |
| T5.4 | [BO] | Talks: 10-min DH talk; JCSSE and ICWSM per format. Rehearse in front of a teacher; prepare "how much help did you have?" answer with `docs/decisions.md` open | May–Jun |
| T5.5 | [BO+sister] | Public site: map, province quiz, one network interactive. Nothing more | Apr–Aug |
| T5.6 | [BO] | Reciprocity: send each participant the map and a printed copy of their recipe as it appears in the dataset | by Jun |
| T5.7 | [BO] | Applications: report the real HuggingFace download count | Sep–Nov 2027 |

Conference dates: ICWSM Edinburgh (TBA, ~May–Jun) · JCSSE 16–18 Jun · DH2027 28 Jun – 3 Jul.

---

## 11. Decision gates — due dates

Bo decides; Claude Code implements only after the entry is marked DECIDED in `docs/decisions.md`.

| Gate | Decision | Due | Blocks |
|---|---|---|---|
| HD-3 | DCP redistribution permission (send request) | send 12 Oct; answer by 1 Jan | ICWSM, recipes release |
| HD-RQ5 | Accept RQ5 resting on Buri Ram's official levels only? (Korat forms carry no usable level) | 12 Oct | RQ5 framing |
| HD-consent | Real-name option removed vs. named credit kept outside DB | 19 Oct | Interviews |
| HD-Q10 | Storage design for Q10 answers | 19 Oct | Interviews |
| HD-15 | ที่มา → acquisition-mode mapping | 26 Oct | Figure 7 |
| HD-6 | Lexicon granularity rules | 20 Oct (rules), ongoing (entries) | RQ1, RQ2, RQ4, cook-alongs |
| HD-Kapook | Province vs. region labelling of commercial recipes | 1 Nov | RQ1, DH |
| HD-sources | Commercial register single-source this cycle | 1 Nov | Limitations |
| HD-1 | Per-province labels review (currently "Selected B" with empty Decision field) | 8 Nov | RQ1 |
| HD-9 | Dish-category taxonomy + cross-register mapping | 6 Dec | Comparability |
| HD-cook | The 8 cook-along dishes | 22 Nov | RQ4 |
| HD-freeze | Freeze date confirmed against ISB exams | 12 Oct | Phase 3 |
| HD-13 | RQ2 decomposition definition | 24 Dec | RQ2 |
| HD-v3 | Fate of v3 figures and Mantel/region-signal code (archive) | 26 Oct | Repo clarity |

---

## 12. Weekly ritual — every Sunday evening (~30 min)

1. `[CC]` `make status` → commit `data/coverage/status_YYYYMMDD.md` (rows per register, provinces covered, lexicon entries and mention coverage, interviews loaded, cook-alongs logged, tests).
2. `[CC]` `make db-dump` + off-laptop backup.
3. `[BO]` Tick completed task IDs in this file; move slipped tasks with a one-line reason.
4. `[BO]` One `docs/notebook.md` entry: what I decided, what surprised me, what I'm unsure about.
5. `[BO]` Check the next gate date.

No week ends with uncommitted work or an unmerged branch.

---

## 13. Risk register

| Risk | Trigger | Response |
|---|---|---|
| Workload (~15 h/week term, ~40 h/week break) | Two missed lexicon quotas in a row | Drop ICWSM; school always wins |
| Exam week inside a phase | Calendar check T0.7 | Shift freeze to 20 Dec; compress Phase 3 |
| Fieldwork slips | <10 interviews by 6 Dec | Freeze anyway; two-register full paper |
| RQ5 too thin (3 Buri Ram dishes) | HD-RQ5 | Report as an existence demonstration; or replace RQ5 with a descriptive endangerment section |
| Kapook labels too sparse | T1.13 yield < ~5 per province | Region-level comparison (HD-Kapook) |
| DCP permission not granted | No answer by 1 Jan | Release without official records; describe them; full paper unaffected |
| PDPA leak | Any PDPA test fails | Stop all work; fix; re-dump; delete affected dumps |
| Data loss | — | Weekly + post-interview backups; tested restore |
| Archival overlap ICWSM/JCSSE | Self-check T3.13 | Distinct contributions; cross-cite |
| Anonymity violation | CFP check T1.1 | Hide GitHub/HF links during review where required |
| Travel / visa / cost | Acceptances in Feb–Apr | Apply early; bursaries; one combined Europe trip |
| Mentor unavailable | No reply by 27 Oct | Second email to Ekapol Chuangsuwanich (Chula Computer Engineering) or Nittaya Kerdprasop (SUT, Korat); project is completable without one |
| Scope creep (site, cooking, extra data in `data/raw/gdcatalog/`) | Any new source or feature request | Park in `docs/later.md`; no new source without an ETHICS.md entry and an RQ that needs it |

---

## 14. Known repo inconsistencies to fix (from the audit)

| Item | Fix | Task |
|---|---|---|
| README RQ section is v3 | Rewrite for v4 | T1.10 |
| `docs/hypotheses.md` is v3 scaffold | Pre-register v4 | T1.8 |
| `CLAUDE.md` targets ~2,200 recipes; says no RQ depends on fieldwork | Update to ~800 and fieldwork-dependent | T1.10 |
| `docs/research_questions.md` missing | Create | T1.10 |
| Bible §10 says Nan + Surin | v4.1 amendment | T1.11 |
| `ACQUISITION_HINTS` encodes undecided HD-15 | Gate it | T1.12 |
| Fieldwork pack says `endangerment_level`; column is `endangerment` | Correct pack | T1.2 |
| Fieldwork pack claims migration 013 supports a dialect axis | Correct or implement after decision | T1.2 |
| Download log lacks URL and timestamp columns | Add reconstructed URL; note timestamp gap in `ETHICS.md` | T1.10 |
| ETHICS.md lacks Cookpad/Krua (unused) and `gdcatalog` sources | Record "not used this cycle" | T1.10 |
| No data licence anywhere | CC-BY-4.0 | T3.9 |

---

## 15. Status tracker

| Phase | Window | Status |
|---|---|---|
| 0 Lock down | 6–12 Oct | ☐ |
| 1 DH sprint + prep | 13 Oct – 20 Nov | ☐ |
| 2 Fieldwork + freeze | 21 Nov – 13 Dec | ☐ |
| 3 ICWSM + JCSSE + release | 14 Dec – 22 Jan | ☐ |
| 4 Full paper | 23 Jan – 31 Mar | ☐ |
| 5 Present | Apr – Jul | ☐ |

Pre-registration commit hash: `________` · Data-freeze tag: `________` · Zenodo DOI: `________`

---

## Sources

- DH2027 Call for Proposals — https://dh2027.adho.org/cfp/
- ICWSM 2027 deadlines — https://mldeadlines.com/conference/icwsm/ ; CFP summary — https://linguistlist.org/issues/37/1534/
- JCSSE 2027 — https://jcsse2027.mfu.ac.th/
- FlavorMap Project Bible v4; `docs/STATUS_2026-10.md`; `DH2027_Short_Paper_Outline.md`
