"""`make status` / `make status-snapshot` — src/status.py and scripts/status.py.

What is asserted:
  - it runs clean against a database with no tables, and against one migrated but empty
    (a throwaway database, created and dropped here; the real one is never emptied);
  - it cannot write: Postgres itself rejects a write on its connection;
  - RQ readiness lines follow the counts, both synthetically and against real rows;
  - no personal data, and no connection string or password, ever reaches the output;
  - the committed (public) form omits the per-province name lists (HD-28).
"""

from __future__ import annotations

import datetime
import sys
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from psycopg.conninfo import conninfo_to_dict, make_conninfo

import src.db
from src.config import get_settings
from src.db import get_connection, run_migrations
from src.ingest.pdpa import find_leaks
from src.status import ReadOnlyDB, collect, render, rq_readiness

TODAY = datetime.date(2026, 9, 28)
EMPTY = {
    "official_with_ingredients": 0, "commercial_with_ingredients": 0,
    "official_recipes": 0, "clean_view": 0, "interview_dishes": 0,
    "stated_absences": 0, "cook_alongs": 0, "official_with_endangerment": 0,
}


def _line(lines: list[str], rq: str) -> str:
    return next(line for line in lines if line.startswith(rq))


# ── readiness (pure) ──────────────────────────────────────────────────────────

def test_nothing_yet_is_no_or_blocked_never_yes() -> None:
    lines = rq_readiness(EMPTY)
    assert _line(lines, "RQ1").startswith("RQ1 no")
    assert "domestic side blocked-on-fieldwork" in _line(lines, "RQ1")
    assert "validation blocked-on-fieldwork" in _line(lines, "RQ2")
    assert _line(lines, "RQ3").startswith("RQ3 blocked-on-fieldwork")
    assert _line(lines, "RQ4").startswith("RQ4 no — 0 of 8")
    assert _line(lines, "RQ5").startswith("RQ5 blocked-on-fieldwork")


def test_readiness_follows_the_counts() -> None:
    lines = rq_readiness({**EMPTY, "official_with_ingredients": 12, "cook_alongs": 3,
                          "interview_dishes": 6, "official_recipes": 201,
                          "official_with_endangerment": 0})
    assert _line(lines, "RQ1").startswith("RQ1 partial")
    assert "official 12, commercial 0" in _line(lines, "RQ1")
    assert "domestic side 6 interview dishes" in _line(lines, "RQ1")
    assert _line(lines, "RQ3").startswith("RQ3 yes")
    assert _line(lines, "RQ4").startswith("RQ4 partial — 3 of 8")
    assert _line(lines, "RQ5").startswith("RQ5 partial")
    assert rq_readiness({**EMPTY, "cook_alongs": 8})[3].startswith("RQ4 yes")


def test_a_missing_count_is_na_not_an_error() -> None:
    lines = rq_readiness({})
    assert all(" n/a" in line for line in lines)


# ── disk facts ────────────────────────────────────────────────────────────────

def _collect(tmp: Path, **kw: object) -> str:
    status = collect(dsn=None, today=TODAY, check_container=False, **kw)  # type: ignore[arg-type]
    return render(status)


def test_backup_age_and_warning(tmp_path: Path) -> None:
    exports = tmp_path / "exports"
    exports.mkdir()
    assert "none in data/exports/" in _collect(tmp_path, exports_dir=exports)
    (exports / "flavormap_20260901_120000.sql.gz").write_bytes(b"")
    text = _collect(tmp_path, exports_dir=exports)
    assert "27 days old" in text and "older than 7 days" in text
    (exports / "flavormap_20260925_120000.sql.gz").write_bytes(b"")
    text = _collect(tmp_path, exports_dir=exports)
    assert "flavormap_20260925_120000.sql.gz, 3 days old" in text
    assert "older than 7 days" not in text


def test_decisions_are_counted_by_dated_section(tmp_path: Path) -> None:
    path = tmp_path / "decisions.md"
    path.write_text(
        "# Log\n\n## HD-n — template\n**Date presented:** YYYY-MM-DD\n\n"
        "## HD-1 — a\n**Date presented:** 2026-08-16\n**Date decided:** 2026-08-20\n\n"
        "## Note — b\n**Date:** 2026-09-12\n\n## Undated\nnothing here\n",
        encoding="utf-8",
    )
    text = _collect(tmp_path, decisions_path=path)
    assert "dated entries          2" in text
    assert "most recent            2026-09-12" in text


# ── database ──────────────────────────────────────────────────────────────────

def _dsn_for(dbname: str) -> str:
    return make_conninfo(get_settings().database_url, dbname=dbname)


@pytest.fixture
def scratch_db(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """A throwaway database, created empty and dropped afterwards."""
    name = "flavormap_status_test"
    admin = psycopg.connect(get_settings().database_url, autocommit=True)
    try:
        admin.execute(f"DROP DATABASE IF EXISTS {name}")
        admin.execute(f"CREATE DATABASE {name}")
        yield _dsn_for(name)
    finally:
        admin.execute(f"DROP DATABASE IF EXISTS {name} WITH (FORCE)")
        admin.close()


def test_runs_clean_on_a_database_with_no_tables(scratch_db: str, tmp_path: Path) -> None:
    text = render(collect(dsn=scratch_db, today=TODAY, check_container=False))
    assert "database: not reachable" not in text
    assert "raw_recipes            n/a" in text
    assert "migrations             n/a applied" in text
    assert "RQ4 n/a" in text


def test_runs_clean_on_a_migrated_empty_database(
    scratch_db: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(src.db, "get_connection", lambda: psycopg.connect(scratch_db))
    run_migrations()
    status = collect(dsn=scratch_db, today=TODAY, check_container=False)
    text = render(status)
    assert "raw_recipes            0" in text
    assert "recipes                0  (official 0, commercial 0, domestic 0)" in text
    assert f"{status.migrations_present} applied of {status.migrations_present} files" in text
    assert "RQ4 no — 0 of 8" in text
    assert "n/a" not in text.split("Lexicon")[1].split("Pipeline")[0]


def test_an_unreachable_database_degrades_and_leaks_no_credentials() -> None:
    dsn = "postgresql://someone:HUNTER2-not-a-real-password@127.0.0.1:1/nowhere"
    text = render(collect(dsn=dsn, today=TODAY, check_container=False))
    assert "database: not reachable" in text
    assert "HUNTER2" not in text and "someone" not in text and "127.0.0.1" not in text


def test_the_status_connection_cannot_write() -> None:
    db = ReadOnlyDB(get_settings().database_url)
    assert db.conn is not None
    try:
        with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
            db.conn.execute(
                "INSERT INTO sources (source_id, source_type, base_url, robots_ok, audited_on)"
                " VALUES ('_test_status_write', 'web_scraped', 'x', true, '2026-09-28')"
            )
    finally:
        db.close()
        # If the guard ever breaks, the write above committed: remove it.
        conn = get_connection()
        conn.execute("DELETE FROM sources WHERE source_id = '_test_status_write'")
        conn.commit()
        conn.close()


def test_output_carries_no_personal_data_and_no_connection_string() -> None:
    status = collect(today=TODAY, check_container=False)
    info = conninfo_to_dict(get_settings().database_url)
    for text in (render(status), render(status, public=True)):
        assert not find_leaks(text), find_leaks(text)
        assert "://" not in text
        assert get_settings().database_url not in text
        if info.get("password"):
            assert str(info["password"]) not in text


def test_public_form_omits_province_name_lists() -> None:
    status = collect(today=TODAY, check_container=False)
    names = [n for names in status.provinces_missing.values() if names for n in names]
    public = render(status, public=True)
    assert "zero:" not in public
    assert not any(name in public for name in names)


_SOURCE_ID = "_test_status_src"


@pytest.fixture
def one_more_cook_along() -> Iterator[None]:
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO sources (source_id, source_type, base_url, robots_ok, audited_on)
               VALUES (%s, 'web_scraped', 'https://example.com', true, '2026-09-28')""",
            (_SOURCE_ID,),
        )
        raw_id = conn.execute(
            """INSERT INTO raw_recipes (source_id, source_url, raw_path, content_hash)
               VALUES (%s, 'https://example.com/1', '/tmp/_test', 'deadbeef')
               RETURNING raw_id""",
            (_SOURCE_ID,),
        ).fetchone()[0]
        recipe_id = conn.execute(
            """INSERT INTO recipes (raw_id, name_th, register)
               VALUES (%s, 'ทดสอบ', 'commercial') RETURNING recipe_id""",
            (raw_id,),
        ).fetchone()[0]
        conn.execute(
            """INSERT INTO cook_along_log (log_key, recipe_id, cook_date)
               VALUES ('test_status_1', %s, '2027-04-01')""",
            (recipe_id,),
        )
        conn.commit()
        yield
    finally:
        conn.rollback()
        conn.execute("DELETE FROM cook_along_log WHERE log_key = 'test_status_1'")
        conn.execute(
            """DELETE FROM recipes WHERE raw_id IN
                   (SELECT raw_id FROM raw_recipes WHERE source_id = %s)""",
            (_SOURCE_ID,),
        )
        conn.execute("DELETE FROM raw_recipes WHERE source_id = %s", (_SOURCE_ID,))
        conn.execute("DELETE FROM sources WHERE source_id = %s", (_SOURCE_ID,))
        conn.commit()
        conn.close()


def test_rq_lines_track_real_rows(one_more_cook_along: None) -> None:
    conn = get_connection()
    try:
        others = conn.execute(
            "SELECT count(*) FROM cook_along_log WHERE log_key <> 'test_status_1'"
        ).fetchone()[0]
    finally:
        conn.close()
    status = collect(today=TODAY, check_container=False)
    assert status.rq_inputs["cook_alongs"] == others + 1
    assert f"{others + 1} of 8 cook-alongs logged" in render(status)


# ── snapshot ──────────────────────────────────────────────────────────────────

def test_snapshot_writes_the_public_form(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import scripts.status

    monkeypatch.setattr(scripts.status, "SNAPSHOT_DIR", tmp_path)
    monkeypatch.setattr(sys, "argv", ["status", "--snapshot"])
    assert scripts.status.main() == 0
    [written] = list(tmp_path.glob("status_*.md"))
    assert written.name == f"status_{datetime.date.today().isoformat()}.md"
    text = written.read_text(encoding="utf-8")
    assert text.startswith("# FlavorMap status")
    assert "zero:" not in text
    assert not find_leaks(text)
