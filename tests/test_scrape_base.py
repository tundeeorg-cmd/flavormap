"""The scraping rules, enforced (docs/scraping_rules.md): src/scrape/{base,cache,ethics,record}.py.

A test-only site (`FixtureSite`) runs against an httpx MockTransport serving the three
synthetic fixture pages in tests/fixtures/scrape/. No network, no real site, no real
person: every person-shaped value in the fixtures uses the ทดสอบ marker. Database tests
write under the source id `_test_scrape_site` and remove every row they create.
"""

from __future__ import annotations

import csv
import datetime
import re
import shutil
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
from selectolax.parser import HTMLParser

import src.scrape.base as base
from src.config import REPO_ROOT
from src.db import get_connection
from src.ingest.pdpa import find_leaks
from src.scrape.cache import MANIFEST_COLUMNS
from src.scrape.ethics import AuditRow, EthicsGateClosed, append_row, flag_tos_clauses
from src.scrape.record import (
    Claim,
    RecordRejected,
    ScrapedRecipe,
    to_parsed_json,
)

FIXTURES = Path(__file__).parent / "fixtures" / "scrape"
SITE = "https://recipes.test"
SOURCE = "_test_scrape_site"
PAGES = {f"/r/{n}": FIXTURES / f"recipe_{n}.html" for n in (1, 2, 3)}
NEVER_STORED = ("วิธีทำ", "ตำพริกกับกระเทียม", "/user/tester99", "นางสมหญิง", "นายสมชาย",
                "อร่อยมาก", "photo.jpg", "08 9876 5432")
REGION_WORDS = ("อีสาน", "ภาคเหนือ", "อาหารเหนือ", "ภาคใต้", "ภาคกลาง")
PROVINCE_WORDS = ("บุรีรัมย์", "นครราชสีมา", "เชียงใหม่")


class FixtureSite(base.SiteScraper):
    """A minimal site scraper, written the way a real one would be."""

    source_id = SOURCE
    slug = SOURCE
    base_url = SITE
    tos_url = f"{SITE}/terms"

    def discover(self, fetcher, limit):  # type: ignore[no-untyped-def]
        for path in [*PAGES, "/r/404"][:limit]:
            yield SITE + path

    def parse(self, html: str, url: str) -> ScrapedRecipe | None:
        tree = HTMLParser(html)
        title = tree.css_first("h1.recipe-title")
        if title is None:
            return None
        t = title.text(strip=True)
        crumbs = [a.text(strip=True) for a in tree.css("nav.breadcrumb a")]
        tags = [a.text(strip=True) for a in tree.css(".tags a.tag")]
        intro_node = tree.css_first("p.intro")
        intro = intro_node.text(strip=True) if intro_node else ""
        time_node = tree.css_first("time.published")
        published = (datetime.date.fromisoformat(time_node.attributes["datetime"] or "")
                     if time_node else None)

        def claim(words: tuple[str, ...]) -> Claim | None:
            for location, texts in (("title", [t]), ("tag", tags),
                                    ("breadcrumb", crumbs), ("intro", [intro])):
                for text in texts:
                    if any(w in text for w in words):
                        return Claim(text=text, location=location)
            return None

        servings = tree.css_first("p.servings")
        return ScrapedRecipe(
            url=url, title_th=t, published_at=published,
            site_category=crumbs[1] if len(crumbs) > 1 else None, site_tags=tags,
            region_claim=claim(REGION_WORDS), province_claim=claim(PROVINCE_WORDS),
            ingredient_lines=[li.text(strip=True) for li in tree.css("ul.ingredients li")],
            servings=servings.text(strip=True) if servings else None,
        )


class Site:
    """The MockTransport handler, counting requests per path."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        self.calls.append(path)
        if path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        if path == "/terms":
            return httpx.Response(200, text=(FIXTURES / "terms.html").read_text(encoding="utf-8"))
        if path in PAGES:
            return httpx.Response(200, text=PAGES[path].read_text(encoding="utf-8"))
        return httpx.Response(404, text="not found")


@pytest.fixture(autouse=True)
def _fast_and_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.scrape.conduct.time.sleep", lambda s: None)
    monkeypatch.setattr(base, "user_agent", lambda: "FlavorMapResearch/1.0 (+test)")


@pytest.fixture
def env(tmp_path: Path) -> Iterator[tuple[FixtureSite, Site, Path]]:
    ethics = tmp_path / "ETHICS.md"
    shutil.copy(REPO_ROOT / "ETHICS.md", ethics)
    site = Site()
    scraper = FixtureSite(raw_root=tmp_path / "raw", coverage_dir=tmp_path / "coverage",
                          ethics_path=ethics, transport=httpx.MockTransport(site))
    yield scraper, site, ethics
    conn = get_connection()
    try:
        conn.execute("DELETE FROM redaction_log WHERE source_id = %s", (SOURCE,))
        conn.execute("DELETE FROM raw_recipes WHERE source_id = %s", (SOURCE,))
        conn.execute("DELETE FROM sources WHERE source_id = %s", (SOURCE,))
        conn.commit()
    finally:
        conn.close()


def _go(ethics: Path) -> None:
    append_row(AuditRow(SOURCE, SITE, "2026-10-06", "allowed", "reviewed", "go"), ethics)


def _q(sql: str, *params: object) -> list[tuple[object, ...]]:
    conn = get_connection()
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


# ── rule 9: the parser on three fixture pages ─────────────────────────────────

SYNTHETIC_PHONES = {"08 1234 5678", "08 9876 5432"}  # the repo's invented test numbers


def test_the_fixtures_carry_no_real_personal_data() -> None:
    """Every person-shaped value in them is a declared synthetic placeholder: a name
    always followed by the surname ทดสอบ, and one of the invented test phone numbers.
    Any other name or number in a fixture fails this test."""
    for f in FIXTURES.glob("*.html"):
        text = f.read_text(encoding="utf-8")
        leaks = find_leaks(text)
        for name in leaks.get("honorific_name", []):
            assert f"{name} ทดสอบ" in text, (f.name, name)
        assert set(leaks.get("phone", [])) <= SYNTHETIC_PHONES, (f.name, leaks)
        assert not set(leaks) - {"honorific_name", "phone"}, (f.name, leaks)


@pytest.mark.parametrize("n", [1, 2, 3])
def test_the_parser_takes_only_the_allowed_fields(n: int) -> None:
    rec = FixtureSite().parse(PAGES[f"/r/{n}"].read_text(encoding="utf-8"), f"{SITE}/r/{n}")
    assert rec is not None and rec.title_th and rec.ingredient_lines
    stored = repr(to_parsed_json(rec, datetime.datetime(2026, 10, 6))[0])
    assert not [w for w in NEVER_STORED if w in stored]


def test_claims_are_exact_spans_with_their_location() -> None:
    one = FixtureSite().parse(PAGES["/r/1"].read_text(encoding="utf-8"), f"{SITE}/r/1")
    assert one is not None
    assert one.region_claim == Claim("ส้มตำทดสอบ สูตรอีสานแท้", "title")
    assert one.province_claim == Claim("ส้มตำแบบบ้านเรา จังหวัดบุรีรัมย์ ทำกินกันทุกบ้าน", "intro")
    assert one.published_at == datetime.date(2025, 3, 14)
    two = FixtureSite().parse(PAGES["/r/2"].read_text(encoding="utf-8"), f"{SITE}/r/2")
    assert two is not None and two.published_at is None  # not shown: never guessed


# ── rules 4, 5, 7: what reaches parsed_json ───────────────────────────────────

def test_parsed_json_redacts_then_keeps_original_and_normalised() -> None:
    rec = ScrapedRecipe(url="u", title_th="แกงทดสอบ โทร 08 1234 5678",
                        ingredient_lines=["หม ู่สับ 200 กรัม"])
    payload, report = to_parsed_json(rec, datetime.datetime(2026, 10, 6))
    assert "08 1234 5678" not in repr(payload) and report.n_phone_numbers == 1
    line = payload["ingredient_lines"][0]  # type: ignore[index]
    assert line["original"] == "หม ู่สับ 200 กรัม"           # kept as written
    assert line["normalised"] == "หมู่สับ 200 กรัม"           # NFC + mark repair
    assert payload["ingredients"] == [{"name_th": "หมู่สับ 200 กรัม", "position": 1}]


@pytest.mark.parametrize("bad", [
    ScrapedRecipe(url="u", title_th="t", ingredient_lines=["ก" * 201]),
    ScrapedRecipe(url="u", title_th=""),
    ScrapedRecipe(url="u", title_th="t", region_claim=Claim("x", "comment")),
])
def test_records_that_break_the_rules_are_rejected(bad: ScrapedRecipe) -> None:
    with pytest.raises(RecordRejected):
        to_parsed_json(bad, datetime.datetime(2026, 10, 6))


def test_a_scraped_recipe_has_no_field_for_forbidden_content() -> None:
    fields = set(ScrapedRecipe.__dataclass_fields__)
    for forbidden in ("method", "instructions", "author", "username", "profile",
                      "comments", "photo", "image", "phone", "email", "address"):
        assert not any(forbidden in f for f in fields), forbidden


# ── rule 1: the ethics gate ───────────────────────────────────────────────────

def test_audit_appends_a_pending_row_and_quotes_flagged_tos(env) -> None:  # type: ignore[no-untyped-def]
    scraper, _, ethics = env
    row = scraper.audit()
    assert row.decision.startswith("pending")
    assert f"| {SOURCE} | {SITE} |" in ethics.read_text(encoding="utf-8")
    report = scraper.audit_report.read_text(encoding="utf-8")
    assert "automated means, robots or scrapers" in report and "ห้ามคัดลอก" in report
    assert "not a verdict" in report


def test_no_crawl_without_a_go_row(env) -> None:  # type: ignore[no-untyped-def]
    scraper, site, _ = env
    with pytest.raises(EthicsGateClosed, match="no row"):
        scraper.pilot(3)
    scraper.audit()                          # now a row exists, but it is pending
    with pytest.raises(EthicsGateClosed, match="not 'go'"):
        scraper.pilot(3)
    assert not any(c.startswith("/r/") for c in site.calls)  # no recipe page fetched


def test_a_later_no_go_closes_an_open_source(env) -> None:  # type: ignore[no-untyped-def]
    scraper, _, ethics = env
    _go(ethics)
    append_row(AuditRow(SOURCE, SITE, "2026-10-07", "allowed", "changed", "no-go"), ethics)
    with pytest.raises(EthicsGateClosed):
        scraper.pilot(3)


def test_flagging_is_not_a_verdict() -> None:
    assert flag_tos_clauses("Use of robots is prohibited.\nWelcome!") == [
        "Use of robots is prohibited."]
    assert flag_tos_clauses("Welcome to our kitchen.") == []


# ── rule 8: stages ────────────────────────────────────────────────────────────

def test_full_is_refused_before_a_pilot(env) -> None:  # type: ignore[no-untyped-def]
    scraper, _, ethics = env
    _go(ethics)
    with pytest.raises(base.StageRefused, match="no pilot report"):
        scraper.full(10)


def test_pilot_stores_raw_only_reports_and_stops(env, capsys) -> None:  # type: ignore[no-untyped-def]
    scraper, site, ethics = env
    _go(ethics)
    before = (_q("SELECT count(*) FROM recipes"), _q("SELECT count(*) FROM province_attribution"))
    result = scraper.pilot(4)                 # 3 recipes + one 404
    assert len(result.stored) == 3 and result.skipped == 1
    assert _q("SELECT count(*) FROM raw_recipes WHERE source_id = %s", SOURCE) == [(3,)]
    assert _q("SELECT count(*) FROM redaction_log WHERE source_id = %s", SOURCE) == [(3,)]
    # Rule 6: never a recipe row, never an attribution.
    assert (_q("SELECT count(*) FROM recipes"),
            _q("SELECT count(*) FROM province_attribution")) == before
    [(phone_redactions,)] = _q("SELECT sum(n_phone_numbers) FROM redaction_log "
                               "WHERE source_id = %s", SOURCE)
    assert phone_redactions == 1              # recipe 2's title
    report = scraper.pilot_report.read_text(encoding="utf-8")
    assert "| published_at | 2 of 3 | 67% |" in report
    # Recipe 2 names no region or province anywhere: a true gap, not a parse miss.
    assert "| region or province claim | 2 of 3 | 67% |" in report
    assert "**STOP.**" in report and "STOP" in capsys.readouterr().out
    assert not find_leaks(report)


def test_the_cache_manifest_and_no_refetch_without_refresh(env) -> None:  # type: ignore[no-untyped-def]
    scraper, site, ethics = env
    _go(ethics)
    scraper.pilot(4)
    manifest = scraper.raw_root / SOURCE / "manifest.csv"
    with manifest.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert tuple(reader.fieldnames or ()) == MANIFEST_COLUMNS
    assert {r["http_status"] for r in rows} == {"200", "404"}
    assert all(r["fetched_at"].endswith("+00:00") for r in rows)
    fetched = sum(c.startswith("/r/") for c in site.calls)
    scraper.pilot(4)                          # cached pages are not fetched again
    assert sum(c.startswith("/r/") for c in site.calls) == fetched + 1  # only the 404
    assert _q("SELECT count(*) FROM raw_recipes WHERE source_id = %s", SOURCE) == [(3,)]
    scraper.pilot(4, refresh=True)
    assert sum(c.startswith("/r/") for c in site.calls) == fetched + 1 + 4


def test_a_pdpa_hit_rolls_the_whole_load_back(env, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    scraper, _, ethics = env
    _go(ethics)
    monkeypatch.setattr(base, "scan_database", lambda conn: ["raw_recipes.parsed_json: x"])
    with pytest.raises(base.PDPAViolation, match="rolled back"):
        scraper.pilot(3)
    assert _q("SELECT count(*) FROM raw_recipes WHERE source_id = %s", SOURCE) == [(0,)]


def test_the_base_never_writes_recipes_or_attributions() -> None:
    source = Path(base.__file__).read_text(encoding="utf-8")
    assert not re.search(r"INSERT INTO (recipes|province_attribution)\b", source)


def test_full_needs_a_limit() -> None:
    with pytest.raises(SystemExit):
        base.main(FixtureSite(), ["--full"])
    with pytest.raises(SystemExit):
        base.main(FixtureSite(), ["--audit", "--pilot"])
