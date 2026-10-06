"""Shared scraping conduct: the politeness rules, enforced in code (docs/scraping_rules.md §2).

Every fetcher in this repo goes through `PoliteFetcher`, so the rules hold for every
source by construction rather than by each script remembering them:

- **Pace.** A randomised gap of 1–2 s between requests (mean 1.5 s, never under 1 s),
  drawn from `random.Random(RANDOM_SEED)` so a run's timing is reproducible (CLAUDE.md
  rule 6).
- **One connection per site.** `make_client()` caps the pool at one connection, and
  requests are strictly sequential.
- **Honest identity.** `user_agent()`:
  ``FlavorMapResearch/1.0 (+https://github.com/tundeeorg-cmd/flavormap; <contact email>)``.
  It refuses to build one under a placeholder address.
- **robots.txt** is fetched at run time through the same client and identity, never
  trusted from an earlier audit. A disallowed root stops the run; a disallowed URL is
  skipped, never fetched.
- **Back-off.** 429 and 5xx responses are retried with exponential back-off (2, 4, 8,
  16 s, capped at 60 s), honouring a numeric ``Retry-After``.
- **Stop on trouble.** Five consecutive errors (a 429/5xx that survived its retries, or
  a transport failure) raise `CrawlAborted`. A 404 is an outcome, not an error.

History: `scripts.fetch_dcp_food` and `scripts.fetch_kapook` each reimplemented this and
had drifted (one lacked the placeholder-email guard). One implementation is what stops
that recurring.
"""

from __future__ import annotations

import random
import time
import urllib.robotparser

import httpx

from src.config import RANDOM_SEED, get_settings

PROJECT_URL = "https://github.com/tundeeorg-cmd/flavormap"
DELAY_RANGE_SEC = (1.0, 2.0)          # randomised gap between requests; mean 1.5 s
BACKOFF_BASE_SEC = 2.0
BACKOFF_CAP_SEC = 60.0
MAX_RETRIES = 4                       # per request, on 429 / 5xx
MAX_CONSECUTIVE_ERRORS = 5            # then the crawl stops
TIMEOUT_SEC = 30.0

# Kept for callers that import it; the pace itself is DELAY_RANGE_SEC.
RATE_LIMIT_SEC = DELAY_RANGE_SEC[0]


class CrawlAborted(RuntimeError):
    """Raised after MAX_CONSECUTIVE_ERRORS errors in a row. The crawl stops."""


def user_agent() -> str:
    """The identifying User-Agent every fetcher must send.

    Refuses to build one under a placeholder contact address: an honest User-Agent
    needs a genuinely reachable email before any fetch, on any source.
    """
    email = get_settings().scraper_contact_email
    if not email or "example.com" in email:
        raise SystemExit(
            "SCRAPER_CONTACT_EMAIL is unset or still a placeholder. A genuinely "
            "reachable address is required in the User-Agent before any fetch."
        )
    return f"FlavorMapResearch/1.0 (+{PROJECT_URL}; {email})"


def make_client(
    ua: str,
    extra_headers: dict[str, str] | None = None,
    timeout: float = TIMEOUT_SEC,
    **kwargs: object,
) -> httpx.Client:
    """An httpx client with exactly one connection, the identifying User-Agent, and a
    timeout. Extra keyword arguments (e.g. a test transport) pass through."""
    return httpx.Client(
        headers={"User-Agent": ua, **(extra_headers or {})},
        timeout=timeout,
        follow_redirects=True,
        limits=httpx.Limits(max_connections=1, max_keepalive_connections=1),
        **kwargs,  # type: ignore[arg-type]
    )


def load_robots(
    client: httpx.Client, base_url: str, ua: str
) -> urllib.robotparser.RobotFileParser:
    """Fetch and parse robots.txt through `client`, under `ua`: re-checked at run time,
    never trusted from an earlier audit. Raises if the root path is disallowed for our
    User-Agent: a disallowed source is dropped, never worked around."""
    response = client.get(f"{base_url}/robots.txt")
    response.raise_for_status()
    parser = urllib.robotparser.RobotFileParser()
    parser.parse(response.text.splitlines())
    if not parser.can_fetch(ua, base_url + "/"):
        raise SystemExit(f"robots.txt disallows our User-Agent at the root, stopping: {base_url}")
    return parser


def _retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("Retry-After", "")
    try:
        return min(float(value), BACKOFF_CAP_SEC) if value else None
    except ValueError:
        return None  # an HTTP-date; fall back to exponential back-off


class PoliteFetcher:
    """Sequential fetcher. One request at a time, a randomised 1–2 s gap, robots.txt
    checked per URL, back-off on 429/5xx, and a hard stop after 5 consecutive errors.

    A disallowed URL is reported and skipped (`None`), never fetched anyway.
    """

    def __init__(
        self,
        client: httpx.Client,
        robots: urllib.robotparser.RobotFileParser,
        ua: str,
        seed: int = RANDOM_SEED,
    ) -> None:
        self.client = client
        self.robots = robots
        self.ua = ua
        self._rng = random.Random(seed)
        self._last = 0.0
        self.consecutive_errors = 0

    def _wait(self) -> None:
        gap = self._rng.uniform(*DELAY_RANGE_SEC)
        elapsed = time.monotonic() - self._last
        if elapsed < gap:
            time.sleep(gap - elapsed)
        self._last = time.monotonic()

    def allowed(self, url: str) -> bool:
        return self.robots.can_fetch(self.ua, url)

    def _error(self, what: str) -> None:
        self.consecutive_errors += 1
        print(f"  ERROR ({self.consecutive_errors}/{MAX_CONSECUTIVE_ERRORS}): {what}")
        if self.consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
            raise CrawlAborted(
                f"{MAX_CONSECUTIVE_ERRORS} consecutive errors; the crawl stops. Last: {what}"
            )

    def _request(self, method: str, url: str) -> httpx.Response | None:
        if not self.allowed(url):
            print(f"  DISALLOWED by robots.txt: {url}")
            return None
        for attempt in range(MAX_RETRIES + 1):
            self._wait()
            try:
                response = self.client.request(method, url)
            except httpx.TransportError as e:
                self._error(f"{type(e).__name__}: {url}")
                return None
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == MAX_RETRIES:
                    self._error(f"HTTP {response.status_code} after {MAX_RETRIES} retries: {url}")
                    return response
                delay = _retry_after(response) or min(
                    BACKOFF_BASE_SEC * 2**attempt, BACKOFF_CAP_SEC
                )
                print(f"  HTTP {response.status_code}, backing off {delay:.0f}s: {url}")
                time.sleep(delay)
                continue
            self.consecutive_errors = 0
            return response
        return None  # unreachable

    def get(self, url: str) -> httpx.Response | None:
        return self._request("GET", url)

    def head(self, url: str) -> httpx.Response | None:
        return self._request("HEAD", url)
