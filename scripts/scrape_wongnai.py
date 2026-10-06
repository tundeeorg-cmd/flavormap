"""Wongnai scraper, under docs/scraping_rules.md.

    uv run python -m scripts.scrape_wongnai --audit

**Stage A (audit) only, so far.** `discover` and `parse` are deliberately not written:
stages B (pilot) and C (full) need the researcher's separate approval and a ``go`` row in
the ETHICS.md register, and the base refuses them without it anyway. Wongnai renders its
pages with JavaScript (source audit, 2026-08-09), so a pilot will also need a decision
on how pages are rendered before a parser can be written against them.

The terms-of-service URL was located by a web search on 2026-10-06 rather than by
crawling the site.
"""

from __future__ import annotations

from collections.abc import Iterator

from src.scrape.base import SiteScraper, main
from src.scrape.conduct import PoliteFetcher
from src.scrape.record import ScrapedRecipe


class Wongnai(SiteScraper):
    source_id = "wongnai"
    slug = "wongnai"
    base_url = "https://www.wongnai.com"
    tos_url = "https://www.wongnai.com/terms"

    def discover(self, fetcher: PoliteFetcher, limit: int) -> Iterator[str]:
        raise NotImplementedError("wongnai: discovery is not built; stage B awaits approval")

    def parse(self, html: str, url: str) -> ScrapedRecipe | None:
        raise NotImplementedError("wongnai: the parser is not built; stage B awaits approval")


if __name__ == "__main__":
    raise SystemExit(main(Wongnai()))
