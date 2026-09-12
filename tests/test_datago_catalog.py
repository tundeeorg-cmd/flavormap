"""`src/ingest/datago_catalog.py` — parsing, content classification, and score_note
attachment for data.go.th's catalogue export.

Fixtures use the real title text that surfaced Task 1's province bug
(`เรือประมงนอกน่านน้ำ...`) and Task 2's score-inversion evidence, both drawn from
`flavormap_datago_catalog.csv` itself (this project has a real copy — see
`docs/decisions.md`), but built as small synthetic rows here rather than depending on
the full 3,861-row file for unit tests.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.ingest.datago_catalog import (
    REQUIRED_COLUMNS,
    SCORE_NOTE,
    to_catalogue_rows,
    validate_columns,
)
from src.ingest.source_catalogue import (
    CATALOGUE_DATAGO,
    CLASS_AGRICULTURAL_PRODUCTION,
    CLASS_LOCAL_DISH_INVENTORY,
    STATUS_NOT_ASSESSED,
)


def _df(rows: list[dict[str, str]]) -> pd.DataFrame:
    base = {c: "" for c in REQUIRED_COLUMNS}
    return pd.DataFrame([{**base, **r} for r in rows])


def test_validate_columns_raises_on_missing() -> None:
    with pytest.raises(ValueError):
        validate_columns(pd.DataFrame([{"dataset_title_th": "x"}]))


def test_to_catalogue_rows_preserves_province_unmodified() -> None:
    """Task 1: this module never rewrites province — it is carried through as-is,
    the corrected matcher's verdict is a separate report."""
    df = _df(
        [
            {
                "dataset_title_th": "เรือประมงนอกน่านน้ำ และเรือขนถ่ายสัตว์น้ำนอกน่านน้ำ",
                "province": "น่าน",
                "relevance_score": "37",
                "flavormap_layer": "3_ingredient_agri",
            }
        ]
    )
    rows = to_catalogue_rows(df)
    assert rows[0].province_th == "น่าน"  # untouched, not corrected in place


def test_to_catalogue_rows_attaches_score_note_to_every_row() -> None:
    df = _df([{"dataset_title_th": "x", "relevance_score": "7"}])
    rows = to_catalogue_rows(df)
    assert rows[0].score_note == SCORE_NOTE


def test_to_catalogue_rows_classifies_by_content_not_by_layer() -> None:
    """The brief's own finding: 1_dish_culture (270 rows) contains household-fuel
    survey noise. A row in that layer with no food-culture keyword must not inherit
    local_dish_inventory just because of its flavormap_layer."""
    df = _df(
        [
            {
                "dataset_title_th": "ร้อยละของครัวเรือนที่มีการใช้เชื้อเพลิงแข็งในการประกอบอาหาร",
                "flavormap_layer": "1_dish_culture",
                "relevance_score": "7",
            },
            {
                "dataset_title_th": "อาหารพื้นเมืองเพชรบูรณ์",
                "flavormap_layer": "1_dish_culture",
                "relevance_score": "6",
            },
        ]
    )
    rows = to_catalogue_rows(df)
    fuel_row, dish_row = rows[0], rows[1]
    assert fuel_row.content_class != CLASS_LOCAL_DISH_INVENTORY
    assert dish_row.content_class == CLASS_LOCAL_DISH_INVENTORY


def test_to_catalogue_rows_sets_catalogue_source_and_no_slug() -> None:
    df = _df([{"dataset_title_th": "x"}])
    rows = to_catalogue_rows(df)
    assert rows[0].catalogue_source == CATALOGUE_DATAGO
    assert rows[0].dataset_slug is None
    assert rows[0].tier is None


def test_to_catalogue_rows_parses_relevance_score_as_float() -> None:
    df = _df([{"dataset_title_th": "x", "relevance_score": "11.5"}])
    rows = to_catalogue_rows(df)
    assert rows[0].relevance_score == 11.5


def test_to_catalogue_rows_unparseable_score_is_none_not_zero() -> None:
    """A blank or garbled score must not silently become 0 — that would itself be a
    highly-ranked-looking value under a naive sort."""
    df = _df([{"dataset_title_th": "x", "relevance_score": ""}])
    rows = to_catalogue_rows(df)
    assert rows[0].relevance_score is None


def test_agricultural_yield_titles_classify_correctly() -> None:
    """The confirmed top-scoring (29-37) rows are all crop-yield statistics."""
    df = _df(
        [
            {
                "dataset_title_th": "เนื้อที่เพาะปลูกข้าวโพดเลี้ยงสัตว์ เนื้อที่เก็บเกี่ยว ผลผลิต",
                "relevance_score": "37",
                "flavormap_layer": "3_ingredient_agri",
            }
        ]
    )
    rows = to_catalogue_rows(df)
    assert rows[0].content_class == CLASS_AGRICULTURAL_PRODUCTION


def test_row_hash_present_and_stable_without_slug() -> None:
    df = _df([{"dataset_title_th": "x", "direct_resource_url": "https://example.com/a.csv"}])
    rows = to_catalogue_rows(df)
    assert rows[0].row_hash
    # Same inputs -> same hash, deterministic.
    rows2 = to_catalogue_rows(df)
    assert rows[0].row_hash == rows2[0].row_hash


def test_new_rows_default_harvest_status_not_assessed_unless_auto_rejected() -> None:
    df = _df([{"dataset_title_th": "อาหารพื้นเมือง", "province": "กาญจนบุรี"}])
    rows = to_catalogue_rows(df)
    assert rows[0].harvest_status == STATUS_NOT_ASSESSED
