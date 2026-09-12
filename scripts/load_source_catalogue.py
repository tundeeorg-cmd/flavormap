"""Load, classify, and merge both gdcatalog source-catalogue exports.

    uv run python -m scripts.load_source_catalogue --report
    uv run python -m scripts.load_source_catalogue

Local-file loader, not a fetcher — see this module's earlier docstring history in
`docs/decisions.md` for why that distinction is what let it be written before either
catalogue's own hosts had a completed `ETHICS.md` audit. Reads three files:

- `flavormap_gdcatalog_sources_full.csv` (culture.gdcatalog.go.th, 1,893 rows)
- `flavormap_gdcatalog_sources_tierA_core.csv` (its tier-A subset, Task 0c check only)
- `flavormap_datago_catalog.csv` (data.go.th, 3,861 rows)

`--report` runs every local-file-only check from both catalogue task briefs: Task
0c's subset check, both catalogues' `content_class` distributions, Task 2a's domain
list, Task 1's province-assignment verdicts (`src/ingest/thai_province_match.py`),
and Task 3's cross-catalogue dedup report (`src/ingest/catalogue_merge.py`). None of
it needs the database or network access.

Loading writes every row from both catalogues into `source_catalogue`
(`catalogue_source` distinguishes them), with `duplicate_of_catalogue_id` resolved
after insertion via each row's `row_hash` — Task 3b's merge, without silently
dropping either catalogue's copy of a shared dataset.
"""

from __future__ import annotations

import argparse
from collections import Counter

from src.config import RAW_DIR
from src.db import get_connection
from src.ingest.catalogue_merge import build_merge_report, mark_duplicates
from src.ingest.datago_catalog import read_raw as read_datago
from src.ingest.datago_catalog import to_catalogue_rows as to_datago_rows
from src.ingest.datago_catalog import validate_columns as validate_datago
from src.ingest.source_catalogue import (
    CatalogueRow,
    build_catalogue_rows,
    class_distribution,
    distinct_domains,
    read_raw,
    validate_columns,
    verify_core_is_subset_of_full,
)
from src.ingest.thai_province_match import (
    VERDICT_TRAP_MISMATCH,
    check_assignment,
)

GDCATALOG_FULL_CSV = RAW_DIR / "gdcatalog" / "flavormap_gdcatalog_sources_full.csv"
GDCATALOG_CORE_CSV = RAW_DIR / "gdcatalog" / "flavormap_gdcatalog_sources_tierA_core.csv"
DATAGO_CSV = RAW_DIR / "gdcatalog" / "flavormap_datago_catalog.csv"


def load(rows_with_dup: list[tuple[CatalogueRow, str | None]], dry_run: bool) -> dict[str, int]:
    stats = {"rows": 0, "inserted": 0, "duplicates_flagged": 0}
    if dry_run:
        stats["rows"] = len(rows_with_dup)
        stats["inserted"] = len(rows_with_dup)
        return stats

    conn = get_connection()
    try:
        hash_to_id: dict[str, int] = {}
        for row, _dup_of_hash in rows_with_dup:
            stats["rows"] += 1
            catalogue_id = conn.execute(
                """
                INSERT INTO source_catalogue
                    (dataset_slug, tier, dataset_title_th, province_th, publisher_th,
                     description_th, formats, n_resources, last_modified, resource_url,
                     content_class, harvest_status, rejection_reason, catalogue_source,
                     row_hash, page_url, flavormap_layer, relevance_score, score_note,
                     geo_coverage)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (row_hash) WHERE row_hash IS NOT NULL DO UPDATE
                    SET content_class = EXCLUDED.content_class,
                        harvest_status = EXCLUDED.harvest_status,
                        rejection_reason = EXCLUDED.rejection_reason
                RETURNING catalogue_id
                """,
                (
                    row.dataset_slug, row.tier, row.dataset_title_th, row.province_th,
                    row.publisher_th, row.description_th, row.formats, row.n_resources,
                    row.last_modified, row.resource_url, row.content_class,
                    row.harvest_status, row.rejection_reason, row.catalogue_source,
                    row.row_hash, row.page_url, row.flavormap_layer, row.relevance_score,
                    row.score_note, row.geo_coverage,
                ),
            ).fetchone()[0]
            stats["inserted"] += 1
            if row.row_hash:
                hash_to_id[row.row_hash] = catalogue_id

        for row, dup_of_hash in rows_with_dup:
            if dup_of_hash and dup_of_hash in hash_to_id and row.row_hash:
                conn.execute(
                    "UPDATE source_catalogue SET duplicate_of_catalogue_id = %s "
                    "WHERE row_hash = %s",
                    (hash_to_id[dup_of_hash], row.row_hash),
                )
                stats["duplicates_flagged"] += 1

        conn.commit()
    finally:
        conn.close()
    return stats


def print_report() -> None:
    gd_full = read_raw(GDCATALOG_FULL_CSV)
    gd_core = read_raw(GDCATALOG_CORE_CSV)
    validate_columns(gd_full)
    validate_columns(gd_core)

    subset = verify_core_is_subset_of_full(gd_core, gd_full)
    print(f"Task 0c — gdcatalog core is subset of full: {subset.core_count}/{subset.full_count}")
    if subset.core_slugs_not_in_full or subset.rows_differing:
        print(f"  slugs in core but not full: {subset.core_slugs_not_in_full}")
        print(f"  rows differing: {subset.rows_differing}")
    else:
        print("  exact match, no discrepancies")

    gd_rows = build_catalogue_rows(gd_full)
    print(f"\ngdcatalog content_class distribution ({len(gd_rows)} rows):")
    for cls, count in sorted(class_distribution(gd_rows).items(), key=lambda kv: -kv[1]):
        print(f"  {count:>5}  {cls}")

    print(f"\ngdcatalog distinct resource_url domains ({len(distinct_domains(gd_full))}):")
    for d in distinct_domains(gd_full):
        print(f"  {d}")

    datago_df = read_datago(DATAGO_CSV)
    validate_datago(datago_df)
    datago_rows = to_datago_rows(datago_df)
    print(f"\ndatago content_class distribution ({len(datago_rows)} rows):")
    for cls, count in sorted(class_distribution(datago_rows).items(), key=lambda kv: -kv[1]):
        print(f"  {count:>5}  {cls}")

    print("\nTask 1 — province assignment verdicts (datago):")
    verdicts = Counter(
        check_assignment(r["province"], r["dataset_title_th"], r["description_th"]).verdict
        for _, r in datago_df.iterrows()
    )
    for v, c in verdicts.most_common():
        print(f"  {c:>5}  {v}")
    trap_rows = [
        (r["province"], r["dataset_title_th"])
        for _, r in datago_df.iterrows()
        if check_assignment(r["province"], r["dataset_title_th"], r["description_th"]).verdict
        == VERDICT_TRAP_MISMATCH
    ]
    print(f"  confirmed trap_mismatch rows ({len(trap_rows)}):")
    for prov, title in trap_rows:
        print(f"    province={prov!r} title={title!r}")

    print("\nTask 3 — cross-catalogue merge report:")
    merge = build_merge_report(gd_rows, datago_rows)
    print(f"  gdcatalog: {merge.gdcatalog_count}, datago: {merge.datago_count}")
    print(f"  url_duplicate_pairs: {merge.url_duplicate_pairs}")
    print(f"  title_org_duplicate_pairs (additional): {merge.title_org_duplicate_pairs}")
    print(f"  same_title_different_resource: {merge.same_title_different_resource}")
    print(f"  combined_distinct_total: {merge.combined_distinct_total}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--report", action="store_true", help="print all local-file checks and exit")
    args = ap.parse_args()

    if args.report:
        if not GDCATALOG_FULL_CSV.exists() or not DATAGO_CSV.exists():
            raise SystemExit("required CSVs not found — see this module's docstring")
        print_report()
        return 0

    if not GDCATALOG_FULL_CSV.exists() or not DATAGO_CSV.exists():
        raise SystemExit("required CSVs not found — see this module's docstring")

    gd_full = read_raw(GDCATALOG_FULL_CSV)
    validate_columns(gd_full)
    gd_rows = build_catalogue_rows(gd_full)

    datago_df = read_datago(DATAGO_CSV)
    validate_datago(datago_df)
    datago_rows = to_datago_rows(datago_df)

    rows_with_dup = mark_duplicates(gd_rows, datago_rows)
    stats = load(rows_with_dup, args.dry_run)
    print("\n" + "\n".join(f"{k:>20}: {v}" for k, v in stats.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
