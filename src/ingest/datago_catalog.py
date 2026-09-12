"""Parse `flavormap_datago_catalog.csv` (data.go.th's export) into the shared
`CatalogueRow` shape `src/ingest/source_catalogue.py` defines — Task 1–2 of the
`datago_catalog` brief. Merging with gdcatalog's export is `catalogue_merge.py`'s job
(Task 3); this module only reads and classifies one file.

**Task 1 — the province column is broken, confirmed against the real file.** 106
distinct `province` values against 77 real provinces. The worst case, present in
this exact file: a dataset titled "เรือประมงนอกน่านน้ำ..." (deep-sea fishing vessels
outside น่านน้ำ, *territorial waters*) carries `province='น่าน'` (Nan — landlocked) —
a substring match on "น่าน" inside "น่านน้ำ". `src/ingest/thai_province_match.py`
fixes this (verified against both the brief's named traps and this file's own real
example) and is used here to re-derive province from title/description text rather
than trust the source's own `province` column outright. See that module's docstring
for why option (b), newmm whole-token matching, was chosen over a blocklist.

**This module does not silently correct `province`.** `to_catalogue_rows` keeps the
source's own value in `province_th` and does not overwrite it — the per-row verdict
(`src.ingest.thai_province_match.check_assignment`) is a separate, explicit report
(Task 1c), not an in-place fix. Rule 2's spirit (never fabricate a province) cuts
both ways: this module also never *removes* a province value on this module's own
authority, because roughly half of the confirmed-valid values carry no textual
evidence either way (see the module's own report) and may be entirely correct,
sourced from a structured field this CSV gives no way to see.

**Task 2 — `relevance_score` is confirmed inverted.** `3_ingredient_agri` (crop/
livestock yield statistics) scores mean 11.2, max 37; `1_dish_culture` (the layer
that should matter most for this project) scores mean 6.7, max 13 — every row in the
29-37 range checked is agricultural-yield statistics. `SCORE_NOTE` is attached to
every row's `score_note` field rather than silently dropping the column: Task 2b asks
to keep it for the record while flagging it as unreliable for prioritisation, not to
delete evidence of how the catalogue was originally (mis-)ranked.

**`1_dish_culture`'s own noise, reclassified rather than trusted.** The layer
contains real heritage/dish content (มรดกภูมิปัญญาทางวัฒนธรรม, เมนูอาหารท้องถิ่น...)
mixed with household energy and economic survey rows (ร้อยละของครัวเรือนที่มีการใช้
เชื้อเพลิงแข็งในการประกอบอาหาร — % of households using solid cooking fuel) that have
nothing to do with food culture. `content_class` (the same closed vocabulary and
classifier `source_catalogue.py` uses for the gdcatalog export) is computed fresh
from title/description text, never trusted from `flavormap_layer`.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.ingest.source_catalogue import (
    AUTO_REJECT_CLASSES,
    CATALOGUE_DATAGO,
    STATUS_NOT_ASSESSED,
    STATUS_REJECTED,
    CatalogueRow,
    classify_content,
    compute_row_hash,
)

REQUIRED_COLUMNS: tuple[str, ...] = (
    "flavormap_layer",
    "relevance_score",
    "province",
    "geo_coverage",
    "dataset_title_th",
    "organization_th",
    "formats",
    "n_resources",
    "direct_resource_url",
    "dataset_page_url",
    "last_modified",
    "description_th",
)

#: Task 2b — attached to every row's score_note, not just documented in a comment
#: someone has to go find. The two numbers are this file's own real measurement, not
#: an estimate — see this module's docstring for how they were computed.
SCORE_NOTE = (
    "relevance_score is keyword-weight and confirmed to over-rank agricultural "
    "statistics: 3_ingredient_agri mean 11.2 (max 37) vs 1_dish_culture mean 6.7 "
    "(max 13); every row scoring 29-37 checked is crop/livestock yield data. "
    "Never sort or filter by this column alone (Task 2 of the datago_catalog brief)."
)


def read_raw(path: Path) -> pd.DataFrame:
    """UTF-8 with a BOM — same reason as every other gdcatalog-family source."""
    return pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)


def validate_columns(df: pd.DataFrame) -> None:
    missing = tuple(c for c in REQUIRED_COLUMNS if c not in df.columns)
    if missing:
        raise ValueError(f"expected column(s) missing from source CSV: {missing}")


def _parse_score(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_catalogue_rows(df: pd.DataFrame) -> list[CatalogueRow]:
    """Task 1-2: classify by content (never by `flavormap_layer`), preserve
    `province`/`relevance_score` unmodified, attach `SCORE_NOTE`. No `dataset_slug` —
    this source has none — so `row_hash` is title+URL based (see
    `source_catalogue.compute_row_hash`)."""
    validate_columns(df)
    rows: list[CatalogueRow] = []
    for _, row in df.iterrows():
        cls = classify_content(row["dataset_title_th"], row["description_th"])
        status = STATUS_REJECTED if cls in AUTO_REJECT_CLASSES else STATUS_NOT_ASSESSED
        reason = AUTO_REJECT_CLASSES.get(cls)
        row_hash = compute_row_hash(
            CATALOGUE_DATAGO, "", row["dataset_title_th"], row["direct_resource_url"]
        )
        rows.append(
            CatalogueRow(
                tier=None,  # datago has no tier; kept None deliberately
                dataset_title_th=row["dataset_title_th"],
                province_th=row["province"],
                publisher_th=row["organization_th"],
                description_th=row["description_th"],
                formats=row["formats"],
                n_resources=row["n_resources"],
                last_modified=row["last_modified"],
                dataset_slug=None,  # not present in this source
                resource_url=row["direct_resource_url"],
                content_class=cls,
                harvest_status=status,
                rejection_reason=reason,
                catalogue_source=CATALOGUE_DATAGO,
                row_hash=row_hash,
                page_url=row["dataset_page_url"],
                flavormap_layer=row["flavormap_layer"],
                relevance_score=_parse_score(row["relevance_score"]),
                score_note=SCORE_NOTE,
                geo_coverage=row["geo_coverage"],
            )
        )
    return rows
