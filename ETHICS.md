# Ethics

Scraping conduct, source permissions, personal-data handling, and fieldwork consent.

**Rule 7 is a gate, not a guideline:** no scraper is written for a source that does not
have a dated row in the table below. A source whose robots.txt disallows the path is
dropped, never worked around.

## Scraping conduct

| Rule | Practice |
|---|---|
| Rate limit | 1 request / second, minimum |
| Identification | `FlavorMapResearchBot/0.1 (+mailto:$SCRAPER_CONTACT_EMAIL; academic research, non-commercial)` |
| robots.txt | Fetched and honoured on every run, not just at audit time |
| Stored | Ingredient lists, province labels, publication dates |
| Never stored | Full recipe prose, instructions, copyrighted text |
| Raw pages | Cached to disk for reproducibility, gitignored, **never published** |

## Source audit

One row per source. **Dated.** A source may not be scraped before its row exists.

| source_id | Domain | robots.txt | Disallowed paths | ToS reviewed | Audited | Decision |
|---|---|---|---|---|---|---|
| `dcp_food` | `food.culture.go.th` | `User-agent: *` → `Allow: /`. **But see content signals below** | none for our UA. `ClaudeBot`, `GPTBot`, `CCBot`, `Google-Extended`, `Bytespider`, `Amazonbot`, `Applebot-Extended`, `meta-externalagent`, `CloudflareBrowserRenderingCrawler` are each `Disallow: /` | no separate ToS page located in this pass | 2026-08-16 | **⛔ HD-3 open — not fetched** |
| `doae` | `www.doae.go.th` | allowed | `/wp-admin/` | pending | 2026-08-09 | **HD-3 open** |
| `wongnai` | `www.wongnai.com` | allowed | `/users/` | pending | 2026-08-09 | **HD-3 open** — JS-hydrated, recipe path unresolved |
| `kapook_cooking` | `cooking.kapook.com` | `User-agent: *` → `Allow: /`, no crawl-delay | none | no terms-of-use page found; linked policy is data-protection only | **2026-08-22** (re-audited) | **HD-3 open** — cleared technically and ethically; see below |
| `tat` | `www.tat.or.th` | allowed | — | pending | 2026-08-09 | **HD-3 open** |
| `pantip_food` | `pantip.com` | allowed for our UA | blocks are scoped to other named bots | pending | 2026-08-09 | **HD-3 open** — JS-hydrated, food board URL unresolved |
| `national_library` | `www.nlt.go.th` | not fetched | — | pending | 2026-08-09 | Blocked: server sends an incomplete TLS chain. Not a workaround candidate — needs a documented justification before any fetch |
| `thaifoodrecipe` | — | — | — | — | 2026-08-09 | **Dropped.** Domain does not exist (NXDOMAIN) |
| `doa` | `www.doa.go.th` | — | — | — | 2026-08-09 | **Dropped.** 403 Forbidden; superseded by `doae.go.th` |

Full technical detail and raw tool output: [`docs/source_audit.md`](docs/source_audit.md).

### `food.culture.go.th` content signals — audited 2026-08-16

The robots.txt is Cloudflare-managed and carries **content signals** alongside the
ordinary directives. Verbatim:

```
User-agent: *
Content-Signal: search=yes,ai-train=no,use=reference
Allow: /
```

preceded by the site's own definition of the terms, and followed by an explicit
`Disallow: /` for nine named AI crawlers.

The file states that restrictions expressed this way are **express reservations of rights
under Article 4 of EU Directive 2019/790**.

Read strictly:

| Signal | Value | What the site is saying |
|---|---|---|
| `search` | `yes` | indexing and short excerpts are fine |
| `ai-train` | **`no`** | **do not use this content to train or fine-tune AI models** |
| `use` | `reference` | AI systems may consume it by reference, not in full |
| `ai-input` | *unspecified* | neither granted nor restricted — the operator is silent |

`urllib.robotparser` confirms `FlavorMapResearchBot/0.1` may fetch every candidate path,
while `ClaudeBot`, `GPTBot`, `CCBot`, `Google-Extended` and `Bytespider` may not.

**Being permitted by the parser is not the same as being welcome.** This source is
therefore held at HD-3 rather than treated as cleared. See `docs/decisions.md`.

### `food.culture.go.th` — fetch record, 2026-08-16

Fetched under HD-3 **option C**: reference layer only, excluded from any public release,
pending a reply to the permission request in `docs/dcp_permission_request.md`.

| | |
|---|---|
| Documents | 231 of 231 (77 provinces × 3 menus), 126 MB |
| Failures | 0 missing, 0 errors |
| Rate | 1 request/second, sequential, no concurrency |
| User-Agent | `FlavorMapResearchBot/0.1 (+mailto:…; academic research, non-commercial)` |
| robots.txt | re-checked at run time, not trusted from the audit |
| Stored | `data/raw/dcp_food/`, gitignored, never published |

**The raw PDFs contain personal data** — informant names, house numbers, postcodes and
mobile numbers, exactly as §1.3 of the form provides for. They are retained locally, and
only locally, so that parsing is reproducible and auditable. They are gitignored, they
never enter a HuggingFace release, and the fields are discarded during parsing before
anything is written to the database.

### `cooking.kapook.com` — re-audit, 2026-08-22

Re-fetched rather than trusted from the 2026-08-09 pass, per the robots.txt rule above.

| | |
|---|---|
| robots.txt | `User-agent: *` → `Allow: /`. No crawl-delay, no disallowed paths |
| AI crawlers | **No blocklist.** `Google-Extended` is explicitly `Allow: /` — an opt-*in* to AI training use, the opposite of `food.culture.go.th`'s `ai-train=no` |
| Content signals | none present |
| Terms of use | **No ToS page found.** The only policy linked from the site is a data-protection notice at `account.kapook.com/privacy`, which contains no mention of copyright, reproduction, scraping, automation or commercial use |
| Rendering | server-rendered, static HTML |
| Sitemap | `sitemap.xml`, 3,770 `<loc>` entries |

**Correction to the 2026-08-09 row.** That audit recorded "3,908 sitemap URLs" as the
candidate recipe count. It is not: 956 of the entries are `/comment/` pages and 43 are
category listings. 2,742 distinct recipe URLs were listed on 2026-08-22 and 2,739 on
2026-08-23 — the sitemap moves, so it is a snapshot rather than a fixed number.

**What was actually fetched (2026-08-23).** 2,702 pages. Of the 2,742 URLs attempted, 40
answer HTTP 200 with a **zero-byte body** — pages the CMS still lists after their content
is gone. They answered identically on a re-probe the following day, so this is a property
of the site, not a transient failure. The fetcher records them as `empty` rather than
`fetched`, which keeps them out of the corpus and out of any coverage denominator.

Against the 3,908 the 2026-08-09 row claimed, then: 2,702 pages fetched, of which
**2,521 yield a machine-readable ingredient list** — 64% of the original figure. The
remaining 181 are product reviews, technique articles, and recipes whose ingredient list
is published as an image or an embedded Facebook post.

**Absence of a ToS is not a licence.** Copyright subsists in the content regardless, which
is why the storage rule above is load-bearing for this source in particular: ingredient
lists, publication dates and derived labels only. The page's JSON-LD carries an
`articleBody` field holding the full prose — it is never stored.

### Consulted by hand, never automated

| Source | Reason |
|---|---|
| `gdcatalog.go.th` | Disallows automated access. Its dataset listing is consulted manually only |

## Personal data (PDPA 2562)

**No personally identifying data enters the database, ever.** Not in a table, not in a
JSONB blob, not in a debug log. Filtering at export is too late — by then it is in the
backups.

Institutional forms in particular carry informant names, house numbers, roads,
subdistricts, postcodes, and mobile numbers. These are **discarded during parsing, before
any write**, and a `redaction_log` row records how many fields of each class were removed
per document. A document yielding zero redactions is treated as a parser failure, not as a
clean document.

Retained from such forms: administrative geography (ตำบล / อำเภอ / จังหวัด) and business
name with the address stripped. Administrative geography is not contact detail.

Raw source documents on disk retain everything they came with. They are gitignored, they
never enter a HuggingFace release, and they are kept locally solely so that parsing is
reproducible and auditable.

### Enforcement status — checked 2026-08-22

**Not yet enforced. `tests/test_pdpa.py` does not exist.** No parser has been written, no
document has been parsed, and every recipe table is empty. There is nothing for such a test
to assert against yet, and a test that passed on zero rows would be a false assurance rather
than a check — which is why the file has not been created as a placeholder.

| | |
|---|---|
| Documents fetched | 231 |
| Documents parsed | 0 |
| Rows in `raw_recipes` / `recipes` / `recipe_ingredients` | 0 |
| Rows in `redaction_log` | 0 |
| `tests/test_pdpa.py` | **absent** |

The requirement is unchanged and it is a gate, not a follow-up: **the parser is not finished
until `tests/test_pdpa.py` exists and passes against the full parsed set**, asserting that no
phone, email, or house-number pattern survives into any table (`CLAUDE.md` §13). It is written
alongside the parser, in the same commit, not after it.

This section is updated when that lands. Until then the rule above states an intention, not an
enforced guarantee, and is written that way deliberately.

## Fieldwork consent

Non-negotiable, per Bible §8:

- Written one-page Thai consent form in plain language
- Anonymised publication by role and province by default
- A parent chaperones every interview, stated plainly in the methods section
- Reciprocity: every participant receives the finished map and a printed copy of their own
  recipe as it appears in the dataset
- No recording without explicit permission
- No user accounts and no personal data collected from minors on the public site

---

*First entry: 2026-08-16, seeded from the 2026-08-09 technical audit.*
