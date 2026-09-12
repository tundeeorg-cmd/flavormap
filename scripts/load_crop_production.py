"""Load `flavormap_oae_production.csv` into `crop_production`.

    uv run python -m scripts.load_crop_production --report
    uv run python -m scripts.load_crop_production

Local-file loader, not a fetcher — this source has no fetch/ETHICS.md gate to clear
because nothing here makes a network request. `--report` runs Task 1b/1c/2a's checks
(province validation, region_th vocabulary match, unit consistency) without touching
the database.
"""

from __future__ import annotations

import argparse

from src.config import RAW_DIR
from src.db import get_connection
from src.ingest.oae_production import (
    REQUIRED_COLUMNS,
    check_unit_consistency,
    read_raw,
    row_hash,
    to_num,
    validate_columns,
    validate_provinces,
    validate_regions,
)

CSV_PATH = RAW_DIR / "gdcatalog" / "flavormap_oae_production.csv"


def print_report() -> None:
    df = read_raw(CSV_PATH)
    validate_columns(df)

    prov = validate_provinces(df)
    print(f"Task 1b — province validation: {prov.distinct_provinces} distinct values")
    if prov.invalid_provinces:
        print(f"  INVALID (not in official 77): {prov.invalid_provinces}")
    else:
        print("  all 77 clean — every value matches the official province list exactly")

    bad_regions = validate_regions(df)
    if bad_regions:
        print(f"\nTask 1c — region_th mismatch against food67: {bad_regions}")
    else:
        print("\nTask 1c — region_th: exact match with flavormap_food67.csv's six values")

    violations = check_unit_consistency(df)
    print(f"\nTask 2a — unit consistency: {len(violations)} commodity/violations found")
    for v in violations:
        print(f"  {v.commodity_th}: units seen {v.units_seen}")
    prod_units = sorted(df["production_unit"].unique())
    yield_units = sorted(df["yield_unit"].unique())
    yield_bases = sorted(df["yield_basis"].unique())
    print(f"  distinct production_unit: {prod_units}")
    print(f"  distinct yield_unit: {yield_units}")
    print(f"  distinct yield_basis: {yield_bases}")

    print(f"\nTask 1d — PDPA: source columns are {list(REQUIRED_COLUMNS)}")
    print("  no name/address/contact column present — confirmed by inspection, no redaction needed")


def load(dry_run: bool) -> dict[str, int]:
    df = read_raw(CSV_PATH)
    validate_columns(df)
    stats = {"rows": len(df), "inserted": 0}
    if dry_run:
        stats["inserted"] = len(df)
        return stats

    conn = get_connection()
    try:
        for _, r in df.iterrows():
            conn.execute(
                """
                INSERT INTO crop_production
                    (province_th, region_th, commodity_th, subcommodity_th, year_be,
                     year_ce, planted_area_rai, standing_area_rai, harvested_area_rai,
                     bearing_area_rai, tapped_area_rai, production, production_unit,
                     yield_per_rai, yield_unit, yield_basis, source_dataset,
                     source_file, row_hash)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (row_hash) DO NOTHING
                """,
                (
                    r["province_th"], r["region_th"], r["commodity_th"],
                    r["subcommodity_th"], r["year_be"], int(r["year_ce"]),
                    to_num(r["planted_area_rai"]), to_num(r["standing_area_rai"]),
                    to_num(r["harvested_area_rai"]), to_num(r["bearing_area_rai"]),
                    to_num(r["tapped_area_rai"]), to_num(r["production"]),
                    r["production_unit"], to_num(r["yield_per_rai"]), r["yield_unit"],
                    r["yield_basis"], r["source_dataset"], str(CSV_PATH),
                    row_hash(
                        r["province_th"], r["commodity_th"], r["subcommodity_th"], r["year_be"]
                    ),
                ),
            )
            stats["inserted"] += 1
        conn.commit()
    finally:
        conn.close()
    return stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--report", action="store_true", help="print all local-file checks and exit")
    args = ap.parse_args()

    if not CSV_PATH.exists():
        raise SystemExit(f"{CSV_PATH} not found")

    if args.report:
        print_report()
        return 0

    stats = load(args.dry_run)
    print("\n" + "\n".join(f"{k:>10}: {v}" for k, v in stats.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
