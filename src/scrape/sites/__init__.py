"""Site scrapers built on :mod:`src.scrape.base` — one module per source, named after its
``source_id``. Each module defines one :class:`~src.scrape.base.SiteScraper` subclass and
must have three fixture pages in ``tests/fixtures/scrape/<source_id>/`` and parser tests
in ``tests/test_scrape_<source_id>.py`` (rule 9; ``tests/test_scrape_rules.py`` checks).

Empty on 2026-10-06: the two existing fetchers (``scripts/fetch_kapook.py``,
``scripts/fetch_dcp_food.py``) predate this base. They share its politeness layer
(:mod:`src.scrape.conduct`) but not its stages, cache layout or record contract — see
``docs/scraping_rules.md`` §"Existing fetchers".
"""
