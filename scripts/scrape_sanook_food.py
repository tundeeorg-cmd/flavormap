"""Sanook food articles (www.sanook.com), under docs/scraping_rules.md.

    uv run python -m scripts.scrape_sanook_food --audit

**A retroactive stage A.** 80 recipe rows (873 ingredient lines) from Sanook articles
were collected on 2026-10-07 **outside these rules**, in a separate session, with no
robots.txt or terms check recorded. They now sit in data/raw/sanook_food/ (local,
gitignored). Their ``register`` column was filled in by that session; no register is
taken from it (every register is the researcher's). Nothing is loaded unless this audit
gets a `go`.

Stage A only: discovery and parsing are not built. The terms page was located by web
search on 2026-10-07.
"""

from __future__ import annotations

from src.scrape.base import AuditOnlyScraper, main


class Site(AuditOnlyScraper):
    source_id = "sanook_food"
    slug = "sanook_food"
    base_url = "https://www.sanook.com"
    tos_url = "https://www.sanook.com/termservice/"


if __name__ == "__main__":
    raise SystemExit(main(Site()))
