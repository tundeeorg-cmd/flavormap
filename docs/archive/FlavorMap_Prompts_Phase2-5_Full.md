# FlavorMap — Claude Code Prompt Sequence: Phases 2–5 (Full Scope)

**Covers:** Sep 2026 – Sep 2027 · **Prerequisite:** `CLAUDE.md` v2.0 at repo root.
**Phase 0–1 prompts:** carry over unchanged from the earlier sequence, with three edits noted below.

---

## Edits to the Phase 0–1 prompts

1. **P0.2 (source audit)** — audit all six Bible §6 sources plus the National Library cookbook catalogue. Exit criterion rises from 800 to **1,200** realistically scrapeable, since the full plan targets 1,500 web recipes.
2. **P0.3 (reference data)** — unchanged.
3. **P1.x** — unchanged. The thin slice is still 300 recipes from one source. Resist the temptation to widen it because the timeline is longer; the whole value of the slice is that it's small.

Add one prompt at the end of Phase 0:

### P0.4 — Fieldwork tracking

```
Read CLAUDE.md §8.3.

Create docs/fieldwork_log.md — a table tracking interviews: informant_id,
target province, region, recruitment channel, contact made, consent
obtained, interview date, dishes recorded, photos taken, transcribed,
ingested. One row per planned interview, 30 rows, pre-populated with the
target province distribution from Bible §7.

Also scripts/coverage_report.py: prints current recipe count per province
from the database, flags provinces below PROVINCE_MIN_N, and ranks them
by gap size. This is what drives interview targeting — fieldwork goes
where the web data is thinnest.

Files: those two only. No ingestion code yet.
```

Run `coverage_report.py` monthly through Phase 2. It's the instrument that keeps fieldwork pointed at the right provinces.

---

## Phase 2 — Collection at volume (Sep 2026 – Mar 2027)

*Roughly one prompt per month, plus continuous `[HD]` work.*

### P2.1 — Remaining scrapers *(Sep)*

```
Read CLAUDE.md §8.1 and docs/source_audit.md.

Implement one scraper module per confirmed source, all against the
existing Scraper protocol in src/scrape/base.py. Use Playwright ONLY for
sources the audit confirmed are JS-hydrated.

Per module: discover(), fetch(), parse(), plus a tests/ file with a
recorded HTML fixture so parsing is testable offline.

Update scripts/scrape.py to accept --source all and run them sequentially
with per-source rate limits.

Do NOT run at full volume yet. Run each with --limit 50 and report per
source: URLs discovered, parsed cleanly, failed with reason, and what
fraction carry any province or region signal.

Do NOT modify base.py's rate limiting or robots handling.
Do NOT touch extraction, canonicalisation, or attribution.
```

**⛔ HD:** researcher reviews the 50-recipe sample from each source and decides which sources are worth running at volume. A source yielding 5% province signal and messy ingredients may cost more cleaning time than it returns. Record the decision.

Then run at volume. Expect this to take several days of wall-clock time at 1 req/sec.

---

### P2.2 — Cookbook ingestion *(Oct)*

```
Read CLAUDE.md §8.2 and the cookbooks DDL in §3.

Build src/ingest/cookbook.py:
- db/migrations/010_cookbooks.sql
- pdfplumber path for born-digital PDFs
- pytesseract path (Thai traineddata) for scanned pages, with a
  preprocessing step: deskew, binarise, upscale to 300dpi equivalent
- page-range configuration per book (front matter and indexes excluded)
- output: one raw_recipes row per detected recipe, source_type='cookbook',
  with the page image path retained

OCR output will be noisy. Do not attempt to clean it here — write it to
raw_recipes exactly as extracted and let the existing extraction pipeline
handle it. Add a quality flag when OCR confidence is below threshold.

scripts/ingest_cookbook.py CLI: --cookbook-id --pdf --pages.

CRITICAL: refuse to ingest any cookbook whose copyright_status is not set
in the cookbooks table. Raise, don't warn.

Files: src/ingest/cookbook.py, the migration, the script, tests using a
synthetic scanned page fixture.
```

**⛔ HD-9:** researcher establishes copyright status per book before ingestion and records the reasoning. Books whose status can't be established are dropped.

---

### P2.3 — Fieldwork ingestion *(Oct)*

```
Read CLAUDE.md §8.3 and rule 8 in §1.

1. src/ingest/interview.py + db/migrations/012_interview_dishes.sql.
   Input: one YAML file per interview at data/interviews/{informant_id}.yaml
   with informant metadata (province, age_bracket, consent flags, dates)
   and a list of dishes, each with name_th, ingredient list as recorded,
   cooking method, distinctiveness_claim, differs_from_bangkok.

   Writes to recipes, recipe_ingredients (extraction_method='interview',
   human_validated=true), province_attribution (tier 1, high),
   interview_dishes, informants.

   VALIDATOR — reject the file, with a clear error, if it contains:
   any key matching name/phone/email/address/line_id, any free-text field
   over 500 chars, any consent flag not explicitly true, or an
   informant_id not matching the pattern INT_{PROVINCE}_{NNN}.

2. src/ingest/photos.py + db/migrations/011_photos.sql.
   - strip ALL EXIF including GPS before storage (piexif or Pillow)
   - reject if consent_photo is false or contains_person is true
   - resize to 512px longest edge, convert to JPEG quality 88
   - store at data/photos/{province_code}/{photo_id}.jpg

3. Write data/interviews/TEMPLATE.yaml with inline comments, so the
   researcher can fill one in during or right after each interview.

4. tests: PII rejection cases, EXIF actually stripped from a fixture with
   GPS tags, consent enforcement.
```

**Continuous through Phase 2:** 3 interviews/month from November. Update `docs/fieldwork_log.md` after each. Run `coverage_report.py` monthly and let it retarget the next month's interviews.

---

### P2.4 — Extraction and canonicalisation at volume *(Nov–Jan)*

```
Read CLAUDE.md §8.4.

The extraction and canonicalisation pipelines already exist from Phase 1.
This prompt scales them.

1. Add batch orchestration to scripts/clean.py: process in chunks of 200
   with resumability, progress reporting, and a per-source error summary.
   The response cache must mean a re-run after a crash costs nothing.

2. Extend scripts/review_aliases.py: --batch-size flag, sorted by
   frequency-weighted score so the researcher reviews high-impact
   candidates first, and a --stats mode reporting current coverage
   (what % of ingredient mentions map to an approved canonical ID).

3. Add src/clean/coverage.py: reports unmapped ingredients ranked by
   frequency. This is the worklist for growing the dictionary from 100
   toward 400.

4. Run extraction across everything ingested so far. Report the error
   rate per source — OCR'd cookbook text will be materially worse than
   scraped HTML and that difference should be quantified, not averaged
   away.

Do NOT auto-approve any alias. Candidates only.
```

**⛔ HD-10:** the dictionary reaches ~400 entries through weekly review batches, one `decision_note` per boundary drawn. Advisor reviews the completed dictionary before Phase 3. This is the single largest `[HD]` time cost in the project (~40 hours cumulative) and the thing every downstream result depends on.

---

### P2.5 — Attribution, dedupe, quality at volume *(Feb)*

```
Read CLAUDE.md §8.5.

1. Extend data/reference/dish_province.csv from 40 to ~200 entries.
   Generate candidates from recipe names in the database that contain a
   province name or a known province-encoded pattern, and write them to
   a review file — do NOT add them to the reference CSV directly.

2. src/clean/dedupe.py: exact content_hash, then Jaccard > 0.85 on
   canonical ingredient sets AND fuzzy title ratio > 0.8. Flagged pairs
   go to a duplicate_candidates table with both recipe_ids and scores.
   scripts/review_duplicates.py for accept/reject.

   Assign a cluster_id to every retained recipe (singletons get their
   own). This cluster_id is what CV folds group on later — without it
   the classifier results are inflated.

3. src/clean/quality.py: flag ingredient_count outside 3–25, recipes
   whose ingredients are >50% unmapped, OCR-confidence-low rows.

4. Re-run attribution across the full corpus. Print the full report:
   tier distribution, confidence distribution, per-province counts,
   provinces clearing PROVINCE_MIN_N.

Files as listed. Do NOT start any analysis module.
```

**⛔ HD-12:** review flagged duplicate pairs, set the source-precedence rule for which copy is retained.
**⛔ HD-11:** code the interview validation responses (Stage 4 — cooks critiquing scraped recipes from their province) and decide whether any source needs down-weighting. Record it; this is the paper's only external check on web-data quality.

---

### P2.6 — Freeze *(31 Mar 2027)*

```
Read CLAUDE.md §8.5 exit criteria.

1. scripts/freeze_dataset.py: runs the full clean pipeline, verifies the
   test suite passes, dumps the database to
   data/exports/frozen_YYYYMMDD.sql.gz, writes a manifest with row counts
   per table, and creates an annotated git tag.

2. Print the final dataset summary: total recipes, breakdown by
   source_type, tier and confidence distribution, canonical ingredient
   count, coverage %, provinces clearing PROVINCE_MIN_N, photo count by
   province.

3. Append that summary to docs/notebook.md under "Dataset freeze".

After this runs, no recipe is added. If something is missing, it is
documented as a limitation, not backfilled.
```

---

## Phase 3 — Analysis (Apr–May 2027)

*Each prompt is one analysis module. Run them in order; each depends on the last.*

### P3.1 — Eligibility and network

```
Read CLAUDE.md §4 and §9.1.

1. src/analyze/eligibility.py: computes eligible_provinces
   (n >= PROVINCE_MIN_N from v_recipes_clean), caches to
   data/processed/eligibility.parquet, and exposes a decorator or guard
   that province-level modules call. If len(eligible_provinces) < 25,
   emit a prominent warning — do not silently produce partial results.

2. src/analyze/network.py: weighted undirected co-occurrence graph.
   --threshold parameter; build at 2, 3, 5. National + four regional
   subgraphs. GraphML + parquet edge list output.

3. tests: undirected, no self-loops, every node in canonical_ingredients,
   edge weights match a hand-computed value on a 10-recipe fixture.

Report: node and edge counts at each threshold, for the national graph
and each regional subgraph.
```

### P3.2 — Centrality with null models *(RQ1)*

```
Read CLAUDE.md §9.2.

src/analyze/centrality.py: degree, weighted betweenness, PageRank,
eigenvector.

REQUIRED: for each metric, generate 1,000 degree-preserving
configuration-model rewirings (networkx double_edge_swap, seeded) and
report each ingredient's observed value as a z-score against that null
distribution. Raw centrality values alone are not reportable.

Output: data/processed/centrality.parquet with raw value, null mean,
null sd, z-score, and empirical p per ingredient per metric, joined to
Thai and English names.

Print the top 25 by betweenness z-score.
```

**⛔ HD-8 revisited:** plausibility check at full scale. Garlic, shallot, fish sauce, chili near the top. If not, canonicalisation broke somewhere between 100 and 400 entries.

### P3.3 — Communities *(RQ2)*

```
Read CLAUDE.md §9.3.

src/analyze/communities.py:
- Louvain at gamma in {0.6, 0.8, 1.0, 1.2, 1.5}, 100 seeds each
- consensus partition via co-assignment matrix thresholded at 0.5
- Leiden via igraph as a robustness check; report agreement with Louvain
- alignment with region4 by NMI and ARI
- REQUIRED: null distribution from 1,000 region-label permutations for
  both metrics; report the observed value's percentile

Output: partition assignments, modularity per gamma, alignment table
with nulls.

Print: number of communities at each gamma, and the alignment table.
```

**⛔ HD-13:** the researcher names and interprets each detected community against known Thai culinary geography. An algorithm produces clusters; only she can say whether cluster 3 is "Southern Muslim-influenced" or an artifact.

### P3.4 — Distinctiveness *(RQ3)*

```
Read CLAUDE.md §9.4.

src/analyze/distinctiveness.py — bootstrap-corrected TF-IDF:
- province documents built from canonical ingredient IDs
- 1,000 bootstrap iterations, each subsampling exactly PROVINCE_MIN_N
  recipes per eligible province without replacement
- report per (province, ingredient): mean TF-IDF, 95% percentile CI
- an ingredient is "distinctive" only if its CI lower bound exceeds the
  cross-province median

Also compute an overall per-province distinctiveness scalar (mean of the
top-10 distinctive ingredient scores) — spatial.py needs it.

Output parquet + a printed top-10 table for the 10 highest-scoring
provinces.

Do NOT report raw uncorrected TF-IDF anywhere. Unequal recipe counts
make it uninterpretable.
```

**⛔ HD-14:** decide which distinctiveness findings are real and which reflect source bias — a province represented mainly by one tourism site will look distinctive for that site's editorial habits.

### P3.5 — Clustering

```
Read CLAUDE.md §9.5.

src/analyze/cluster.py:
- province TF-IDF matrix over eligible provinces
- UMAP (n_neighbors=10, min_dist=0.1, metric='cosine', seeded) FOR
  VISUALISATION ONLY — never as input to a statistical test
- PCA alongside, with explained variance reported
- KMeans k in {4,6,8}, silhouette scores, on the FULL matrix
- Ward hierarchical clustering + dendrogram data

Output: embeddings, cluster labels, linkage matrix.

Print silhouette scores and, for k=4, the province membership of each
cluster next to its region4 label.
```

### P3.6 — Spatial *(RQ4 — the headline)*

```
Read CLAUDE.md §9.6 carefully, including all three corrections.

src/analyze/spatial.py:

1. Moran's I on INTERPRETABLE scalars: per-province distinctiveness score
   and top-3 individual ingredient prevalences. Queen contiguity weights
   from provinces.geom, plus a KNN(k=5) fallback matrix. Report both.
   Never on a UMAP dimension.

2. mantel(d1, d2, n_perm=9999, seed) by permutation, exactly as
   specified in §9.6(b). Not scipy.stats.pearsonr on upper triangles.

3. Four distance matrices over eligible provinces: D_culinary, D_geo,
   D_lang, D_border, per the table in §9.6(c).

4. Partial Mantel for every meaningful pairing, controlling for the
   third matrix. Output one table: pair, controlled-for, r, p, n.

5. tests: mantel recovers a planted r=0.5 at p<0.01 on synthetic data;
   D_lang is symmetric with zero diagonal; every eligible province
   appears in every matrix.

Print the full partial Mantel table. This is the paper's headline result.
```

### P3.7 — Classifier and sensitivity *(RQ5)*

```
Read CLAUDE.md §9.7 and §9.8.

src/analyze/classifier.py:
- multi-hot canonical ingredient features
- region (4-class) primary; province secondary, eligible provinces only
- LogisticRegression(L2), RandomForest, GradientBoosting
- BASELINES, always reported: majority class, and n_ingredients alone
- StratifiedGroupKFold(n_splits=5) grouped on cluster_id from dedupe —
  near-duplicates must not straddle folds
- headline metric MACRO-F1, with accuracy reported alongside
- permutation importance (not Gini), 30 repeats
- confusion matrices at both levels

Then: rank-correlate top-20 permutation-importance ingredients against
the distinctiveness ranking from P3.4. Report Spearman rho.

src/analyze/sensitivity.py: re-run P3.4 through P3.7 with
confidence='low' included, and again at PROVINCE_MIN_N=30. Output one
table stating whether each conclusion holds.

Print: baseline vs model macro-F1 at both levels, and the cross-method
rho.
```

**⛔ HD-15:** interpret the confusion matrix. Which province confusions reflect real shared culinary tradition, which reflect thin data? Surin/Sisaket confusion is a finding; a province with n=21 being confused with everything is a data limitation.

### P3.8 — Figures and lock

```
Read CLAUDE.md §11.1.

src/paper/figures.py and tables.py: regenerate F1-F8 at 300dpi with a
colourblind-safe palette, plus every LaTeX/markdown table the manuscript
needs, all from data/processed/. Wire `make figures`.

Then run `make verify`: fresh clone + the frozen dump + `make all`, and
confirm every figure and number reproduces bit-identically where
deterministic and within tolerance where stochastic.

Report anything that doesn't reproduce. That is a bug, not a rounding
issue.
```

---

## Phase 4 — Production build (Jun–Jul 2027)

### P4.1 — Data layer for the web app

```
Read CLAUDE.md §10.1.

src/viz/map_data.py: materialise everything the public site needs as
static JSON in data/exports/web/:
- provinces.json (geometry simplified to ~50KB total, cluster labels,
  top distinctive ingredients with CIs, recipe count, region)
- network.json (Sigma.js format: nodes with size/color/community, edges
  with weight; a filtered version per region)
- comparisons.json (pairwise culinary distances)
- recipes_sample.json (5 per province, no source URLs for interview data)

CRITICAL: no informant_id, no interview free text, no personal data of
any kind reaches these files. Add a test asserting it.

Every province object includes n_recipes so the UI can display support.
```

### P4.2 — FastAPI

```
Read CLAUDE.md §10.1.

src/api/: FastAPI serving the static JSON from P4.1 — endpoints
/provinces, /provinces/{code}, /provinces/compare, /network,
/ingredients/{id}, /recipes. Pydantic response schemas. Response caching.
CORS restricted to the flavormap domains. Health check endpoint.
Dockerfile + railway.toml.

The API must NEVER query Postgres at request time. It loads the
materialised JSON at startup. The public site must survive a database
outage.

Tests for every endpoint against the real exported data.
```

### P4.3–P4.5 — Frontend

Three prompts, one per view, in this order: choropleth map (Mapbox GL JS) → ingredient network (Sigma.js) → comparison tool. Each specifies the endpoint it consumes, the interaction spec from Bible §12, and a hard requirement that recipe counts are visible on every province surface.

```
Read CLAUDE.md §10.2 and Bible §12 View {N}.

Build web/ (Next.js 14 App Router + Tailwind) — View {N} only.
{view-specific interaction spec}

Requirements across all views:
- every province surface displays n_recipes; thin support must be visible
- loading and error states for every data fetch
- mobile-responsive; an admissions reader may open this on a phone
- no client-side secrets; the Mapbox token is a public scoped token

Do NOT build the other two views in this session.
Do NOT take down or break the Folium prototype deployment.
```

### P4.6 — Vision dataset

```
Read CLAUDE.md §10.3.

Only proceed if the photos table has >= 400 rows. Check first and stop
if not, reporting the count.

src/vision/dataset.py: PyTorch Dataset over data/photos/, region and
province labels, standard EfficientNet transforms, augmentation
(RandomResizedCrop, HorizontalFlip, ColorJitter) on train only.

CRITICAL — splits are grouped BY INFORMANT, not by photo. Two photos
from the same cook share kitchen, lighting, and plates; splitting by
photo teaches the model to recognise kitchens and reports a fake number.
Use GroupShuffleSplit on informant_id. Add a test asserting no
informant_id appears in two splits.

Report: photos per region, per province, per informant, and the
resulting split sizes.
```

### P4.7 — Vision training and honest evaluation

```
Read CLAUDE.md §10.3 and rule 9 in §1.

src/vision/train.py: EfficientNet-B0 from timm, freeze all but the last
two blocks + classifier, region-level 4-class. AdamW, cosine schedule,
early stopping on validation macro-F1, seeded.

src/vision/evaluate.py: MUST report, in this order:
1. majority-class baseline
2. model macro-F1 and per-class recall
3. confusion matrix
4. the gap between train and validation performance

With a few hundred photos across four classes, near-baseline performance
is the likely outcome. Report the number you get. Do not tune
hyperparameters against the test split, do not re-split until the number
improves, and do not drop the component if it underperforms — a negative
result is a finding and it goes in the paper.
```

**⛔ HD-16:** honest read of the vision results, written into `docs/decisions.md` before any further tuning.

---

## Phase 5 — Paper and release (Jul–Sep 2027)

### P5.1 — Dataset export

```
Read CLAUDE.md §11.2.

scripts/export_dataset.py building data/exports/openflavorth/:
recipes.csv, ingredients_canonical.json, provinces.csv, network.graphml,
photos/ (only where consent_photo and no person), README.md data card.

The data card is generated from the database, not hand-written: real
collection dates, real source counts, real tier distribution, the actual
list of provinces below PROVINCE_MIN_N by name, coverage percentages.
The bias section is a template the researcher completes.

EXCLUSIONS, enforced by test: no informant_id, no interview free text,
no source_url for interview rows, no cookbook text where
copyright_status='fair_use_excerpt' (derived ingredient lists only).

Print a manifest with row counts and file sizes.
```

**⛔ HD-20:** the researcher reads the entire export looking for anything identifying before publication. Irreversible once live.

### P5.2 — Repository publication

```
Read CLAUDE.md §12.

Prepare the repo for public release:
- README with the research questions, findings summary, reproduction
  instructions, and a link to the paper and dataset
- CITATION.cff
- LICENSE (MIT for code; CC-BY-4.0 for data, noted separately)
- .env.example verified complete; scan git history for any committed
  secret and report anything found
- docs/decisions.md tidied into a readable decision log
- scrub data/interviews/ and data/photos/ from any tracked path;
  verify with git log --all --full-history

Run `make verify` one final time and report.
```

---

## Prompt count and gate load

| Phase | Prompts | `[HD]` gates | Researcher hours |
|---|---|---|---|
| 0 | 4 | HD-1,2,3 | ~8 |
| 1 | 6 | HD-4,5,6,7,8 | ~16 |
| 2 | 6 | HD-9,10,11,12 | ~90 (dictionary + fieldwork dominate) |
| 3 | 8 | HD-13,14,15 | ~35 |
| 4 | 7 | HD-16 | ~25 |
| 5 | 2 | HD-17,18,19,20 | ~50 (paper writing) |
| **Total** | **33** | **20** | **~225** |

Plus roughly 190 hours of interviews, transcription, and reading — which is where the Bible's 415-hour estimate lands, and which is not coding work at all.

The ratio holds throughout: about seven hours of the researcher's judgment for every coding session. That is what makes the project hers.
