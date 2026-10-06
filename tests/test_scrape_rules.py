"""docs/scraping_rules.md, checked across the whole package rather than per module.

* Rule 9 — every site scraper in ``src/scrape/sites/`` has three fixture pages, the
  fixtures carry no personal data, and it has its own parser test file. Vacuous until
  the first site lands; it is here so the first one cannot land without them.
* Rules 4 and 6 — nothing in ``src/scrape/`` writes anything but ``raw_recipes``: no
  ``recipes`` row (so ``method_text`` stays empty), no province attribution, no dish
  category.
* Rule 4 — ``recipes.method_text`` is empty in the database.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
import re

import pytest

import src.scrape.sites as sites
from src.config import REPO_ROOT
from src.ingest.pdpa import find_leaks
from src.scrape.base import SiteScraper
from src.scrape.ethics import page_text

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "scrape"
SCRAPE_SRC = REPO_ROOT / "src" / "scrape"


def _site_scrapers() -> list[type[SiteScraper]]:
    found: list[type[SiteScraper]] = []
    for info in pkgutil.iter_modules(sites.__path__):
        module = importlib.import_module(f"{sites.__name__}.{info.name}")
        found += [obj for _, obj in inspect.getmembers(module, inspect.isclass)
                  if issubclass(obj, SiteScraper) and obj is not SiteScraper
                  and obj.__module__ == module.__name__]
    return found


@pytest.mark.parametrize("scraper", _site_scrapers(), ids=lambda s: s.source_id)
def test_every_site_has_three_clean_fixtures_and_parser_tests(scraper: type[SiteScraper]) -> None:
    fixtures = sorted((FIXTURES / scraper.source_id).glob("*.html"))
    assert len(fixtures) >= 3, f"{scraper.source_id}: needs 3 fixture pages in {FIXTURES}"
    for path in fixtures:
        leaks = find_leaks(page_text(path.read_text(encoding="utf-8")))
        assert not leaks, f"{path.name}: fixture carries personal data ({sorted(leaks)})"
    assert (REPO_ROOT / "tests" / f"test_scrape_{scraper.source_id}.py").exists()


def test_site_modules_are_named_after_their_source() -> None:
    for scraper in _site_scrapers():
        assert scraper.__module__.rsplit(".", 1)[1] == scraper.source_id


_WRITES = re.compile(r"\b(?:INSERT\s+INTO|UPDATE|DELETE\s+FROM)\s+(\w+)", re.I)


def test_the_scrape_package_writes_raw_recipes_only() -> None:
    offenders: list[str] = []
    for path in SCRAPE_SRC.rglob("*.py"):
        for table in _WRITES.findall(path.read_text(encoding="utf-8")):
            if table.lower() != "raw_recipes":
                offenders.append(f"{path.relative_to(REPO_ROOT)} writes {table}")
    assert not offenders, offenders


def test_the_scrape_package_assigns_no_register_province_or_category() -> None:
    pattern = re.compile(
        r"\b(?:register|province|dish_category|method_text)\s*=(?!=)|"
        r"[\"'](?:register|province|dish_category|method_text)[\"']\s*:"
    )
    offenders = [str(p.relative_to(REPO_ROOT)) for p in SCRAPE_SRC.rglob("*.py")
                 if pattern.search(p.read_text(encoding="utf-8"))]
    assert not offenders, offenders


def test_method_text_is_empty_in_the_database() -> None:
    try:
        from src.db import get_connection

        conn = get_connection()
    except Exception as exc:  # no .env or no Postgres: nothing to inspect
        pytest.skip(f"database unavailable: {type(exc).__name__}")
    try:
        (n,) = conn.execute(
            "SELECT count(*) FROM recipes WHERE coalesce(method_text, '') <> ''"
        ).fetchone()
        assert n == 0, f"{n} recipes carry method prose (rule 4)"
    finally:
        conn.close()

