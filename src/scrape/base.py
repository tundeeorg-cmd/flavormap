"""The base every site scraper extends (docs/scraping_rules.md). It enforces the rules in
code, so a new scraper inherits them instead of reimplementing them.

A site scraper supplies four attributes and two methods:

    source_id, slug, base_url, tos_url
    discover(fetcher, limit) -> iterator of recipe-page URLs
    parse(html, url) -> ScrapedRecipe | None

and gets the three stages, each refusing to run out of order:

``--audit``
    robots.txt checked and the ToS page fetched under our identity. Flagged clauses are
    quoted into ``data/coverage/<slug>_audit.md``, and a dated row, decision
    ``pending``, is appended to the ETHICS.md register. **Stops.** The researcher records
    go or no-go.
``--pilot N`` (default 20)
    Requires a ``go`` row. Fetches N recipe pages (cached), stores them, writes
    ``data/coverage/<slug>_pilot.md`` with field fill rates and 5 example records.
    **Stops** for review.
``--full --limit N``
    Requires a ``go`` row **and** a pilot report. Stores up to N records, then prints the
    after-a-full-crawl checklist (rule 10).

**What a load writes, and what it never writes.** Each record goes through
`to_parsed_json` (PDPA redaction, then Thai normalisation, both forms kept) into
``raw_recipes`` under the source's own ``source_id``, with its ``redaction_log`` row.
Inside the same transaction, `src.ingest.pdpa.scan_database` then scans the whole
database; any hit rolls the load back. **A scraper never writes ``recipes``,
``province_attribution`` or a register.** Turning claims into attributions follows the
decided HD-Kapook rule, which is a separate step (rule 6).
"""

from __future__ import annotations

import argparse
import datetime
import json
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from selectolax.parser import HTMLParser

from src.config import DATA_DIR, RAW_DIR
from src.db import get_connection
from src.ingest.pdpa import RedactionReport, scan_database
from src.scrape.cache import CachedPage, PageCache
from src.scrape.conduct import PoliteFetcher, load_robots, make_client, user_agent
from src.scrape.ethics import (
    ETHICS_PATH,
    AuditRow,
    append_row,
    flag_tos_clauses,
    require_go,
    today,
)
from src.scrape.record import RecordRejected, ScrapedRecipe, to_parsed_json

COVERAGE_DIR = DATA_DIR / "coverage"
DEFAULT_PILOT = 20
N_EXAMPLES = 5


class StageRefused(SystemExit):
    """A stage was asked for out of order (e.g. --full before any pilot)."""


class PDPAViolation(RuntimeError):
    """The whole-database scan found personal data after a load. It was rolled back."""


@dataclass
class LoadResult:
    stored: list[tuple[CachedPage, ScrapedRecipe, dict[str, object]]] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)
    skipped: int = 0


class SiteScraper(ABC):
    source_id: str
    slug: str
    base_url: str
    tos_url: str | None = None

    def __init__(
        self,
        *,
        raw_root: Path = RAW_DIR,
        coverage_dir: Path = COVERAGE_DIR,
        ethics_path: Path = ETHICS_PATH,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.raw_root = raw_root
        self.coverage_dir = coverage_dir
        self.ethics_path = ethics_path
        self.transport = transport  # tests inject a MockTransport; never set in production

    # ── to implement per site ────────────────────────────────────────────────

    @abstractmethod
    def discover(self, fetcher: PoliteFetcher, limit: int) -> Iterator[str]:
        """Recipe-page URLs on this site, at most `limit` of them."""

    @abstractmethod
    def parse(self, html: str, url: str) -> ScrapedRecipe | None:
        """One recipe page into the allowed fields only, or None if it is not a recipe."""

    # ── plumbing ─────────────────────────────────────────────────────────────

    def _client(self, ua: str) -> httpx.Client:
        if self.transport is not None:
            return make_client(ua, transport=self.transport)
        return make_client(ua)

    @property
    def pilot_report(self) -> Path:
        return self.coverage_dir / f"{self.slug}_pilot.md"

    @property
    def audit_report(self) -> Path:
        return self.coverage_dir / f"{self.slug}_audit.md"

    # ── stage 1: audit ───────────────────────────────────────────────────────

    def audit(self) -> AuditRow:
        ua = user_agent()
        with self._client(ua) as client:
            try:
                load_robots(client, self.base_url, ua)
                robots = "allowed at root for our User-Agent"
            except SystemExit as e:
                robots = f"DISALLOWED: {e}"
            except httpx.HTTPError as e:
                robots = f"robots.txt not readable ({type(e).__name__})"
            quotes: list[str] = []
            if self.tos_url is None:
                tos = "no ToS URL known: the researcher must locate it"
            else:
                try:
                    r = client.get(self.tos_url)
                    body = HTMLParser(r.text).body
                    page_text = body.text(separator="\n") if body else r.text
                    quotes = flag_tos_clauses(page_text)
                    tos = (f"HTTP {r.status_code}; {len(quotes)} clause(s) flagged for "
                           f"review, see data/coverage/{self.slug}_audit.md")
                except httpx.HTTPError as e:
                    tos = f"ToS not readable ({type(e).__name__})"
        row = AuditRow(self.source_id, self.base_url, today(), robots, tos,
                       "pending (researcher)")
        self.coverage_dir.mkdir(parents=True, exist_ok=True)
        self.audit_report.write_text(
            f"# {self.source_id}: audit, {row.date}\n\n"
            f"- Site: {self.base_url}\n- robots.txt: {robots}\n"
            f"- Terms of service: {self.tos_url or '(not located)'}: {tos}\n\n"
            "## Flagged clauses (quoted, for the researcher to read in full on the site)\n\n"
            + ("\n".join(f"> {q}\n" for q in quotes) or "_none flagged_\n")
            + "\nThe keyword flag is not a verdict. Read the full terms before deciding.\n",
            encoding="utf-8",
        )
        append_row(row, self.ethics_path)
        print(f"audit row appended to {self.ethics_path.name} (decision: pending)")
        print(f"evidence: {self.audit_report}")
        if "DISALLOWED" in robots or quotes:
            print("STOP: robots.txt or the terms need the researcher's review before any crawl.")
        return row

    # ── stages 2 and 3: pilot, full ──────────────────────────────────────────

    def _crawl(self, n: int, refresh: bool) -> LoadResult:
        gate = require_go(self.source_id, self.ethics_path)
        ua = user_agent()
        result = LoadResult()
        cache = PageCache(self.slug, self.raw_root)
        scraped_at = datetime.datetime.now(datetime.UTC)
        records: list[tuple[CachedPage, ScrapedRecipe]] = []
        with self._client(ua) as client:
            fetcher = PoliteFetcher(client, load_robots(client, self.base_url, ua), ua)
            for url in self.discover(fetcher, n):
                page = cache.fetch(fetcher, url, refresh=refresh)
                if page is None or page.http_status != 200:
                    result.skipped += 1
                    continue
                if (rec := self.parse(page.text, url)) is not None:
                    records.append((page, rec))
        self._store(records, scraped_at, gate, result)
        return result

    def _store(self, records: list[tuple[CachedPage, ScrapedRecipe]],
               scraped_at: datetime.datetime, gate: AuditRow, result: LoadResult) -> None:
        conn = get_connection()
        try:
            with conn.transaction():
                conn.execute(
                    """INSERT INTO sources (source_id, source_type, base_url, robots_ok,
                           audited_on)
                       VALUES (%s, 'web_scraped', %s, true, %s)
                       ON CONFLICT (source_id) DO NOTHING""",
                    (self.source_id, self.base_url, gate.date))
                for page, rec in records:
                    try:
                        payload, report = to_parsed_json(rec, scraped_at)
                    except RecordRejected as e:
                        result.rejected.append(str(e))
                        continue
                    raw_id = conn.execute(
                        """INSERT INTO raw_recipes (source_id, source_url, raw_path,
                               published_at, parsed_json, content_hash, http_status)
                           VALUES (%s, %s, %s, %s, %s, %s, %s)
                           ON CONFLICT (source_id, content_hash) DO UPDATE SET
                               parsed_json = EXCLUDED.parsed_json,
                               published_at = EXCLUDED.published_at
                           RETURNING raw_id""",
                        (self.source_id, rec.url, str(page.path), rec.published_at,
                         json.dumps(payload, ensure_ascii=False), page.content_sha256,
                         page.http_status),
                    ).fetchone()[0]  # type: ignore[index]
                    self._log_redactions(conn, raw_id, page, report)
                    result.stored.append((page, rec, payload))
                # Rule 5: the whole-database scan must pass after every load. Any hit
                # rolls this transaction back; nothing personal is ever committed.
                if offenders := scan_database(conn):
                    raise PDPAViolation("load rolled back; personal data found: "
                                        + "; ".join(offenders[:5]))
        finally:
            conn.close()

    def _log_redactions(self, conn: object, raw_id: int, page: CachedPage,
                        report: RedactionReport) -> None:
        cols = list(RedactionReport.COLUMNS.values())
        conn.execute(  # type: ignore[attr-defined]
            f"""INSERT INTO redaction_log (raw_id, source_id, document_ref, {", ".join(cols)},
                    suspected_parser_failure)
                VALUES (%s, %s, %s, {", ".join(["%s"] * len(cols))}, false)
                ON CONFLICT (raw_id) DO UPDATE SET
                    {", ".join(f"{c} = EXCLUDED.{c}" for c in cols)}""",
            (raw_id, self.source_id, page.path.name, *(getattr(report, c) for c in cols)),
        )

    def pilot(self, n: int = DEFAULT_PILOT, refresh: bool = False) -> LoadResult:
        result = self._crawl(n, refresh)
        self.coverage_dir.mkdir(parents=True, exist_ok=True)
        self.pilot_report.write_text(pilot_report(self.source_id, result), encoding="utf-8")
        print(f"pilot: {len(result.stored)} stored, {len(result.rejected)} rejected, "
              f"{result.skipped} skipped. Report: {self.pilot_report}")
        print("STOP: review the pilot report before any --full run.")
        return result

    def full(self, limit: int, refresh: bool = False) -> LoadResult:
        if not self.pilot_report.exists():
            raise StageRefused(f"{self.source_id}: no pilot report at {self.pilot_report}. "
                               "Run --pilot and review it before --full.")
        result = self._crawl(limit, refresh)
        n = len(result.stored)
        print(f"full: {n} stored, {len(result.rejected)} rejected, {result.skipped} skipped.")
        print("After a full crawl (docs/scraping_rules.md §10), now:\n"
              "  1. make db-dump\n"
              "  2. make backup TO=<off-laptop path>   (you type the passphrase)\n"
              "  3. make status-snapshot\n"
              f"  4. commit: \"data({self.source_id}): {n} recipes scraped "
              f"{datetime.date.today().isoformat()}\"")
        return result


def _filled(payload: dict[str, object], key: str) -> bool:
    value = payload.get(key)
    return bool(value) and value != []


def pilot_report(source_id: str, result: LoadResult) -> str:
    """Fill rates per field and five example records, as Markdown."""
    n = len(result.stored)
    fields = (("published_at", "published_at"), ("site_category", "site_category"),
              ("region or province claim", None), ("ingredient lines", "ingredient_lines"))
    lines = [f"# {source_id}: pilot, {today()}", "",
             f"{n} records stored, {len(result.rejected)} rejected, "
             f"{result.skipped} pages skipped (not 200 or disallowed).", "",
             "| Field | Filled | Rate |", "|---|---|---|"]
    for label, key in fields:
        if key is None:
            k = sum(1 for _, _, p in result.stored
                    if _filled(p, "region_claim") or _filled(p, "province_claim"))
        else:
            k = sum(1 for _, _, p in result.stored if _filled(p, key))
        lines.append(f"| {label} | {k} of {n} | {k / n:.0%} |" if n else f"| {label} | 0 | — |")
    lines += ["", "## Example records", ""]
    for _, _rec, payload in result.stored[:N_EXAMPLES]:
        lines.append("```json")
        lines.append(json.dumps(
            {k: payload[k] for k in ("url", "title_th", "published_at", "site_category",
                                     "region_claim", "province_claim", "ingredient_lines")},
            ensure_ascii=False, indent=1))
        lines.append("```")
    if result.rejected:
        lines += ["", "## Rejected", ""] + [f"- {r}" for r in result.rejected]
    lines += ["", "**STOP.** Review before any `--full` run.", ""]
    return "\n".join(lines)


def main(scraper: SiteScraper, argv: list[str] | None = None) -> int:
    """The command line every site scraper exposes."""
    ap = argparse.ArgumentParser(description=f"Scrape {scraper.source_id} under the rules "
                                             "in docs/scraping_rules.md")
    stage = ap.add_mutually_exclusive_group(required=True)
    stage.add_argument("--audit", action="store_true", help="robots.txt + ToS; then stop")
    stage.add_argument("--pilot", nargs="?", type=int, const=DEFAULT_PILOT,
                       help=f"store N records (default {DEFAULT_PILOT}), report, stop")
    stage.add_argument("--full", action="store_true", help="the full crawl (needs --limit)")
    ap.add_argument("--limit", type=int, help="maximum records for --full")
    ap.add_argument("--refresh", action="store_true", help="re-fetch pages already cached")
    args = ap.parse_args(argv)
    if args.audit:
        scraper.audit()
    elif args.pilot is not None:
        scraper.pilot(args.pilot, refresh=args.refresh)
    else:
        if not args.limit:
            ap.error("--full needs --limit N")
        scraper.full(args.limit, refresh=args.refresh)
    return 0
