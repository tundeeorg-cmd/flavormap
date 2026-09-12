"""`src/ingest/local_dish_inventory.py` — column drop, dish-name extraction, and the
district-to-province verification.

Fixtures here are built from the brief's own documented shape (8 real columns plus
`Unnamed:` padding; mixed \\r\\n/\\n line endings; the file's own quoted district list)
rather than from the real `อาหารพื้นถิ่น.csv`, which this project does not have a copy
of — see `docs/decisions.md`'s 2026-09-12 note. Nothing here claims to be the real
file's actual row count or dish content.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.ingest.local_dish_inventory import (
    DROPPED_ALWAYS,
    KEEP_COLUMNS,
    PHETCHABURI_DISTRICTS,
    build_report,
    check_districts_are_phetchaburi,
    drop_non_analytical,
    extract_dish_names,
    read_raw,
)

# Column names as the module itself defines them — never retyped as Thai literals
# here. A Thai string typed twice by hand in the same file is exactly how this test
# file first shipped a real bug: SARA AM (ำ, one codepoint) versus the visually
# identical NIKHAHIT+SARA AA sequence (ํ + า, two codepoints) produced two different
# dict keys that both render as "อำเภอ", so an override silently added a second
# column instead of replacing the first. Unicode NFC normalisation does not unify
# them — Thai does not canonically decompose SARA AM — so the fix is to never retype
# the string a second time, not to normalise it.
COL_COMMUNITY, COL_MOO, COL_SUBDISTRICT, COL_DISTRICT, COL_MENU, COL_PRODUCTS = KEEP_COLUMNS
COL_ADDRESS, COL_IMAGE_URL = DROPPED_ALWAYS

#: The brief's own quoted list of the file's eight `อำเภอ` values.
BRIEF_DISTRICTS = (
    "เขาย้อย",
    "บ้านแหลม",
    "ท่ายาง",
    "แก่งกระจาน",
    "เมืองเพชรบุรี",
    "บ้านลาด",
    "ชะอำ",
    "หนองหญ้าปล้อง",
)


# ── district verification ───────────────────────────────────────────────────────

def test_briefs_own_district_list_is_exactly_phetchaburi() -> None:
    """The core factual check Task 1 asks for: do the eight named districts belong
    to Phetchaburi and nowhere else? Phetchaburi has exactly eight districts, so this
    also confirms the brief's list is Phetchaburi's *complete* set, not a subset."""
    assert set(BRIEF_DISTRICTS) == PHETCHABURI_DISTRICTS


def test_check_districts_all_present() -> None:
    result = check_districts_are_phetchaburi(list(BRIEF_DISTRICTS))
    assert result.all_in_phetchaburi
    assert not result.unrecognised
    assert len(result.districts_in_file) == 8


def test_check_districts_flags_an_outsider() -> None:
    """A district from another province must stop the loader, never be guessed past."""
    result = check_districts_are_phetchaburi([*BRIEF_DISTRICTS, "หาดใหญ่"])  # Songkhla
    assert not result.all_in_phetchaburi
    assert "หาดใหญ่" in result.unrecognised


def test_check_districts_ignores_blank_values() -> None:
    result = check_districts_are_phetchaburi(["เขาย้อย", "", "  ", "เขาย้อย"])
    assert result.districts_in_file == ("เขาย้อย",)
    assert result.all_in_phetchaburi


# ── dish-name extraction ─────────────────────────────────────────────────────────

def test_extract_dish_names_crlf() -> None:
    text = "1.ขนมจีนซาวน้ำ\r\n2.แกงส้ม\r\n3.น้ำพริกปลาทู"
    assert extract_dish_names(text) == ["ขนมจีนซาวน้ำ", "แกงส้ม", "น้ำพริกปลาทู"]


def test_extract_dish_names_lf() -> None:
    text = "1.ขนมจีนซาวน้ำ\n2.แกงส้ม\n3.น้ำพริกปลาทู"
    assert extract_dish_names(text) == ["ขนมจีนซาวน้ำ", "แกงส้ม", "น้ำพริกปลาทู"]


def test_extract_dish_names_mixed_line_endings_in_one_field() -> None:
    """The brief is explicit that line endings are mixed ACROSS rows; this also
    covers the harder case of a mix within one field."""
    text = "1.ขนมจีนซาวน้ำ\r\n2.แกงส้ม\n3.น้ำพริกปลาทู\r4.ตาลเชื่อม"
    assert extract_dish_names(text) == [
        "ขนมจีนซาวน้ำ", "แกงส้ม", "น้ำพริกปลาทู", "ตาลเชื่อม",
    ]


def test_extract_dish_names_drops_empty_lines() -> None:
    text = "1.ขนมจีนซาวน้ำ\r\n\r\n2.แกงส้ม\r\n"
    assert extract_dish_names(text) == ["ขนมจีนซาวน้ำ", "แกงส้ม"]


def test_extract_dish_names_thai_numerals() -> None:
    text = "๑.ขนมจีนซาวน้ำ\n๒.แกงส้ม"
    assert extract_dish_names(text) == ["ขนมจีนซาวน้ำ", "แกงส้ม"]


@pytest.mark.parametrize("value", [None, ""])
def test_extract_dish_names_empty_field(value: str | None) -> None:
    assert extract_dish_names(value) == []


def test_extract_dish_names_never_splits_a_slash_alternative() -> None:
    """A dish name may itself contain a slash; extraction must not be confused with
    the alternatives-marker handling in the sibling gdcatalog ingester."""
    text = "1.แกงคั่วปูทะเล/ปูม้า"
    assert extract_dish_names(text) == ["แกงคั่วปูทะเล/ปูม้า"]


# ── column drop ──────────────────────────────────────────────────────────────────

def _fixture_csv(tmp_path: Path, rows: list[dict[str, str]]) -> Path:
    path = tmp_path / "fixture.csv"
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
    return path


def _base_row(
    *,
    community: str = "บ้านทดสอบ",
    moo: str = "1",
    subdistrict: str = "ตำบลทดสอบ",
    district: str = "เขาย้อย",
    menu: str = "1.ขนมจีนซาวน้ำ\r\n2.แกงส้ม",
    products: str = "ขนมหม้อแกง ผ้าบาติก",
) -> dict[str, str]:
    return {
        COL_COMMUNITY: community,
        COL_MOO: moo,
        COL_SUBDISTRICT: subdistrict,
        COL_DISTRICT: district,
        COL_ADDRESS: f"1 หมู่ {moo} {subdistrict} อำเภอ{district} จังหวัดเพชรบุรี",
        COL_MENU: menu,
        COL_PRODUCTS: products,
        COL_IMAGE_URL: "https://pic.in.th/image/fake123",
        "Unnamed: 8": "",
        "Unnamed: 9": "",
    }


def test_keep_columns_whitelisted(tmp_path: Path) -> None:
    path = _fixture_csv(tmp_path, [_base_row()])
    clean, report = drop_non_analytical(read_raw(path))

    assert set(clean.columns) == set(KEEP_COLUMNS)
    assert COL_ADDRESS not in clean.columns
    assert COL_IMAGE_URL not in clean.columns
    assert not any(c.startswith("Unnamed:") for c in clean.columns)
    assert COL_ADDRESS in report.dropped_named
    assert COL_IMAGE_URL in report.dropped_named
    assert set(report.dropped_unnamed) == {"Unnamed: 8", "Unnamed: 9"}


def test_drop_non_analytical_raises_on_missing_keep_column() -> None:
    df = pd.DataFrame([{"ตำบล": "x"}])
    with pytest.raises(ValueError):
        drop_non_analytical(df)


# ── whole-file report ────────────────────────────────────────────────────────────

def test_build_report_counts_dishes_and_communities(tmp_path: Path) -> None:
    rows = [
        _base_row(menu="1.ขนมจีนซาวน้ำ\r\n2.แกงส้ม\r\n3.น้ำพริกปลาทู"),
        _base_row(district="ชะอำ", menu="1.คั่วไก่"),
    ]
    path = _fixture_csv(tmp_path, rows)
    report = build_report(path)

    assert report.total_rows == 2
    assert report.total_dishes == 4
    assert report.district_check.all_in_phetchaburi
    assert not report.empty_menu_rows


def test_build_report_lists_rows_with_zero_dishes_rather_than_dropping_them(
    tmp_path: Path,
) -> None:
    rows = [_base_row(menu="")]
    path = _fixture_csv(tmp_path, rows)
    report = build_report(path)

    assert report.total_rows == 1
    assert report.total_dishes == 0
    assert report.empty_menu_rows == [0]


def test_build_report_flags_a_non_phetchaburi_district(tmp_path: Path) -> None:
    rows = [_base_row(district="หาดใหญ่")]
    path = _fixture_csv(tmp_path, rows)
    report = build_report(path)

    assert not report.district_check.all_in_phetchaburi
    assert "หาดใหญ่" in report.district_check.unrecognised


def test_build_report_keeps_featured_products_raw_and_unclassified(tmp_path: Path) -> None:
    """ผลิตภัณฑ์เด่น is stored verbatim — food and non-food together, no split."""
    rows = [_base_row(products="ขนมหม้อแกง ไข่เค็มสูตรสมุนไพร ผ้าบาติก กรอบรูป ปูนปั้นหัวสัตว์")]
    path = _fixture_csv(tmp_path, rows)
    report = build_report(path)

    assert report.communities[0].featured_products == (
        "ขนมหม้อแกง ไข่เค็มสูตรสมุนไพร ผ้าบาติก กรอบรูป ปูนปั้นหัวสัตว์"
    )
