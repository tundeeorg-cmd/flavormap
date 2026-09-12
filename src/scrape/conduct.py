"""Shared scraping conduct — rule 7 (ETHICS.md), implemented once.

1 request/second minimum, an honest User-Agent carrying SCRAPER_CONTACT_EMAIL,
robots.txt re-checked at run time on every run rather than trusted from the audit.

`scripts.fetch_dcp_food` and `scripts.fetch_kapook` each reimplemented this
independently, and the two copies had already drifted: `fetch_kapook.py`'s
`user_agent()` was missing the placeholder-email guard `fetch_dcp_food.py` had, so an
unconfigured `SCRAPER_CONTACT_EMAIL` (still holding `.env.example`'s
`you@example.com`) would have silently fetched `cooking.kapook.com` under a fake,
unreachable contact address — exactly what rule 7 exists to prevent. Sharing one
implementation is what keeps that kind of drift from happening again, not just less
code.

`load_robots` also standardises on fetching robots.txt *through the same client and
identifying User-Agent as every other request*, rather than a bare `urllib.robotparser`
read outside the client (as `fetch_dcp_food.py` did) — one honest identity for the
entire run, robots.txt included, and a clear failure if the root path turns out to be
disallowed rather than a run that proceeds regardless.
"""

from __future__ import annotations

import time
import urllib.robotparser

import httpx

from src.config import get_settings

RATE_LIMIT_SEC = 1.0


def user_agent() -> str:
    """The identifying User-Agent every fetcher must send.

    Refuses to build one under a placeholder contact address — rule 7 requires a
    genuinely reachable email before any fetch, on any source.
    """
    email = get_settings().scraper_contact_email
    if not email or "example.com" in email:
        raise SystemExit(
            "SCRAPER_CONTACT_EMAIL is unset or still a placeholder. Rule 7 requires a "
            "genuinely reachable address in the User-Agent before any fetch."
        )
    return f"FlavorMapResearchBot/0.1 (+mailto:{email}; academic research, non-commercial)"


def load_robots(
    client: httpx.Client, base_url: str, ua: str
) -> urllib.robotparser.RobotFileParser:
    """Fetch and parse robots.txt through `client`, under `ua` — re-checked at run
    time, never trusted from an earlier audit. Raises if the root path is disallowed
    for our own User-Agent; rule 7 says a disallowed source is dropped, never worked
    around, and that has to hold before a single page is fetched, not after."""
    response = client.get(f"{base_url}/robots.txt")
    response.raise_for_status()
    parser = urllib.robotparser.RobotFileParser()
    parser.parse(response.text.splitlines())
    if not parser.can_fetch(ua, base_url + "/"):
        raise SystemExit(
            f"robots.txt disallows our User-Agent at the root — stopping (rule 7): {base_url}"
        )
    return parser


class PoliteFetcher:
    """Sequential fetcher: one request per second, robots.txt-checked, no concurrency.

    A disallowed URL is reported and skipped, never fetched anyway (rule 7) — callers
    that need to distinguish "disallowed" from "fetched" should check `allowed()`
    first if the distinction matters to them.
    """

    def __init__(
        self,
        client: httpx.Client,
        robots: urllib.robotparser.RobotFileParser,
        ua: str,
    ) -> None:
        self.client = client
        self.robots = robots
        self.ua = ua
        self._last = 0.0

    def _wait(self) -> None:
        elapsed = time.monotonic() - self._last
        if elapsed < RATE_LIMIT_SEC:
            time.sleep(RATE_LIMIT_SEC - elapsed)
        self._last = time.monotonic()

    def allowed(self, url: str) -> bool:
        return self.robots.can_fetch(self.ua, url)

    def get(self, url: str) -> httpx.Response | None:
        if not self.allowed(url):
            print(f"  DISALLOWED by robots.txt: {url}")
            return None
        self._wait()
        return self.client.get(url)

    def head(self, url: str) -> httpx.Response | None:
        if not self.allowed(url):
            print(f"  DISALLOWED by robots.txt: {url}")
            return None
        self._wait()
        return self.client.head(url)
