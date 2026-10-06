"""The base every site scraper is built on — `docs/scraping_rules.md`, enforced.

A site scraper is a :class:`SiteScraper` subclass in ``src/scrape/sites/<source_id>.py``
that supplies three things — where recipes are listed (:meth:`~SiteScraper.discover`),
how one page reads (:meth:`~SiteScraper.parse`), and its ToS URL — and ends with::

    if __name__ == "__main__":
        raise SystemExit(run(MySiteScraper))

Everything else is here, so no scraper can skip it:

==========  ===============================================================================
Rule 1      :class:`Crawler` refuses to exist for a source without a cleared ETHICS.md row
            (:func:`src.scrape.ethics.require_cleared`). ``--audit`` needs no row and writes
            no decision.
Rule 2      every network request goes through :class:`src.scrape.conduct.PoliteFetcher`
Rule 3      every page goes through :class:`src.scrape.cache.PageCache`; cached pages are
            never re-fetched without ``--refresh``, and robots.txt is not even requested
            while everything needed is on disk
Rules 4–7   :meth:`~SiteScraper.parse` must return a :class:`~src.scrape.record.ScrapedRecipe`,
            and only :func:`~src.scrape.record.finalise`'s output can be written
Rule 5      after a load, :func:`src.ingest.pdpa.scan_database` runs inside the same
            transaction; any leak anywhere rolls the whole load back
Rule 8      ``--audit`` / ``--pilot N`` / ``--full [--limit N]``. ``--pilot`` writes
            ``data/coverage/<source>_pilot.md`` and stops; ``--full`` refuses until that
            report carries a ``**Reviewed:** YYYY-MM-DD`` line written by the researcher
Rule 10     ``--full`` ends by printing the post-crawl checklist with the exact commit line
==========  ===============================================================================
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from itertools import islice
from pathlib import Path
from typing import Any, ClassVar

import httpx

from src.config import DATA_DIR, RAW_DIR
from src.ingest.pdpa import scan_database
from src.scrape.cache import CachedPage, PageCache
from src.scrape.conduct import CrawlAborted, PoliteFetcher, load_robots, make_client, user_agent
from src.scrape.ethics import AUDIT_DIR, ETHICS_PATH, audit_site, require_cleared, write_audit
from src.scrape.record import Finalised, RecordRefused, ScrapedRecipe, finalise, insert_raw_recipe

COVERAGE_DIR = DATA_DIR / "coverage"
DEFAULT_PILOT_N = 20
PILOT_EXAMPLES = 5
_REVIEWED = re.compile(r"^\*\*Reviewed:\*\*\s*(\d{4}-\d{2}-\d{2})", re.M)


class SiteScraper(ABC):
    """One source. Subclasses set the three class attributes and implement two methods."""

    source_id: ClassVar[str]  # the ETHICS.md / sources.source_id slug
    base_url: ClassVar[str]  # scheme + host, no trailing slash
    tos_url: ClassVar[str | None] = None  # None only if the audit found no ToS page

    @abstractmethod
    def discover(self, crawler: Crawler) -> Iterator[str]:
        """Recipe page URLs in a stable order. Fetch listing pages via ``crawler.page``."""

    @abstractmethod
    def parse(self, html: str, url: str, scraped_at: datetime) -> ScrapedRecipe | None:
        """One page → one record, or None if the page is not a recipe. Verbatim only:
        copy what the site says, decide nothing (rule 6)."""


class Crawler:
    """Cache-first, gate-checked page access for one source."""

    def __init__(
        self,
        scraper: SiteScraper,
        *,
        refresh: bool = False,
        ethics_path: Path = ETHICS_PATH,
        cache_root: Path = RAW_DIR,
        client_factory: Callable[[str], httpx.Client] = make_client,
        ua: str | None = None,
    ) -> None:
        require_cleared(scraper.source_id, ethics_path)  # rule 1: before anything else
        self.scraper = scraper
        self.refresh = refresh
        self.cache = PageCache(scraper.source_id, cache_root)
        self._client_factory = client_factory
        self._ua = ua
        self._client: httpx.Client | None = None
        self._fetcher: PoliteFetcher | None = None
        self.network_requests = 0
        self.cache_hits = 0

    def _fetch(self) -> PoliteFetcher:
        if self._fetcher is None:
            ua = self._ua or user_agent()
            self._client = self._client_factory(ua)
            robots = load_robots(self._client, self.scraper.base_url, ua)
            self._fetcher = PoliteFetcher(self._client, robots, ua)
            self._fetcher.note_request()
        return self._fetcher

    def page(self, url: str) -> CachedPage | None:
        """The page from cache, else from the network (then cached). None if not a 200."""
        if not self.refresh and (cached := self.cache.get(url)) is not None:
            self.cache_hits += 1
            return cached
        response = self._fetch().get(url)
        if response is None:
            return None
        self.network_requests += 1
        return self.cache.record(url, response.status_code, response.content)

    def close(self) -> None:
        if self._client is not None:
            self._client.close()


@dataclass
class CrawlResult:
    requested: int = 0
    unavailable: int = 0
    not_a_recipe: int = 0
    refused: list[str] = field(default_factory=list)
    records: list[tuple[CachedPage, Finalised]] = field(default_factory=list)


def crawl(crawler: Crawler, limit: int | None) -> CrawlResult:
    result = CrawlResult()
    for url in islice(crawler.scraper.discover(crawler), limit):
        result.requested += 1
        page = crawler.page(url)
        if page is None:
            result.unavailable += 1
            continue
        rec = crawler.scraper.parse(page.text(), url, page.fetched_at)
        if rec is None:
            result.not_a_recipe += 1
            continue
        try:
            result.records.append((page, finalise(rec)))
        except RecordRefused as exc:
            result.refused.append(str(exc))
    return result


# ── reports ──────────────────────────────────────────────────────────────────

FILL_FIELDS = (
    ("published_at", lambda p: p["published_at"] is not None),
    ("site_category", lambda p: bool(p["site_category"])),
    ("site_tags", lambda p: bool(p["site_tags"])),
    ("region_claim", lambda p: p["region_claim"] is not None),
    ("province_claim", lambda p: p["province_claim"] is not None),
    ("ingredient_lines", lambda p: bool(p["ingredient_lines"])),
    ("servings", lambda p: p["servings"] is not None),
)


def fill_rates(payloads: list[dict[str, Any]]) -> dict[str, tuple[int, int]]:
    total = len(payloads)
    return {name: (sum(1 for p in payloads if test(p)), total) for name, test in FILL_FIELDS}


def render_pilot(source_id: str, n: int, result: CrawlResult, today: date) -> str:
    payloads = [fin.payload for _, fin in result.records]
    lines = [
        f"# Pilot — `{source_id}` — {today.isoformat()}",
        "",
        "Written by `--pilot` (`src/scrape/base.py`). Nothing was written to the database.",
        "",
        "**Reviewed:** ← researcher: replace this arrow and text with the date (YYYY-MM-DD) "
        "you read the examples below. `--full` refuses until this line carries a date.",
        "",
        "## Counts",
        "",
        "| | |",
        "|---|---|",
        f"| URLs requested (pilot N) | {result.requested} (N = {n}) |",
        f"| not available (non-200, disallowed, empty) | {result.unavailable} |",
        f"| not a recipe (parser returned None) | {result.not_a_recipe} |",
        f"| refused by rules 4–7 | {len(result.refused)} |",
        f"| records that would load | {len(payloads)} |",
        "",
        "## Field fill rates (over records that would load)",
        "",
        "| field | filled | of | rate |",
        "|---|---|---|---|",
    ]
    for name, (filled, total) in fill_rates(payloads).items():
        rate = f"{filled / total:.0%}" if total else "—"
        lines.append(f"| {name} | {filled} | {total} | {rate} |")
    lines += ["", f"## {min(PILOT_EXAMPLES, len(payloads))} example records", ""]
    for payload in payloads[:PILOT_EXAMPLES]:
        shown = {k: v for k, v in payload.items() if not k.endswith("_norm")}
        lines += ["```json", json.dumps(shown, ensure_ascii=False, indent=2), "```", ""]
    if result.refused:
        lines += ["## Refusals (first 10)", ""]
        lines += [f"- {reason}" for reason in result.refused[:10]]
        lines.append("")
    return "\n".join(lines)


def pilot_reviewed(path: Path) -> date | None:
    if not path.exists():
        return None
    match = _REVIEWED.search(path.read_text(encoding="utf-8"))
    return date.fromisoformat(match.group(1)) if match else None


def post_crawl_checklist(source_id: str, loaded: int, today: date) -> str:
    return "\n".join([
        "",
        "AFTER A FULL CRAWL (rule 10) — these are yours, in this order:",
        "  1. make db-dump",
        "  2. make backup TO=<off-laptop path>",
        "  3. make status-snapshot",
        f'  4. git commit -m "data({source_id}): full crawl, {loaded} records loaded, '
        f'{today.isoformat()}"',
    ])


# ── stages ───────────────────────────────────────────────────────────────────

def stage_audit(scraper: SiteScraper, client: httpx.Client, ua: str, out_dir: Path,
                today: date) -> int:
    report = audit_site(client, scraper.source_id, scraper.base_url, scraper.tos_url, ua, today)
    path = write_audit(report, out_dir)
    print(f"audit written: {path}")
    if report.must_stop:
        print("STOP: robots.txt disallows us, or the ToS may forbid automated collection or "
              "reuse. Read the quoted clauses; no crawl until the researcher decides.")
        return 2
    print("Next: read the report, paste its row into ETHICS.md, and get the HD-3 decision.")
    return 0


def stage_pilot(crawler: Crawler, n: int, coverage_dir: Path, today: date) -> int:
    result = crawl(crawler, n)
    coverage_dir.mkdir(parents=True, exist_ok=True)
    path = coverage_dir / f"{crawler.scraper.source_id}_pilot.md"
    path.write_text(render_pilot(crawler.scraper.source_id, n, result, today), encoding="utf-8")
    print(f"pilot report: {path}")
    print("STOP: review the report. --full refuses until its **Reviewed:** line is dated.")
    return 0


def stage_full(crawler: Crawler, limit: int | None, coverage_dir: Path,
               connect: Callable[[], Any], today: date) -> int:
    source_id = crawler.scraper.source_id
    report = coverage_dir / f"{source_id}_pilot.md"
    if pilot_reviewed(report) is None:
        print(f"refused: {report} is missing or has no dated **Reviewed:** line. "
              "Run --pilot and have it reviewed first (rule 8).", file=sys.stderr)
        return 2
    result = crawl(crawler, limit)
    print(f"crawled {result.requested}: {len(result.records)} to load, "
          f"{len(result.refused)} refused, {result.not_a_recipe} not recipes, "
          f"{result.unavailable} unavailable")
    conn = connect()
    try:
        for page, fin in result.records:
            insert_raw_recipe(conn, source_id, fin, raw_path=str(page.path),
                              http_status=page.http_status, fetched_at=page.fetched_at)
        if offenders := scan_database(conn):  # rule 5, inside the same transaction
            conn.rollback()
            print("PDPA scan failed — load rolled back:\n  " + "\n  ".join(offenders[:20]),
                  file=sys.stderr)
            return 3
        conn.commit()
    finally:
        conn.close()
    print(post_crawl_checklist(source_id, len(result.records), today))
    return 0


def run(
    scraper_cls: type[SiteScraper],
    argv: list[str] | None = None,
    *,
    connect: Callable[[], Any] | None = None,
    crawler_kwargs: dict[str, Any] | None = None,
    coverage_dir: Path = COVERAGE_DIR,
    audit_dir: Path = AUDIT_DIR,
    today: date | None = None,
) -> int:
    ap = argparse.ArgumentParser(description=f"Scrape {scraper_cls.source_id} under "
                                 "docs/scraping_rules.md")
    stage = ap.add_mutually_exclusive_group(required=True)
    stage.add_argument("--audit", action="store_true",
                       help="fetch robots.txt + ToS, write a dated audit report, crawl nothing")
    stage.add_argument("--pilot", nargs="?", type=int, const=DEFAULT_PILOT_N, metavar="N",
                       help=f"crawl N pages (default {DEFAULT_PILOT_N}), write the pilot "
                       "report, stop")
    stage.add_argument("--full", action="store_true",
                       help="crawl and load into raw_recipes (needs a reviewed pilot)")
    ap.add_argument("--limit", type=int, help="with --full: stop after N recipe URLs")
    ap.add_argument("--refresh", action="store_true",
                    help="re-fetch pages that are already cached")
    args = ap.parse_args(argv)
    if args.limit is not None and not args.full:
        ap.error("--limit goes with --full; --pilot takes its own N")
    if args.pilot is not None and args.pilot < 1:
        ap.error("--pilot N must be at least 1")
    today = today or datetime.now(UTC).date()
    scraper = scraper_cls()
    kwargs = dict(crawler_kwargs or {})

    if args.audit:
        ua = kwargs.get("ua") or user_agent()
        factory = kwargs.get("client_factory", make_client)
        with factory(ua) as client:
            return stage_audit(scraper, client, ua, audit_dir, today)

    crawler = Crawler(scraper, refresh=args.refresh, **kwargs)
    try:
        if args.pilot is not None:
            return stage_pilot(crawler, args.pilot, coverage_dir, today)
        if connect is None:
            from src.db import get_connection

            connect = get_connection
        return stage_full(crawler, args.limit, coverage_dir, connect, today)
    except CrawlAborted as exc:
        print(f"CRAWL ABORTED: {exc}", file=sys.stderr)
        return 4
    finally:
        crawler.close()
