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
| `doae` | `www.doae.go.th` | allowed | `/wp-admin/` | pending | 2026-08-09 | **HD-3 open** |
| `wongnai` | `www.wongnai.com` | allowed | `/users/` | pending | 2026-08-09 | **HD-3 open** — JS-hydrated, recipe path unresolved |
| `kapook_cooking` | `cooking.kapook.com` | allowed | none | pending | 2026-08-09 | **HD-3 open** — strongest technical candidate (3,908 sitemap URLs, server-rendered) |
| `tat` | `www.tat.or.th` | allowed | — | pending | 2026-08-09 | **HD-3 open** |
| `pantip_food` | `pantip.com` | allowed for our UA | blocks are scoped to other named bots | pending | 2026-08-09 | **HD-3 open** — JS-hydrated, food board URL unresolved |
| `national_library` | `www.nlt.go.th` | not fetched | — | pending | 2026-08-09 | Blocked: server sends an incomplete TLS chain. Not a workaround candidate — needs a documented justification before any fetch |
| `thaifoodrecipe` | — | — | — | — | 2026-08-09 | **Dropped.** Domain does not exist (NXDOMAIN) |
| `doa` | `www.doa.go.th` | — | — | — | 2026-08-09 | **Dropped.** 403 Forbidden; superseded by `doae.go.th` |

Full technical detail and raw tool output: [`docs/source_audit.md`](docs/source_audit.md).

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

Enforced by `tests/test_pdpa.py` against the full parsed set.

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
