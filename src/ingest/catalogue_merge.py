"""Cross-catalogue deduplication — Task 3 of the `datago_catalog` brief.

Two independently-produced catalogue exports (`flavormap_gdcatalog_sources_full.csv`
and `flavormap_datago_catalog.csv`) describe overlapping sets of the same real
datasets. This module finds the overlap; it never resolves it. Which row of a
duplicate pair is authoritative — when the two disagree on province, description, or
anything else — is a source-precedence call in the same class as HD-12 (recipe dedup
retention rule) and stays a flag (`duplicate_of_catalogue_id`), not an automatic
merge.

**Two-stage detection, per the brief (Task 3a):**

1. Exact `resource_url` match — "most reliable". Two rows fetching the identical file
   are the same dataset regardless of what their titles say.
2. Among the rest, `dataset_title_th` + `publisher_th`/`organization_th` match — a
   weaker signal (metadata drift between the two exports means the same real
   organisation can appear under differently-formatted names, which this method
   cannot see past) that still catches same-title-different-resource duplicates the
   URL check alone would miss.

A pair matching on title alone, with different resource URLs, is reported separately
(`same_title_different_resource`) rather than folded into the duplicate count — the
brief is explicit these are not the same finding, and pooling them would overstate
how much genuine overlap the two catalogues have.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.ingest.source_catalogue import CatalogueRow


@dataclass
class MergeReport:
    gdcatalog_count: int
    datago_count: int
    url_duplicate_pairs: int
    title_org_duplicate_pairs: int  # additional pairs found by title+org, beyond URL
    same_title_different_resource: int
    combined_distinct_total: int


def _key_url(row: CatalogueRow) -> str | None:
    return row.resource_url or None


def _key_title_org(row: CatalogueRow) -> tuple[str, str] | None:
    if not row.dataset_title_th:
        return None
    return (row.dataset_title_th, row.publisher_th or "")


def _key_title_only(row: CatalogueRow) -> str | None:
    return row.dataset_title_th or None


def build_merge_report(
    gdcatalog_rows: list[CatalogueRow], datago_rows: list[CatalogueRow]
) -> MergeReport:
    """Task 3a/3c: how much overlap is there, and what is the true combined total?

    A row counts as a duplicate of exactly one earlier row (first catalogue's rows
    are checked first, so a datago row duplicating a gdcatalog row is the one
    "removed" from the combined count — gdcatalog's province_th is the cleaner field,
    Task 1d, which is the only reason for this direction rather than the reverse; it
    does not decide which row's *other* fields are kept, only which is counted).
    """
    all_rows = gdcatalog_rows + datago_rows

    seen_urls: dict[str, int] = {}
    seen_title_org: dict[tuple[str, str], int] = {}
    seen_titles: dict[str, int] = {}

    url_dupe_count = 0
    title_org_dupe_count = 0
    same_title_diff_resource_ids: set[int] = set()
    duplicate_indices: set[int] = set()

    for i, row in enumerate(all_rows):
        url_key = _key_url(row)
        if url_key is not None and url_key in seen_urls:
            url_dupe_count += 1
            duplicate_indices.add(i)
            continue

        title_org_key = _key_title_org(row)
        if title_org_key is not None and title_org_key in seen_title_org:
            title_org_dupe_count += 1
            duplicate_indices.add(i)
            if url_key is not None:
                seen_urls[url_key] = i
            continue

        # Not a duplicate by either strong key. Still check for same-title-
        # different-resource, reported separately per the brief.
        title_key = _key_title_only(row)
        if title_key is not None and title_key in seen_titles:
            same_title_diff_resource_ids.add(i)
            same_title_diff_resource_ids.add(seen_titles[title_key])

        if url_key is not None:
            seen_urls[url_key] = i
        if title_org_key is not None:
            seen_title_org[title_org_key] = i
        if title_key is not None:
            seen_titles[title_key] = i

    return MergeReport(
        gdcatalog_count=len(gdcatalog_rows),
        datago_count=len(datago_rows),
        url_duplicate_pairs=url_dupe_count,
        title_org_duplicate_pairs=title_org_dupe_count,
        same_title_different_resource=len(same_title_diff_resource_ids),
        combined_distinct_total=len(all_rows) - len(duplicate_indices),
    )


def mark_duplicates(
    gdcatalog_rows: list[CatalogueRow], datago_rows: list[CatalogueRow]
) -> list[tuple[CatalogueRow, str | None]]:
    """Same detection as :func:`build_merge_report`, but returns every row paired
    with the `row_hash` of the earlier row it duplicates (or `None`). Real
    `catalogue_id` values only exist once rows are in the database, so this works in
    terms of `row_hash` instead — stable, computed before insert, and already unique
    per row — for the caller (the loader) to resolve into `duplicate_of_catalogue_id`
    after both catalogues have been inserted.

    Order: `gdcatalog_rows` then `datago_rows`, unchanged from the input order.
    """
    all_rows = gdcatalog_rows + datago_rows
    seen_urls: dict[str, str] = {}
    seen_title_org: dict[tuple[str, str], str] = {}

    result: list[tuple[CatalogueRow, str | None]] = []
    for row in all_rows:
        dup_of: str | None = None
        url_key = _key_url(row)
        if url_key is not None and url_key in seen_urls:
            dup_of = seen_urls[url_key]
        else:
            title_org_key = _key_title_org(row)
            if title_org_key is not None and title_org_key in seen_title_org:
                dup_of = seen_title_org[title_org_key]

        result.append((row, dup_of))
        if row.row_hash:
            if url_key is not None and url_key not in seen_urls:
                seen_urls[url_key] = row.row_hash
            title_org_key = _key_title_org(row)
            if title_org_key is not None and title_org_key not in seen_title_org:
                seen_title_org[title_org_key] = row.row_hash

    return result
