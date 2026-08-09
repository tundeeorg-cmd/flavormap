from src.config import RANDOM_SEED
from src.db import get_connection


def test_random_seed_pinned() -> None:
    assert RANDOM_SEED == 42


def test_database_connection_and_postgis_installed() -> None:
    """Requires `make setup` to have already started Postgres and applied migrations."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT extname FROM pg_extension WHERE extname = 'postgis'"
        ).fetchone()
        assert row is not None, "postgis extension is not installed on the database"
    finally:
        conn.close()
