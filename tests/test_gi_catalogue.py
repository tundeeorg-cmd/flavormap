"""`src/ingest/gi_catalogue.py` — GI registrant-vs-product safety classification.

Every title here is real: found in `flavormap_datago_catalog.csv` /
`flavormap_gdcatalog_sources_full.csv` (this project has real copies — see
`docs/decisions.md`) among the 61 distinct GI-classified dataset titles across both
catalogues.
"""

from __future__ import annotations

import pytest

from src.ingest.gi_catalogue import extract_likely_product_name, is_registrant_level

# The brief's own two named examples.
BRIEF_EXAMPLES_REGISTRANT = (
    "ผู้ขอใช้ตราสิ่งบ่งชี้ทางภูมิศาสตร์ข้าวหอมมะลิสุรินทร์",
    "ผู้ผลิตที่ใช้ตราสิ่งบ่งชี้ทางภูมิศาสตร์ข้าวหอมมะลิทุ่งกุลาร้องไห้",
)

# Additional real titles the brief's own two-phrase filter would have missed.
WIDER_REGISTRANT_EXAMPLES = (
    "ผู้ประกอบการที่ขอใช้ตราสัญลักษณ์สิ่งบ่งชี้ทางภูมิศาสตร์",
    "ผู้ปลูกส้มโอทับทิมสยาม อำเภอปากพนัง ที่ขอใช้ตรา GI Geographical Indications",
    "ผู้ได้รับหนังสืออนุญาตให้ใช้ตราสัญลักษณ์สิ่งบ่งชี้ทางภูมิศาสตร์ไทย(GI) สินค้ามังคุดเขาคีรีวง",
    "รายชื่อผู้ที่ได้รับหนังสืออนุญาตให้ใช้ตราสัญลักษณ์สิ่งบ่งชี้ทางภูมิศาสตร์ (GI) ส้มโอทับทิมสยามปากพนัง",
    "เกษตรกรที่ขอขึ้นทะเบียนสิ่งบ่งชี้ทางภูมิศาสตร์(GI ทุเรียนภูเขาไฟ)",
)

# Real titles that must NOT be flagged — aggregates/statistics/product designations.
SAFE_EXAMPLES = (
    "จำนวนผู้ได้รับการอนุญาตใช้ตราสัญลักษณ์ GI ทุเรียน",  # a COUNT of registrants, not a list
    "ตราสัญลักษณ์ GI ข้าวไร่ดอกข่า",
    "สถิติการขึ้นทะเบียนสิ่งบ่งชี้ทางภูมิศาสตร์",
    "มูลค่าการจำหน่ายมะพร้าวน้ำหอม GI",
    "ข้าวหอมมะลิดินภูเขาไฟ สู่การรับรองสิ่งบ่งชี้ทางภูมิศาสตร์",
    "พื้นที่ปลูกทุเรียนที่ได้ขึ้นทะเบียนสิ่งบ่งชี้ทางภูมิศาสตร์ (GI ทุเรียนภูเขาไฟ)",
)


@pytest.mark.parametrize("title", BRIEF_EXAMPLES_REGISTRANT)
def test_briefs_own_examples_are_registrant_level(title: str) -> None:
    assert is_registrant_level(title) is True


@pytest.mark.parametrize("title", WIDER_REGISTRANT_EXAMPLES)
def test_wider_registrant_shapes_the_briefs_own_two_phrases_would_have_missed(title: str) -> None:
    assert is_registrant_level(title) is True


@pytest.mark.parametrize("title", SAFE_EXAMPLES)
def test_aggregates_and_product_designations_are_not_registrant_level(title: str) -> None:
    assert is_registrant_level(title) is False


def test_aggregate_marker_overrides_a_registrant_marker() -> None:
    """"จำนวนผู้..." (the NUMBER who...) contains "ผู้ได้รับ"-shaped text but is a
    count, not a list — the aggregate marker must win."""
    assert is_registrant_level("จำนวนผู้ได้รับการอนุญาตใช้ตราสัญลักษณ์ GI ทุเรียน") is False


def test_empty_title_is_not_registrant_level() -> None:
    assert is_registrant_level("") is False


# ── product name extraction (best-effort, human-confirmed) ────────────────────────

def test_extract_product_name_from_khor_use_example() -> None:
    result = extract_likely_product_name("ผู้ขอใช้ตราสิ่งบ่งชี้ทางภูมิศาสตร์ข้าวหอมมะลิสุรินทร์")
    assert result == "ข้าวหอมมะลิสุรินทร์"


def test_extract_product_name_from_phu_use_example() -> None:
    result = extract_likely_product_name(
        "ผู้ผลิตที่ใช้ตราสิ่งบ่งชี้ทางภูมิศาสตร์ข้าวหอมมะลิทุ่งกุลาร้องไห้"
    )
    assert result == "ข้าวหอมมะลิทุ่งกุลาร้องไห้"


def test_extract_product_name_returns_none_when_no_known_prefix() -> None:
    assert extract_likely_product_name("มูลค่าการจำหน่ายมะพร้าวน้ำหอม GI") is None
