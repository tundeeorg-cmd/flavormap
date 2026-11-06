# DH2027: every number the paper uses

Each number in `OUTLINE.md` (v0.2) has a line here. A line stays `[TBD: script]` until
the named script has been run and its output file and git commit are written beside it.
**No number goes into the draft unless it has a filled line here** (reviewer checklist:
"Is every number traceable to a commit or query?").

Fill a line as: `value` · output file · commit · date.

- **RQ1 unit is the region**, not the province (HD-37 C, 2026-11-06). The outline still
  says "province" in Sections 4 and 5, so its wording needs updating to match.
- **Lexicon provenance (2026-11-06).** 302 of 492 entries were drafted by the agent and
  are not reviewed yet. Report every lexicon-dependent number **both ways**: all entries,
  and reviewed only (researcher-drafted or reviewed). Use `make rq1` and
  `make rq1 REVIEWED=1`; `scripts.lexicon_coverage` prints both.
- **HD-44 (decided 2026-11-06):** report `p_unit_shuffle` (region-label shuffle), Holm-adjusted
  across the 4 regions within each scope. Intervals: 9,999 resamples, bias-corrected
  percentile, 95%. The adjustment and the interval type are not built yet.

## Section 3: Data (Table 1)

### Official register
| Number | Value |
|---|---|
| DCP PDFs in the programme year (231 = 3 × 77, from the outline) | [TBD: scripts.inventory_sources] |
| Official recipes loaded | [TBD: scripts.status] |
| Provinces with ≥ 1 official recipe | [TBD: scripts.status] |
| Official recipes in `v_recipes_clean` (high/medium confidence, 3–25 mapped ingredients) | [TBD: scripts.status] |
| Official recipes entering RQ1, by region | [TBD: scripts.run_rq1] |

### Commercial register
| Number | Value |
|---|---|
| Kapook recipes loaded | [TBD: scripts.status] |
| MThai recipes loaded | [TBD: scripts.status] |
| Sanook recipes loaded (0 unless written permission arrives, HD-40) | [TBD: scripts.status] |
| Cross-source pairs flagged as duplicates (HD-41 B), and how many you removed | [TBD: scripts.parse_mthai] |
| Commercial recipes after dedup | [TBD: scripts.status] |
| Commercial recipes with a region label (high + medium) | [TBD: scripts.status] |
| … with a province label | [TBD: scripts.status] |
| Commercial recipes entering RQ1, by region and by source | [TBD: scripts.run_rq1] |

### Domestic register
| Number | Value |
|---|---|
| Interviews completed by submission (target 12) | [TBD: scripts.status] |
| Provinces covered (Nakhon Ratchasima, Buri Ram) | [TBD: scripts.status] |
| Domestic dishes recorded | [TBD: scripts.status] |

## Section 4: Method

| Number | Value |
|---|---|
| Lexicon entries at submission (outline: ~150; target ~400) | [TBD: scripts.lexicon_coverage] |
| Ingredient mentions mapped, all sources (%) | [TBD: scripts.lexicon_coverage] |
| … per source: dcp_food / kapook_cooking / mthai_food (%) | [TBD: scripts.lexicon_coverage] |
| Aliases (mapping decisions) in the lexicon | [TBD: scripts.load_lexicon] |
| Split strings (HD-6 Q5) | [TBD: scripts.load_lexicon] |
| Recipes with mapped ingredients (`recipe_ingredients`) | [TBD: scripts.canonicalise] |
| Lexicon entries drafted by the researcher / by the agent / agent-drafted and reviewed | [TBD: scripts.lexicon_coverage] |
| Mentions mapped: all entries vs reviewed only (%) | [TBD: scripts.lexicon_coverage] |
| Recipes qualifying (3–25 mapped) per register: all entries vs reviewed only | [TBD: scripts.lexicon_coverage] (`qualifying_YYYYMMDD.csv`) |
| Main result rerun on reviewed entries only: does the order of regions change? | [TBD: scripts.run_rq1 --reviewed-only] |
| Permutations per distance (outline: 9,999) | [TBD: scripts.run_rq1] (json: `permutations`) |
| Bootstrap resamples per distance | [TBD: scripts.run_rq1] (json: `bootstrap`) |
| Random seed | [TBD: scripts.run_rq1] (json: `seed`) |
| Sample sizes beside every distance: official vs commercial, per region | [TBD: scripts.run_rq1] |

## Section 5: Preliminary results

Primary = TF-IDF, sensitivity = prevalence (HD-38). Source file: `data/coverage/rq1_registers_YYYYMMDD.csv`.

| Number | Value |
|---|---|
| Official↔commercial distance per region, with 95% bootstrap CI (TF-IDF, pooled) | [TBD: scripts.run_rq1] |
| Median distance across regions | [TBD: scripts.run_rq1] |
| Range of distances across regions | [TBD: scripts.run_rq1] |
| Regions differing more than chance, Holm-adjusted p < 0.05 ("n of N"), region-label shuffle (HD-44) | [TBD: scripts.run_rq1] |
| p-value per region (HD-44's null) | [TBD: scripts.run_rq1] |
| Region where the registers agree most | [TBD: scripts.run_rq1] |
| Region where the registers agree least | [TBD: scripts.run_rq1] |
| Sensitivity: the same per-region distances under prevalence, and whether the order of regions changes | [TBD: scripts.run_rq1] |
| Robustness: Kapook-only distances per region, with n | [TBD: scripts.run_rq1] |
| Robustness: MThai-only distances per region, with n | [TBD: scripts.run_rq1] |
| Figure 1 / Figure 6 caption: recipes per region per register; ingredients shown (top 60 by variance) | [TBD: scripts.make_figure6] |
| Fieldwork: interviews completed; the one early observation, if any | [TBD: scripts.status] |

## Section 7: Limitations

| Number | Value |
|---|---|
| Official dishes per province (3) | [TBD: scripts.status] |
| Commercial portals used | [TBD: scripts.status] |
| Provinces in fieldwork (2) | [TBD: scripts.status] |

## Submission checks

| Number | Value |
|---|---|
| Word count, captions included (1,000–1,250) | [TBD: script — none yet] |
| References verified (count) | [TBD: script — none yet] |
