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
    assert ua == ("FlavorMapResearch/1.0 (+https://github.com/tundeeorg-cmd/flavormap; "
                  "researcher@example.org)")


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


def _fetcher(handler, monkeypatch, clock=None):  # type: ignore[no-untyped-def]
    import urllib.robotparser

    sleeps: list[float] = []
    t = clock if clock is not None else {"t": 1_000.0}
    monkeypatch.setattr("src.scrape.conduct.time.monotonic", lambda: t["t"])
    monkeypatch.setattr("src.scrape.conduct.time.sleep", lambda s: sleeps.append(s))
    robots = urllib.robotparser.RobotFileParser()
    robots.parse(ALLOW_ALL_ROBOTS.splitlines())
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return PoliteFetcher(client, robots, "FlavorMapResearch/1.0"), sleeps, t


def test_polite_fetcher_waits_a_randomised_one_to_two_seconds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The fake clock starts far from 0.0, as real time.monotonic() does, so the first
    # call sees a long gap and does not sleep.
    fetcher, sleeps, clock = _fetcher(lambda r: httpx.Response(200), monkeypatch)
    fetcher.get("https://example.com/0")
    gaps = []
    for n in range(1, 30):
        clock["t"] += 0.1                       # each call comes 0.1 s after the last
        before = len(sleeps)
        fetcher.get(f"https://example.com/{n}")
        gaps.append(sleeps[before] + 0.1)       # the total gap actually enforced
    assert all(1.0 <= g <= 2.0 for g in gaps)
    assert 1.3 < sum(gaps) / len(gaps) < 1.7    # mean about 1.5 s
    assert len(set(round(g, 3) for g in gaps)) > 5  # randomised, not fixed


def test_the_pace_is_reproducible_from_the_seed(monkeypatch: pytest.MonkeyPatch) -> None:
    runs = []
    for _ in range(2):
        fetcher, sleeps, clock = _fetcher(lambda r: httpx.Response(200), monkeypatch)
        for n in range(5):
            clock["t"] += 0.1
            fetcher.get(f"https://example.com/{n}")
        runs.append(sleeps)
    assert runs[0] == runs[1]


def test_429_and_5xx_back_off_exponentially_then_succeed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replies = iter([503, 503, 429, 200])
    fetcher, sleeps, _ = _fetcher(lambda r: httpx.Response(next(replies)), monkeypatch)
    response = fetcher.get("https://example.com/x")
    assert response is not None and response.status_code == 200
    backoffs = [s for s in sleeps if s >= 2.0]
    assert backoffs[:3] == [2.0, 4.0, 8.0]
    assert fetcher.consecutive_errors == 0


def test_retry_after_is_honoured(monkeypatch: pytest.MonkeyPatch) -> None:
    replies = iter([httpx.Response(429, headers={"Retry-After": "7"}), httpx.Response(200)])
    fetcher, sleeps, _ = _fetcher(lambda r: next(replies), monkeypatch)
    fetcher.get("https://example.com/x")
    assert 7.0 in sleeps


def test_five_consecutive_errors_stop_the_crawl(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.scrape.conduct import CrawlAborted

    fetcher, _, _ = _fetcher(lambda r: httpx.Response(500), monkeypatch)
    for n in range(4):
        fetcher.get(f"https://example.com/{n}")   # each survives its retries as an error
    with pytest.raises(CrawlAborted):
        fetcher.get("https://example.com/4")


def test_a_404_is_an_outcome_not_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    fetcher, _, _ = _fetcher(lambda r: httpx.Response(404), monkeypatch)
    for n in range(10):
        assert fetcher.get(f"https://example.com/{n}").status_code == 404  # type: ignore[union-attr]
    assert fetcher.consecutive_errors == 0


def test_a_success_resets_the_error_count(monkeypatch: pytest.MonkeyPatch) -> None:
    replies = iter([500] * 5 + [200] + [500] * 5 * 4)
    fetcher, _, _ = _fetcher(lambda r: httpx.Response(next(replies)), monkeypatch)
    fetcher.get("https://example.com/a")        # error 1
    fetcher.get("https://example.com/b")        # 200: reset
    for n in range(4):
        fetcher.get(f"https://example.com/{n}")
    assert fetcher.consecutive_errors == 4


def test_make_client_allows_one_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.scrape import conduct

    seen: dict[str, object] = {}
    real = httpx.Client

    def spy(**kwargs: object) -> httpx.Client:
        seen.update(kwargs)
        return real(**kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(conduct.httpx, "Client", spy)
    conduct.make_client("FlavorMapResearch/1.0").close()
    limits = seen["limits"]
    assert isinstance(limits, httpx.Limits)
    assert limits.max_connections == 1 and limits.max_keepalive_connections == 1
    assert seen["headers"] == {"User-Agent": "FlavorMapResearch/1.0"}
