"""TAT local-food articles (tourismthailand.org), under docs/scraping_rules.md.

    uv run python -m scripts.scrape_tat_food --audit

**A retroactive stage A.** 718 dish rows from Tourism Authority of Thailand articles
were collected on 2026-10-06 **outside these rules**, in a separate session, through the
Thai site, the English site and the article API, with no robots.txt or terms check
recorded. They now sit in data/raw/tat_food/ (local, gitignored). Nothing is loaded
unless this audit gets a `go`.

robots.txt is checked on every host the data came through (the Thai site, the English
site and the API), plus the host of the terms page. Stage A only: discovery and parsing
are not built, and no register is assigned. Policy pages were located by web search on
2026-10-07.
"""

from __future__ import annotations

from src.scrape.base import AuditOnlyScraper, main


class Site(AuditOnlyScraper):
    source_id = "tat_food"
    slug = "tat_food"
    base_url = "https://thai.tourismthailand.org"
    tos_url = "https://operator.tourismthailand.org/Information/Terms-and-Conditions"
    policy_urls = ("https://www.tourismthailand.org/Information/Privacy-Policy",)
    extra_robots_hosts = (
        "https://www.tourismthailand.org",
        "https://api.tourismthailand.org",
        "https://operator.tourismthailand.org",
    )


if __name__ == "__main__":
    raise SystemExit(main(Site()))
