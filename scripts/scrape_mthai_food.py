"""MThai FOOD (mthai.com), under docs/scraping_rules.md.

    uv run python -m scripts.scrape_mthai_food --audit

**A retroactive stage A.** 200 recipes from this source were collected on 2026-10-06
**outside these rules**, in a separate session and through the researcher's browser,
with no robots.txt or terms check recorded. They now sit in data/raw/mthai_food/
(local, gitignored), and they hold method prose, intros and author bylines, which rule 4
says are never stored. Nothing from them is loaded unless this audit gets a `go`, and
then only a copy without the method, intro and author columns.

Stage A only: discovery and parsing are not built. No register is assigned; the
collected CSV's own register column says `commercial`, which is not a decision.
The terms page was located by web search on 2026-10-07.
"""

from __future__ import annotations

from src.scrape.base import AuditOnlyScraper, main


class Site(AuditOnlyScraper):
    source_id = "mthai_food"
    slug = "mthai_food"
    base_url = "https://mthai.com"
    tos_url = "https://mthai.com/app-terms-of-service"


if __name__ == "__main__":
    raise SystemExit(main(Site()))
