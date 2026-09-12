"""Load and classify the gdcatalog source inventory into `source_catalogue`.

    uv run python -m scripts.load_source_catalogue --report
    uv run python -m scripts.load_source_catalogue

This is a **local-file loader, not a fetcher** — unlike every other script in
`scripts/` named `fetch_*`, this one never makes a network request. It only reads
`flavormap_gdcatalog_sources_full.csv` / `..._tierA_core.csv` off disk. That
distinction is why this script exists at all despite `culture.gdcatalog.go.th` and
its sibling hosts not having a completed, dated audit in `ETHICS.md` yet: rule 7 gates
*fetching*, and Task 2 of the brief that specified this table is explicit that no
domain should be fetched from before its `ETHICS.md` entry exists — but classifying
and tracking a catalogue export that is already sitting on disk is not a fetch, and
does not need to wait on that gate. Harvesting the three local-food files
(the brief's Task 3) and the GI product records (Task 4) genuinely does need that
gate, which is why no fetch script for those exists yet — see `docs/decisions.md`.

`--report` runs Task 0c (core-is-subset-of-full), Task 1's class distribution, and
Task 2a's distinct-domain list — all three need only the two CSVs, not the database
or network access.
"""

from __future__ import annotations

import argparse

from src.config import RAW_DIR
from src.db import get_connection
from src.ingest.source_catalogue import (
    CatalogueRow,
    build_catalogue_rows,
    class_distribution,
    distinct_domains,
    read_raw,
    validate_columns,
    verify_core_is_subset_of_full,
)

FULL_CSV = RAW_DIR / "gdcatalog" / "flavormap_gdcatalog_sources_full.csv"
CORE_CSV = RAW_DIR / "gdcatalog" / "flavormap_gdcatalog_sources_tierA_core.csv"


def load(catalogue: list[CatalogueRow], dry_run: bool) -> dict[str, int]:
    stats = {"rows": 0, "inserted": 0}
    if dry_run:
        stats["rows"] = len(catalogue)
        stats["inserted"] = len(catalogue)
        return stats

    conn = get_connection()
    try:
        for row in catalogue:
            stats["rows"] += 1
            conn.execute(
                """
                INSERT INTO source_catalogue
                    (dataset_slug, tier, dataset_title_th, province_th, publisher_th,
                     description_th, formats, n_resources, last_modified, resource_url,
                     content_class, harvest_status, rejection_reason)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (dataset_slug) DO UPDATE
                    SET content_class = EXCLUDED.content_class,
                        harvest_status = EXCLUDED.harvest_status,
                        rejection_reason = EXCLUDED.rejection_reason
                """,
                (
                    row.dataset_slug, row.tier, row.dataset_title_th, row.province_th,
                    row.publisher_th, row.description_th, row.formats, row.n_resources,
                    row.last_modified, row.resource_url, row.content_class,
                    row.harvest_status, row.rejection_reason,
                ),
            )
            stats["inserted"] += 1
        conn.commit()
    finally:
        conn.close()
    return stats


def print_report() -> None:
    full = read_raw(FULL_CSV)
    core = read_raw(CORE_CSV)
    validate_columns(full)
    validate_columns(core)

    subset = verify_core_is_subset_of_full(core, full)
    print(f"Task 0c — core is subset of full: {subset.core_count}/{subset.full_count}")
    if subset.core_slugs_not_in_full:
        print(f"  slugs in core but not full: {subset.core_slugs_not_in_full}")
    if subset.rows_differing:
        print(f"  rows differing between the two copies: {subset.rows_differing}")
    if not subset.core_slugs_not_in_full and not subset.rows_differing:
        print("  exact match, no discrepancies")

    catalogue = build_catalogue_rows(full)
    dist = class_distribution(catalogue)
    print("\nTask 1 — content_class distribution (all rows in full):")
    for cls, count in sorted(dist.items(), key=lambda kv: -kv[1]):
        print(f"  {count:>5}  {cls}")

    print(f"\nTask 2a — distinct resource_url domains ({len(distinct_domains(full))}):")
    for domain in distinct_domains(full):
        print(f"  {domain}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--report", action="store_true", help="print Task 0c/1/2a and exit")
    args = ap.parse_args()

    if not FULL_CSV.exists() or not CORE_CSV.exists():
        raise SystemExit(
            f"{FULL_CSV} and/or {CORE_CSV} not found. Not fetched automatically — "
            "see this module's docstring."
        )

    if args.report:
        print_report()
        return 0

    full = read_raw(FULL_CSV)
    validate_columns(full)
    catalogue = build_catalogue_rows(full)
    stats = load(catalogue, args.dry_run)
    print("\n" + "\n".join(f"{k:>10}: {v}" for k, v in stats.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
