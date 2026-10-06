"""Rule 1 of docs/scraping_rules.md — the ETHICS.md gate and the --audit stage. Offline."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import httpx
import pytest

from src.scrape.ethics import (
    ETHICS_PATH,
    EthicsGateError,
    audit_rows,
    audit_site,
    relevant_clauses,
    render_audit,
    require_cleared,
    write_audit,
)

UA = "FlavorMapResearch/1.0 (+https://github.com/tundeeorg-cmd/flavormap; r@example.org)"
HEADER = (
    "| source_id | Domain | robots.txt | Disallowed paths | ToS reviewed | Audited | Decision |\n"
    "|---|---|---|---|---|---|---|\n"
)


def _ethics(tmp_path: Path, row: str) -> Path:
    path = tmp_path / "ETHICS.md"
    path.write_text("# Ethics\n\n" + HEADER + row + "\n\nAfter the table.\n", encoding="utf-8")
    return path


# ── the gate, against the real ETHICS.md ─────────────────────────────────────

def test_the_real_table_parses() -> None:
    rows = audit_rows(ETHICS_PATH.read_text(encoding="utf-8"))
    assert {"kapook_cooking", "dcp_food", "wongnai", "thaifoodrecipe"} <= set(rows)


def test_kapook_is_cleared_by_its_decided_row() -> None:
    row = require_cleared("kapook_cooking")
    assert row.audited_on == date(2026, 8, 22)


@pytest.mark.parametrize(
    "source_id",
    [
        "dcp_food",  # HD-3 open (fetched under option C by default, never decided go)
        "wongnai",  # ToS pending
        "tat",  # ToS pending
        "thaifoodrecipe",  # dropped
        "national_library",  # blocked
        "never_audited",  # no row at all
    ],
)
def test_every_other_source_is_refused(source_id: str) -> None:
    with pytest.raises(EthicsGateError):
        require_cleared(source_id)


# ── the gate, cell by cell ───────────────────────────────────────────────────

GOOD = "| `newsite` | `new.example` | allowed | none | no prohibition | 2026-10-06 | ✅ HD-3 go |"


def test_a_complete_decided_row_passes(tmp_path: Path) -> None:
    assert require_cleared("newsite", _ethics(tmp_path, GOOD)).domain == "`new.example`"


@pytest.mark.parametrize(
    "row,why",
    [
        (GOOD.replace("2026-10-06", "recently"), "not dated"),
        (GOOD.replace("| allowed |", "| not fetched |"), "robots"),
        (GOOD.replace("no prohibition", "pending"), "Terms-of-Service"),
        (GOOD.replace("✅ HD-3 go", "**HD-3 open**"), "decided go"),
    ],
)
def test_an_incomplete_row_is_refused_with_its_reason(tmp_path: Path, row: str, why: str) -> None:
    with pytest.raises(EthicsGateError, match=why):
        require_cleared("newsite", _ethics(tmp_path, row))


# ── --audit ──────────────────────────────────────────────────────────────────

TOS_HTML = """<html><body><h1>Terms</h1>
<p>Welcome to our site. Enjoy the recipes.</p>
<p>You may not use robots, spiders or other automated means to access the site.</p>
<p>Content may be copied for personal use.</p>
<p>ห้ามคัดลอกหรือทำซ้ำเนื้อหาโดยไม่ได้รับอนุญาต</p>
<script>var automated = "not a clause";</script>
</body></html>"""


def test_relevant_clauses_are_quoted_and_prohibitions_flagged() -> None:
    from src.scrape.ethics import page_text

    clauses = relevant_clauses(page_text(TOS_HTML))
    texts = [c.text for c in clauses]
    assert "Welcome to our site." not in texts
    assert not any("not a clause" in t for t in texts), "script text is not the ToS"
    flagged = {c.text for c in clauses if c.possible_prohibition}
    assert any("automated means" in t for t in flagged)
    assert any("ห้ามคัดลอก" in t for t in flagged)
    assert "Content may be copied for personal use." in texts
    assert "Content may be copied for personal use." not in flagged


def _site(robots: str, tos: str | None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=robots)
        if request.url.path == "/terms" and tos is not None:
            return httpx.Response(200, text=tos, headers={"content-type": "text/html"})
        return httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_a_prohibiting_tos_means_stop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.scrape.conduct.time.sleep", lambda s: None)
    with _site("User-agent: *\nAllow: /\n", TOS_HTML) as client:
        report = audit_site(client, "newsite", "https://new.example", "https://new.example/terms",
                            UA, date(2026, 10, 6))
    assert report.must_stop
    path = write_audit(report, tmp_path)
    text = path.read_text(encoding="utf-8")
    assert path.name == "newsite_2026-10-06.md"
    assert "## STOP" in text
    assert "possible prohibition" in text
    row = next(line for line in text.splitlines() if line.startswith("| `newsite`"))
    assert row.endswith("| 2026-10-06 | **HD-3 open** |"), "the audit proposes, never decides"
    assert "✅" not in row


def test_a_clean_tos_proposes_a_row_and_does_not_stop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.scrape.conduct.time.sleep", lambda s: None)
    with _site("User-agent: *\nAllow: /\n", "<p>Recipes are for cooking.</p>") as client:
        report = audit_site(client, "newsite", "https://new.example", "https://new.example/terms",
                            UA, date(2026, 10, 6))
    assert not report.must_stop
    assert "## STOP" not in render_audit(report)


def test_a_robots_disallow_means_stop_and_the_tos_is_not_fetched() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200, text="User-agent: *\nDisallow: /\n")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        report = audit_site(client, "newsite", "https://new.example", "https://new.example/terms",
                            UA, date(2026, 10, 6))
    assert report.must_stop
    assert seen == ["/robots.txt"]


def test_the_audit_never_edits_ethics_md() -> None:
    import inspect

    import src.scrape.ethics as ethics

    source = inspect.getsource(ethics)
    assert "ETHICS_PATH.write" not in source and "ethics_path.write" not in source
