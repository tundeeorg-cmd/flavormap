"""Run the province-eligibility threshold sweep (CLAUDE.md §7.5) against the database.

    uv run python -m scripts.eligibility_sweep [--out data/processed/eligibility_sweep.csv]

Counts recipes per province in `v_recipes_clean` for each register the threshold
applies to — the commercial register only, per HD-23 — and writes one row per
(register, threshold) for every threshold 5–30. Prints the headline
thresholds (10 / 15 / 25) to stdout.

Recipes with `province_code IS NULL` are excluded from the counts, never assigned
anywhere (rule 2). Provinces with no recipes in a register simply never appear as
eligible for it.

Until HD-6 lands, `recipe_ingredients` is empty and `v_recipes_clean` — which INNER
JOINs it — returns nothing, so every threshold reports zero. That is the true state of
the analysis view, not a failure of this script.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from src.analyze.eligibility import (
    HEADLINE_THRESHOLDS,
    THRESHOLD_REGISTERS,
    TOTAL_PROVINCES,
    sweep_by_register,
)
from src.config import PROCESSED_DIR
from src.db import get_connection

QUERY = """
SELECT register, province_code, count(*)
  FROM v_recipes_clean
 WHERE province_code IS NOT NULL
   AND register = ANY(%s)
 GROUP BY register, province_code
"""

def province_counts_by_register() -> dict[str, dict[str, int]]:
    """`{register: {province_code: n_recipes}}` from `v_recipes_clean`, for the
    registers in `THRESHOLD_REGISTERS`. Each appears even with zero rows, so an empty
    register reports zero rather than vanishing from the output."""
    conn = get_connection()
    try:
        rows = conn.execute(QUERY, (list(THRESHOLD_REGISTERS),)).fetchall()
    finally:
        conn.close()
    counts: dict[str, dict[str, int]] = {r: {} for r in THRESHOLD_REGISTERS}
    for register, province_code, n in rows:
        counts.setdefault(register, {})[province_code] = n
    return counts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=PROCESSED_DIR / "eligibility_sweep.csv")
    args = ap.parse_args()

    rows = sweep_by_register(province_counts_by_register())

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["register", "threshold", "n_eligible", "province_codes"])
        for register, threshold, n, codes in rows:
            writer.writerow([register, threshold, n, " ".join(codes)])
    print(f"wrote {args.out} ({len(rows)} rows)")

    print(f"headline — provinces with at least k recipes in v_recipes_clean, of {TOTAL_PROVINCES}:")
    for register, threshold, n, _ in rows:
        if threshold in HEADLINE_THRESHOLDS:
            print(f"  {register:<10} k={threshold:<3} {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
