"""scripts/restore_db.sh: a dump restores faithfully, and a bad restore can never
report success or damage an existing database.

Every restore targets a throwaway database (``flavormap_restore_pytest``) via
``--db``; the live database is only ever read. The dump is made with the same
``pg_dump`` command scripts/dump_db.sh uses, but written to pytest's temp directory, so
nothing is added to data/exports/.

Background (2026-09-28): the previous script, run after ``make db-reset``, printed 84
errors, exited 0, and lost all 201 province_attribution rows. These tests pin each
behaviour that closes that gap.
"""

from __future__ import annotations

import gzip
import subprocess
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from psycopg.conninfo import make_conninfo

from src.config import REPO_ROOT, get_settings

SCRIPT = REPO_ROOT / "scripts" / "restore_db.sh"
TARGET = "flavormap_restore_pytest"

# Enough to show a restore is faithful: every public table's rows, plus content
# checksums for the two tables whose silent loss started this.
FINGERPRINT = """
SELECT (SELECT string_agg(t, ',' ORDER BY t) FROM (
            SELECT tablename AS t FROM pg_tables WHERE schemaname = 'public') s),
       (SELECT string_agg(version, ',' ORDER BY version) FROM schema_migrations),
       (SELECT md5(string_agg(recipe_id || name_th || register, '|' ORDER BY recipe_id))
          FROM recipes),
       (SELECT md5(string_agg(recipe_id || coalesce(province_code, '-') || confidence,
                              '|' ORDER BY recipe_id)) FROM province_attribution),
       (SELECT count(*) FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace
         WHERE n.nspname = 'public')
"""


def _fingerprint(dbname: str) -> tuple[object, ...]:
    dsn = make_conninfo(get_settings().database_url, dbname=dbname)
    with psycopg.connect(dsn, options="-c default_transaction_read_only=on") as conn:
        row = conn.execute(FINGERPRINT).fetchone()
        assert row is not None
        counts = {
            t: conn.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0]  # type: ignore[index]
            for (t,) in conn.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        }
    return (*row, counts)


def _live_dbname() -> str:
    with psycopg.connect(get_settings().database_url) as conn:
        return str(conn.info.dbname)


def _restore(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), *args], cwd=REPO_ROOT,
        capture_output=True, text=True, timeout=180, check=False,
    )


def _drop(name: str) -> None:
    with psycopg.connect(get_settings().database_url, autocommit=True) as conn:
        conn.execute(f"DROP DATABASE IF EXISTS {name} WITH (FORCE)")


@pytest.fixture(scope="module")
def dump(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A fresh dump of the live database, made exactly as scripts/dump_db.sh makes it."""
    out = tmp_path_factory.mktemp("dump") / "flavormap_test.sql.gz"
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", "db", "sh", "-c",
         'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"'],
        cwd=REPO_ROOT, capture_output=True, timeout=120, check=True,
    )
    out.write_bytes(gzip.compress(result.stdout))
    return out


@pytest.fixture
def target() -> Iterator[str]:
    _drop(TARGET)
    _drop(f"{TARGET}_restore_staging")
    yield TARGET
    _drop(TARGET)
    _drop(f"{TARGET}_restore_staging")


def test_a_dump_restores_identical_to_the_live_database(dump: Path, target: str) -> None:
    result = _restore("--db", target, str(dump))
    assert result.returncode == 0, result.stderr
    assert _fingerprint(target) == _fingerprint(_live_dbname())
    assert "province attributions" in result.stdout


def test_a_populated_target_is_refused_without_force(dump: Path, target: str) -> None:
    assert _restore("--db", target, str(dump)).returncode == 0
    before = _fingerprint(target)
    result = _restore("--db", target, str(dump))
    assert result.returncode != 0
    assert "refused" in result.stderr
    assert _fingerprint(target) == before


def test_force_replaces_without_duplicating_rows(dump: Path, target: str) -> None:
    assert _restore("--db", target, str(dump)).returncode == 0
    result = _restore("--force", "--db", target, str(dump))
    assert result.returncode == 0, result.stderr
    assert _fingerprint(target) == _fingerprint(_live_dbname())


def test_a_bad_dump_fails_loudly_and_leaves_the_target_untouched(
    dump: Path, target: str, tmp_path: Path
) -> None:
    assert _restore("--db", target, str(dump)).returncode == 0
    before = _fingerprint(target)
    corrupt = tmp_path / "corrupt.sql.gz"
    corrupt.write_bytes(gzip.compress(
        gzip.decompress(dump.read_bytes())
        + b"\nINSERT INTO recipes (recipe_id) VALUES ('not a number');\n"
    ))
    result = _restore("--force", "--db", target, str(corrupt))
    assert result.returncode != 0
    assert "was not changed" in result.stderr
    assert _fingerprint(target) == before
    with psycopg.connect(get_settings().database_url) as conn:
        assert conn.execute(
            "SELECT count(*) FROM pg_database WHERE datname = %s",
            (f"{target}_restore_staging",),
        ).fetchone() == (0,)


@pytest.mark.parametrize("bad", ["x; drop", "Flavormap", "a-b"])
def test_unsafe_database_names_are_rejected(dump: Path, bad: str) -> None:
    result = _restore("--db", bad, str(dump))
    assert result.returncode != 0
    assert "must be lowercase" in result.stderr


def test_an_empty_db_name_never_falls_through_to_the_live_database(dump: Path) -> None:
    """`--db ""` must be a usage error. Before this was pinned it silently meant the live
    database, and with --force would have replaced it."""
    result = _restore("--force", "--db", "", str(dump))
    assert result.returncode != 0
    assert "Usage" in result.stderr
    assert "Restoring" not in result.stdout


def test_a_missing_dump_file_is_an_error(target: str) -> None:
    result = _restore("--db", target, "/nonexistent/dump.sql.gz")
    assert result.returncode != 0
    assert "not found" in result.stderr
