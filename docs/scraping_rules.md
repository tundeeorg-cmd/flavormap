# Scraping rules

**Every scraper in this repo follows these rules.** Most are enforced in code: a new site
scraper extends `src/scrape/base.py::SiteScraper`, and inherits the enforcement instead
of reimplementing it. Where a rule needs a human, that is said plainly.

Adopted 2026-10-06. Read with `CLAUDE.md`, `docs/TIMELINE.md` §0 and `ETHICS.md`.

| # | Rule | Enforced by |
|---|---|---|
| 1 | Ethics first | `src/scrape/ethics.py`: `require_go`, the ETHICS.md register |
| 2 | Politeness | `src/scrape/conduct.py`: `PoliteFetcher`, `make_client`, `user_agent` |
| 3 | Cache | `src/scrape/cache.py`: `PageCache` |
| 4 | What to store | `src/scrape/record.py`: `ScrapedRecipe`, `to_parsed_json` |
| 5 | PDPA | `to_parsed_json` (redaction) + `src/ingest/pdpa.py::scan_database` in every load |
| 6 | No decisions | `base.py` writes `raw_recipes` only; tested |
| 7 | Thai text | `to_parsed_json`: original + `normalize_thai` form |
| 8 | Stages | `base.py`: `audit`, `pilot`, `full`, and `main()` |
| 9 | Tests | each scraper's own tests on 3 fixture pages; see `tests/test_scrape_base.py` |
| 10 | After a full crawl | printed by `full()`; the backup needs the researcher |

---

## 1. Ethics first

Before any crawl, `--audit`:

- fetches `robots.txt` under our own User-Agent, and the site's Terms of Service / Terms
  of Use page;
- quotes the ToS clauses that mention automated access, scraping, copying or reuse
  (English and Thai keywords) into `data/coverage/<source>_audit.md`;
- appends a **dated row** to the *Scraper audit register* in `ETHICS.md`:
  `source_id | site | date | robots.txt | terms of service | decision`, with decision
  `pending (researcher)`.

**The decision is the researcher's** (the source go/no-go gate, CLAUDE.md §9). The keyword
flag is not a verdict: read the full terms on the site. If the terms forbid automated
collection or reuse, the decision is `no-go` and the source is dropped.

**Enforced:** `--pilot` and `--full` call `require_go()`, which refuses unless the **latest**
register row for the source says `go`. A later `pending` or `no-go` row closes a source
that was open. The two pre-existing fetchers (`fetch_dcp_food`, `fetch_kapook`) call the
same gate.

**Never** bypass a login, paywall, CAPTCHA, rate limit or premium content. A robots.txt
that disallows our User-Agent stops the run; a disallowed URL is skipped, never fetched.

## 2. Politeness

**Enforced in `PoliteFetcher` / `make_client`:**

- a randomised 1–2 s gap between requests (mean 1.5 s, never under 1 s), seeded from
  `RANDOM_SEED` so the pace is reproducible;
- one connection per site (`max_connections=1`), requests strictly sequential;
- User-Agent `FlavorMapResearch/1.0 (+https://github.com/tundeeorg-cmd/flavormap; <SCRAPER_CONTACT_EMAIL>)`,
  refused if the email is unset or a placeholder;
- 429 and 5xx retried with exponential back-off (2, 4, 8, 16 s, capped at 60 s),
  honouring a numeric `Retry-After`;
- **5 consecutive errors stop the crawl** (`CrawlAborted`). A 404 is an outcome, not an error.

## 3. Cache

**Enforced in `PageCache`:** raw HTML goes to `data/raw/<source_slug>/<url_sha1>.html`
(gitignored, never published). Every fetch appends a row to `manifest.csv`:
`url, url_sha1, fetched_at (UTC ISO), http_status, bytes, content_sha256`. Re-runs read
from the cache; a cached page is re-fetched only with `--refresh`.

`dcp_food` and `kapook_cooking` predate this rule and keep their own manifests.
`data/raw/` is read-only to everything but its fetcher, so they are not rewritten.

## 4. What to store

Per recipe, into `raw_recipes` under the source's `source_id`, `parsed_json` holds:

- `url`, `title_th` (verbatim), `published_at` (if shown, else `null`, **never guessed**),
  `scraped_at`, `site_category` (verbatim), `site_tags` (verbatim list);
- `region_claim` and `province_claim`: the **exact text span** that claims a region or
  province, and where it was found (`title`, `tag`, `breadcrumb` or `intro`);
- `ingredient_lines`: verbatim (quantity + unit + name as written), in order;
- `servings`, if shown.

**Never stored:** method or instruction prose, author names or usernames, profile links,
comments, photos, phone numbers, emails, addresses. `recipes.method_text` stays empty.

**Enforced:** `ScrapedRecipe` has a field for each allowed item and nothing else, so the
forbidden ones have nowhere to go. A single "ingredient line" over 200 characters is
refused as probable method prose.

## 5. PDPA

**Enforced:** `to_parsed_json` runs `src/ingest/pdpa.py::redact` on every text value before
anything is written, and the counts go to `redaction_log`. Inside the same transaction,
every load then runs `scan_database`, the same whole-database scan as
`tests/test_pdpa.py`. **Any hit rolls the load back**: nothing personal is committed.

## 6. No decisions

A scraper copies the site's own claims and nothing more. It **never** assigns a register,
a province label or a dish category, and **never writes `recipes` or
`province_attribution`** (tested: `test_the_base_never_writes_recipes_or_attributions`).

Turning claims into attributions is a separate step that follows the decided HD-Kapook
rule in `docs/decisions.md`. **As of 2026-10-06, HD-Kapook is not decided**, so no scraped
claim becomes an attribution. A source that needs a different rule gets an OPEN entry
in `docs/decisions.md`, and work stops there.

## 7. Thai text

**Enforced:** every stored text value keeps the (redacted) original **and** a normalised
form: NFC plus the existing sara-am and combining-mark repair (`normalize_thai`).

## 8. Stages

Every site scraper exposes, through `src.scrape.base.main`:

```bash
uv run python -m scripts.scrape_<source> --audit
```
```bash
uv run python -m scripts.scrape_<source> --pilot 20
```
```bash
uv run python -m scripts.scrape_<source> --full --limit 600
```

- `--audit`: rule 1; then **stop**.
- `--pilot N` (default 20): needs `go`; stores N records and writes
  `data/coverage/<source>_pilot.md` (fill rates for `published_at`, `site_category`,
  region/province claim and ingredient lines, plus 5 example records); then **stop for
  review**.
- `--full --limit N`: needs `go` **and** a pilot report. Refuses otherwise.

## 9. Tests

Each scraper gets parser tests on **3 saved fixture pages**, under `tests/fixtures/`.
Fixtures contain no personal data. Where a test needs a person-shaped value to prove it
is not stored, it uses a declared synthetic placeholder (surname ทดสอบ, the invented test
phone numbers), and a test checks that nothing else appears.
`tests/test_scrape_base.py` shows the pattern. `pytest`, `ruff` and `mypy` must be green
before any commit.

## 10. After a full crawl

`full()` prints this checklist. Steps 1, 3 and 4 can be run for you; **step 2 needs the
researcher**, who types the backup passphrase:

1. `make db-dump`
2. `make backup TO=<off-laptop path>`
3. `make status-snapshot`
4. Commit with the source, the count and the date, e.g.
   `data(<source>): 512 recipes scraped 2026-11-02`.

## Writing a new site scraper

```python
from src.scrape.base import SiteScraper, main
from src.scrape.record import Claim, ScrapedRecipe

class MySite(SiteScraper):
    source_id = "mysite"
    slug = "mysite"
    base_url = "https://www.mysite.example"
    tos_url = "https://www.mysite.example/terms"

    def discover(self, fetcher, limit): ...   # yield recipe-page URLs
    def parse(self, html, url): ...           # return ScrapedRecipe or None

if __name__ == "__main__":
    raise SystemExit(main(MySite()))
```
