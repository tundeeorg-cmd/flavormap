"""SheSimmers (Leela Punyaratabandhu), under docs/scraping_rules.md.

    uv run python -m scripts.scrape_shesimmers --audit


Stage A (audit) only. Discovery and parsing are not built: stage B (pilot) needs the
researcher's approval and a `go` row in the ETHICS.md register.

**Register: not assigned.** Whether English-language sites belong to the commercial
register or a separate one is the open HD-register-EN (docs/decisions.md). Nothing from
this source becomes a `recipes` row until that is decided.

**Pilot field plan (if approved; up to 100 recipes):** title (English, verbatim); the
Thai dish name, if the page shows one; the region claim (exact span and its location);
the publish date (as shown, never guessed); ingredient lines (English, verbatim, never
translated). `ScrapedRecipe` needs an English-title field and an optional Thai-name
field before then, since it was written for Thai titles.

Policy pages located by web search on 2026-10-06, not by crawling: no terms page found;
the site carries a copyright notice. Parts are now premium newsletter content, which
rule 1 never bypasses.
"""

from __future__ import annotations

from src.scrape.base import AuditOnlyScraper, main


class Site(AuditOnlyScraper):
    source_id = "shesimmers"
    slug = "shesimmers"
    base_url = "https://shesimmers.com"
    tos_url = None
    policy_urls = ("https://shesimmers.com/",)


if __name__ == "__main__":
    raise SystemExit(main(Site()))
