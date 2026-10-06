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
from src.scrape.recon import MAX_PROBE_REQUESTS, SitemapProbe, policy_text, probe_sitemaps
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
    # Further pages to read for clauses: a copyright notice, a footer, a privacy policy.
    policy_urls: tuple[str, ...] = ()
    # Other hosts the source's data comes through (e.g. an API host). Their robots.txt
    # is checked too, since data read from them is collection from them.
    extra_robots_hosts: tuple[str, ...] = ()

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
        """Stage A. robots.txt, then every policy page (`tos_url` and `policy_urls`),
        then the sitemap probe. All through the PoliteFetcher; never a recipe page."""
        ua = user_agent()
        quotes: list[tuple[str, str]] = []          # (page, quoted clause)
        policies: list[str] = []
        probe = SitemapProbe()
        with self._client(ua) as client:
            try:
                parser = load_robots(client, self.base_url, ua)
                robots = "allowed at root for our User-Agent"
            except SystemExit as e:
                parser, robots = None, f"DISALLOWED: {e}"
            except httpx.HTTPError as e:
                parser, robots = None, f"robots.txt not readable ({_why(e)})"
            signals = self._robots_signals(client)
            for host in self.extra_robots_hosts:
                try:
                    load_robots(client, host, ua)
                    robots += f"; {host}: allowed at root"
                except SystemExit:
                    robots += f"; {host}: DISALLOWED at root"
                except httpx.HTTPError as e:
                    robots += f"; {host}: robots.txt not readable ({_why(e)})"
            if parser is not None:
                fetcher = PoliteFetcher(client, parser, ua)
                for url in [u for u in (self.tos_url, *self.policy_urls) if u]:
                    r = fetcher.get(url)
                    if r is None:
                        policies.append(f"{url}: disallowed by robots.txt")
                        continue
                    found = flag_tos_clauses(policy_text(r.text)) if r.status_code == 200 else []
                    quotes.extend((url, q) for q in found)
                    policies.append(f"{url}: HTTP {r.status_code}, {len(found)} flagged")
                probe = probe_sitemaps(fetcher, self.base_url, parser)
        if parser is None:
            policies.append("policy pages not fetched (robots.txt unreadable)")
        if self.tos_url is None:
            policies.insert(0, "no terms-of-service page located: the researcher must check")
        tos = "; ".join(policies) + f"; see data/coverage/{self.slug}_audit.md"
        row = AuditRow(self.source_id, self.base_url, today(), robots, tos,
                       "pending (researcher)")
        self.coverage_dir.mkdir(parents=True, exist_ok=True)
        self.audit_report.write_text(
            audit_report(self, row, robots, signals, policies, quotes, probe), encoding="utf-8")
        append_row(row, self.ethics_path)
        print(f"audit row appended to {self.ethics_path.name} (decision: pending)")
        print(f"evidence: {self.audit_report}")
        print("STOP: the researcher reviews robots.txt, the terms and the probe before any crawl.")
        return row

    def _robots_signals(self, client: httpx.Client) -> list[str]:
        """robots.txt lines about AI use or content signals, quoted for the researcher."""
        try:
            text = client.get(f"{self.base_url}/robots.txt").text
        except httpx.HTTPError:
            return []
        keys = ("content-signal", "ai-train", "ai-input", "gptbot", "ccbot", "google-extended",
                "claudebot", "crawl-delay")
        return [ln.strip() for ln in text.splitlines()
                if any(k in ln.lower() for k in keys)][:20]

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


def _why(e: httpx.HTTPError) -> str:
    """The HTTP status when there is one (403 and 404 mean different things), else the
    error type."""
    if isinstance(e, httpx.HTTPStatusError):
        return f"HTTP {e.response.status_code}"
    return type(e).__name__


class AuditOnlyScraper(SiteScraper):
    """A site at stage A only. Discovery and parsing refuse until the researcher approves
    stage B; the ETHICS go-gate refuses `--pilot` and `--full` in any case."""

    def discover(self, fetcher: PoliteFetcher, limit: int) -> Iterator[str]:
        raise NotImplementedError(f"{self.source_id}: discovery is not built; "
                                  "stage B awaits the researcher's approval")

    def parse(self, html: str, url: str) -> ScrapedRecipe | None:
        raise NotImplementedError(f"{self.source_id}: the parser is not built; "
                                  "stage B awaits the researcher's approval")


def audit_report(scraper: SiteScraper, row: AuditRow, robots: str, signals: list[str],
                 policies: list[str], quotes: list[tuple[str, str]],
                 probe: SitemapProbe) -> str:
    """The stage-A evidence, as Markdown, for the researcher."""
    out = [f"# {scraper.source_id}: audit, {row.date}", "",
           f"- Site: {scraper.base_url}", f"- robots.txt: {robots}", ""]
    out += ["## robots.txt lines about AI use, content signals or crawl delay", ""]
    out += [f"    {s}" for s in signals] or ["_none_"]
    out += ["", "## Policy pages read", ""] + [f"- {p}" for p in policies]
    out += ["", "## Flagged clauses (quoted; read them in full on the site)", ""]
    out += [f"> {q}  \n> — {url}\n" for url, q in quotes] or ["_none flagged_"]
    out += ["", "The keyword flag is not a verdict. Read the full terms before deciding.", "",
            f"## Sitemap probe ({probe.requests_used} of {MAX_PROBE_REQUESTS} requests; "
            "sitemaps only, no recipe page fetched)", "",
            f"- Sitemap index: {probe.index_url or 'none found'}",
            f"- Child sitemaps: {len(probe.child_sitemaps)}",
            f"- Taxonomy sitemaps read: {len(probe.taxonomy_sitemaps)}",
            f"- Category/tag/course/cuisine pages: {len(probe.terms)}", "",
            "### Recipe index pages", ""]
    out += [f"- {t}" for t in probe.recipe_index_pages[:40]] or ["_none found by name_"]
    out += ["", "### Region-like terms (a hint, not a claim)", ""]
    out += [f"- {t}" for t in probe.region_terms[:60]] or ["_none found_"]
    if probe.notes:
        out += ["", "### Probe notes", ""] + [f"- {n}" for n in probe.notes]
    return "\n".join(out) + "\n"


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
