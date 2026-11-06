# DH2027 Short Paper — Outline

**Working title:** *Three Dishes per Province: How the Thai State and the Web Record Regional Food Differently*

**Author:** Jenissa (Bo) — International School Bangkok · **Version:** outline v0.2, 5 November 2026 (RQs revised; RQ1 now includes a permutation baseline and bootstrap confidence intervals) · **Deadline:** 20 November 2026, 23:59 AoE

## Submission requirements (DH2027 CFP)

| Item | Requirement |
|---|---|
| Format | Short paper — for work in progress, experiments and exploratory research; ~10-minute presentation |
| Length | **1,000–1,250 words**, including captions; excluding table contents and references |
| Language | English |
| Review | **Not anonymous** — name, school and GitHub link may appear |
| AI disclosure | Required; does not count toward the word limit |
| Figures / tables | Allowed; may be placed in an appendix |
| Theme | *Creativity* — as object of study, research practice, and feature of digital environments |
| Review criteria | Current knowledge and references · advancement beyond existing practice · methodological clarity · diversity of perspectives · writing clarity |

## Core claim (one sentence)

The same cuisine documented by three actors with three different motives — the state, the commercial web, and home cooks — produces three measurably different records, and the gaps between them are a finding about how cultural datasets are made.

## Research questions (v2, 5 Nov 2026)

The DH paper reports **RQ1** with preliminary results. RQ2–RQ5 appear only as the planned design (one sentence each in Section 4). Full wording in Thai and English: `FlavorMap_Research_Questions.md` (project doc).

| RQ | Short version |
|---|---|
| **RQ1** | How different are the dishes the state chose to represent each province, the recipes on the web, and what people in that province actually cook, and are the differences real or just chance? |
| RQ2 | Does a region's food identity come from the ingredients it uses, or from the ingredients it refuses to use? |
| RQ3 | Which dishes and ingredients do people actually cook that are missing from the state's list? |
| RQ4 | Researchers study food from ingredient lists alone. Without the cooking steps, can we still actually make the dish? |
| RQ5 | Is the internet helping to preserve endangered local dishes, or letting them disappear? |

## Section plan — target 1,200 words

### 1. Opening: the kitchen · ~150 words

- First sentence starts with cooking, not method. Method enters no earlier than sentence three.
- **[Origin story — fill in after cooking the dish. Use what actually happened, including what contradicted the remembered version. Do not draft this from memory.]**
- Turn: the family version of the dish is not the version the government lists, nor the version a recipe site publishes. Which one is "Thai regional food"?

### 2. Background and gap · ~200 words

- Computational gastronomy treats recipes as bags of ingredients (e.g. Ahn et al. 2011, flavour networks).
- Critical dataset studies show that corpora carry the choices of whoever assembled them (e.g. Gebru et al. 2021, *Datasheets for Datasets*).
- Heritage studies describe state curation as an "authorised" discourse (Smith 2006, *Uses of Heritage*).
- **Gap 1:** no study compares state-curated, commercial and domestic records of the same cuisine for the same provinces.
- **Gap 2:** computational food studies represent recipes as ingredient lists, but no study checks whether those lists still describe a cookable dish (RQ4).
- **Gap 3:** standard distinctiveness measures (log-odds, Monroe et al. 2008; Zeta, Burrows 2007) measure presence only — a region's refusals are invisible to them.
- *Verify every citation and add 2–3 Thai food-studies sources before submission.*

### 3. Data: three registers · ~300 words

Include Table 1 (counts in table cells do not count toward the word limit).

| Register | Source | Size (update before submission) | Selection pressure |
|---|---|---|---|
| Official | Department of Cultural Promotion local-food forms, `food.culture.go.th`, programme year 2568 | 231 PDFs, 3 dishes × 77 provinces; [n] loaded, [n] provinces | Cultural policy, provincial representation |
| Commercial | `cooking.kapook.com`, `sanook.com`, `mthai.com` (per HD-sources) | [1,360] Kapook + [n] Sanook + [n] MThai, after dedup [n]; [n] province- or region-labelled | Web publishing, ingredient availability, readership |
| Domestic | Interviews, Nakhon Ratchasima and Buri Ram | Target 12; [n] completed by submission | Season, cost, habit, what grows nearby |

- Each register is a biased sample; none is the ground truth — the comparison is the instrument.
- Ethics: personal data stripped at parse time under Thailand's PDPA, with a database-wide test; robots.txt / ToS audits dated; consent forms in Thai; parent present at every interview; ingredient lists only, no recipe prose redistributed.
- One sentence on the two Thai PDF extraction traps (sara am, checkbox glyphs) — signals methodological care; details go to the JCSSE paper.

### 4. Method · ~250 words

- Ingredient normalisation to a controlled Thai vocabulary ([~150] entries at submission; target ~400), each mapping decision logged.
- Region × ingredient vectors per register (HD-37 C; province rows shown where they exist); pairwise cosine distance (official↔commercial now; three-way for the two fieldwork provinces later).
- Primary test chosen after trial results; disclosed.
- **Is the difference real? (new in v2; test revised 2026-11-06, HD-44)** For each region (HD-37), compare the observed official↔commercial distance with a **permutation baseline**: within the region, shuffle the official/commercial labels across its recipes 9,999 times (register-label shuffle) and report where the real distance falls (empirical p-value, Holm-adjusted across the four regions). Secondary check: shuffle region labels within each register. Report **95% bias-corrected bootstrap confidence intervals** (resampling recipes within each region) beside every distance. The primary test was chosen after trial results were seen; say so.
- Robustness: commercial side repeated per source (Kapook / Sanook / MThai) so the result is not one site's house style.
- Sample sizes reported beside every distance — registers are unequal (3 vs. [n] vs. ~6).
- Planned (RQ2): presence/absence decomposition of distinctiveness, validated against interview question 9, *"What do people in other provinces put in this that we would never put in?"* (อะไรที่คนจังหวัดอื่นใส่ในจานนี้ แต่บ้านเราไม่มีวันใส่?)
- Planned (RQ3): overlap between dishes named by cooks and the state's list, reported as raw counts.
- Planned (RQ4): cooking eight dishes (state, web and home-cook sources) from ingredient lists only, to test the field's standard representation and log what is lost.
- Planned (RQ5): web presence of dishes the state marks as endangered versus dishes still passed on.

### 5. Preliminary results · ~200 words

**Do not write until the preliminary analysis is run. No numbers before then.**

- Distribution of official↔commercial distance across regions: [median, range], each with [95% bootstrap CI].
- Against the permutation baseline (register-label shuffle, primary, HD-44): [n of N] regions differ more than chance (Holm-adjusted p < 0.05); give the region-label shuffle result beside it as secondary; state the overall result in one sentence. If the registers are no more different than chance, say so — that is a finding.
- Regions where the registers agree most and least: [names].
- Figure 1 (appendix): region × ingredient heatmap, seriated by clustering, faceted by register.
- Fieldwork status: [n] interviews completed; one concrete early observation if one exists.
- Report a null or weak result plainly if that is what the data shows.

### 6. Creativity: cooking as a research method · ~100 words

- Ties to the DH2027 theme.
- Recipes are creative practice; pipelines flatten them. Cooking from the normalised data is a way of testing a dataset that only someone who cooks can perform.
- Domestic cooks' substitutions and refusals are creative acts that no official or commercial record captures.

### 7. Limitations and next steps · ~100 words

- 3 official dishes per province (wide confidence intervals — reported, not hidden); commercial register from three portals only; fieldwork in two neighbouring Isaan provinces only.
- Endangerment level is self-reported by submitters.
- Next: complete fieldwork (Dec 2026), release OpenFlavorTH on HuggingFace (Jan 2027), full paper by March 2027. Results will be presented in Galway.

### AI disclosure (not counted)

> I used Claude Code to build the data pipeline and scrapers and to debug Thai text extraction. Claude (claude.ai chat) wrote the first draft of this paper from my outline, decisions and results; I revise it. Every analytical decision — vocabulary granularity, labelling rules, thresholds and the choice of statistical test — is mine and is recorded in `docs/decisions.md`, including those that followed an AI recommendation.

*Updated 2026-11-06: the earlier version said the text was the author's own; the first draft is Claude-written.*

### References (not counted)

Ahn et al. 2011 · Burrows 2007 · Gebru et al. 2021 · Monroe, Colaresi & Quinn 2008 · Smith 2006 · 2–3 Thai food-studies sources · DCP source citation · OpenFlavorTH GitHub repository.

## Writing schedule (remaining)

| Date | Task |
|---|---|
| by 8 Nov | Run preliminary RQ1 with permutation baseline and bootstrap CIs; heatmap |
| 9–12 Nov | Section 5; full first draft; word count check |
| ~10 Nov | Send draft to mentor for a 30-minute review |
| 13–18 Nov | Revise; verify every citation; final numbers into Table 1 |
| 19 Nov | Final read aloud; ConfTool account ready |
| **20 Nov** | **Submit** |

## Reviewer checklist

- Does the opening start in a kitchen?
- Is every number traceable to a commit or query?
- Are sample sizes stated beside every comparison?
- Does every distance carry a confidence interval, and is the permutation result stated?
- Is the creativity theme connected explicitly, not decoratively?
- Is the gap stated as a disagreement with existing practice?
- Word count between 1,000 and 1,250 (captions included)?
