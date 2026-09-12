"""`src/ingest/gdcatalog.py` — column whitelist and `material` format handling.

Fixtures here are built from the brief's own documented shape (16 columns; three
observed `material` formats; the file's three Nan dishes) rather than from the real
`thaitastetherapy.csv`, which this project does not have a copy of — see
`docs/decisions.md`'s 2026-09-12 infrastructure note. Nothing here is a claim about
the real file's actual row count, format distribution, or ingredient content.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.ingest.gdcatalog import (
    FORMAT_CLEAN_LIST,
    FORMAT_EMPTY,
    FORMAT_NUMBERED_LIST,
    FORMAT_PROSE,
    KEEP_COLUMNS,
    PII_COLUMNS,
    build_report,
    classify_material,
    drop_pii,
    extract_ingredients,
    read_raw,
)

CLEAN_EXAMPLE = "ถั่วแปป กระเทียม หอมแดง เกลือ พริก"
NUMBERED_EXAMPLE = "1.หอม 2.กระเทียม 3.ตะไคร้/ข่า 4.ปลา 5.มะขามเปียก"

# Illustrative only, built from the brief's description (full prose, ingredients
# embedded in narrative, literal backslash-n sequences) — not lifted from the real file.
PROSE_EXAMPLE = (
    "นำไก่มาหั่นเป็นชิ้นพอคำ\\nใส่ตะไคร้ ข่า ใบมะกรูดที่หั่นแล้วลงไปคั่วให้หอม\\n"
    "ปรุงรสด้วยน้ำปลาและพริกป่นตามชอบแล้วจึงยกลง"
)

#: The file's three Nan dishes, named directly in the brief — used here only to
#: exercise dish-name handling, never as a stand-in for the file's ingredient content.
NAN_DISHES = ("คั่วไก่", "ตำถั่วแปป", "แกงสะแล")


# ── material format classification ─────────────────────────────────────────────

def test_classify_clean_list() -> None:
    assert classify_material(CLEAN_EXAMPLE) == FORMAT_CLEAN_LIST


def test_classify_numbered_list() -> None:
    assert classify_material(NUMBERED_EXAMPLE) == FORMAT_NUMBERED_LIST


def test_classify_prose() -> None:
    assert classify_material(PROSE_EXAMPLE) == FORMAT_PROSE


@pytest.mark.parametrize("value", [None, "", "   "])
def test_classify_empty(value: str | None) -> None:
    assert classify_material(value) == FORMAT_EMPTY


def test_classify_long_field_is_prose_even_without_a_marker() -> None:
    long_no_stop = ("ไก่ " * 250).strip()  # 750+ chars, no full stop, no \n
    assert len(long_no_stop) > 400
    assert classify_material(long_no_stop) == FORMAT_PROSE


# ── extraction ───────────────────────────────────────────────────────────────────

def test_extract_clean_list() -> None:
    result = extract_ingredients(CLEAN_EXAMPLE)
    assert result.format == FORMAT_CLEAN_LIST
    assert result.items == ["ถั่วแปป", "กระเทียม", "หอมแดง", "เกลือ", "พริก"]


def test_extract_numbered_list() -> None:
    result = extract_ingredients(NUMBERED_EXAMPLE)
    assert result.format == FORMAT_NUMBERED_LIST
    assert result.items == ["หอม", "กระเทียม", "ตะไคร้/ข่า", "ปลา", "มะขามเปียก"]


def test_extract_numbered_list_keeps_alternatives_as_one_token() -> None:
    """"ตะไคร้/ข่า" (lemongrass OR galangal) is an alternatives marker. Splitting it
    into two ingredients is an ingredient-segmentation judgment call — flagged in
    docs/decisions.md, not decided by this parser."""
    result = extract_ingredients(NUMBERED_EXAMPLE)
    assert "ตะไคร้/ข่า" in (result.items or [])
    assert "ตะไคร้" not in (result.items or [])
    assert "ข่า" not in (result.items or [])


def test_extract_prose_is_reported_not_guessed() -> None:
    result = extract_ingredients(PROSE_EXAMPLE)
    assert result.format == FORMAT_PROSE
    assert result.items is None
    assert result.note


def test_extract_empty() -> None:
    result = extract_ingredients("")
    assert result.format == FORMAT_EMPTY
    assert result.items == []


# ── column whitelist ───────────────────────────────────────────────────────────

def _fixture_csv(tmp_path: Path, rows: list[dict[str, str]]) -> Path:
    path = tmp_path / "fixture.csv"
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
    return path


def _base_row(**overrides: str) -> dict[str, str]:
    row = {
        "ownerprefix": "นาง",
        "ownername": "ก",
        "ownersurname": "ทดสอบ",
        "address": "1 หมู่ 1",
        "gps": "18.000000,100.000000",
        "picowner": "https://drive.google.com/file/d/x/view",
        "picadress": "https://drive.google.com/file/d/y/view",
        "region": "ภาคเหนือ",
        "province": "น่าน",
        "foodname": "",
        "originalfoodname": "",
        "otherfoodname": "",
        "material": "",
    }
    row.update(overrides)
    return row


def test_keep_columns_are_whitelisted(tmp_path: Path) -> None:
    path = _fixture_csv(tmp_path, [_base_row(foodname=NAN_DISHES[0], material=CLEAN_EXAMPLE)])
    clean, report = drop_pii(read_raw(path))

    assert set(clean.columns) == set(KEEP_COLUMNS)
    for col in PII_COLUMNS:
        assert col not in clean.columns
    assert set(report.pii_columns_present) == set(PII_COLUMNS)
    assert not report.pii_columns_missing


def test_drop_pii_raises_rather_than_guesses_on_schema_drift() -> None:
    """A CSV missing one of the six analytical columns is refused, not silently
    loaded with a hole in it."""
    df = pd.DataFrame([{"region": "ภาคเหนือ", "province": "น่าน"}])
    with pytest.raises(ValueError):
        drop_pii(df)


def test_build_report_never_carries_pii_columns_on_any_row(tmp_path: Path) -> None:
    rows = [
        _base_row(foodname=NAN_DISHES[0], material=CLEAN_EXAMPLE),
        _base_row(foodname=NAN_DISHES[1], material=NUMBERED_EXAMPLE),
        _base_row(foodname=NAN_DISHES[2], material=PROSE_EXAMPLE),
    ]
    path = _fixture_csv(tmp_path, rows)
    report = build_report(path)

    assert report.total_rows == 3
    for record in report.parsed + report.unparsed:
        for pii_col in PII_COLUMNS:
            assert pii_col not in record


def test_build_report_holds_out_prose_rows_without_dropping_them(tmp_path: Path) -> None:
    rows = [
        _base_row(foodname=NAN_DISHES[0], material=CLEAN_EXAMPLE),
        _base_row(foodname=NAN_DISHES[2], material=PROSE_EXAMPLE),
    ]
    path = _fixture_csv(tmp_path, rows)
    report = build_report(path)

    assert report.total_rows == 2
    assert len(report.parsed) == 1
    assert len(report.unparsed) == 1
    assert report.unparsed[0]["foodname"] == NAN_DISHES[2]
    # The row is listed, not discarded — its raw material text is still there for
    # hand review.
    assert report.unparsed[0]["material_raw"] == PROSE_EXAMPLE


def test_build_report_carries_raw_region_string_unmapped(tmp_path: Path) -> None:
    """Region mapping is an open decision gate (docs/decisions.md) — the report must
    surface the source's raw string, never a collapsed/guessed canonical region."""
    rows = [_base_row(region="ภาคกลางและตะวันออก", foodname=NAN_DISHES[0], material=CLEAN_EXAMPLE)]
    path = _fixture_csv(tmp_path, rows)
    report = build_report(path)
    assert report.distinct_regions == ["ภาคกลางและตะวันออก"]
