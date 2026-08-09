# FlavorMap — Build Plan for Claude Code (Full Scope)

**Version:** 2.0 · **Written:** 2026-08-04 · **Supersedes:** v1.0 (compressed 6-month plan)
**Window:** Aug 2026 – Oct 2027 · **Place at repo root as `CLAUDE.md`.**

---

## 0. How to use this document

Spec for an AI coding agent working alongside a Grade 10 student researcher (**the researcher**). Defines what gets built, in what order, with what acceptance criteria.

- **[CC]** — Claude Code executes: scaffolding, parsing, wrangling, plumbing, plotting, deployment.
- **[HD]** — Human Decision. A judgment call the researcher makes and records with written rationale in `docs/decisions.md`. Claude Code implements the decision but never makes it, and never proceeds past an open gate.

There are **20 `[HD]` gates** in the full plan. They are the project's intellectual content — every one appears in the paper and has to be defensible in a university interview.

**Authorship note for the agent:** write clean, idiomatic, documented code. Do not stylize output to imitate a novice, do not stage commit histories, do not introduce deliberate errors. The agent builds machinery; the researcher owns every analytical decision. That only holds if the gates are respected.

---

## 1. Non-negotiable rules

1. **Raw data is immutable.** `raw_*` tables are append-only. Cleaning writes to new tables.
2. **Never fabricate a province.** Attribution failure → `province = NULL`.
3. **Never impute quantities.** "ตามชอบ" → NULL, `has_quantity = false`.
4. **Never merge canonical ingredients without `[HD]` approval.** Similarity produces candidates only.
5. **`make figures` regenerates every number and figure in the paper** from the database.
6. **Every stochastic operation takes an explicit seed** (`RANDOM_SEED = 42` in `src/config.py`).
7. **Respect robots.txt.** 1 req/sec, identifying User-Agent with contact email. Disallowed → source dropped, not worked around.
8. **No personally identifying data enters the database, ever.** No names, contacts, addresses, faces, or GPS-tagged photos. Enforced by tests.
9. **Negative results ship.** If the image classifier performs at baseline, that is the finding. Nothing gets quietly dropped because it didn't work.

---

## 2. Environment and repo

### 2.1 Stack

| Concern | Choice |
|---|---|
| Python | 3.11, `uv` |
| Database | PostgreSQL 15 + PostGIS (Supabase; schema `flavormap`) |
| Lint / types / tests | `ruff`, `mypy` on `src/`, `pytest` |
| Migrations | numbered SQL in `db/migrations/`, applied by `scripts/migrate.py` |
| Scraping | `httpx` + `selectolax`; `playwright` only where JS rendering is confirmed |
| PDF / cookbooks | `pdfplumber`, `pytesseract` (Thai traineddata) for scanned pages |
| LLM | `anthropic` SDK, model pinned in `src/config.py` |
| Analysis | `pandas`, `networkx`, `python-louvain`, `igraph`, `scikit-learn`, `umap-learn`, `scipy`, `geopandas`, `libpysal`, `esda` |
| Vision | `torch`, `torchvision`, `timm` (EfficientNet-B0) |
| API | `fastapi` + `uvicorn`, deployed on Railway |
| Frontend | Next.js 14 + Tailwind, Mapbox GL JS, Sigma.js, deployed on Vercel |
| Paper figures | `matplotlib` (never hand-edited) |

### 2.2 Layout

```
flavormap/
  CLAUDE.md  Makefile  pyproject.toml  .env.example
  db/migrations/
  data/
    raw/            # scraped HTML, cookbook scans — gitignored, backed up
    reference/      # provinces.csv, dialect_groups.csv, dish_province.csv — committed
    photos/         # fieldwork images, EXIF-stripped, gitignored
    processed/      # parquet analysis outputs
    exports/        # HuggingFace release bundle
  src/
    config.py  db.py
    scrape/    base.py doae.py tat.py wongnai.py kapook.py thaitaste.py pantip.py
    ingest/    interview.py cookbook.py photos.py
    clean/     extract.py normalize_th.py canonicalize.py attribute.py dedupe.py quality.py
    analyze/   eligibility.py network.py centrality.py communities.py distinctiveness.py
               cluster.py spatial.py classifier.py sensitivity.py
    vision/    dataset.py train.py evaluate.py
    api/       main.py routers/ schemas.py
    viz/       folium_map.py network_export.py map_data.py
    paper/     figures.py tables.py
  web/                        # Next.js app
  scripts/  tests/  notebooks/  figures/
  docs/  decisions.md  notebook.md  source_audit.md  fieldwork_log.md
```

### 2.3 Makefile targets

```make
setup scrape ingest clean analyze vision figures api web export test
all      # clean analyze figures
verify   # fresh-clone reproducibility check
```

`make all` must run end to end from a fresh clone plus a database dump. Checked at the end of every phase, not once at the end.

---

## 3. Data model

Full DDL in `db/migrations/`. Core tables as in v1.0 (`sources`, `raw_recipes`, `recipes`, `canonical_ingredients`, `ingredient_aliases`, `ingredient_conflations`, `recipe_ingredients`, `province_attribution`, `provinces`, `informants`), plus:

```sql
-- 010  cookbook sources
CREATE TABLE cookbooks (
  cookbook_id    TEXT PRIMARY KEY,
  title_th       TEXT NOT NULL,
  publisher      TEXT,
  year_published INTEGER,
  region_focus   TEXT,
  library_call_no TEXT,
  scanned_pages  INTEGER,
  copyright_status TEXT NOT NULL       -- public_domain | permission_granted | fair_use_excerpt
);

-- 011  fieldwork photos
CREATE TABLE photos (
  photo_id       TEXT PRIMARY KEY,
  informant_id   TEXT REFERENCES informants,
  province_code  TEXT REFERENCES provinces,
  dish_name_th   TEXT,
  subject_type   TEXT NOT NULL,        -- dish | ingredient | preparation
  file_path      TEXT NOT NULL,
  exif_stripped  BOOLEAN NOT NULL,     -- must be true; enforced by test
  consent_photo  BOOLEAN NOT NULL,     -- must be true
  contains_person BOOLEAN NOT NULL     -- must be false
);

-- 012  interview dishes (the qualitative layer)
CREATE TABLE interview_dishes (
  dish_id        BIGSERIAL PRIMARY KEY,
  informant_id   TEXT REFERENCES informants,
  recipe_id      BIGINT REFERENCES recipes,
  distinctiveness_claim TEXT,          -- what the cook says makes it provincial
  differs_from_bangkok TEXT,
  validation_notes TEXT                -- their reaction to scraped recipes from their province
);
```

Analysis view `v_recipes_clean` unchanged from v1.0: `confidence IN ('high','medium')` and `n_ingredients BETWEEN 3 AND 25`.

---

## 4. Scope targets

| | Target | Minimum acceptable |
|---|---|---|
| Recipes total | 2,200–2,600 | 1,540 (20 × 77) |
| Web-scraped | 1,500 | 1,000 |
| Interviews | 25–30 | 18 |
| Interview recipes | 300–500 | 200 |
| Cookbook recipes | 200–300 | 0 (droppable) |
| Institutional | 200–300 | 100 |
| Canonical ingredients | ~400 | 300 |
| Provinces with n ≥ 20 | 50+ | 25 |
| Fieldwork photos | 800+ | 400 (below this, drop the vision component) |

`PROVINCE_MIN_N = 20` still gates province-level analysis via `src/analyze/eligibility.py`. In the full plan province-level is **co-primary** with region-level rather than secondary — but the eligibility gate stays, and every province-level figure caption still auto-prints `n = {k} of 77`.

---

## 5. Phases

| Phase | Window | Content |
|---|---|---|
| 0 | Aug 2026 | Source audit, reference data, advisor, IRB |
| 1 | Aug–Sep 2026 | Thin end-to-end slice, 300 recipes |
| 2 | Sep 2026 – Mar 2027 | Collection at volume: all sources, cookbooks, 25–30 interviews, photos |
| 3 | Apr–May 2027 | Full analysis, all five RQs |
| 4 | Jun–Jul 2027 | Production visualisation + FastAPI + image classifier |
| 5 | Jul–Sep 2027 | Paper, dataset release, reproducibility |
| 6 | Oct 2027 | arXiv, CHR2028 submission, application materials |

**School-calendar reality:** ISB runs a US-style year. Phase 2 spans two school terms at ~5–8 hrs/week — deliberately, because collection is chunky, interruptible work. Phases 3 and 4 land in the summer break, when 20+ hrs/week is possible. That is why analysis is scheduled *after* eight months of collection rather than in the middle: the intense work has to sit where the time actually is.

**Dataset freeze: 31 March 2027.** Hard. Tagged commit plus a database dump. No recipes added after, or the analysis never converges and the paper never gets written.

---

## 6. Phase 0 — Foundations (Aug 2026)

**HD-1** dialect group assignments for ambiguous provinces · **HD-2** land-border definition · **HD-3** the manual source audit and go/no-go.

Exit: `docs/source_audit.md` complete, ≥800 realistically scrapeable recipes confirmed, 77-province reference table loaded with geometry, 3+ advisor emails sent, IRB request drafted.

**Critical path note:** the advisor gates the IRB, the IRB gates the interviews, and the interviews are the eight-month component. Advisor outreach happens in week one, before any code.

---

## 7. Phase 1 — Thin slice (Aug–Sep 2026)

Entire pipeline against one source and 300 recipes. Scraper → extraction → canonicalisation → attribution → network → Folium map.

**HD-4** read 20 recipes, write the defect list · **HD-5** validate 50 extractions by hand · **HD-6** author the first 100 canonical ingredients · **HD-7** set attribution confidence thresholds · **HD-8** centrality plausibility check.

Exit: `make all` runs end to end on 300 recipes; first advisor meeting held with the network on screen.

---

## 8. Phase 2 — Collection at volume (Sep 2026 – Mar 2027)

### 8.1 Remaining scrapers
One module per confirmed source, same `Scraper` protocol. Playwright only for Wongnai if the audit confirms JS hydration. Target 1,500 web recipes.

### 8.2 Cookbook ingestion
`src/ingest/cookbook.py` — `pdfplumber` for born-digital, `pytesseract` with Thai traineddata for scans. Page images retained in `data/raw/cookbooks/`.

**HD-9 — copyright.** Every cookbook gets a `copyright_status` before ingestion. Public-domain and permission-granted texts can be released in the dataset; fair-use excerpts are used for analysis but their text is **not** redistributed — only derived ingredient lists. The researcher decides per book and records it. Cookbooks whose status can't be established are dropped, not risked.

### 8.3 Fieldwork ingestion
`src/ingest/interview.py` — structured YAML per interview → `recipes`, `recipe_ingredients` (`extraction_method='interview'`), `province_attribution` (tier 1, high), `interview_dishes`. Validator **rejects** any file containing a name, phone, email, or free-text field over 500 chars.

`src/ingest/photos.py` — strips all EXIF including GPS before storage, rejects any file where `contains_person` is true or `consent_photo` is false, assigns `photo_id`, resizes to 512px longest edge for storage.

### 8.4 Dictionary to ~400
Weekly batches: embedding candidates → `review_aliases.py` → `[HD]` accept/reject. Coverage target ≥95% of ingredient mentions.

**HD-10** the completed dictionary, reviewed by the advisor before Phase 3.
**HD-11** the validation layer: interview Stage 4 asks cooks to critique scraped recipes from their province. The researcher codes those responses and decides whether any source needs down-weighting or exclusion. This is the project's only external check on web-data quality and it belongs in the paper.

### 8.5 Dedupe and quality
Exact `content_hash`, then Jaccard on canonical ingredient sets > 0.85 **and** fuzzy title ratio > 0.8 → flagged for review. Must run **before** any train/test split or near-duplicates leak across folds.

**HD-12** review the flagged duplicate pairs and set the retention rule (which source wins).

Exit: **dataset frozen 31 March 2027**, tagged and dumped.

---

## 9. Phase 3 — Analysis (Apr–May 2027)

Every module writes to `data/processed/*.parquet`, takes `--seed`, and is called by `make analyze`.

### 9.1 `network.py`
Weighted undirected co-occurrence graph. Edge threshold parameterised; run at 2, 3, 5 with a sensitivity table in the appendix. National graph plus four regional subgraphs. GraphML export.

### 9.2 `centrality.py` (RQ1)
Degree, weighted betweenness, PageRank, eigenvector — **each with a null model**: 1,000 degree-preserving configuration-model rewirings, reported as z-scores. "Garlic is central" without a null is not a finding.

### 9.3 `communities.py` (RQ2)
Louvain across γ ∈ {0.6, 0.8, 1.0, 1.2, 1.5}, 100 seeds each, consensus partition via co-assignment. Leiden via `igraph` as a robustness check. Alignment with `region4` by NMI and ARI, **each against a null from 1,000 label permutations**, reported as a percentile.

### 9.4 `distinctiveness.py` (RQ3)
Raw TF-IDF is confounded by unequal recipes per province. Required correction: bootstrap 1,000 iterations subsampling to `PROVINCE_MIN_N` per province, report mean + 95% percentile CI. Only ingredients whose CI excludes the cross-province median are reported distinctive.

### 9.5 `cluster.py`
UMAP (`n_neighbors=10, min_dist=0.1, metric='cosine'`) **for visualisation only — never as input to a statistical test**. PCA alongside for comparison. K-means k ∈ {4,6,8} with silhouette; Ward hierarchical with dendrogram. All clustering on the full TF-IDF matrix, not the projection.

### 9.6 `spatial.py` (RQ4) — three corrections to the Bible's code

**(a) Moran's I on an interpretable scalar** — per-province distinctiveness score and top-3 ingredient prevalences. Not a UMAP axis; UMAP dimensions carry no interpretable meaning and aren't seed-stable. Queen contiguity, with KNN(k=5) fallback for provinces lacking queen neighbours (Phuket). Report both.

**(b) Mantel by permutation, not `pearsonr`** — 9,999 label shuffles. Correlating upper triangles with a parametric p-value ignores the non-independence the Mantel test exists to handle.

```python
def mantel(d1, d2, n_perm=9999, seed=42):
    idx = np.triu_indices(d1.shape[0], k=1)
    r_obs = pearsonr(d1[idx], d2[idx])[0]
    rng, count = np.random.default_rng(seed), 0
    for _ in range(n_perm):
        p = rng.permutation(d1.shape[0])
        count += abs(pearsonr(d1[np.ix_(p, p)][idx], d2[idx])[0]) >= abs(r_obs)
    return r_obs, (count + 1) / (n_perm + 1)
```

**(c) Partial Mantel — this is what actually answers the research question.** Four matrices over eligible provinces:

| Matrix | Definition |
|---|---|
| `D_culinary` | cosine distance between province TF-IDF vectors |
| `D_geo` | haversine distance between centroids (km) |
| `D_lang` | 0 if same `dialect_group`, else 1 |
| `D_border` | 0 if same `border_country` (both NULL counts as same), else 1 |

Report all partial statistics in one table: culinary~geo controlling for language, culinary~language controlling for geo, and the border variants. The Bible's stated question is geography *versus* trade routes *versus* linguistic boundaries; this table is the only thing in the project that distinguishes between them.

### 9.7 `classifier.py` (RQ5)
Region (4-class) and province (restricted to eligible provinces). LogisticRegression / RandomForest / GradientBoosting. **Baselines always reported:** majority class, and `n_ingredients` alone. **Macro-F1 as headline**, not accuracy — classes are badly imbalanced. 5-fold stratified CV grouped by `content_hash` cluster so near-duplicates can't straddle folds. Permutation feature importance, not Gini.

**Cross-method validation:** rank-correlate the top-20 permutation-importance features against the TF-IDF distinctive ingredients from §9.4. Agreement across independent methods is the strongest evidence in the paper; disagreement is a finding to investigate, not a bug to hide.

### 9.8 `sensitivity.py`
Re-run §9.4–9.7 including `confidence='low'`, and again at `PROVINCE_MIN_N = 30`. One appendix table stating whether conclusions change.

**HD-13** interpret the community structure against known Thai culinary geography · **HD-14** decide which distinctiveness findings are real vs. artifacts of source bias · **HD-15** interpret the confusion matrix — which province confusions are meaningful.

---

## 10. Phase 4 — Production build (Jun–Jul 2027)

### 10.1 API (`src/api/`)
FastAPI on Railway. Endpoints: `/provinces`, `/provinces/{code}`, `/provinces/compare?a=&b=`, `/network?region=`, `/ingredients/{id}`, `/recipes?province=`. All read from materialised parquet/JSON built by `src/viz/map_data.py` — the API never queries Postgres live, so the public site can't be taken down by a database issue. Response caching, CORS locked to the flavormap domain.

### 10.2 Frontend (`web/`)
Next.js + Tailwind, three views per Bible §12: choropleth map (Mapbox GL JS), ingredient network (Sigma.js), province comparison tool. Every province surface displays its recipe count so viewers can see thin support. Deploy to Vercel.

**Ship the Folium prototype publicly first and keep it live** at a stable URL until the production site is reviewed. A working simple map beats a broken sophisticated one, and the prototype is the fallback if the Next.js build slips.

### 10.3 Image classifier (`src/vision/`)
Only if ≥400 usable photos exist. EfficientNet-B0, freeze all but the last two blocks + classifier, region-level 4-class first.

**Leakage is the whole game here.** Splits must be grouped **by informant**, not by photo — two photos of the same cook's same dish in the same kitchen share lighting, plates, and background, and a model that splits by photo will report 90% accuracy while having learned to recognise kitchens. Report: majority-class baseline, macro-F1, per-class recall, and a confusion matrix.

**HD-16** honest read of the vision results. With a few hundred photos, near-baseline performance is the likely and publishable outcome. Report it as such; do not tune until the number looks good.

### 10.4 Reproducibility
`make verify`: fresh clone + database dump + `make all` on a different machine reproduces every number in the paper. Run this in July, not the week before submission.

---

## 11. Phase 5 — Paper and release (Jul–Sep 2027)

### 11.1 Paper
8,000–10,000 words, structure per Bible §15. Written in the order: Methods → Results → Discussion → Limitations → Related Work → Introduction → Abstract. `src/paper/figures.py` and `tables.py` regenerate every figure at 300 dpi with a colourblind-safe palette; nothing is hand-edited.

Figures: F1 centrality with z-scores · F2 community–region alignment with null distribution · F3 dendrogram · F4 UMAP scatter · F5 choropleth · F6 confusion matrix · F7 partial Mantel table · F8 sensitivity · F9 vision confusion matrix (if built).

**HD-17** the limitations section — written by the researcher, not generated. It's the part reviewers read most carefully and the part that has to reflect what she actually knows went wrong.
**HD-18** authorship order and the contribution statement, agreed with the advisor.
**HD-19** the AI-use disclosure. CHR and *Cultural Analytics* both expect one. State plainly that an AI coding assistant built the pipeline and that the researcher made the analytical decisions, with `docs/decisions.md` as the record. This is straightforward to write when it's true, and the decision log is what makes it true.

### 11.2 Dataset release (`make export`)
`data/exports/openflavorth/`: `recipes.csv`, `ingredients_canonical.json`, `provinces.csv`, `network.graphml`, `photos/` (if consent permits), `README.md` data card.

Data card must state: collection dates, source breakdown with counts, confidence-tier distribution, named provinces with thin coverage, fieldwork consent protocol, intended and prohibited uses. Interview data released as anonymised dish-level records only — never transcripts, never anything traceable to an informant. Cookbook-derived rows carry only ingredient lists where copyright status is `fair_use_excerpt`.

**HD-20** final release review: the researcher reads the full export looking for anything identifying before it goes public. Irreversible once published.

---

## 12. Phase 6 — Submission (Oct 2027)

arXiv preprint (cs.SI or cs.CY) posted first — it timestamps priority regardless of venue outcome. Then CHR2028 (deadline expected ~Aug 2027; **verify the actual CFP when it opens** rather than trusting this estimate) and *Journal of Cultural Analytics* in parallel where their policies permit. HuggingFace release live. Repo public with README, license, and citation file.

---

## 13. Tests (`make test`)

| Test | Asserts |
|---|---|
| `test_raw_immutable` | no UPDATE/DELETE targets `raw_*` anywhere in `src/` |
| `test_canonicalize_deterministic` | same input → same canonical_id across runs |
| `test_conflation_guard` | no alias maps across an `ingredient_conflations` pair |
| `test_attribution_precedence` | tier 1 always beats tier 4 |
| `test_clean_view_excludes_low` | zero `confidence='low'` rows in `v_recipes_clean` |
| `test_mantel_recovers_known` | planted r=0.5 on synthetic data → p < 0.01 |
| `test_no_leakage_recipes` | no `content_hash` cluster spans two CV folds |
| `test_no_leakage_photos` | no `informant_id` spans two vision splits |
| `test_no_pii` | no table column matches name/phone/email patterns |
| `test_exif_stripped` | every row in `photos` has `exif_stripped=true`; spot-check files carry no GPS |
| `test_figures_regenerate` | `make figures` produces every file referenced by the manuscript |

---

## 14. Effort and risk

Bible §17 estimates ~415 hours without the vision stretch. Against this calendar: ~215 hours across two school terms at 5–8 hrs/week, plus ~200 hours across the summer at 20–25 hrs/week. The arithmetic works, but only if the summer is genuinely protected. **Grade 11 is the heaviest academic year; the 5 hrs/week term-time cap in Bible §21 is a real constraint, not a guideline.**

The three risks that actually threaten completion, in order:

1. **Advisor never materialises** → no IRB, no interviews, no co-author, no venue credibility. Mitigation: contact 4+ people in week one, offer co-authorship explicitly, escalate at two weeks.
2. **Interviews slip past March** → dataset freeze slips → analysis compresses into term time → paper doesn't get written. Mitigation: 3 interviews/month from Nov, tracked in `docs/fieldwork_log.md`, with Bangkok diaspora cooks as the default (no travel required).
3. **Scope creep into the production frontend** → the Next.js build absorbs the summer that Phase 3 needs. Mitigation: analysis is complete and frozen before any frontend work starts, and the Folium map stays live as the shippable fallback.
