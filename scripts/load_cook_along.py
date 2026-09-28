"""Load hand-written cook-along logs into ``cook_along_log`` (RQ4).

    uv run python -m scripts.load_cook_along [--dir data/cook_along]

Reads every ``*.toml`` file in the directory except ``_``-prefixed ones (the template),
validates each with ``src.ingest.cook_along``, and upserts on ``log_key`` (the file
stem, migration 022) so re-running after an edit updates rows in place.

All-or-nothing: every file is validated before anything is written, the writes share
one transaction, and a single
invalid file — a bad fidelity value, an unknown key, personal data in a note — stops
the whole load with every problem listed. A partial load would leave Figure 4 built
from whichever files happened to sort first.

Files that were loaded once and later deleted are not removed from the table; the
script reports them so the researcher can decide what a deleted log means.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from psycopg import errors

from src.config import COOK_ALONG_DIR
from src.db import get_connection
from src.ingest.cook_along import CookAlongEntry, CookAlongError, log_files, read_entry

_COLUMNS = (
    "log_key", "recipe_id", "cook_date", "missing_ingredients", "substitutions_made",
    "normalization_losses", "result_recognizable", "classifier_gets_wrong",
    "fidelity_quantities", "fidelity_order", "fidelity_technique",
    "fidelity_specificity", "fidelity_completeness", "notes",
)

UPSERT = f"""
INSERT INTO cook_along_log ({", ".join(_COLUMNS)})
VALUES ({", ".join(["%s"] * len(_COLUMNS))})
ON CONFLICT (log_key) DO UPDATE SET
  {", ".join(f"{c} = EXCLUDED.{c}" for c in _COLUMNS if c != "log_key")}
"""


def read_all(directory: Path) -> list[CookAlongEntry]:
    """Validate every file; raise one ``CookAlongError`` listing all failures."""
    entries: list[CookAlongEntry] = []
    errors: list[str] = []
    for path in log_files(directory):
        try:
            entries.append(read_entry(path))
        except CookAlongError as e:
            errors.append(str(e))
    if errors:
        raise CookAlongError("\n".join(errors))
    return entries


def load(entries: list[CookAlongEntry]) -> list[str]:
    """Upsert `entries` in one transaction. Returns log_keys in the table that no
    longer have a file."""
    conn = get_connection()
    try:
        with conn.transaction():
            for e in entries:
                try:
                    conn.execute(UPSERT, tuple(getattr(e, c) for c in _COLUMNS))
                except errors.ForeignKeyViolation as exc:
                    raise CookAlongError(
                        f"{e.log_key}: recipe_id {e.recipe_id} is not in recipes"
                    ) from exc
        in_table = {r[0] for r in conn.execute("SELECT log_key FROM cook_along_log")}
    finally:
        conn.close()
    return sorted(in_table - {e.log_key for e in entries})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", type=Path, default=COOK_ALONG_DIR)
    args = ap.parse_args()

    try:
        entries = read_all(args.dir)
    except CookAlongError as e:
        print(f"refused — nothing loaded:\n{e}", file=sys.stderr)
        return 1

    try:
        orphans = load(entries)
    except CookAlongError as e:
        print(f"refused — nothing loaded:\n{e}", file=sys.stderr)
        return 1
    print(f"loaded {len(entries)} cook-along log(s) from {args.dir}")
    if orphans:
        print(f"in cook_along_log with no file (not removed): {', '.join(orphans)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
