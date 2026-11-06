# DH2027: every number the paper uses

Each number in `OUTLINE.md` (v0.2) has a line here. A line stays `[TBD: script]` until
the named script has been run and its output file and git commit are written beside it.
**No number goes into the draft unless it has a filled line here** (reviewer checklist:
"Is every number traceable to a commit or query?").

Fill a line as: `value` · output file · commit · date.

- **RQ1 unit is the region**, not the province (HD-37 C, 2026-11-06). OUTLINE Sections
  4 and 5 updated to match on 2026-11-06.
- **Minimum n (researcher, 2026-11-06; HD-37 amendment):** a cell with fewer than 5
  commercial recipes is marked **below minimum n**. It is kept, not deleted, and stays in
  its Holm family. `run_rq1` writes `below_min_n`. Cells below: Kapook-only Central (4),
  MThai-only North (4), MThai-only South (3), under both weightings. No pooled cell is
  below.
- **Coverage scope (HD-6, decided 2026-11-06):** the paper reports lexicon coverage over
  RQ1's registers (official + commercial): the `rq1_registers` row of
  `lexicon_coverage`. State-promotional (TAT) coverage is reported separately (58.7%).
  The all-register figure (79.8% after the TAT load) is not the paper's number.
- **Filled 2026-11-06** from the 9,999/9,999 runs at commit 7cedfe2. Numbers only; no
  interpretation is written here. Commercial-side n per region per source are small
  (as low as 3), and are printed beside each distance.
- **Lexicon provenance (2026-11-06).** Report every lexicon-dependent number **both
  ways**: all entries, and reviewed only (researcher-drafted or reviewed). Use `make rq1` and
  `make rq1 REVIEWED=1`; `scripts.lexicon_coverage` prints both.
  *Update 2026-11-06 (later):* all 302 agent-drafted entries are now reviewed by the
  researcher (commit 6950051), so both ways give identical numbers at this commit.
- **HD-44 (revised 2026-11-06):** report `p_register_holm` (register-label shuffle, primary),
  Holm-adjusted across the 4 regions within each scope; `p_unit_holm` (region-label shuffle)
  as secondary. Intervals: 9,999 resamples, bias-corrected percentile, 95%. The primary
  test was chosen after trial results were seen; the paper must say so.

## Section 3: Data (Table 1)

### Official register
| Number | Value |
|---|---|
| DCP PDFs in the programme year (231 = 3 × 77, from the outline) | `231` · PDFs in `data/raw/dcp_food/` (`ls *.pdf | wc -l`) · commit 7cedfe2 · 2026-11-06 |
| Official recipes loaded | `203` · `make status` · commit 7cedfe2 · 2026-11-06 |
| Provinces with ≥ 1 official recipe | `74 of 77` (none: Nakhon Nayok, Nakhon Phanom, Suphan Buri) · `make status` · commit 7cedfe2 · 2026-11-06 |
| Official recipes in `v_recipes_clean` (high/medium confidence, 3–25 mapped ingredients) | `144` · `make status` (RQ2 line) / `v_recipes_clean` · commit 7cedfe2 · 2026-11-06 |
| Official recipes entering RQ1, by region | Central `49`, North `33`, Northeast `34`, South `28` (total `144`) · `rq1_registers_20261106.csv` (all entries) and `…_reviewed.csv` · commit 7cedfe2 · 2026-11-06 |

### Commercial register
| Number | Value |
|---|---|
| Kapook recipes loaded | `1,360` · `recipes` ⋈ `raw_recipes` by source · commit 7cedfe2 · 2026-11-06 |
| MThai recipes loaded | `193` (of 200 posts; 7 multi-section held out, HD-22 rule) · same query · commit 7cedfe2 · 2026-11-06 |
| Sanook recipes loaded (0 unless written permission arrives, HD-40) | `0` · same query · commit 7cedfe2 · 2026-11-06 |
| Cross-source pairs flagged as duplicates (HD-41 B), and how many you removed | `0` flagged (best MThai↔Kapook Jaccard < 0.5 for every post), `0` removed · `make parse-mthai` · commit 18c4aa9 · 2026-11-06 |
| Commercial recipes after dedup | `1,553` · `make status` · commit 7cedfe2 · 2026-11-06 |
| Commercial recipes with a region label (high + medium) | `86` (of which `83` have 3–25 mapped ingredients and enter `v_recipes_clean`) · `province_attribution` query · commit 7cedfe2 · 2026-11-06 |
| … with a province label | `18` · same query · commit 7cedfe2 · 2026-11-06 |
| Commercial recipes entering RQ1, by region and by source | pooled: Central `18`, North `12`, Northeast `35`, South `18` (total `83`); Kapook: `4` (below minimum n) / `8` / `28` / `15`; MThai: `14` / `4` (below minimum n) / `7` / `3` (below minimum n) · `rq1_registers_20261106.csv` (all entries) and `…_reviewed.csv` · commit 7cedfe2 · 2026-11-06 |

### Domestic register
| Number | Value |
|---|---|
| Interviews completed by submission (target 12) | `0` as of 2026-11-06 · `make status` · commit 7cedfe2 · 2026-11-06 |
| Provinces covered (Nakhon Ratchasima, Buri Ram) | `0` as of 2026-11-06 · `make status` · commit 7cedfe2 · 2026-11-06 |
| Domestic dishes recorded | `0` as of 2026-11-06 · `make status` · commit 7cedfe2 · 2026-11-06 |

## Section 4: Method

| Number | Value |
|---|---|
| Lexicon entries at submission (outline: ~150; target ~400) | `492` as of 2026-11-06 · `lexicon_20261106.csv` · commit 7cedfe2 · 2026-11-06 |
| Ingredient mentions mapped, RQ1 registers: official + commercial (%) (HD-6 scope) | `81.4%` (11,462 of 14,084; excluded mentions left out of the share) · `rq1_registers` row of `lexicon_20261106.csv` · commit b5f6d85 · 2026-11-06 (same value as the 'all' row at 7cedfe2, before TAT) |
| State-promotional (TAT), reported separately (%) | `58.7%` (619 of 1,054) · `register:state_promotional` row of `lexicon_20261106.csv` · commit bb94074 · 2026-11-06 |
| … per source: dcp_food / kapook_cooking / mthai_food (%) | `78.6%` / `81.1%` / `84.9%` · `lexicon_20261106.csv` · commit 7cedfe2 · 2026-11-06 |
| Aliases (mapping decisions) in the lexicon | `5,864` · `ingredient_aliases` · commit 7cedfe2 · 2026-11-06 |
| Split strings (HD-6 Q5) | `226` strings (`514` split rows) · `ingredient_alias_splits` · commit 7cedfe2 · 2026-11-06 |
| Recipes with mapped ingredients (`recipe_ingredients`) | `1,716` recipes (`11,584` rows) · `recipe_ingredients` · commit 7cedfe2 · 2026-11-06 |
| Lexicon entries drafted by the researcher / by the agent / agent-drafted and reviewed | `190` / `302` / `302` · `canonical_ingredients.csv` (`drafted_by`, `reviewed_by_bo`) · commit 7cedfe2 · 2026-11-06 |
| Mentions mapped: all entries vs reviewed only (%) | `81.4%` / `81.4%` · `lexicon_20261106.csv` · commit 7cedfe2 · 2026-11-06 |
| Recipes qualifying (3–25 mapped) per register: all entries vs reviewed only | official `144` / `144`; commercial `83` / `83` · `qualifying_20261106.csv` · commit 7cedfe2 · 2026-11-06 |
| Main result rerun on reviewed entries only: does the order of regions change? | No: the two output files are identical in every row, because all 492 entries are reviewed · `rq1_registers_20261106.csv` (all entries) and `…_reviewed.csv` · commit 7cedfe2 · 2026-11-06 |
| Permutations per distance (outline: 9,999) | `9,999` (smallest attainable p = 1/10,000 = 0.0001) · `rq1_registers_20261106.json` · commit 7cedfe2 · 2026-11-06 |
| Bootstrap resamples per distance | `9,999` · `rq1_registers_20261106.json` · commit 7cedfe2 · 2026-11-06 |
| Random seed | `42` · `rq1_registers_20261106.json` · commit 7cedfe2 · 2026-11-06 |
| Sample sizes beside every distance: official vs commercial, per region | see Section 3 rows above · `rq1_registers_20261106.csv` (all entries) and `…_reviewed.csv` · commit 7cedfe2 · 2026-11-06 |

## Section 5: Preliminary results

Primary = TF-IDF, sensitivity = prevalence (HD-38). Source file: `data/coverage/rq1_registers_YYYYMMDD.csv`.

| Number | Value |
|---|---|
| Official↔commercial distance per region, with 95% bootstrap CI (TF-IDF, pooled) | Central `0.568` [0.453, 0.592]; North `0.649` [0.541, 0.649]; Northeast `0.430` [0.286, 0.485]; South `0.494` [0.393, 0.483]. At 4 decimals the observed value lies above its interval in North (0.6494 vs 0.6490) and South (0.4943 vs 0.4832); in Kapook-only South too (0.5217 vs 0.5138). This is the bias-correction limit recorded in HD-44 · `rq1_registers_20261106.csv` (all entries) and `…_reviewed.csv` · commit 7cedfe2 · 2026-11-06 |
| Median distance across regions | `0.531` (mean of 0.494 and 0.568) · `rq1_registers_20261106.csv` (all entries) and `…_reviewed.csv` · commit 7cedfe2 · 2026-11-06 |
| Range of distances across regions | `0.430`–`0.649` · `rq1_registers_20261106.csv` (all entries) and `…_reviewed.csv` · commit 7cedfe2 · 2026-11-06 |
| Regions differing more than chance, Holm-adjusted p < 0.05 ("n of N"), register-label shuffle (primary, HD-44); same under the region-label shuffle (secondary) | primary `4 of 4`; secondary `0 of 4` (TF-IDF, pooled) · `rq1_registers_20261106.csv` (all entries) and `…_reviewed.csv` · commit 7cedfe2 · 2026-11-06 |
| p-value per region: `p_register_holm` (primary), `p_unit_holm` (secondary) | Central `0.0021` / `0.4276`; North `0.0198` / `0.4276`; Northeast `0.0004` / `1.0000`; South `0.0108` / `1.0000` (TF-IDF, pooled) · `rq1_registers_20261106.csv` (all entries) and `…_reviewed.csv` · commit 7cedfe2 · 2026-11-06 |
| Region where the registers agree most | smallest distance: Northeast `0.430` (TF-IDF, pooled) · `rq1_registers_20261106.csv` (all entries) and `…_reviewed.csv` · commit 7cedfe2 · 2026-11-06 |
| Region where the registers agree least | largest distance: North `0.649` (TF-IDF, pooled) · `rq1_registers_20261106.csv` (all entries) and `…_reviewed.csv` · commit 7cedfe2 · 2026-11-06 |
| Sensitivity: the same per-region distances under prevalence, and whether the order of regions changes | Central `0.417`, North `0.484`, Northeast `0.329`, South `0.415`; ascending order Northeast < South < Central < North under both weightings (South and Central differ by 0.0015 under prevalence) · `rq1_registers_20261106.csv` (all entries) and `…_reviewed.csv` · commit 7cedfe2 · 2026-11-06 |
| Robustness: Kapook-only distances per region, with n | Central `0.750` (49 / 4; **below minimum n**), North `0.683` (33 / 8), Northeast `0.439` (34 / 28), South `0.522` (28 / 15); Holm p (primary) 0.1454 / 0.1454 / 0.0004 / 0.0468 · `rq1_registers_20261106.csv` (all entries) and `…_reviewed.csv` · commit 7cedfe2 · 2026-11-06 |
| Robustness: MThai-only distances per region, with n | Central `0.601` (49 / 14), North `0.813` (33 / 4; **below minimum n**), Northeast `0.526` (34 / 7), South `0.643` (28 / 3; **below minimum n**); Holm p (primary) 0.0068 / 0.3465 / 0.4650 / 0.5478 · `rq1_registers_20261106.csv` (all entries) and `…_reviewed.csv` · commit 7cedfe2 · 2026-11-06 |
| Figure 1 / Figure 6 caption: recipes per region per register; ingredients shown (top 60 by variance) | Figure 6: 4 regions × `60` ingredients; recipes per region as in Section 3 (official 49/33/34/28, commercial 18/12/35/18) · `figures/fig6_heatmap.png`, `fig6_heatmap_reviewed.png`; counts in the caption block `figures/fig6_heatmap.json` · commit 7cedfe2 · 2026-11-06 |
| Fieldwork: interviews completed; the one early observation, if any | `0` interviews as of 2026-11-06 · `make status` · commit 7cedfe2 · 2026-11-06 |

## Section 7: Limitations

| Number | Value |
|---|---|
| Official dishes per province (3) | `3` by design; `203` loaded across `74` provinces · `make status` · commit 7cedfe2 · 2026-11-06 |
| Commercial portals used | `2` (Kapook, MThai; Sanook pending permission) · `make status` · commit 7cedfe2 · 2026-11-06 |
| Provinces in fieldwork (2) | `2` planned (HD-32), `0` visited as of 2026-11-06 · `make status` · commit 7cedfe2 · 2026-11-06 |

## Submission checks

| Number | Value |
|---|---|
| Word count, captions included (1,000–1,250) | [TBD: scripts.paper_audit] (`make paper-audit WRITE=1` once `draft.md` exists) |
| References verified (count) | [TBD: scripts.paper_audit] (counts only; verifying is T1.25) |

## T1.24 number audit

`make paper-audit` (`scripts/paper_audit.py`) reads `paper/dh2027/draft.md` and checks
every number in its prose and captions against the value cells of the filled rows above.
It prints the word count (captions in; tables and references out), the reference count,
and each **untraced** number with its line. T1.24 is done when it reports zero untraced.
It exits 2 while any number is untraced. `WRITE=1` fills the two submission-check rows.
