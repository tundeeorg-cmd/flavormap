# Source audit — Phase 0

**Status:** technical pass complete (`[CC]`), go/no-go pending (`[HD-3]`).
**Tool:** `scripts/audit_source.py` — raw output archived at the bottom of this file.
**Audited:** 2026-08-09, live requests against each domain (robots.txt + sitemap + one
homepage fetch per source), 1 req/sec, identifying User-Agent.

> ⚠️ **`SCRAPER_CONTACT_EMAIL` is not set yet.** This pass used a clearly-labelled
> placeholder (`flavormap-audit@example.com (PLACEHOLDER)`) in the User-Agent because
> `.env` doesn't exist yet. Set a real, monitored address in `.env` before Phase 1
> scraping begins — rule 7 requires it to be genuinely reachable, not a placeholder.

## Exit criterion

CLAUDE.md v2 §Phase 0 edits: **≥1,200 realistically-scrapeable recipes confirmed**
across sources before proceeding to Phase 1. **This has not been assessed yet** — the
technical audit below tells you which sources are technically reachable; it does not
and cannot tell you how many recipes are actually behind each one, whether they carry
usable province signal, or whether the extraction is worth the engineering cost. That
judgment is `[HD-3]`, per row below.

## The DOAE / doa.go.th discrepancy — resolved

CLAUDE.md flagged this as needing resolution before writing the first scraper.
Confirmed today: **`www.doa.go.th` returns `403 Forbidden`** (blocked or defunct).
**`www.doae.go.th` is live** (301 → resolves cleanly, has a sitemap, WordPress-based).
กรมส่งเสริมการเกษตร (Department of Agricultural Extension) is **DOAE**, matching the
live domain. Use `doae.go.th`. Do not use `doa.go.th`.

## Bible §6 URLs that were stale

Two of the six URLs given in the Project Bible no longer resolve or point to the wrong
thing — normal for a document written in advance of actually visiting the sites.
Corrected candidates are audited below instead:

| Bible said | Reality (checked 2026-08-09) | Used instead |
|---|---|---|
| `recipe.wongnai.com` | DNS does not resolve (subdomain doesn't exist) | `www.wongnai.com` (recipe content likely lives under a path on the main domain now — needs manual exploration, see HD-3 notes) |
| `thaifoodrecipe.com` | NXDOMAIN — domain does not exist | none found yet — **HD-3: needs a replacement candidate or this source is dropped** |
| `amazingthailand.com` | TLS hostname mismatch (wrong cert — likely not actually TAT's domain) | `www.tat.or.th` (government domain, resolves cleanly) — `tourismthailand.org` also exists but returned `403` on this pass |

## Objective technical findings

| source_id | source_type | URL audited | robots_ok | sitemap | rendering | Thai recipe signal on homepage | Notes |
|---|---|---|---|---|---|---|---|
| `doae` | web_scraped | `www.doae.go.th` | ✅ allowed, only `/wp-admin/` disallowed | ✅ `/wp-sitemap.xml`, 24 `<loc>` entries | server-rendered (ratio 0.26) | none (homepage is a news page, not a recipe index) | **Highest-priority per Bible** — need to find the actual recipe/knowledge-base section, sitemap of only 24 URLs seems low for "2,000+ recipes" claimed in the Bible; worth double-checking this is even the right department sub-site |
| `wongnai` | web_scraped | `www.wongnai.com` | ✅ allowed, only `/users/` disallowed | ❌ no `/sitemap.xml` found at the usual paths | **JS-hydrated** (`id="app"` SPA root, low text/html ratio 0.06 despite large payload) | none on homepage (nav is client-rendered) | Confirms Bible's own note: Playwright required. Homepage doesn't expose a `/recipe` path in static HTML — needs a human to browse and find the real recipe section URL structure before a scraper can be written |
| `thaifoodrecipe` | web_scraped | *(domain doesn't exist)* | — | — | — | — | **Dead. HD-3: find a replacement "Thai Taste"-equivalent source or drop the slot** |
| `kapook_cooking` | web_scraped | `cooking.kapook.com` | ✅ allowed, no disallow rules | ✅ `/sitemap.xml`, **3,908** `<loc>` entries (also a `sitemap_news.xml`) | server-rendered (ratio 0.14) | **found**: วิธีทำ, วัตถุดิบ on the homepage itself | Cleanest technical result of the six — large sitemap, real Thai recipe vocabulary present, static HTML. Best first-scraper candidate on technical grounds alone |
| `tat` | institutional | `www.tat.or.th` | ✅ allowed | ✅ `/sitemap.xml`, 84 `<loc>` entries | server-rendered (ratio 0.45) | none on homepage (tourism content, not recipes — expected, Bible says TAT's value is province attribution quality, not recipe volume) | Small sitemap (84 URLs) — matches Bible's "500+ [total across pages]" being a modest source. `tourismthailand.org` (English-facing site) returned `403` to this bot; `tat.or.th` (Thai, government) is the one that works |
| `pantip_food` | web_scraped | `pantip.com` | ✅ allowed for this UA at root (robots.txt has several `Disallow: /` blocks but they're scoped to *other*, specifically-named bots — `can_fetch()` confirms our generic UA is not blocked) | ✅ `/sitemap.xml`, 43 `<loc>` entries | **JS-hydrated** (`id="__next"`, Next.js) | **found**: เครื่องปรุง, วัตถุดิบ on the homepage | The Bible's `pantip.com/club/food` path 404s — Pantip's board structure has changed. Needs a human to find the current food-board URL/tag structure. JS-hydrated confirms the Bible's own caveat ("community posts... lower reliability") plus now also a scraping-difficulty problem |
| `national_library` | cookbook catalogue | `www.nlt.go.th` | robots.txt not fetched (see note) | not found | not assessed | not assessed | **TLS chain issue**: server (Fine Arts Department, real cert from DigiCert/Thawte) doesn't send its intermediate certificate, so standard clients fail verification (confirmed with both `curl` and `openssl s_client` — this is server-side, not a bug in our tool). The site is real and live over plain HTTP-status checks. A scraper here will likely need `verify=False` with a documented justification, or a manually-supplied intermediate cert. `digital.nlt.go.th/dlib/` (their digital collections platform) has the same issue |

## What's still needed — `[HD-3]`

Per CLAUDE.md: *"the researcher opens each of the six candidate sources manually and
fills in the audit table by hand: does it exist, how many recipes are actually
reachable, is province exposed anywhere, is it worth building a scraper."*

The technical pass above narrows this down but doesn't replace it. Specifically still open:

1. **DOAE** — browse `doae.go.th` to find where the actual recipe/farming-knowledge content lives (24 sitemap URLs is far short of "2,000+" — is that the whole site, or is there a separate recipe subsection with its own sitemap?).
2. **Wongnai** — browse `www.wongnai.com` to find the current recipe section's URL pattern (search, category page, etc.) now that `recipe.wongnai.com` no longer exists.
3. **Thai Taste replacement** — find a live equivalent, or make the call to drop this slot and lean more on Kapook/interviews to cover the gap.
4. **Kapook Cooking** — spot-check 5–10 real recipe pages (not just the homepage) for province/region signal — the sitemap size and homepage keyword hits are promising, but that's not the same as confirming province coverage.
5. **TAT** — confirm `tat.or.th` actually has a destination/food content section (vs. being purely institutional/booking-oriented) and estimate real reachable count.
6. **Pantip** — find the current food board/tag URL and judge whether the JS-hydration + "community post, mention-in-body" attribution problem makes this worth the engineering cost at all.
7. **National Library** — in person or via `nlt.go.th`'s catalogue search, confirm which cookbooks are digitized/accessible vs. physical-only, and get a realistic count for Phase 2's cookbook ingestion target.
8. Record the **go/no-go per source** and the resulting realistically-scrapeable total in `docs/decisions.md` as HD-3, once the above is done. If the total is below 600, CLAUDE.md says stop and re-plan rather than proceeding on optimism.

## Raw tool output

<details>
<summary>doae.go.th</summary>

```
=== Source audit: https://www.doae.go.th ===
robots.txt: fetched, root_allowed=True, sitemap=https://www.doae.go.th/wp-sitemap.xml (24 URLs)
rendering: server-rendered (text/html ratio 0.2649)
homepage: no recipe keywords, no JSON-LD Recipe
```
</details>

<details>
<summary>wongnai.com</summary>

```
=== Source audit: https://www.wongnai.com ===
robots.txt: fetched, root_allowed=True, disallow /users/, no sitemap found at standard paths
rendering: JS-HYDRATED (id="app" SPA root, text/html ratio 0.0632 despite 278KB page)
homepage: no recipe keywords found in static HTML (client-rendered nav)
```
</details>

<details>
<summary>cooking.kapook.com</summary>

```
=== Source audit: https://cooking.kapook.com ===
robots.txt: fetched, root_allowed=True, no disallow rules
sitemap: https://cooking.kapook.com/sitemap.xml — 3,908 <loc> entries (+ sitemap_news.xml)
rendering: server-rendered (text/html ratio 0.1382)
homepage: Thai recipe keywords found: วิธีทำ, วัตถุดิบ. thai_char_ratio 0.66
```
</details>

<details>
<summary>tat.or.th</summary>

```
=== Source audit: https://www.tat.or.th ===
robots.txt: fetched, root_allowed=True
sitemap: https://www.tat.or.th/sitemap.xml — 84 <loc> entries
rendering: server-rendered (text/html ratio 0.4492)
homepage: no recipe keywords (expected — institutional/tourism content)
```
</details>

<details>
<summary>pantip.com</summary>

```
=== Source audit: https://pantip.com ===
robots.txt: fetched, root_allowed=True (Disallow:/ blocks scoped to other named bots)
sitemap: https://pantip.com/sitemap.xml — 43 <loc> entries
rendering: JS-HYDRATED (id="__next", Next.js)
homepage: Thai recipe keywords found: เครื่องปรุง, วัตถุดิบ
```
</details>

<details>
<summary>doa.go.th (rejected — see discrepancy note above)</summary>

```
HTTP 403 Forbidden on plain HEAD request.
```
</details>

<details>
<summary>nlt.go.th (National Library)</summary>

```
TLS verify failed: unable to get local issuer certificate.
openssl s_client confirms server does not send its intermediate cert
(subject: *.nlt.go.th, issued by DigiCert/Thawte — genuine cert, broken chain).
Plain HTTP status check: 200 OK, server: nginx.
```
</details>
