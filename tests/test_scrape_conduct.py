"""Offline tests for src/scrape/conduct.py — the shared fetch conduct both
scripts.fetch_dcp_food and scripts.fetch_kapook now use.

No live network calls: httpx.MockTransport stands in for the real site, and
time.monotonic/time.sleep are monkeypatched for the rate-limit test, matching
tests/test_audit_source.py's pattern for its own (separate) rate limiter.

This module exists because the two fetchers had already reimplemented this conduct
independently and drifted: fetch_kapook.py's user_agent() was missing the
placeholder-email guard fetch_dcp_food.py had. test_user_agent_rejects_a_placeholder
is the test that would have caught that.
"""

from __future__ import annotations

import httpx
import pytest

from src.scrape.conduct import PoliteFetcher, load_robots, user_agent

ALLOW_ALL_ROBOTS = "User-agent: *\nAllow: /\n"
DISALLOW_ALL_ROBOTS = "User-agent: *\nDisallow: /\n"
# Python's urllib.robotparser matches rules in file order — the first matching path
# wins, not the most specific one — so the Disallow line must precede any broader
# Allow for the same path. An `Allow: /` listed first would shadow this entirely.
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


def test_user_agent_accepts_a_real_address(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.scrape.conduct.get_settings", lambda: _FakeSettings("researcher@example.org")
    )
    ua = user_agent()
    assert "researcher@example.org" in ua
    assert "FlavorMapResearchBot" in ua


def _mock_client(robots_txt: str) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/robots.txt"
        return httpx.Response(200, text=robots_txt)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_load_robots_allows_when_root_is_open() -> None:
    with _mock_client(ALLOW_ALL_ROBOTS) as client:
        parser = load_robots(client, "https://example.com", "FlavorMapResearchBot/0.1")
        assert parser.can_fetch("FlavorMapResearchBot/0.1", "https://example.com/anything")


def test_load_robots_raises_when_root_is_disallowed() -> None:
    with _mock_client(DISALLOW_ALL_ROBOTS) as client:
        with pytest.raises(SystemExit):
            load_robots(client, "https://example.com", "FlavorMapResearchBot/0.1")


def test_polite_fetcher_skips_a_disallowed_path_without_fetching_it() -> None:
    called: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        called.append(request.url.path)
        return httpx.Response(200, text="ok")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        import urllib.robotparser

        robots = urllib.robotparser.RobotFileParser()
        robots.parse(DISALLOW_PATH_ROBOTS.splitlines())

        fetcher = PoliteFetcher(client, robots, "FlavorMapResearchBot/0.1")
        response = fetcher.get("https://example.com/private/secret")

        assert response is None
        assert called == []  # never reached the transport at all


def test_polite_fetcher_rate_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    # Seeded away from 0.0 deliberately: PoliteFetcher._last starts at 0.0, and real
    # time.monotonic() is always far larger than that (it tracks process/system
    # uptime), so the first real call never sees elapsed < RATE_LIMIT_SEC. Starting
    # the fake clock at 0.0 would test an edge case that cannot occur in practice
    # rather than the actual rate-limiting behaviour.
    clock = {"t": 1_000.0}
    sleeps: list[float] = []
    monkeypatch.setattr("src.scrape.conduct.time.monotonic", lambda: clock["t"])
    monkeypatch.setattr("src.scrape.conduct.time.sleep", lambda s: sleeps.append(s))

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="ok")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        import urllib.robotparser

        robots = urllib.robotparser.RobotFileParser()
        robots.parse(ALLOW_ALL_ROBOTS.splitlines())

        fetcher = PoliteFetcher(client, robots, "FlavorMapResearchBot/0.1")
        fetcher.get("https://example.com/1")  # first call: far past RATE_LIMIT_SEC, no sleep
        clock["t"] = 1_000.3
        fetcher.get("https://example.com/2")  # only 0.3s elapsed, should sleep ~0.7s

    assert sleeps == pytest.approx([0.7])
