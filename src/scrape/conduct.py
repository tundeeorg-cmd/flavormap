"""Shared scraping conduct — `docs/scraping_rules.md` rule 2 (politeness), enforced once.

Every request any FlavorMap fetcher makes goes through :class:`PoliteFetcher`, so the
rules below hold by construction rather than by each script remembering them:

* **Pace.** At least :data:`MIN_DELAY_SEC` and at most :data:`MAX_DELAY_SEC` between the
  *starts* of two requests to a site, drawn uniformly — 1.5 s on average. Retries and
  HEAD requests pay the same wait; nothing skips the queue.
* **One connection per site.** :func:`make_client` caps the pool at one connection, and
  the fetcher is sequential. There is no concurrency anywhere in this package.
* **Identity.** :func:`user_agent` is the only User-Agent, and it refuses to build under a
  placeholder contact address.
* **robots.txt** is fetched through the same client, under the same User-Agent, at run
  time on every run — never trusted from an earlier audit (:func:`load_robots`). A
  disallowed URL is skipped, never fetched.
* **Back-off.** 429 and 5xx are retried with exponential back-off (2, 4, 8, 16 s), or the
  server's ``Retry-After`` if that is longer.
* **Stop.** :data:`MAX_CONSECUTIVE_ERRORS` consecutive failed requests raise
  :class:`CrawlAborted`. So does any sign of a login wall, paywall or CAPTCHA
  (:func:`challenge_reason`): those are never bypassed, so the only correct response to
  meeting one is to stop and report it.

History. `scripts.fetch_dcp_food` and `scripts.fetch_kapook` each reimplemented this
conduct independently, and the two copies drifted: `fetch_kapook.py`'s `user_agent()` lost
the placeholder-email guard, so an unconfigured `SCRAPER_CONTACT_EMAIL` would have fetched
under a fake contact address. One implementation is what stops that kind of drift. Both
scripts still use this module, so they inherit the 2026-10-06 tightening (1 s fixed →
1–2 s randomised, back-off, the error stop, the new User-Agent) without changes of their
own.
"""

from __future__ import annotations

import random
import re
import time
import urllib.robotparser
from collections.abc import Callable
from email.utils import parsedate_to_datetime

import httpx

from src.config import RANDOM_SEED, get_settings

# Rule 2. The mean is the "1 request per 1.5 s" the rule states; the range is its jitter.
MIN_DELAY_SEC = 1.0
MAX_DELAY_SEC = 2.0
# Retained for callers that only need the floor (scripts/audit_source.py's own limiter).
RATE_LIMIT_SEC = MIN_DELAY_SEC

RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
MAX_RETRIES = 4
BACKOFF_BASE_SEC = 2.0
BACKOFF_CAP_SEC = 120.0
MAX_CONSECUTIVE_ERRORS = 5

REPO_URL = "https://github.com/tundeeorg-cmd/flavormap"
UA_PRODUCT = "FlavorMapResearch/1.0"


class CrawlAborted(RuntimeError):
    """The crawl must stop now. Never caught and retried — read the message, then decide."""


def build_user_agent(email: str) -> str:
    """Rule 2's User-Agent. Refuses an empty or placeholder contact address."""
    if not email or "example.com" in email or "@" not in email:
        raise SystemExit(
            "SCRAPER_CONTACT_EMAIL is unset or still a placeholder. Rule 2 requires a "
            "genuinely reachable address in the User-Agent before any fetch."
        )
    return f"{UA_PRODUCT} (+{REPO_URL}; {email})"


def user_agent() -> str:
    """The identifying User-Agent every fetcher must send, from the configured email."""
    return build_user_agent(get_settings().scraper_contact_email)


def make_client(ua: str, timeout: float = 30.0) -> httpx.Client:
    """The only way a scraper should open a client: one connection, honest identity,
    no cookies carried in, no credentials. Redirects are followed so a moved page is
    found, but a redirect into a login wall is caught by :func:`challenge_reason`."""
    return httpx.Client(
        headers={"User-Agent": ua, "Accept-Language": "th,en;q=0.8"},
        timeout=timeout,
        follow_redirects=True,
        limits=httpx.Limits(max_connections=1, max_keepalive_connections=1),
    )


def load_robots(
    client: httpx.Client, base_url: str, ua: str
) -> urllib.robotparser.RobotFileParser:
    """Fetch and parse robots.txt through `client`, under `ua` — re-checked at run
    time, never trusted from an earlier audit. Raises if the root path is disallowed
    for our own User-Agent: a disallowed source is dropped, never worked around, and
    that has to hold before a single page is fetched, not after.

    A 404 is the standard "no restrictions" signal and parses as allow-all. Any other
    failure is an error: a robots.txt we could not read is not one that said yes.
    """
    response = client.get(f"{base_url}/robots.txt")
    parser = urllib.robotparser.RobotFileParser()
    if response.status_code == 404:
        parser.parse([])
    else:
        response.raise_for_status()
        parser.parse(response.text.splitlines())
    if not parser.can_fetch(ua, base_url + "/"):
        raise SystemExit(
            f"robots.txt disallows our User-Agent at the root — stopping: {base_url}"
        )
    return parser


# Markers of a challenge page. Deliberately specific (widget class names, challenge
# script paths). A marker alone is not enough — an ordinary recipe page can carry a
# reCAPTCHA on its comment form — so it counts only on an error status or a page too
# small to be content (:data:`_CHALLENGE_MAX_BYTES`): what a challenge interstitial is.
_CHALLENGE_MARKERS = (
    ("captcha", re.compile(r"g-recaptcha|h-captcha|hcaptcha\.com|recaptcha/api\.js|"
                           r"cf-turnstile|challenges\.cloudflare\.com|/cdn-cgi/challenge|"
                           r"cf_chl_|captcha-delivery\.com")),
    ("paywall", re.compile(r"\bpaywall\b|subscribe to (?:continue|read)|"
                           r"สมัครสมาชิกเพื่ออ่าน")),
    ("login wall", re.compile(r"(?:please|you must) (?:log ?in|sign ?in) to|"
                              r"กรุณาเข้าสู่ระบบ")),
)
_CHALLENGE_MAX_BYTES = 30_000
_LOGIN_PATH = re.compile(r"/(?:login|signin|sign-in|log-in|auth|account/login)\b", re.I)


def challenge_reason(response: httpx.Response) -> str | None:
    """Why this response is a wall we must stop at, or None. Never a puzzle to solve."""
    if response.status_code in (401, 407):
        return f"HTTP {response.status_code}: authentication required"
    if response.status_code == 402:
        return "HTTP 402: payment required"
    if response.headers.get("cf-mitigated", "").lower() == "challenge":
        return f"captcha challenge (cf-mitigated) at {response.url}"
    if response.history and _LOGIN_PATH.search(response.url.path):
        return f"redirected to a login page: {response.url}"
    content_type = response.headers.get("content-type", "")
    if content_type and "html" not in content_type:
        return None
    small = len(response.content) < _CHALLENGE_MAX_BYTES
    if not (small or response.status_code >= 400):
        return None
    head = response.text[:200_000].lower()
    for kind, pattern in _CHALLENGE_MARKERS:
        if pattern.search(head):
            return f"{kind} detected at {response.url}"
    return None


def _retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("retry-after")
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        pass
    try:
        when = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, when.timestamp() - time.time())


class PoliteFetcher:
    """Sequential, paced, robots-checked fetcher with back-off and an error stop.

    A disallowed URL is reported and skipped (``None``), never fetched anyway. A
    response that is a login wall, paywall or CAPTCHA raises :class:`CrawlAborted`.
    After retries, a 429/5xx response is *returned* (so callers can record it) and
    counts as one error; :data:`MAX_CONSECUTIVE_ERRORS` in a row abort the crawl. A
    transport error is counted and re-raised.
    """

    def __init__(
        self,
        client: httpx.Client,
        robots: urllib.robotparser.RobotFileParser,
        ua: str,
        *,
        rng: random.Random | None = None,
        sleep: Callable[[float], None] | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.client = client
        self.robots = robots
        self.ua = ua
        # Seeded (CLAUDE.md rule 6): the jitter is stochastic, so it is reproducible.
        self.rng = rng or random.Random(RANDOM_SEED)
        self._sleep = sleep or time.sleep
        self._clock = clock or time.monotonic
        self._last: float | None = None
        self.consecutive_errors = 0

    def _wait(self) -> None:
        delay = self.rng.uniform(MIN_DELAY_SEC, MAX_DELAY_SEC)
        if self._last is not None:
            elapsed = self._clock() - self._last
            if elapsed < delay:
                self._sleep(delay - elapsed)
        self._last = self._clock()

    def _error(self, what: str) -> None:
        self.consecutive_errors += 1
        if self.consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
            raise CrawlAborted(
                f"{self.consecutive_errors} consecutive errors (last: {what}) — the crawl "
                "stops here. Check the site by hand before running again."
            )

    def note_request(self) -> None:
        """Record a request made outside this fetcher (robots.txt), so the next one waits."""
        self._last = self._clock()

    def allowed(self, url: str) -> bool:
        return self.robots.can_fetch(self.ua, url)

    def _request(self, method: str, url: str) -> httpx.Response | None:
        if not self.allowed(url):
            print(f"  DISALLOWED by robots.txt: {url}")
            return None
        attempt = 0
        while True:
            self._wait()
            try:
                response = self.client.request(method, url)
            except httpx.TransportError as exc:
                self._error(f"{type(exc).__name__} on {url}")
                raise
            if response.status_code in RETRY_STATUSES and attempt < MAX_RETRIES:
                backoff = min(BACKOFF_BASE_SEC * 2**attempt, BACKOFF_CAP_SEC)
                server = _retry_after(response)
                if server is not None:
                    backoff = min(max(backoff, server), BACKOFF_CAP_SEC)
                print(f"  HTTP {response.status_code} on {url}; backing off {backoff:.0f}s")
                self._sleep(backoff)
                attempt += 1
                continue
            break
        if method == "GET" and (reason := challenge_reason(response)):
            raise CrawlAborted(f"{reason} — never bypassed. Stop and report.")
        if response.status_code in RETRY_STATUSES or response.status_code == 403:
            self._error(f"HTTP {response.status_code} on {url}")
        else:
            self.consecutive_errors = 0
        return response

    def get(self, url: str) -> httpx.Response | None:
        return self._request("GET", url)

    def head(self, url: str) -> httpx.Response | None:
        return self._request("HEAD", url)
