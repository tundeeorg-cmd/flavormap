# Scraping rules

**Adopted:** 2026-10-06 · **Applies to:** every scraper in this repository · **Enforced by:**
`src/scrape/` (`conduct.py`, `ethics.py`, `cache.py`, `record.py`, `base.py`) and the
`tests/test_scrape_*.py` suite

This file states the rules. The code makes them true. Where a rule can be enforced in code,
it is, and the table under each rule says where; where it cannot (a decision, a backup, a
commit), that is said too, and the code stops and asks rather than guessing.

It sits alongside `CLAUDE.md` §1 rules 7 and 8 and `ETHICS.md`, and is stricter than both
on pace and identity: **1–2 s randomised, not 1 s fixed; `FlavorMapResearch/1.0`, not
`FlavorMapResearchBot/0.1`.** Where they differ, this file is the newer statement.

---

## How a scraper is built

A site scraper is one module, `src/scrape/sites/<source_id>.py`, holding one
`SiteScraper` subclass:

```python
class ExampleSite(SiteScraper):
    source_id = "example_site"                 # the ETHICS.md / sources.source_id slug
    base_url = "https://www.example.co.th"
    tos_url = "https://www.example.co.th/terms"

    def discover(self, crawler):               # recipe URLs, stable order
        sitemap = crawler.page(f"{self.base_url}/sitemap.xml")
        ...

    def parse(self, html, url, scraped_at):    # one page -> ScrapedRecipe | None
        ...

if __name__ == "__main__":
    raise SystemExit(run(ExampleSite))
```

and is run as `uv run python -m src.scrape.sites.example_site --audit | --pilot [N] |
--full [--limit N] [--refresh]`. Everything below — the gate, the pace, the cache, PDPA,
the stages — lives in the base, so a scraper cannot leave it out.

---

## 1. Ethics first

Before any crawl: fetch robots.txt and the Terms of Service / Terms of Use page, quote
the relevant clauses, and add a **dated** row to the `ETHICS.md` source-audit table (site,
date, robots result, ToS result, decision). If the ToS forbids automated collection or
reuse, **stop and report**. Never bypass logins, paywalls, CAPTCHAs, rate limits or premium
content.

| Enforced | Where |
|---|---|
| `--audit` fetches robots.txt and the ToS page, quotes every clause on automated access or reuse (English and Thai), flags those that read as prohibitions, and writes `docs/source_audits/<source_id>_<date>.md` with a **proposed** table row | `ethics.audit_site`, `ethics.write_audit` |
| A flagged clause or a robots.txt root disallow → the report ends in **STOP** and the command exits 2 | `AuditReport.must_stop` |
| `--pilot` and `--full` refuse to construct a crawler unless the `ETHICS.md` row exists, is dated, has a robots result **and** a ToS result (not `pending`), and its Decision cell carries `✅` | `ethics.require_cleared`, called first in `Crawler.__init__` |
| Login redirects, 401/402/407, CAPTCHA and challenge pages, and paywall/login-wall interstitials abort the crawl — they are never solved, worked round, or retried | `conduct.challenge_reason` → `CrawlAborted` |
| No cookies, credentials or sessions are ever supplied | `conduct.make_client` |

**Not enforced in code, by design.** The Decision cell. `--audit` writes `HD-3 open` and
never edits `ETHICS.md`; reading the quoted clauses and deciding is the researcher's
(HD-3). The keyword scan is a prompt for that reading, not a substitute: it over-flags on
purpose, and a ToS with no flagged clause is not thereby cleared.

## 2. Politeness

At most one request per 1.5 s on average — each gap drawn uniformly from **1–2 s**,
measured between request starts. One connection per site. Honest User-Agent:

```
FlavorMapResearch/1.0 (+https://github.com/tundeeorg-cmd/flavormap; <SCRAPER_CONTACT_EMAIL>)
```

Exponential back-off on 429 and 5xx. Stop the crawl after **5 consecutive errors**.

| Enforced | Where |
|---|---|
| 1–2 s uniform jitter, seeded from `RANDOM_SEED` (CLAUDE.md rule 6); retries and HEADs pay it too | `conduct.PoliteFetcher._wait` |
| One connection: `httpx.Limits(max_connections=1)`, sequential fetcher, no concurrency anywhere | `conduct.make_client` |
| User-Agent built in one place; refuses an empty or `example.com` contact | `conduct.build_user_agent` |
| robots.txt fetched through the same client and UA on every run; disallowed URLs skipped, never fetched; root disallow stops the run | `conduct.load_robots`, `PoliteFetcher.allowed` |
| 429/500/502/503/504 retried at 2, 4, 8, 16 s (or a longer `Retry-After`, capped at 120 s) | `PoliteFetcher._request` |
| 5 consecutive errors (transport failures, exhausted retries, 403) → `CrawlAborted` | `PoliteFetcher._error` |

## 3. Cache

Raw HTML is saved to `data/raw/<source_slug>/` (gitignored), named by the SHA-1 of its URL,
with a manifest `_manifest.csv`:

```
url, url_sha1, fetched_at (UTC ISO), http_status, bytes, content_sha256
```

Re-runs read from cache. A cached page is never re-fetched without `--refresh`.

| Enforced | Where |
|---|---|
| Every page goes through the cache; the network is used only on a miss, and robots.txt is not even requested while everything needed is on disk | `base.Crawler.page` |
| Manifest columns exactly as above; append-only (a `--refresh` adds a row); latest row wins | `cache.PageCache` |
| A non-200 or empty response is logged, not cached, so it is asked for again next run | `PageCache.record` |
| `data/raw/` is gitignored | `.gitignore`; `tests/test_scrape_cache.py` |

## 4. What to store

Per recipe, into `raw_recipes` under the source's `source_id`:

- `url`, `title_th` (verbatim), `published_at` (if the page shows it, else NULL — **never
  guessed**), `scraped_at`, `site_category` (verbatim), `site_tags` (verbatim list)
- `region_claim` and `province_claim`: the exact text span that claims a region or
  province, and where it was — `title`, `tag`, `category`, `breadcrumb` or `intro`
- ingredient lines verbatim (quantity + unit + name as written), in page order
- servings, if shown

**Never stored:** method or instruction prose, author names or usernames, profile links,
comments, photos, phone numbers, emails, addresses. `recipes.method_text` stays empty.

| Enforced | Where |
|---|---|
| `ScrapedRecipe` has a field for each allowed item and **no field** for anything forbidden | `record.ScrapedRecipe` |
| The stored payload's keys must equal `ALLOWED_PAYLOAD_KEYS`; widening it is a reviewed edit to that line and to this file together | `record.finalise`, `record.insert_raw_recipe` |
| Links (other than the page URL), image filenames, and over-long lines (> 150 chars: prose, not an ingredient line) refuse the record | `record._check_text` |
| A `title`/`tag`/`category` claim must be found verbatim in that field; `breadcrumb`/`intro` claims are capped at 200 chars — a span, not a passage | `record._claim_found` |
| Only `finalise()` output can be written, and the writer touches `raw_recipes` only — never `recipes`, so `method_text` is never written | `record.insert_raw_recipe`; `tests/test_scrape_rules.py` |
| `recipes.method_text` is empty in the database | `tests/test_scrape_rules.py::test_method_text_is_empty_in_the_database` |

## 5. PDPA

`src/ingest/pdpa.py` runs on every record before any database write. The
`tests/test_pdpa.py` whole-database scan must pass after every load.

| Enforced | Where |
|---|---|
| `redact()` over every string of every record; the serialised payload is then scanned with `find_leaks()` and any hit refuses the record | `record.finalise` |
| After a `--full` load, `pdpa.scan_database()` — the same function `tests/test_pdpa.py` calls — runs **inside the load's transaction**; any leak anywhere rolls the whole load back (exit 3) | `base.stage_full` |
| Refusal messages name classes, never the matched text | `record.finalise` |

`scan_database` was moved out of `tests/test_pdpa.py` into `pdpa.py` on 2026-10-06 so the
post-load check and the test are one implementation, not two that can drift.

## 6. No decisions

A scraper does not assign a register, a province label, or a dish category. It copies the
site's own claims, verbatim, with their location, and that is all.

Province attribution for web sources follows the decided kapook rule — **HD-3, option A
(2026-08-23)**, as implemented by `scripts/parse_kapook.py`: the source is a coverage
corpus, site claims are kept as text, and **no `province_attribution` row is written**.
(There is no gate literally named "HD-Kapook"; this is the decided rule that governs it.)
Register is likewise not assigned here: it is a per-source fact set by that source's
loader once decided, as `parse_kapook.py` sets `commercial`.

If a new source needs a different rule — it carries structured province fields, say, or a
register that is not obvious — **write an `OPEN` entry in `docs/decisions.md` and stop.**

| Enforced | Where |
|---|---|
| No field for register, province or dish category exists on the record | `record.ScrapedRecipe` |
| Nothing in `src/scrape/` writes any table but `raw_recipes`, or assigns `register`, `province`, `dish_category` or `method_text` | `tests/test_scrape_rules.py` |

## 7. Thai text

Normalise Unicode (NFC), apply the existing sara-am repair, and keep the original string
alongside any normalised one.

| Enforced | Where |
|---|---|
| Every text field is stored twice: as found (after PDPA redaction) and as `<field>_norm` — NFC plus `src.clean.normalize_th.normalize_thai` (PUA, orphaned marks, segmentation-arbitrated sara am). The original is never overwritten | `record.finalise` |

## 8. Stages

Every site scraper supports `--audit`, `--pilot N` (default 20) and `--full --limit N`.

| Stage | Does | Writes | Then |
|---|---|---|---|
| `--audit` | robots.txt + ToS, quoted (rule 1) | `docs/source_audits/<source>_<date>.md` | exit 2 on STOP; otherwise add the row and get the decision |
| `--pilot [N]` | crawls N recipe URLs through the full pipeline | `data/coverage/<source>_pilot.md`: counts, fill rates for `published_at`, `site_category`, `site_tags`, region/province claim, ingredient lines, servings; **5 example records**; the first 10 refusals. **No database writes** | **STOP for review** |
| `--full [--limit N]` | crawls and loads into `raw_recipes` | database, in one transaction, PDPA-scanned before commit | the rule 10 checklist |

`--full` refuses until the pilot report's `**Reviewed:**` line carries a date
(`YYYY-MM-DD`). The researcher writes that date after reading the five examples; the
agent does not.

`data/coverage/*` is gitignored except status snapshots, so pilot reports stay on the
machine that ran them. That is deliberate — they quote site content — and it means the
review date lives there too.

Exit codes: 0 ok · 2 refused or STOP · 3 PDPA scan failed, rolled back · 4 crawl aborted
(errors, wall).

## 9. Tests

Each scraper gets parser tests on **3 saved fixture pages** (`tests/fixtures/scrape/
<source_id>/*.html`), in `tests/test_scrape_<source_id>.py`. Fixtures contain no personal
data — trim author blocks and comments out of the saved page before committing it. `pytest`,
`ruff check` and `mypy` are green before every commit.

| Enforced | Where |
|---|---|
| Every `SiteScraper` in `src/scrape/sites/` has ≥ 3 fixtures, none with a `find_leaks` hit in its visible text, and its own test file; its module is named after its `source_id` | `tests/test_scrape_rules.py` |

## 10. After a full crawl

```
make db-dump
make backup TO=<off-laptop path>
make status-snapshot
git commit -m "data(<source>): full crawl, <N> records loaded, <YYYY-MM-DD>"
```

`--full` prints this list with the source, count and date filled in. It does not run it:
the backup needs a drive only the researcher can plug in, and the commit is theirs.

---

## Existing fetchers

`scripts/fetch_kapook.py` and `scripts/fetch_dcp_food.py` predate this base. As of
2026-10-06:

- **They share rule 2** through `src/scrape/conduct.py`, so they now pace at 1–2 s, back
  off, stop after 5 consecutive errors, abort on a wall, and send the new User-Agent.
- **They do not use rules 1, 3, 4 or 8.** Their manifests have their own columns
  (`fetch_kapook.py`'s `outcome`/`recipe_id`; DCP's own) and their files are named by page
  ID, and both corpora are already parsed and loaded. Moving them would rename cached
  raw files and rewrite manifests that `scripts/parse_*.py` and the audit trail depend on.
- **`dcp_food` would not pass the rule 1 gate.** Its `ETHICS.md` Decision cell is
  "⚠️ HD-3 open — fetched under option C", not `✅`. `fetch_dcp_food.py` is not gated, so
  `make scrape` still runs it; whether it should be is the open HD-3 (dcp_food), not a
  call for this file.

Any **new** source is built on `src/scrape/base.py`. A re-crawl of an old one is a
decision about migrating it, and goes to `docs/decisions.md` first.
