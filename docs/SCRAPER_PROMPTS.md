# FlavorMap — Claude Code Scraper Prompts

**Version:** v2 · 12 Oct 2026 · Use with `docs/TIMELINE.md` (v3) and `CLAUDE.md`

## Status of sources (12 Oct 2026)

| # | Source | Status | What to run |
|---|---|---|---|
| 6 | Kapook | Collected + loaded (1,360 recipes) | Prompt 6 (label yield, no crawl) |
| 4 | Sanook | **Collected 7 Oct** (`data/raw/sanook_food/`), not loaded | **Prompt P** (post-collection), not prompt 4 |
| 5 | MThai | **Collected 7 Oct** (`data/raw/mthai_food/`), not loaded | **Prompt P** |
| 9 | TAT | **Collected 7 Oct** (`data/raw/tat_food/`), not loaded | **Prompt P**; register = HD-register |
| 7/8 | Ministry of Culture | **Collected 7 Oct** (`data/raw/m_culture/`), not loaded | **Prompt P**; register = HD-register |
| 10 | bookfood67 | CSV on disk (`gdcatalog/`) | Prompt 10 (profile only) — after 1 Nov |
| 1, 2, 3 | Wongnai, Cookpad, Krua | Not collected | **Frozen until after 13 Dec** — the commercial register already exceeds the ~550 web target |
| 11–15 | English sites, Pantip, YouTube | Not collected | Not this cycle |

## How to use

1. Run **Prompt 0 once** (shared rules), if `docs/scraping_rules.md` doesn't exist yet.
2. For the four folders already collected, run **Prompt P** once per source — it audits, inventories and loads
   existing files without re-crawling. This is timeline tasks T1.13a, T1.13b and T1.13e.
3. Site prompts 1–15 are for **new** crawls only, each in 3 stages with a stop after each:
   (A) ethics audit → (B) 20-recipe pilot → (C) full crawl.

---

## Prompt P — Post-collection audit and load (already-scraped folders)

Run once per source: `sanook_food`, `mthai_food`, `tat_food`, `m_culture`.

```
Read docs/TIMELINE.md (§0, §2.1, §6.3), docs/scraping_rules.md (if present), CLAUDE.md
and ETHICS.md. Source folder: data/raw/<SOURCE>/. DO NOT fetch anything from the web
except robots.txt and the Terms page for the ethics row.

Stage 1 — Inventory (T1.13a), read-only:
- Count files by type; check for a manifest (url, fetched_at, http_status, hash). If
  missing, build one from the files on disk (url from page metadata where present).
- Count distinct pages and distinct recipes (split multi-recipe articles; keep
  recipe_index_in_article).
- Field fill rates: title, published_at, site category/tags, region-claim text,
  province-claim text, ingredient lines, servings.
- Flag personal data present in raw pages (author names, usernames, phone, LINE IDs,
  emails, comments) — report counts only, never print the values.
- For tat_food and m_culture: are these recipes with ingredient lists, or dish
  lists / descriptions? Give 5 anonymised examples.
- Write data/coverage/sources_<YYYYMMDD>.md (append a section for this source) and
  fill the [TBD] cells for this source in docs/TIMELINE.md §2.1.

Stage 2 — Ethics backfill (T1.13b):
- Fetch robots.txt and the Terms of Use page today; quote the relevant clauses.
- Add a dated ETHICS.md row. State honestly whether robots/ToS were checked before
  the 7 Oct collection (check git history and docs); if not, label it
  "retrospective audit, <date>".
- If the terms forbid automated collection or reuse: mark the source EXCLUDED in
  docs/source_audit.md, keep files local only, and STOP.

STOP after Stage 2 and report. I will make HD-register / HD-sources / HD-dedup /
HD-balance decisions in docs/decisions.md.

Stage 3 — Load (T1.13e), only after the relevant decisions are DECIDED:
- Add a row to the sources table. Parser in src/ingest/<source>.py with tests on 3
  PII-free fixtures.
- Run the PDPA filter before every DB write. Store: title, published_at, site
  category/tags, region/province claim text, ingredient lines verbatim. Never store
  method prose, author names, comments or photos.
- Register exactly as decided (commercial for Sanook/MThai; HD-register for TAT and
  m-culture). Do not write province_attribution — that is T1.15.
- After loading: measure cross-source duplicates (ingredient-set Jaccard) against all
  commercial sources and report the distribution before applying HD-dedup.
- pytest, ruff, mypy green; make db-dump; off-laptop backup; commit
  "data: load <source> (<n> recipes)".
Report counts loaded, excluded and duplicated.
```

---

**Priority for new crawls (after 13 Dec only):**

| Priority | Sites | Why |
|---|---|---|
| First | 1 Wongnai or 2 Cookpad | Regional tags and dates |
| Later / optional | 3 Krua | Editorial quality |
| Not this cycle | 11–13 English sites, 14 Pantip, 15 YouTube | New register or heavy PDPA risk |

---

## Prompt 0 — Shared scraping rules (run once)

```
Read docs/TIMELINE.md §0, CLAUDE.md, ETHICS.md and src/scrape/conduct.py.

Create docs/scraping_rules.md that every scraper in this repo must follow, then
refactor src/scrape/conduct.py (or add src/scrape/base.py) so the rules are enforced
in code, not just documented. Rules:

1. ETHICS FIRST. Before any crawl: fetch robots.txt and the Terms of Service / Terms of
   Use page, quote the relevant clauses, and add a dated row to the ETHICS.md audit
   table (site, date, robots result, ToS result, decision). If the ToS forbids automated
   collection or reuse, STOP and report. Never bypass logins, paywalls, CAPTCHAs,
   rate limits or premium content.
2. POLITENESS. Max 1 request per 1.5 s (randomised 1–2 s), one connection per site,
   honest User-Agent "FlavorMapResearch/1.0 (+https://github.com/tundeeorg-cmd/flavormap; contact email)",
   exponential back-off on 429/5xx, stop the crawl after 5 consecutive errors.
3. CACHE. Raw HTML saved to data/raw/<source_slug>/ (gitignored), with a manifest CSV:
   url, url_sha1, fetched_at (UTC ISO), http_status, bytes, content_sha256.
   Re-runs read from cache; never re-fetch a cached page without --refresh.
4. WHAT TO STORE (per recipe, into raw_recipes with the source's source_id):
   - url, title_th (verbatim), published_at (if shown; else NULL — never guessed),
     scraped_at, site_category (verbatim), site_tags (verbatim list)
   - region_claim_text and province_claim_text: the exact text span that claims a
     region/province (title, tag, breadcrumb or intro sentence), with its location
   - ingredient lines verbatim (quantity + unit + name as written), in order
   - servings if shown
   NEVER store: method/instruction prose, author names or usernames, profile links,
   comments, photos, phone numbers, emails, addresses. recipes.method_text stays empty.
5. PDPA. Run src/ingest/pdpa.py on every record before any DB write. The existing
   tests/test_pdpa.py whole-database scan must pass after every load.
6. NO DECISIONS. Do not assign register, province labels or dish categories beyond
   copying the site's own claims. Province attribution follows the decided HD-Kapook
   rules in docs/decisions.md; if a new source needs a different rule, write an OPEN
   entry and stop.
7. THAI TEXT. Normalise Unicode (NFC), apply the existing sara-am repair, keep the
   original string alongside any normalised one.
8. STAGES. Every site scraper supports --audit, --pilot N (default 20) and --full
   --limit N. After --pilot, write data/coverage/<source>_pilot.md with field fill
   rates (published_at, site_category, region/province claim, ingredient lines) and
   5 example records, then STOP for review.
9. TESTS. Each scraper gets parser tests on 3 saved fixture pages (fixtures contain no
   personal data). pytest, ruff and mypy green before commit.
10. AFTER A FULL CRAWL: make db-dump, off-laptop backup, update data/coverage/status,
    commit with a message stating source, count and date.

Commit docs/scraping_rules.md and the enforcement code with tests. Report what changed.
```

---

## Site prompt template (used by all prompts below)

Each site prompt below is the **site-specific part**. Paste it after this line:

```
Follow docs/scraping_rules.md exactly. Source slug: <slug>. Run stage A (--audit) now,
add the ETHICS.md row, and STOP with a report. I will approve stages B and C separately.
```

---

## 1 — Wongnai Cooking · `wongnai.com/cooking`

```
Source slug: wongnai_cooking. Register: commercial.
Goal: Thai recipes with regional labels and publish dates.

Discovery: start from Wongnai Cooking's regional cookbooks/collections (e.g. the
"isan-food-recipes" cookbook) and search/category pages for อาหารเหนือ, อาหารอีสาน,
อาหารใต้, อาหารภาคกลาง, and each of the 77 province names. Discover the real URL
patterns from the pages; do not guess IDs.
robots.txt (checked 6 Oct 2026) disallows /users/ only — never fetch /users/ pages,
and do not store author names. Still read and quote the Wongnai Terms of Use.
Capture: title, publish date shown on the page, cookbook/collection name as
region_claim_text, ingredient lines, tags.
Target: up to 300 recipes, prioritising those with a region or province claim.
Report the fraction with region claims and with province claims in the pilot.
```

## 2 — Cookpad Thailand · `cookpad.com/th`

```
Source slug: cookpad_th. Register: commercial (home-cook uploads).
Goal: home-cook recipes naming local dishes, provinces or regions.

robots.txt (checked 6 Oct 2026) allows /th recipe pages but disallows
/*/recipes/*/reactions, /similar_recipes, /newer_premium_recipes,
/cooksnaps_section and /print — never fetch those, and never fetch premium recipes.
Read and quote the Cookpad Terms of Service; if they prohibit automated collection,
STOP — do not proceed to the pilot.
Discovery: Cookpad search for อาหารเหนือ / อาหารอีสาน / อาหารใต้ / อาหารพื้นบ้าน and
each of the 77 province names (+ "อาหาร<province>"). Record which query found each
recipe in a found_by_query field.
PDPA: Cookpad pages are user-generated. Do NOT store usernames, profile URLs, bios,
cooksnaps, comments or photos. Run the PDPA filter on ingredient lines too (users
sometimes write phone numbers or LINE IDs).
Capture: title, publish date, tags, region/province claim text, ingredient lines.
Target: up to 300 recipes with a region or province claim.
```

## 3 — Krua.co · `krua.co`

```
Source slug: krua_co. Register: commercial (editorial/magazine).
Goal: editorial recipes, especially regional food features.

Check robots.txt (it uses Content Signals; record the search/ai-input/ai-train
signals verbatim) and the site's terms. Some content may be paywalled or
members-only — skip anything behind a login.
Discovery: recipe sections and regional articles (อาหารเหนือ, อาหารอีสาน, อาหารใต้,
อาหารพื้นบ้าน, อาหารถิ่น). Capture the article/section heading as region_claim_text.
Capture: title, publish date, section/category, ingredient lines.
Target: up to 200 recipes.
```

## 4 — Sanook food · `sanook.com`

```
Source slug: sanook_food. Register: commercial (mainstream portal).
Discovery: locate Sanook's recipe/cooking section from the site navigation; crawl
only recipe articles (skip news, ads, sponsored posts). Record the article tags.
Capture: title, publish date, tags, region/province claim, ingredient lines.
Many articles list several recipes — split into one record per recipe and record
recipe_index_in_article.
Target: up to 200 recipes with a region claim.
```

## 5 — MThai food · `mthai.com`

```
Source slug: mthai_food. Register: commercial (mainstream portal).
Same approach as Sanook: find the cooking/recipe section from navigation, recipe
articles only, one record per recipe, tags verbatim, publish date if shown.
Report in the audit whether the section is still active (last publish date) —
if nothing new since 2020, flag it as a historical archive in the pilot report.
Target: up to 200 recipes.
```

## 6 — Kapook Cooking · `cooking.kapook.com` (already scraped)

```
Source slug: kapook_cooking. NO NEW CRAWLING.
The 2,702 cached pages / 1,360 recipes are already in raw_recipes and recipes.
Task: T1.13 from docs/TIMELINE.md. From the cached HTML only, extract every
region_claim_text and province_claim_text (title, category, tags, breadcrumb,
intro sentence) into raw_recipes. Measure the yield of three rule families:
(a) explicit province names, (b) regional words (เหนือ/อีสาน/ใต้/กลาง/ล้านนา/ปักษ์ใต้),
(c) dish-name match against official DCP dish names.
Report counts per province and per region. Do NOT write province_attribution —
that waits for my HD-Kapook decision.
```

## 7 — Ministry of Culture intangible heritage database (ICH)

```
Source slug: ich_culture. Register: DO NOT ASSIGN — write an OPEN decision entry
(HD-register-ICH): is this "official" (state-curated, like DCP) or a separate
"heritage" register? Stop after the audit until I decide.
Goal: food-related intangible cultural heritage entries with province labels.
Discovery: find the Ministry of Culture's intangible cultural heritage
(มรดกภูมิปัญญาทางวัฒนธรรม) database and its food / ความรู้และแนวปฏิบัติเกี่ยวกับธรรมชาติ
และจักรวาล / อาหารและโภชนาการ category. Verify the official domain before crawling.
Check whether an open-data download or API exists on data.go.th first — if it does,
use it instead of scraping and record the dataset URL and licence.
Capture: entry title, province, region, category, year registered/announced,
ingredient lines if present, and the description's ingredient mentions only
(no full prose).
Target: all food entries.
```

## 8 — Provincial culture offices · `<province>.m-culture.go.th` (สำนักงานวัฒนธรรมจังหวัด)

```
Source slug: provincial_culture. Register: DO NOT ASSIGN (same HD-register question
as ICH — add this source to that entry).
Goal: local dish pages for each of the 77 provinces.
Discovery: find each provincial culture office website (verify the official domain
pattern first; list all 77 with status in data/coverage/provincial_culture_sites.csv:
found / not found / no food pages). Then find their local food pages
(อาหารพื้นถิ่น, อาหารพื้นบ้าน, อาหารประจำจังหวัด, ของดีประจำจังหวัด).
Many pages are PDFs or images — save them; extract text with the existing PDF
pipeline; list image-only pages separately for a later decision (no OCR).
Capture: province (from the office, not inferred), dish name, district if given,
ingredient lines if given, page date if shown.
Target: as many of the 77 provinces as possible; report coverage per region.
```

## 9 — TAT and provincial tourism pages

```
Source slug: tat_food. Register: DO NOT ASSIGN — it's a promotional/state register;
add it to the HD-register entry.
Goal: "must-eat" / local food lists per province from the Tourism Authority of
Thailand and official provincial tourism pages.
Discovery: TAT's official sites (Thai and English) — find province pages and their
food/อาหารขึ้นชื่อ sections. Verify official domains.
Capture: province, dish name (Thai and English if both), short dish-type label,
ingredient mentions only if listed, page date if shown. No descriptions.
Target: all provinces with food listings; report coverage.
```

## 10 — food.culture.go.th bookfood67 (already downloaded)

```
Source slug: dcp_bookfood67. NO SCRAPING — the CSV exists at
data/raw/gdcatalog/flavormap_food67.csv (6,737 rows).
Task: profile the file — columns, row meaning (one row per dish? per ingredient?),
provinces covered, overlap with the 231 DCP food68 forms (dish-name match),
and whether it contains personal data. Write data/coverage/bookfood67_profile.md.
Add an ETHICS.md row with provenance. Do NOT load into recipes — write an OPEN
decision entry: should bookfood67 expand the official register beyond 3 dishes
per province? Stop for my decision.
```

## 11–13 — English sites (Hot Thai Kitchen, SheSimmers, Thai Food Master) — OPTIONAL

```
Source slugs: hotthaikitchen, shesimmers, thaifoodmaster. Register: DO NOT ASSIGN —
write an OPEN decision entry (HD-register-EN): are English-language sites part of
the commercial register or a separate "international" register? Stop after audit.
For each site: robots.txt, terms, recipe index pages, whether regional tags exist.
Capture in the pilot: title (English), Thai dish name if shown, region claim,
publish date, ingredient lines (English; keep verbatim — do not translate).
Target (only if I approve): up to 100 per site.
```

## 14 — Pantip food room · `pantip.com` — NOT THIS CYCLE

```
Source slug: pantip_food. AUDIT ONLY — do not crawl.
Report: robots.txt, terms, whether an official API exists, and the PDPA risk
(posts are personal; usernames, locations and life details appear in text).
Estimate how many threads in the food room mention a province + a dish.
Write the findings to docs/source_audit.md and stop.
```

## 15 — YouTube channel descriptions — NOT THIS CYCLE

```
Source slug: youtube_desc. AUDIT ONLY — do not crawl and do not scrape youtube.com.
The only allowed route is the official YouTube Data API v3 under its terms.
Report: API quota, terms on storing descriptions, and a list of ~20 Thai regional
cooking channels found via the API search endpoint (channel title + ID only).
Write findings to docs/source_audit.md and stop.
```

---

## After each source

- Review the pilot report before approving stage C.
- Log the decision in `docs/decisions.md` (approve / reject / cap).
- Update `docs/limitations.md` with what the source over- or under-represents.
- Re-run lexicon coverage — new sources bring new ingredient spellings.
