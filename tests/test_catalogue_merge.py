"""`src/ingest/catalogue_merge.py` — cross-catalogue dedup detection (Task 3).

Fixtures are small synthetic pairs shaped like the real overlap this project's own
data shows: 980 exact resource_url matches, 1,124 title matches (866 of which also
share a URL, 258 same-title-different-resource) — see `docs/decisions.md` for the
real numbers this module's report format was built to produce.
"""

from __future__ import annotations

from src.ingest.catalogue_merge import build_merge_report, mark_duplicates
from src.ingest.source_catalogue import CATALOGUE_DATAGO, CATALOGUE_GDCATALOG, CatalogueRow


def _row(
    title: str,
    url: str = "",
    publisher: str = "",
    source: str = CATALOGUE_GDCATALOG,
    row_hash: str = "",
) -> CatalogueRow:
    return CatalogueRow(
        tier=None,
        dataset_title_th=title,
        province_th="",
        publisher_th=publisher,
        description_th="",
        formats="",
        n_resources="",
        last_modified="",
        dataset_slug=None,
        resource_url=url,
        content_class="irrelevant",
        harvest_status="not_assessed",
        rejection_reason=None,
        catalogue_source=source,
        row_hash=row_hash or f"{source}:{title}:{url}",
    )


def test_exact_url_duplicate_detected() -> None:
    gd = [_row("อาหารพื้นเมือง", url="https://x/a.csv", source=CATALOGUE_GDCATALOG)]
    dg = [_row("อาหารพื้นเมืองก", url="https://x/a.csv", source=CATALOGUE_DATAGO)]
    report = build_merge_report(gd, dg)
    assert report.url_duplicate_pairs == 1
    assert report.combined_distinct_total == 1


def test_title_and_publisher_duplicate_detected_without_shared_url() -> None:
    gd = [_row("อาหารพื้นเมือง", url="https://gd/a.csv", publisher="สนง.จังหวัด")]
    dg = [_row("อาหารพื้นเมือง", url="https://datago/b.csv", publisher="สนง.จังหวัด")]
    report = build_merge_report(gd, dg)
    assert report.title_org_duplicate_pairs == 1
    assert report.combined_distinct_total == 1


def test_same_title_different_publisher_is_not_a_duplicate_but_is_flagged() -> None:
    """Different organisations under the same title: not a confident duplicate (the
    brief's title+org key requires both), but worth surfacing separately."""
    gd = [_row("รายงานประจำปี", url="https://gd/a.csv", publisher="กรม ก")]
    dg = [_row("รายงานประจำปี", url="https://datago/b.csv", publisher="กรม ข")]
    report = build_merge_report(gd, dg)
    assert report.title_org_duplicate_pairs == 0
    assert report.same_title_different_resource == 2
    assert report.combined_distinct_total == 2  # both kept — no confident dup key matched


def test_unrelated_rows_not_flagged() -> None:
    gd = [_row("อาหารพื้นเมือง", url="https://gd/a.csv", publisher="กรม ก")]
    dg = [_row("ผลผลิตข้าว", url="https://datago/b.csv", publisher="กรม ข")]
    report = build_merge_report(gd, dg)
    assert report.url_duplicate_pairs == 0
    assert report.title_org_duplicate_pairs == 0
    assert report.same_title_different_resource == 0
    assert report.combined_distinct_total == 2


def test_combined_total_matches_counts() -> None:
    gd = [_row("a", url="u1"), _row("b", url="u2")]
    dg = [_row("c", url="u1"), _row("d", url="u3")]  # c duplicates a's URL
    report = build_merge_report(gd, dg)
    assert report.gdcatalog_count == 2
    assert report.datago_count == 2
    assert report.url_duplicate_pairs == 1
    assert report.combined_distinct_total == 3


def test_mark_duplicates_links_to_the_earlier_rows_hash() -> None:
    gd = [_row("อาหารพื้นเมือง", url="https://x/a.csv", row_hash="hash_gd")]
    dg = [_row("อาหารพื้นเมืองข", url="https://x/a.csv", row_hash="hash_dg")]
    result = mark_duplicates(gd, dg)
    assert result[0] == (gd[0], None)  # first-seen: not a duplicate of anything
    assert result[1] == (dg[0], "hash_gd")  # duplicates the gdcatalog row


def test_mark_duplicates_no_match_returns_none() -> None:
    gd = [_row("a", url="u1", row_hash="h1")]
    dg = [_row("b", url="u2", row_hash="h2")]
    result = mark_duplicates(gd, dg)
    assert result[0] == (gd[0], None)
    assert result[1] == (dg[0], None)


def test_mark_duplicates_preserves_input_order() -> None:
    gd = [_row("a", row_hash="h1"), _row("b", row_hash="h2")]
    dg = [_row("c", row_hash="h3")]
    result = mark_duplicates(gd, dg)
    assert [row for row, _ in result] == [gd[0], gd[1], dg[0]]
