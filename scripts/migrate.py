"""CLI: apply any pending db/migrations/*.sql files.

Run via `make setup` or `uv run python -m scripts.migrate`.
"""

from __future__ import annotations

from src.db import run_migrations


def main() -> None:
    applied = run_migrations()
    if applied:
        print(f"Applied {len(applied)} migration(s): {', '.join(applied)}")
    else:
        print("No pending migrations.")


if __name__ == "__main__":
    main()
