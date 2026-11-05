# FlavorMap — RQ Playbook (how to answer all five research questions)

**Version:** v1 · 5 November 2026 · **Save in repo as:** `docs/RQ_PLAYBOOK.md`
**Works with:** `docs/TIMELINE.md` (when, task IDs) · `FlavorMap_Project_Bible_v5.md` (why) · `docs/MASTER_PROMPT.md` (how Claude Code runs)

> **How the three files divide the work.** The **timeline** says *when* and in *what order* (task IDs T…, I…).
> This **playbook** says *what exactly* to do for each research question: inputs, steps, decisions, outputs and
> the test for "done". The **master prompt** makes Claude Code execute both. Nothing else is needed.

---

## 0. Why one playbook, not five RQ files

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **One master file for everything** | One place | Mixes schedule and method; becomes 2,000 lines; hard to use when writing one paper section | ✗ |
| **Five files, one per RQ** | Clean per-RQ focus | The five RQs share ~70% of the work (database, lexicon, labels, dish taxonomy). Five files would repeat it and drift apart; Claude Code could build the same thing five times | ✗ |
| **Timeline + this playbook (shared foundation once, then one section per RQ)** | No duplication; each RQ section is self-contained enough to paste into a paper's Methods; matches the "fewest files" rule | — | ✅ **Use this** |

**Rule:** shared work lives in §2 (Foundation) once. Each RQ section (§3–§7) only lists what is specific to that RQ
and points back to Foundation tasks. If an RQ section grows past ~2 pages, split *that one* into `docs/rq/RQn.md` —
not before.

---

## 1. Where the project stands (5 Nov 2026)

What is known from the 6 Oct audit (`docs/STATUS_2026-10.md`), the 12 Oct data-folder check and the repo listing.
**Claude Code must re-verify every line on its first run** (master prompt Step 1).

| Area | Status | Evidence |
|---|---|---|
| Repo, tests, CI hygiene | ✅ Strong — 414 tests passing, ruff/mypy clean, public repo | Audit §1.6 |
| PDPA stripping at parse time | ✅ Done, tested (24 + 103 tests) | Audit §1.6 |
| Official register (231 DCP PDFs) | ✅ All downloaded; ~201 loaded → ~212 after pattern-A fix; Nakhon Nayok transcribed by hand (`data/raw/dcp_manual/`) | Audit §1.4–1.5; folder 6 Oct |
| Sara am repair, checkbox extraction | ✅ Built and tested; endangerment extracted for ~157/231; **6 fieldwork readings not yet checked by eye** | Audit §1.6, §2 |
| Commercial register | ⚠️ **Kapook** 1,360 recipes loaded, **0 province labels**. **Sanook, MThai** collected 7 Oct, **not loaded** | Audit §1.8; folders 7 Oct |
| State promotional sources | ⚠️ **TAT, Ministry of Culture** collected 7 Oct, **not loaded**; register undecided | Folders 7 Oct |
| Other downloaded data | ⚠️ `data/raw/gdcatalog/` — 8 CSVs (data.go.th catalogue, bookfood67, OAE crops, GI, …) used by nothing | Audit §1.12 |
| Lexicon (ingredient vocabulary) | ❌ **0 entries** (tooling only; 8,157 distinct raw strings to work through) | Audit §1.7 |
| Pre-registration (`docs/hypotheses.md`) | ❌ Still v3 | Audit §1.9 |
| Interviews | ❌ 0 of 12; protocol partly draft; consent form needs fixes | Audit §1.9 |
| Cook-alongs | ❌ 0 of 8 (machinery ready) | Audit §1.10 |
| v4/v5 analyses, figures | ❌ None run | Audit §1.10 |
| Origin story | ❌ Not written | Audit §1.9 |
| `private/` folder (7 Oct) | ❓ Unknown contents — **must be gitignored if it holds anything personal** | Repo listing |
| Recent activity | ⚠️ Top-level folders show no changes after **12 Oct** | Repo listing (5 Nov) |

**Overall ≈ 20%.** Engineering is ahead; everything that needs Bo's judgment (lexicon, decisions, interviews,
cooking, writing) is behind. **DH2027 is due 20 Nov** and needs the lexicon + preliminary RQ1.

**About all the downloaded web data:** having more recipes does not move the project much now. The bottleneck is
(1) the lexicon and (2) labels (which province/region a recipe belongs to). Do not download more before 13 Dec.

---

## 2. Shared foundation (used by every RQ)

| ID | What | Owner | Needed by | Done when |
|---|---|---|---|---|
| **F1** | **Phase 0 clean-up** — parser fix merged, off-laptop backup, 30 failed PDFs + Nakhon Nayok loaded (T0.1–T0.8) | CC (+ Bo decides T0.1) | All | 231 official rows or listed exclusions; backup in 2 places |
| **F2** | **Load new sources** — inventory, ethics rows, Bo's decisions (HD-register / sources / dedup / balance), load Sanook + MThai (+ TAT/m-culture if decided), duplicate report (T1.13a–e; Scraper Prompt P) | CC + Bo | RQ1, RQ5 | Rows per source; ETHICS.md rows; duplicate rate reported |
| **F3** | **Lexicon** — HD-6 granularity rules, then entries by frequency: ≥150 (≥80% of mentions) by 8 Nov; ~400 with English glosses (≥90%) by 13 Dec (T1.16–17, T2.3) | **Bo** | All | Coverage report per source |
| **F4** | **Labels** — measure province/region label yield per source, decide (HD-labelling), apply (T1.13–T1.15) | CC + Bo | RQ1, RQ2, RQ5 | `province_attribution` filled per decided rules |
| **F5** | **Dish-category taxonomy** + mapping across sources (HD-9, T2.4) | Bo → CC | RQ1 (subset analyses), RQ5 | Every recipe mapped or "unmapped" |
| **F6** | **Parquet export** (no PII) — one command (T1.18) | CC | All analyses | `make export` regenerates `data/processed/*.parquet` |
| **F7** | **Pre-registration** for RQ v2 — one dated prediction per RQ + what a NO looks like (T1.8) | **Bo** | Credibility | Committed before interview 1 |
| **F8** | **Data freeze** 13 Dec — tag + dump (T2.10) | CC | Full paper, release | `data-freeze-v1` tag |

---

## 3. RQ1 — State, market, kitchen: real difference or chance?

**Short:** อาหารประจำจังหวัดที่รัฐเลือก สูตรบนเว็บ และอาหารที่คนในจังหวัดทำกินจริง ต่างกันจริง หรือแค่บังเอิญ?
**Role:** headline of every paper. **Used in:** DH2027 (preliminary, official↔commercial), dataset paper (baseline stats), full paper (three-way for Korat + Buri Ram).

**Inputs:** official recipes (F1), commercial recipes with labels (F2, F4), lexicon (F3), interviews for the three-way part.

**Steps**

1. **[Bo] Decide the unit** (HD-labelling): province where labels allow, region otherwise. Write down the minimum n per unit (e.g. ≥5 commercial recipes) below which a unit is dropped.
2. **[CC] Build vectors**: for each unit × register, a normalised ingredient vector (share of recipes containing each canonical ingredient). Keep n per cell.
3. **[CC] Distance**: cosine distance official↔commercial per unit (and official↔domestic, commercial↔domestic for Korat and Buri Ram once interviews are in).
4. **[CC] Permutation baseline**: shuffle unit labels within each register 9,999 times, recompute distances; empirical p = share of shuffled distances ≥ observed. Also report the pooled result ("X of N units differ more than chance").
5. **[CC] Bootstrap CI**: resample recipes within each unit 2,000 times → 95% CI per distance.
6. **[CC] Robustness**: repeat with commercial = Kapook only / Sanook only / MThai only; and excluding manual Nakhon Nayok rows.
7. **[CC] Optional second test**: classifier (e.g. logistic regression or random forest) predicting region from ingredients, cross-validated; compare accuracy on official vs. commercial recipes.
8. **[CC] Figures**: Figure 6 heatmap (seriated, faceted by register); Figure 1 register triangles (Korat, Buri Ram) + two-register lines with CIs elsewhere.
9. **[Bo] Interpret**: 5 written observations in `docs/notebook.md`; compare with the pre-registered prediction.

**Decisions (Bo):** HD-labelling, minimum n, HD-balance, HD-dedup.
**Outputs:** `results/rq1_distances.csv` (unit, pair, distance, CI low/high, p, n each side), Figures 1 and 6.
**Done when:** every distance has n + CI + p; per-source robustness table exists; null results stated plainly.
**Pitfalls:** comparing units with very different n without saying so; alphabetical axis order; presenting a national three-register map (only 2 provinces have three registers).
**Effort:** ~22 h CC-assisted + ~3 h Bo interpretation.

---

## 4. RQ2 — Identity from what's used, or what's refused?

**Short:** อาหารแต่ละภาคมีเอกลักษณ์เพราะวัตถุดิบที่ใส่ หรือเพราะวัตถุดิบที่คนในภาคไม่ใส่?
**Role:** the data-science selling point (a new measure). **Used in:** full paper; mentioned as design in DH.

**Inputs:** RQ1 vectors (§3 step 2), national mean vector, interview Q9 answers.

**Steps**

1. **[Bo] Define the measure (HD-13)** — the core intellectual work (~15 h thinking). One candidate to start from, not a decision: split a unit's difference from the national mean, d = v − μ, into a **presence part** (ingredients where v > μ) and an **absence part** (where v < μ), and compare their sizes (e.g. share of the squared distance from each part). Write the chosen definition, at least two rejected alternatives, and why.
2. **[Bo] Decide thresholds**: when an ingredient counts as "refused" (e.g. used in <X% of a unit's recipes while ≥Y% nationally).
3. **[CC] Implement** the decided definition only; unit tests on toy data where the right answer is known.
4. **[CC] Uncertainty**: bootstrap the presence/absence shares per unit.
5. **[CC] Figure 2**: presence-driven (x) vs absence-driven (y), one point per unit, diagonal = balanced, CIs as whiskers.
6. **[Bo] Validate with Q9**: for Korat and Buri Ram, compare the ingredients the measure flags as "refused" with what cooks said they would never put in. Report overlaps as counts.
7. **[Bo] Write** the definition section for the paper from the decision entry.

**Decisions (Bo):** HD-13 (definition), refusal thresholds.
**Outputs:** `results/rq2_decomposition.csv`, `stated_absences.csv`, Figure 2.
**Done when:** definition DECIDED with rejected alternatives; toy-data tests pass; Q9 comparison written.
**Pitfalls:** letting Claude Code choose the definition (it must not); treating inferred absence as proof without Q9.
**Effort:** ~15 h Bo thinking + ~3 h coding + ~2 h validation.

---

## 5. RQ3 — What does the state's list leave out?

**Short:** มีอาหารหรือวัตถุดิบอะไรบ้างที่คนในจังหวัดทำกินจริง แต่ไม่อยู่ในรายชื่ออาหารของรัฐ?
**Role:** authorship evidence — fieldwork only Bo can do. **Used in:** full paper ("What the record leaves out").

**Inputs:** 12 interviews (Korat 6, Buri Ram 6), official list (3 dishes per province), commercial recipes, optionally TAT/m-culture lists.

**Steps**

1. **[Bo] Prepare** (before interview 1): final protocol (Q1–Q10), Thai consent form without a real-name option, pre-registration committed, dates booked, parent available.
2. **[Bo + FAM] Interview** — consent first; ask "what do you actually cook?" (dish list), Q9 (refusals), Q10 (the 3 government dishes). Photograph dishes/ingredients with permission. **Write up the same day** with the template.
3. **[CC] Load** each write-up through the interview loader (PDPA checks; Q10 into `dish_status_reports`, never as recipes).
4. **[Bo] Map** each named dish and ingredient to the lexicon / official dish names (judgment calls logged).
5. **[CC] Compare** at dish level and ingredient level: in official list / in commercial recipes / in neither — raw counts per province.
6. **[CC] Figure 3** stacked bars; table of "neither" items.
7. **[Bo] Write** as an existence claim ("n of 6 cooks named…"), never as a ranking.

**Decisions (Bo):** what counts as "the same dish" across sources; mapping of local names.
**Outputs:** `fieldwork.csv` (anonymised), Figure 3, "neither" table.
**Done when:** ≥10 interviews loaded (Gate G4), comparison table and figure exist.
**Pitfalls:** percentages with n≈6; names or addresses anywhere in the repo; asking Q9 so it sounds like a test.
**Effort:** ~36 h interviews + write-ups, ~6 h analysis.

---

## 6. RQ4 — Without the steps, can you still make the dish?

**Short:** นักวิจัยศึกษาอาหารจากรายชื่อวัตถุดิบอย่างเดียว ถ้าไม่มีขั้นตอนการทำ เราจะยังทำอาหารจานนั้นออกมาได้จริงไหม?
**Role:** validation / methods contribution; most memorable. **Used in:** JCSSE (core), full paper, DH talk.

**Inputs:** lexicon v1.0 (F3), cleaned ingredient lists, original source recipes for comparison.

**Steps**

1. **[Bo] Choose 8 dishes (HD-cook)**: ≥2 official, ≥2 the pipeline handles badly (local ingredients, technique-heavy), ≥1 from an interview, the rest web.
2. **[CC] Print a cooking sheet** per dish from the database: the cleaned ingredient list only — no quantities, no steps (existing cooking-sheet tool).
3. **[Bo] Cook** each dish from the sheet only. Photograph the mise en place and the result.
4. **[Bo] Log** in the cook-along template: what was missing; what was substituted and why; what was lost (quantities, order, technique, specificity, completeness) scored 0 survived / 1 degraded / 2 lost; recognisable? (yes/partly/no); one sensory sentence.
5. **[Bo] Compare** with the original recipe after cooking (not before).
6. **[CC] Load** logs; Figure 4 fidelity matrix (8 dishes × 5 classes).
7. **[CC] Optional AI test**: give a language model the ingredient list only, ask for steps, score its steps against the original with the same 0–2 scale. The model is what is tested; it never scores itself.
8. **[Bo] Send** the photo of an interview dish back to that cook (reciprocity).

**Decisions (Bo):** HD-cook; scoring rubric wording.
**Outputs:** `cook_along_log.csv`, Figure 4, photos (no faces unless consented).
**Done when:** 8 rows logged; matrix generated from data.
**Pitfalls:** reading the original recipe before cooking; turning it into a food blog; only picking easy dishes.
**Effort:** 8 cooking sessions (~24 h) + ~8 h analysis/writing.

---

## 7. RQ5 — Is the internet preserving or abandoning endangered dishes?

**Short:** อินเทอร์เน็ตกำลังช่วยรักษา หรือปล่อยให้เมนูพื้นบ้านที่ใกล้สูญหายหายไป?
**Role:** public stake; feeds the impact track (I2 creators, I3 policy brief). **Used in:** full paper, policy brief.

**Inputs:** official dishes with endangerment level (~157 extracted; verified sample from T2.8), all commercial recipes (F2), dish taxonomy (F5).

**Steps**

1. **[Bo] Verify readings**: hand-check the 6 fieldwork-province forms (T0.4) and a random ~40-form sample (T2.8); report extraction accuracy.
2. **[Bo] Decide matching rules (HD-match)**: normalisation (remove prefixes like "แกง", spacing, spelling variants?), fuzzy threshold, what counts as a match.
3. **[CC] Match** official dish names to commercial recipe titles: exact → fuzzy → candidate list.
4. **[Bo] Hand-check** a random sample of ≥100 candidate pairs (match / not); **[CC]** compute precision and recall; adjust once if poor, then freeze the rule.
5. **[CC] Presence**: per official dish, number of matching web recipes and an online yes/no flag.
6. **[CC] Compare** endangered vs. still-transmitted: counts and rates with 95% CIs; a test controlling for region (stratified comparison or logistic regression with region).
7. **[CC] Figure 5** + `endangered_web_presence.csv`; list endangered dishes with **zero** online recipes.
8. **[Bo] Qualitative check**: Buri Ram Q10 answers beside the result.
9. **[Bo] Interpret** both directions (absence online = risk; presence online = web may preserve or the label is outdated).

**Decisions (Bo):** HD-match; how to treat dishes with unreadable endangerment (exclude, report count).
**Outputs:** Figure 5, `endangered_web_presence.csv`, zero-recipe list.
**Done when:** matching precision/recall reported; comparison with CIs; list ready for I2/I3.
**Pitfalls:** calling endangerment a measured rate (it is self-reported); trusting fuzzy matches without the hand check.
**Effort:** ~12 h CC-assisted + ~4 h Bo.

---

## 8. Order of work (critical path)

```
F1 → F2 → F3(150) → F4 → RQ1 preliminary ──► DH2027 (20 Nov)
                 └─ F7 pre-registration ─► RQ3 interviews (31 Oct–6 Dec)
F3(400) → RQ4 cooking (Nov–Dec) ──────────► JCSSE (22 Jan)
F3(400) + F5 + F8 freeze (13 Dec) ─► release ─► LaTeCH/ICWSM (Jan)
RQ2 definition (by 24 Dec) → RQ2 analysis ┐
RQ5 matching (Dec–Jan) → RQ5 analysis ─────┼─► Full paper (31 Mar) ─► Impact I1–I7
RQ1 three-way (after interviews) ──────────┘
```

**This week:** F1/F2 status check (Claude Code), F3 lexicon to 150 (Bo), HD-labelling (Bo) → RQ1 preliminary.

---

## 9. Prompt to give Claude Code

> Read `docs/TIMELINE.md` §0, `docs/RQ_PLAYBOOK.md` and `CLAUDE.md`. Re-verify §1 of the playbook against the repo and
> database and correct any line that is wrong, with evidence. Then do the next READY [CC] steps in playbook order
> (F1 → F2 → F4 → RQ1 steps 2–8), stopping at every Bo decision with an OPEN entry in `docs/decisions.md`.
