"""Database connection helper and migration runner.

Migrations are plain numbered SQL files in db/migrations/ (e.g. 001_sources.sql),
applied in order, tracked in a schema_migrations table.
"""

from __future__ import annotations

from pathlib import Path

import psycopg
from psycopg import Connection

from src.config import MIGRATIONS_DIR, get_settings


def get_connection() -> Connection:
    return psycopg.connect(get_settings().database_url)


def _ensure_schema_migrations_table(conn: Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version     TEXT PRIMARY KEY,
            applied_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    conn.commit()


def _applied_versions(conn: Connection) -> set[str]:
    rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
    return {row[0] for row in rows}


def _migration_sort_key(path: Path) -> int:
    return int(path.stem.split("_", 1)[0])


def _migration_files(migrations_dir: Path) -> list[Path]:
    return sorted(migrations_dir.glob("*.sql"), key=_migration_sort_key)


def run_migrations(migrations_dir: Path = MIGRATIONS_DIR) -> list[str]:
    """Apply any not-yet-applied db/migrations/*.sql files, in numbered order.

    Returns the versions newly applied (empty if the schema was already current).
    """
    conn = get_connection()
    try:
        _ensure_schema_migrations_table(conn)
        applied = _applied_versions(conn)
        newly_applied: list[str] = []
        for path in _migration_files(migrations_dir):
            version = path.stem
            if version in applied:
                continue
            conn.execute(path.read_text(encoding="utf-8"))
            conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
            conn.commit()
            newly_applied.append(version)
        return newly_applied
    finally:
        conn.close()
