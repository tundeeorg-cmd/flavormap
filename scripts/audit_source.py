"""CLI: technical audit of a candidate recipe source, ahead of the human go/no-go call.

Usage:
    uv run python -m scripts.audit_source <base_url> [urls...] [--json] [--render]
                                           [--contact-email you@example.com]

For a given domain this reports, purely mechanically:
  - robots.txt directives (crawl-delay, disallow rules, sitemap pointers)
  - whether a sitemap is reachable
  - whether sample pages look server-rendered or JS-hydrated
  - which generic fields (title, JSON-LD Recipe schema, ingredient-shaped blocks,
    Thai-text presence) are extractable from each sample page

This tool makes the go/no-go call *possible*, it does not make it. Per CLAUDE.md
Phase 0 / HD-3, a human still has to open each source, judge how many recipes are
actually reachable, whether province is exposed anywhere, and whether it's worth
building a scraper for. This script's output is raw material for that judgment,
written into docs/source_audit.md.

Respects CLAUDE.md rule 7: identifying User-Agent with a contact email, 1 request/
second, and robots.txt disallow rules are honored — this tool never fetches a URL
robots.txt disallows, it only reports that it would have been disallowed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.robotparser
from dataclasses import asdict, dataclass, field
from urllib.parse import urljoin, urlparse

import httpx
from selectolax.parser import HTMLParser

DEFAULT_RATE_LIMIT_SEC = 1.0
REQUEST_TIMEOUT_SEC = 15.0

# Heuristic markers of a client-hydrated (JS-rendered) page shell.
SPA_ROOT_MARKERS = (
    'id="__next"',
    'id="root"',
    'id="app"',
    "ng-version",
    "__NUXT__",
    "__INITIAL_STATE__",
)

# Thai keywords that show up on almost any recipe page regardless of markup.
RECIPE_KEYWORDS_TH = ("ส่วนผสม", "วิธีทำ", "เครื่องปรุง", "วัตถุดิบ")


def build_user_agent(contact_email: str) -> str:
    return f"FlavorMapResearchBot/0.1 (+mailto:{contact_email}; academic research, non-commercial)"


@dataclass
class RobotsReport:
    url: str
    fetched_ok: bool
    crawl_delay: float | None
    sitemaps: list[str]
    root_allowed: bool
    disallow_rules_for_our_ua: list[str]
    disallow_rules_for_star: list[str]


@dataclass
class SitemapReport:
    checked_paths: list[str]
    found_at: str | None
    url_count_sample: int | None  # None if not found / not parseable


@dataclass
class HydrationReport:
    method: str  # "static-heuristic" | "rendered-comparison" | "render-unavailable"
    static_text_len: int
    static_html_len: int
    text_to_html_ratio: float
    spa_markers_found: list[str]
    rendered_text_len: int | None = None
    rendered_static_ratio: float | None = None
    verdict: str = "unknown"  # "server-rendered" | "js-hydrated" | "uncertain"


@dataclass
class PageFieldReport:
    url: str
    disallowed_by_robots: bool
    fetch_ok: bool
    http_status: int | None
    title: str | None
    has_jsonld_recipe: bool
    thai_keyword_hits: list[str]
    candidate_ingredient_blocks: int
    thai_char_ratio: float
    text_length: int


@dataclass
class SourceAuditReport:
    base_url: str
    audited_at: str
    user_agent: str
    robots: RobotsReport
    sitemap: SitemapReport
    hydration: HydrationReport | None
    pages: list[PageFieldReport] = field(default_factory=list)


class RateLimiter:
    """Sleeps as needed so consecutive calls are spaced >= min_interval apart."""

    def __init__(self, min_interval_sec: float) -> None:
        self.min_interval_sec = min_interval_sec
        self._last_call: float | None = None

    def wait(self) -> None:
        if self._last_call is not None:
            elapsed = time.monotonic() - self._last_call
            remaining = self.min_interval_sec - elapsed
            if remaining > 0:
                time.sleep(remaining)
        self._last_call = time.monotonic()


def fetch_robots(
    base_url: str, user_agent: str, client: httpx.Client, limiter: RateLimiter
) -> RobotsReport:
    robots_url = urljoin(base_url, "/robots.txt")
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(robots_url)

    limiter.wait()
    try:
        resp = client.get(robots_url, headers={"User-Agent": user_agent})
        fetched_ok = resp.status_code == 200
        raw = resp.text if fetched_ok else ""
    except httpx.HTTPError:
        fetched_ok = False
        raw = ""

    parser.parse(raw.splitlines())

    sitemaps: list[str] = []
    for line in raw.splitlines():
        if line.strip().lower().startswith("sitemap:"):
            sitemaps.append(line.split(":", 1)[1].strip())

    our_disallow = [
        line.strip() for line in raw.splitlines() if line.strip().lower().startswith("disallow")
    ] if fetched_ok else []

    raw_crawl_delay = parser.crawl_delay(user_agent)
    crawl_delay = float(raw_crawl_delay) if raw_crawl_delay is not None else None

    return RobotsReport(
        url=robots_url,
        fetched_ok=fetched_ok,
        crawl_delay=crawl_delay,
        sitemaps=sitemaps,
        root_allowed=parser.can_fetch(user_agent, base_url) if fetched_ok else True,
        disallow_rules_for_our_ua=our_disallow,
        disallow_rules_for_star=our_disallow,
    )


def check_sitemap(
    base_url: str,
    client: httpx.Client,
    user_agent: str,
    limiter: RateLimiter,
    robots: RobotsReport,
) -> SitemapReport:
    candidates = list(robots.sitemaps) or [
        urljoin(base_url, "/sitemap.xml"),
        urljoin(base_url, "/sitemap_index.xml"),
    ]
    for candidate in candidates:
        limiter.wait()
        try:
            resp = client.get(candidate, headers={"User-Agent": user_agent})
        except httpx.HTTPError:
            continue
        if resp.status_code == 200 and ("<urlset" in resp.text or "<sitemapindex" in resp.text):
            count = resp.text.count("<loc>")
            return SitemapReport(
                checked_paths=candidates, found_at=candidate, url_count_sample=count
            )
    return SitemapReport(checked_paths=candidates, found_at=None, url_count_sample=None)


def _text_and_html_len(html: str) -> tuple[int, int]:
    tree = HTMLParser(html)
    text = tree.body.text(separator=" ", strip=True) if tree.body else ""
    return len(text), len(html)


def analyze_hydration_static(html: str) -> HydrationReport:
    text_len, html_len = _text_and_html_len(html)
    ratio = text_len / html_len if html_len else 0.0
    markers = [m for m in SPA_ROOT_MARKERS if m in html]

    if markers or ratio < 0.02:
        verdict = "js-hydrated"
    elif ratio > 0.08:
        verdict = "server-rendered"
    else:
        verdict = "uncertain"

    return HydrationReport(
        method="static-heuristic",
        static_text_len=text_len,
        static_html_len=html_len,
        text_to_html_ratio=round(ratio, 4),
        spa_markers_found=markers,
        verdict=verdict,
    )


def analyze_hydration_rendered(url: str, static_html: str, user_agent: str) -> HydrationReport:
    """Strongest signal: render with headless Chromium and compare to the static fetch."""
    base = analyze_hydration_static(static_html)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        base.method = "render-unavailable"
        return base

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page(user_agent=user_agent)
                page.goto(url, timeout=REQUEST_TIMEOUT_SEC * 1000, wait_until="networkidle")
                rendered_html = page.content()
            finally:
                browser.close()
    except Exception:  # noqa: BLE001 — audit tooling degrades gracefully, never crashes the audit
        base.method = "render-unavailable"
        return base

    rendered_text_len, _ = _text_and_html_len(rendered_html)
    static_ratio = base.static_text_len / rendered_text_len if rendered_text_len else 0.0

    if static_ratio < 0.5 and rendered_text_len - base.static_text_len > 200:
        verdict = "js-hydrated"
    else:
        verdict = "server-rendered"

    return HydrationReport(
        method="rendered-comparison",
        static_text_len=base.static_text_len,
        static_html_len=base.static_html_len,
        text_to_html_ratio=base.text_to_html_ratio,
        spa_markers_found=base.spa_markers_found,
        rendered_text_len=rendered_text_len,
        rendered_static_ratio=round(static_ratio, 4),
        verdict=verdict,
    )


def extract_fields(url: str, html: str) -> PageFieldReport:
    tree = HTMLParser(html)
    title_node = tree.css_first("title")
    title = title_node.text(strip=True) if title_node else None

    has_jsonld_recipe = False
    for script in tree.css('script[type="application/ld+json"]'):
        content = script.text() or ""
        if '"@type"' in content and "Recipe" in content:
            has_jsonld_recipe = True
            break

    body_text = tree.body.text(separator=" ", strip=True) if tree.body else ""
    keyword_hits = [kw for kw in RECIPE_KEYWORDS_TH if kw in body_text]

    ingredient_block_selectors = (
        '[class*="ingredient" i]',
        '[class*="ingred" i]',
        '[id*="ingredient" i]',
    )
    candidate_blocks = 0
    for sel in ingredient_block_selectors:
        candidate_blocks += len(tree.css(sel))

    thai_chars = sum(1 for ch in body_text if "฀" <= ch <= "๿")
    thai_ratio = thai_chars / len(body_text) if body_text else 0.0

    return PageFieldReport(
        url=url,
        disallowed_by_robots=False,
        fetch_ok=True,
        http_status=200,
        title=title,
        has_jsonld_recipe=has_jsonld_recipe,
        thai_keyword_hits=keyword_hits,
        candidate_ingredient_blocks=candidate_blocks,
        thai_char_ratio=round(thai_ratio, 4),
        text_length=len(body_text),
    )


def audit_page(
    url: str,
    robots: RobotsReport,
    robots_parser_allows: bool,
    client: httpx.Client,
    user_agent: str,
    limiter: RateLimiter,
) -> PageFieldReport:
    if not robots_parser_allows:
        return PageFieldReport(
            url=url,
            disallowed_by_robots=True,
            fetch_ok=False,
            http_status=None,
            title=None,
            has_jsonld_recipe=False,
            thai_keyword_hits=[],
            candidate_ingredient_blocks=0,
            thai_char_ratio=0.0,
            text_length=0,
        )

    limiter.wait()
    try:
        resp = client.get(url, headers={"User-Agent": user_agent}, follow_redirects=True)
    except httpx.HTTPError as exc:
        return PageFieldReport(
            url=url,
            disallowed_by_robots=False,
            fetch_ok=False,
            http_status=None,
            title=f"fetch error: {exc}",
            has_jsonld_recipe=False,
            thai_keyword_hits=[],
            candidate_ingredient_blocks=0,
            thai_char_ratio=0.0,
            text_length=0,
        )

    if resp.status_code != 200:
        return PageFieldReport(
            url=url,
            disallowed_by_robots=False,
            fetch_ok=False,
            http_status=resp.status_code,
            title=None,
            has_jsonld_recipe=False,
            thai_keyword_hits=[],
            candidate_ingredient_blocks=0,
            thai_char_ratio=0.0,
            text_length=0,
        )

    return extract_fields(url, resp.text)


def run_audit(
    base_url: str,
    sample_urls: list[str],
    contact_email: str,
    render: bool,
    rate_limit_sec: float = DEFAULT_RATE_LIMIT_SEC,
) -> SourceAuditReport:
    user_agent = build_user_agent(contact_email)
    limiter = RateLimiter(rate_limit_sec)

    robots_parser = urllib.robotparser.RobotFileParser()

    with httpx.Client(timeout=REQUEST_TIMEOUT_SEC) as client:
        robots = fetch_robots(base_url, user_agent, client, limiter)
        robots_parser.set_url(urljoin(base_url, "/robots.txt"))
        if robots.fetched_ok:
            limiter.wait()
            try:
                robots_url = urljoin(base_url, "/robots.txt")
                raw = client.get(robots_url, headers={"User-Agent": user_agent}).text
            except httpx.HTTPError:
                raw = ""
            robots_parser.parse(raw.splitlines())

        sitemap = check_sitemap(base_url, client, user_agent, limiter, robots)

        urls_to_sample = sample_urls or [base_url]
        pages: list[PageFieldReport] = []
        hydration: HydrationReport | None = None

        for i, url in enumerate(urls_to_sample):
            allowed = robots_parser.can_fetch(user_agent, url) if robots.fetched_ok else True
            page_report = audit_page(url, robots, allowed, client, user_agent, limiter)
            pages.append(page_report)

            if i == 0 and page_report.fetch_ok:
                limiter.wait()
                try:
                    headers = {"User-Agent": user_agent}
                    resp = client.get(url, headers=headers, follow_redirects=True)
                    static_html = resp.text
                except httpx.HTTPError:
                    static_html = ""
                hydration = (
                    analyze_hydration_rendered(url, static_html, user_agent)
                    if render
                    else analyze_hydration_static(static_html)
                )

    return SourceAuditReport(
        base_url=base_url,
        audited_at=time.strftime("%Y-%m-%d", time.gmtime()),
        user_agent=user_agent,
        robots=robots,
        sitemap=sitemap,
        hydration=hydration,
        pages=pages,
    )


def _print_human(report: SourceAuditReport) -> None:
    print(f"=== Source audit: {report.base_url} ===")
    print(f"Audited: {report.audited_at}  |  User-Agent: {report.user_agent}")
    print()
    print("-- robots.txt --")
    print(f"  fetched: {report.robots.fetched_ok}  root_allowed: {report.robots.root_allowed}")
    print(f"  crawl_delay: {report.robots.crawl_delay}")
    print(f"  sitemaps declared: {report.robots.sitemaps or 'none'}")
    if report.robots.disallow_rules_for_star:
        print(f"  disallow rules ({len(report.robots.disallow_rules_for_star)}):")
        for rule in report.robots.disallow_rules_for_star[:15]:
            print(f"    {rule}")
    print()
    print("-- sitemap --")
    checked = ", ".join(report.sitemap.checked_paths)
    found_desc = report.sitemap.found_at or f"not found at {checked}"
    print(f"  found: {found_desc}")
    if report.sitemap.url_count_sample is not None:
        print(f"  <loc> count in that file: {report.sitemap.url_count_sample}")
    print()
    if report.hydration:
        print("-- rendering --")
        print(f"  method: {report.hydration.method}  verdict: {report.hydration.verdict}")
        print(
            f"  static text/html ratio: {report.hydration.text_to_html_ratio}  "
            f"spa markers: {report.hydration.spa_markers_found or 'none'}"
        )
        if report.hydration.rendered_text_len is not None:
            print(
                f"  static text len: {report.hydration.static_text_len}  "
                f"rendered text len: {report.hydration.rendered_text_len}  "
                f"static/rendered ratio: {report.hydration.rendered_static_ratio}"
            )
        print()
    print(f"-- sample pages ({len(report.pages)}) --")
    for p in report.pages:
        if p.disallowed_by_robots:
            print(f"  {p.url}\n    DISALLOWED by robots.txt — not fetched")
            continue
        if not p.fetch_ok:
            print(f"  {p.url}\n    fetch failed (status={p.http_status}): {p.title}")
            continue
        print(f"  {p.url}")
        print(f"    title: {p.title}")
        print(f"    JSON-LD Recipe schema: {p.has_jsonld_recipe}")
        print(f"    Thai recipe keywords found: {p.thai_keyword_hits or 'none'}")
        print(f"    candidate ingredient blocks (heuristic): {p.candidate_ingredient_blocks}")
        print(f"    thai_char_ratio: {p.thai_char_ratio}  text_length: {p.text_length}")
    print()
    print("NOTE: this is a mechanical audit only. Whether the source is worth building a")
    print("scraper for is [HD-3] — the researcher's call, recorded in docs/decisions.md.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url", help="Domain root to audit, e.g. https://recipe.wongnai.com")
    parser.add_argument(
        "sample_urls", nargs="*", help="Specific recipe page URLs to sample (optional)"
    )
    parser.add_argument(
        "--json", action="store_true", help="Print JSON instead of a human-readable report"
    )
    parser.add_argument(
        "--render",
        action="store_true",
        help="Also render with headless Chromium via Playwright for a stronger JS-hydration signal",
    )
    parser.add_argument(
        "--contact-email",
        default=os.environ.get("SCRAPER_CONTACT_EMAIL"),
        help="Included in the User-Agent per rule 7. Falls back to $SCRAPER_CONTACT_EMAIL.",
    )
    parser.add_argument("--rate-limit-sec", type=float, default=DEFAULT_RATE_LIMIT_SEC)
    args = parser.parse_args()

    if not args.contact_email:
        print(
            "error: --contact-email is required (or set SCRAPER_CONTACT_EMAIL). "
            "Rule 7 requires an identifying User-Agent for every request to a third party.",
            file=sys.stderr,
        )
        raise SystemExit(2)

    parsed = urlparse(args.base_url)
    if not parsed.scheme:
        args.base_url = "https://" + args.base_url

    report = run_audit(
        base_url=args.base_url,
        sample_urls=args.sample_urls,
        contact_email=args.contact_email,
        render=args.render,
        rate_limit_sec=args.rate_limit_sec,
    )

    if args.json:
        print(json.dumps(asdict(report), indent=2, ensure_ascii=False))
    else:
        _print_human(report)


if __name__ == "__main__":
    main()
