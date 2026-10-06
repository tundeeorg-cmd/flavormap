"""src/scrape/base.py end to end — stages, gate, cache, load — against a fake site. Offline.

The fake site is served by httpx.MockTransport, ETHICS.md is a temporary copy with a row
for it, and the database is a recording stub, so every rule the base enforces is checked
without a network or a Postgres.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from datetime import date, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from selectolax.parser import HTMLParser

from src.scrape.base import Crawler, SiteScraper, pilot_reviewed, run
from src.scrape.ethics import EthicsGateError
from src.scrape.record import Claim, ScrapedRecipe

UA = "FlavorMapResearch/1.0 (+https://github.com/tundeeorg-cmd/flavormap; r@example.org)"
TODAY = date(2026, 10, 6)
ROW = "| `fakesite` | `fake.example` | allowed | none | none found | 2026-10-06 | ✅ HD-3 go |"
HEADER = (
    "| source_id | Domain | robots.txt | Disallowed paths | ToS reviewed | Audited | Decision |\n"
    "|---|---|---|---|---|---|---|\n"
)


def _page(i: int) -> str:
    published = f'<time datetime="2025-01-0{i % 9 + 1}">' if i % 2 else ""
    return f"""<html><body><h1>แกงเหลือง สูตรที่ {i} ภาคใต้</h1>{published}
<nav class="crumb">อาหารใต้</nav>
<ul class="ing"><li>ปลา {i} ตัว</li><li>พริกแกง 1 ถ้วย</li></ul>
<div class="author">นางสมหญิง ทดสอบ</div>
<div class="method">ตั้งหม้อ ใส่พริกแกง ...</div></body></html>"""


class FakeSite(SiteScraper):
    source_id = "fakesite"
    base_url = "https://fake.example"
    tos_url = "https://fake.example/terms"

    def discover(self, crawler: Crawler) -> Iterator[str]:
        index = crawler.page(f"{self.base_url}/sitemap")
        assert index is not None
        yield from re.findall(r"<loc>([^<]+)</loc>", index.text())

    def parse(self, html: str, url: str, scraped_at: datetime) -> ScrapedRecipe | None:
        tree = HTMLParser(html)
        h1 = tree.css_first("h1")
        if h1 is None:
            return None
        title = h1.text(strip=True)
        time_node = tree.css_first("time")
        crumb = tree.css_first("nav.crumb")
        return ScrapedRecipe(
            url=url,
            title_th=title,
            scraped_at=scraped_at,
            published_at=date.fromisoformat(time_node.attributes["datetime"] or "")
            if time_node else None,
            site_category=crumb.text(strip=True) if crumb else None,
            region_claim=Claim("ภาคใต้", "title") if "ภาคใต้" in title else None,
            ingredient_lines=[li.text(strip=True) for li in tree.css("ul.ing li")],
        )


class Site:
    """The fake site, counting every request it serves."""

    def __init__(self, n: int = 8) -> None:
        self.n = n
        self.requests: list[str] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request.url.path)
        assert request.headers["user-agent"] == UA
        path = request.url.path
        if path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        if path == "/sitemap":
            locs = "".join(f"<loc>https://fake.example/r/{i}</loc>" for i in range(self.n))
            return httpx.Response(200, text=f"<urlset>{locs}</urlset>")
        if path == "/r/3":
            return httpx.Response(404)
        if path.startswith("/r/"):
            return httpx.Response(200, text=_page(int(path.rsplit("/", 1)[1])),
                                  headers={"content-type": "text/html"})
        if path == "/terms":
            return httpx.Response(200, text="<p>Recipes are for cooking.</p>",
                                  headers={"content-type": "text/html"})
        return httpx.Response(404)


class FakeConn:
    def __init__(self) -> None:
        self.rows: list[tuple[Any, ...]] = []
        self.committed = False
        self.rolled_back = False

    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> None:
        assert "INSERT INTO raw_recipes" in sql
        assert params is not None
        self.rows.append(params)

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        pass


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    monkeypatch.setattr("src.scrape.conduct.time.sleep", lambda s: None)
    monkeypatch.setattr("src.scrape.base.scan_database", lambda conn: [])
    ethics = tmp_path / "ETHICS.md"
    ethics.write_text(HEADER + ROW + "\n", encoding="utf-8")
    site = Site()
    conn = FakeConn()

    def factory(ua: str) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(site.handler),
                            headers={"User-Agent": ua})

    def go(*argv: str) -> int:
        return run(
            FakeSite, list(argv),
            connect=lambda: conn,
            crawler_kwargs={"ethics_path": ethics, "cache_root": tmp_path / "raw",
                            "client_factory": factory, "ua": UA},
            coverage_dir=tmp_path / "coverage",
            audit_dir=tmp_path / "audits",
            today=TODAY,
        )

    return {"go": go, "site": site, "conn": conn, "tmp": tmp_path, "ethics": ethics}


def test_no_row_means_no_crawl_and_no_request(env: dict[str, Any]) -> None:
    env["ethics"].write_text(HEADER, encoding="utf-8")
    with pytest.raises(EthicsGateError):
        env["go"]("--pilot", "3")
    assert env["site"].requests == []


def test_audit_needs_no_row_and_writes_a_report(env: dict[str, Any]) -> None:
    env["ethics"].write_text(HEADER, encoding="utf-8")
    assert env["go"]("--audit") == 0
    assert (env["tmp"] / "audits" / "fakesite_2026-10-06.md").exists()
    assert env["site"].requests == ["/robots.txt", "/terms"]


def test_pilot_writes_the_report_and_stops(env: dict[str, Any]) -> None:
    assert env["go"]("--pilot", "6") == 0
    report = (env["tmp"] / "coverage" / "fakesite_pilot.md").read_text(encoding="utf-8")
    assert env["conn"].rows == [], "a pilot writes nothing to the database"
    assert "| URLs requested (pilot N) | 6 (N = 6) |" in report
    assert "| not available (non-200, disallowed, empty) | 1 |" in report
    assert "| published_at | 2 | 5 | 40% |" in report
    assert "| region_claim | 5 | 5 | 100% |" in report
    assert "| ingredient_lines | 5 | 5 | 100% |" in report
    assert report.count("```json") == 5
    assert "สมหญิง" not in report and "ตั้งหม้อ" not in report
    assert pilot_reviewed(env["tmp"] / "coverage" / "fakesite_pilot.md") is None


def test_pilot_defaults_to_twenty(env: dict[str, Any]) -> None:
    env["site"].n = 30
    env["go"]("--pilot")
    report = (env["tmp"] / "coverage" / "fakesite_pilot.md").read_text(encoding="utf-8")
    assert "(N = 20)" in report


def test_a_rerun_reads_the_cache_and_never_touches_the_network(env: dict[str, Any]) -> None:
    env["go"]("--pilot", "5")
    first = len(env["site"].requests)
    env["site"].requests.clear()
    env["go"]("--pilot", "5")
    # /r/3 was a 404, so it is not cached and is asked for again — and only it.
    assert env["site"].requests == ["/robots.txt", "/r/3"]
    assert first > 2
    env["site"].requests.clear()
    assert env["go"]("--pilot", "3", "--refresh") == 0
    assert "/sitemap" in env["site"].requests and "/r/0" in env["site"].requests


def test_full_refuses_without_a_reviewed_pilot(env: dict[str, Any]) -> None:
    assert env["go"]("--full") == 2
    env["go"]("--pilot", "3")
    assert env["go"]("--full") == 2
    assert env["conn"].rows == []


def _review(env: dict[str, Any]) -> None:
    path = env["tmp"] / "coverage" / "fakesite_pilot.md"
    text = path.read_text(encoding="utf-8")
    path.write_text(re.sub(r"^\*\*Reviewed:\*\*.*$", "**Reviewed:** 2026-10-07", text,
                           flags=re.M), encoding="utf-8")


def test_full_loads_only_finalised_records_and_prints_the_checklist(
    env: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    env["go"]("--pilot", "3")
    _review(env)
    assert env["go"]("--full", "--limit", "6") == 0
    conn = env["conn"]
    assert conn.committed and len(conn.rows) == 5
    source_id, url, _, status, raw_path, _, parsed_json, content_hash = conn.rows[0]
    payload = json.loads(parsed_json)
    assert source_id == "fakesite" and status == 200 and raw_path.endswith(".html")
    assert payload["title_th"] == "แกงเหลือง สูตรที่ 0 ภาคใต้"
    assert "สมหญิง" not in parsed_json and "ตั้งหม้อ" not in parsed_json
    out = capsys.readouterr().out
    assert "make db-dump" in out and "make backup TO=" in out
    assert 'git commit -m "data(fakesite): full crawl, 5 records loaded, 2026-10-06"' in out


def test_a_pdpa_leak_anywhere_rolls_the_load_back(
    env: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    env["go"]("--pilot", "3")
    _review(env)
    monkeypatch.setattr("src.scrape.base.scan_database", lambda conn: ["t.c: {'phone': [...]}"])
    assert env["go"]("--full") == 3
    assert env["conn"].rolled_back and not env["conn"].committed


def test_limit_belongs_to_full(env: dict[str, Any]) -> None:
    with pytest.raises(SystemExit):
        env["go"]("--pilot", "3", "--limit", "5")
    with pytest.raises(SystemExit):
        env["go"]("--pilot", "--full")


def test_an_abort_stops_the_stage_with_its_own_exit_code(
    env: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def walled(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="")
        return httpx.Response(403, text='<div class="g-recaptcha"></div>',
                              headers={"content-type": "text/html"})

    monkeypatch.setattr(env["site"], "handler", walled)
    assert env["go"]("--pilot", "3") == 4
