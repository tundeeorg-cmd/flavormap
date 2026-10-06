"""Offline tests for src/scrape/conduct.py — rule 2 of docs/scraping_rules.md.

No live network calls: httpx.MockTransport stands in for the real site, and the
fetcher's clock and sleep are injected so pacing and back-off are asserted exactly.

This module exists because the two fetchers had already reimplemented this conduct
independently and drifted: fetch_kapook.py's user_agent() was missing the
placeholder-email guard fetch_dcp_food.py had. test_user_agent_rejects_a_placeholder
is the test that would have caught that.
"""

from __future__ import annotations

import random
import urllib.robotparser
from collections.abc import Callable

import httpx
import pytest

from src.scrape.conduct import (
    MAX_CONSECUTIVE_ERRORS,
    MAX_DELAY_SEC,
    MAX_RETRIES,
    MIN_DELAY_SEC,
    CrawlAborted,
    PoliteFetcher,
    challenge_reason,
    load_robots,
    make_client,
    user_agent,
)

UA = "FlavorMapResearch/1.0 (+https://github.com/tundeeorg-cmd/flavormap; r@example.org)"
ALLOW_ALL_ROBOTS = "User-agent: *\nAllow: /\n"
DISALLOW_ALL_ROBOTS = "User-agent: *\nDisallow: /\n"
# Python's urllib.robotparser matches rules in file order — the first matching path
# wins, not the most specific one — so the Disallow line must precede any broader
# Allow for the same path.
DISALLOW_PATH_ROBOTS = "User-agent: *\nDisallow: /private/\n"


class _FakeSettings:
    def __init__(self, email: str) -> None:
        self.scraper_contact_email = email


def test_user_agent_rejects_a_placeholder(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.scrape.conduct.get_settings", lambda: _FakeSettings("you@example.com")
    )
    with pytest.raises(SystemExit):
        user_agent()


def test_user_agent_rejects_an_empty_address(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.scrape.conduct.get_settings", lambda: _FakeSettings(""))
    with pytest.raises(SystemExit):
        user_agent()


def test_user_agent_is_rule_2s_exact_format(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.scrape.conduct.get_settings", lambda: _FakeSettings("researcher@example.org")
    )
    assert user_agent() == (
        "FlavorMapResearch/1.0 (+https://github.com/tundeeorg-cmd/flavormap; "
        "researcher@example.org)"
    )


def test_the_client_holds_one_connection_and_identifies_itself() -> None:
    with make_client(UA) as client:
        pool = client._transport._pool  # type: ignore[attr-defined]
        assert pool._max_connections == 1
        assert client.headers["User-Agent"] == UA
        assert not client.cookies


def _mock_client(robots_txt: str, status: int = 200) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/robots.txt"
        return httpx.Response(status, text=robots_txt)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_load_robots_allows_when_root_is_open() -> None:
    with _mock_client(ALLOW_ALL_ROBOTS) as client:
        parser = load_robots(client, "https://example.com", UA)
        assert parser.can_fetch(UA, "https://example.com/anything")


def test_load_robots_raises_when_root_is_disallowed() -> None:
    with _mock_client(DISALLOW_ALL_ROBOTS) as client:
        with pytest.raises(SystemExit):
            load_robots(client, "https://example.com", UA)


def test_a_missing_robots_txt_is_allow_all_but_a_server_error_is_not() -> None:
    with _mock_client("", status=404) as client:
        assert load_robots(client, "https://example.com", UA).can_fetch(UA, "https://example.com/x")
    with _mock_client("", status=500) as client:
        with pytest.raises(httpx.HTTPStatusError):
            load_robots(client, "https://example.com", UA)


# ── the fetcher ──────────────────────────────────────────────────────────────

class _Clock:
    def __init__(self) -> None:
        self.t = 1_000.0
        self.sleeps: list[float] = []

    def now(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.sleeps.append(s)
        self.t += s


def _fetcher(
    handler: Callable[[httpx.Request], httpx.Response],
    robots_txt: str = ALLOW_ALL_ROBOTS,
    clock: _Clock | None = None,
) -> tuple[PoliteFetcher, _Clock]:
    clock = clock or _Clock()
    robots = urllib.robotparser.RobotFileParser()
    robots.parse(robots_txt.splitlines())
    client = httpx.Client(transport=httpx.MockTransport(handler))
    fetcher = PoliteFetcher(client, robots, UA, rng=random.Random(0),
                            sleep=clock.sleep, clock=clock.now)
    return fetcher, clock


def _ok(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, text="<html>" + "x" * 40_000 + "</html>",
                          headers={"content-type": "text/html"})


def test_a_disallowed_path_is_never_fetched() -> None:
    called: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        called.append(request.url.path)
        return _ok(request)

    fetcher, _ = _fetcher(handler, DISALLOW_PATH_ROBOTS)
    assert fetcher.get("https://example.com/private/secret") is None
    assert called == []


def test_requests_are_spaced_between_one_and_two_seconds() -> None:
    fetcher, clock = _fetcher(_ok)
    for i in range(30):
        fetcher.get(f"https://example.com/{i}")
    # Back-to-back calls with no time passing: every wait is the full drawn delay.
    assert len(clock.sleeps) == 29
    assert all(MIN_DELAY_SEC <= s <= MAX_DELAY_SEC for s in clock.sleeps)
    assert len(set(clock.sleeps)) > 1, "the delay is randomised, not fixed"


def test_time_already_spent_counts_toward_the_wait() -> None:
    fetcher, clock = _fetcher(_ok)
    fetcher.get("https://example.com/1")
    clock.t += 5.0  # the caller spent longer than any delay parsing the page
    fetcher.get("https://example.com/2")
    assert clock.sleeps == []


def test_429_backs_off_exponentially_then_succeeds() -> None:
    responses = iter([429, 503, 200])

    def handler(request: httpx.Request) -> httpx.Response:
        status = next(responses)
        return _ok(request) if status == 200 else httpx.Response(status)

    fetcher, clock = _fetcher(handler)
    response = fetcher.get("https://example.com/r")
    assert response is not None and response.status_code == 200
    backoffs = [s for s in clock.sleeps if s >= 2.0]
    assert backoffs == [2.0, 4.0]
    assert fetcher.consecutive_errors == 0


def test_retry_after_is_honoured_when_longer() -> None:
    responses = iter([httpx.Response(429, headers={"retry-after": "30"}), None])

    def handler(request: httpx.Request) -> httpx.Response:
        return next(responses) or _ok(request)

    fetcher, clock = _fetcher(handler)
    fetcher.get("https://example.com/r")
    assert 30.0 in clock.sleeps


def test_retries_are_bounded_and_the_last_response_is_returned() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(503)

    fetcher, _ = _fetcher(handler)
    response = fetcher.get("https://example.com/down")
    assert response is not None and response.status_code == 503
    assert len(calls) == MAX_RETRIES + 1
    assert fetcher.consecutive_errors == 1


def test_five_consecutive_errors_stop_the_crawl() -> None:
    fetcher, _ = _fetcher(lambda r: httpx.Response(503))
    for i in range(MAX_CONSECUTIVE_ERRORS - 1):
        fetcher.get(f"https://example.com/{i}")
    with pytest.raises(CrawlAborted):
        fetcher.get("https://example.com/last")


def test_a_success_resets_the_error_count() -> None:
    statuses = iter([403, 403, 403, 403, 200, 403])

    def handler(request: httpx.Request) -> httpx.Response:
        s = next(statuses)
        return _ok(request) if s == 200 else httpx.Response(s)

    fetcher, _ = _fetcher(handler)
    for i in range(6):
        fetcher.get(f"https://example.com/{i}")
    assert fetcher.consecutive_errors == 1


def test_transport_errors_count_and_propagate() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    fetcher, _ = _fetcher(handler)
    for i in range(MAX_CONSECUTIVE_ERRORS - 1):
        with pytest.raises(httpx.ConnectError):
            fetcher.get(f"https://example.com/{i}")
    with pytest.raises(CrawlAborted):
        fetcher.get("https://example.com/last")


# ── walls are never bypassed ─────────────────────────────────────────────────

def _response(status: int, body: str, url: str = "https://example.com/p",
              headers: dict[str, str] | None = None) -> httpx.Response:
    return httpx.Response(status, text=body, request=httpx.Request("GET", url),
                          headers={"content-type": "text/html", **(headers or {})})


@pytest.mark.parametrize(
    "response",
    [
        _response(403, '<div class="g-recaptcha"></div>'),
        _response(200, '<script src="https://challenges.cloudflare.com/x.js"></script>'),
        _response(200, "<p>ok</p>", headers={"cf-mitigated": "challenge"}),
        _response(401, ""),
        _response(402, ""),
        _response(200, "<p>กรุณาเข้าสู่ระบบ</p>"),
    ],
)
def test_walls_are_detected(response: httpx.Response) -> None:
    assert challenge_reason(response) is not None


def test_a_recaptcha_on_a_full_content_page_is_not_a_wall() -> None:
    # A recipe page with a reCAPTCHA on its comment form is still a recipe page.
    body = "<article>" + "ส่วนผสม " * 10_000 + '</article><div class="g-recaptcha"></div>'
    assert challenge_reason(_response(200, body)) is None


def test_meeting_a_captcha_aborts_the_crawl() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text='<div class="h-captcha"></div>',
                              headers={"content-type": "text/html"})

    fetcher, _ = _fetcher(handler)
    with pytest.raises(CrawlAborted, match="never bypassed"):
        fetcher.get("https://example.com/p")
