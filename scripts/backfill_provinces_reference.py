"""Refresh non-geometry reference columns on an already-loaded `provinces` table.

    uv run python -m scripts.backfill_provinces_reference [--dry-run]

`scripts/load_geometry.py` is the real loader, but it needs GADM v4.1
(`geodata.ucdavis.edu`), which this project's network access has not been able to
reach in any session so far. The 77 rows currently in `provinces` were loaded once,
without geometry, as a documented stopgap (`docs/decisions.md`, 2026-09-12) — this
script is the general tool that stopgap should have been from the start: it updates
`region4`, `dialect_group`, `border_country`, and `region6` from
`data/reference/provinces.csv` for rows that already exist, so a CSV-only change
(HD-1's dialect reassignment, HD-23's region6 addition, anything similar later) can
reach the database without waiting on GADM access.

**Never touches `geom` or the derived centroids.** Those still need
`scripts/load_geometry.py` and real GADM geometry — this script only refreshes columns
that come from the CSV directly, and does not fabricate geometry from Bangkok being
the only real point anyone typed by hand.

**Refuses to INSERT.** A province_code in the CSV with no matching row in the
database is reported, not created — creating a province row with `geom IS NULL` in
this script, silently, is exactly the kind of partial load `load_geometry.py`
already refuses to produce, and this script should not reopen that door for updates.
"""

from __future__ import annotations

import argparse
import csv

from src.config import REFERENCE_DIR
from src.db import get_connection


def read_reference() -> list[dict[str, str]]:
    path = REFERENCE_DIR / "provinces.csv"
    if not path.exists():
        raise SystemExit(f"{path} not found")
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 77:
        raise SystemExit(f"expected 77 provinces in {path}, found {len(rows)}")
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    reference = read_reference()

    if args.dry_run:
        print(f"dry run — would refresh region4/dialect_group/border_country/region6 "
              f"for up to {len(reference)} provinces")
        return 0

    conn = get_connection()
    try:
        existing = {
            row[0] for row in conn.execute("SELECT province_code FROM provinces").fetchall()
        }
        missing = [r["province_code"] for r in reference if r["province_code"] not in existing]
        if missing:
            print(f"NOT updated — {len(missing)} province_code(s) not present in the "
                  f"database (run scripts.load_geometry first): {missing}")

        updated = 0
        for row in reference:
            if row["province_code"] not in existing:
                continue
            conn.execute(
                """
                UPDATE provinces SET
                    region4        = %s,
                    dialect_group  = NULLIF(%s, ''),
                    border_country = %s,
                    region6        = NULLIF(%s, '')
                WHERE province_code = %s
                """,
                (
                    row["region4"],
                    row["dialect_group"],
                    row["border_country"].split("|") if row["border_country"] else None,
                    row["region6"],
                    row["province_code"],
                ),
            )
            updated += 1
        conn.commit()
        print(f"refreshed {updated}/{len(reference)} provinces")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
