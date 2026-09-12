"""PDPA: confirm `อาหารพื้นถิ่น.csv`'s lighter-but-not-zero exposure is actually zero
after parsing.

Per the brief: no individual names appear anywhere in this file (confirmed across all
rows, not assumed), `Url รูปภาพ` (a third-party image host link) is dropped without
ever being fetched, and `ที่อยู่` (a village-level, non-personal address) is dropped
rather than partially trusted even though it is "safe" on its own.

All fixture values are invented, never lifted from a real file — this project does
not have a copy of `อาหารพื้นถิ่น.csv` (see `docs/decisions.md`, 2026-09-12).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.ingest.local_dish_inventory import (
    KEEP_COLUMNS,
    build_report,
    drop_non_analytical,
    read_raw,
)
from src.ingest.pdpa import find_leaks

FAKE_DRIVE_STYLE_IMAGE_URL = "https://pic.in.th/image/fake-photo-abc123.html"
FAKE_ADDRESS = "12 หมู่ 3 ตำบลทดสอบ อำเภอเขาย้อย จังหวัดเพชรบุรี"


def _fixture_csv(tmp_path: Path) -> Path:
    df = pd.DataFrame(
        [
            {
                "ชุมชน/หมู่บ้าน": "บ้านทดสอบ",
                "หมู่ที่": "3",
                "ตำบล": "ตำบลทดสอบ",
                "อำเภอ": "เขาย้อย",
                "ที่อยู่": FAKE_ADDRESS,
                "เมนูอาหารพื้นถิ่น": "1.ขนมจีนซาวน้ำ\r\n2.แกงส้ม",
                "ผลิตภัณฑ์เด่น": "ขนมหม้อแกง ผ้าบาติก",
                "Url รูปภาพ": FAKE_DRIVE_STYLE_IMAGE_URL,
                "Unnamed: 8": "",
            }
        ]
    )
    path = tmp_path / "อาหารพื้นถิ่น_fixture.csv"
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def test_address_and_image_url_columns_absent_from_cleaned_frame(tmp_path: Path) -> None:
    clean, report = drop_non_analytical(read_raw(_fixture_csv(tmp_path)))
    assert set(clean.columns) == set(KEEP_COLUMNS)
    assert "ที่อยู่" not in clean.columns
    assert "Url รูปภาพ" not in clean.columns
    assert "ที่อยู่" in report.dropped_named
    assert "Url รูปภาพ" in report.dropped_named


def test_no_address_or_image_url_value_survives_serialisation(tmp_path: Path) -> None:
    clean, _ = drop_non_analytical(read_raw(_fixture_csv(tmp_path)))
    csv_text = clean.to_csv(index=False)
    json_text = clean.to_json(orient="records", force_ascii=False)

    for forbidden in (FAKE_ADDRESS, "12 หมู่ 3", FAKE_DRIVE_STYLE_IMAGE_URL, "pic.in.th"):
        assert forbidden not in csv_text, f"leaked into CSV: {forbidden!r}"
        assert forbidden not in json_text, f"leaked into JSON: {forbidden!r}"


def test_build_report_records_never_carry_the_address_or_image_url(tmp_path: Path) -> None:
    report = build_report(_fixture_csv(tmp_path))
    for community in report.communities:
        serialised = repr(community)
        assert FAKE_ADDRESS not in serialised
        assert FAKE_DRIVE_STYLE_IMAGE_URL not in serialised
        assert "pic.in.th" not in serialised


def test_leak_detector_still_fires_if_a_name_appeared() -> None:
    """Defense in depth: the brief says no names appear in this file, and this
    module has no dedicated stripper for it (there is nothing to strip from). If a
    name ever did end up in a kept field, the shared detector must still catch it.

    `pic.in.th` links are handled separately (`test_no_address_or_image_url_value_
    survives_serialisation` above) by direct string absence, not by this detector:
    `find_leaks`'s `drive_url` class is specific to `drive.google.com` /
    `docs.google.com` — the shape `gdcatalog`'s *other* file's `picowner`/`picadress`
    columns carry — and a blanket bare-URL pattern was deliberately not added to it,
    because `sources.base_url` legitimately stores URLs and a blanket pattern would
    flag that column as a false leak.
    """
    leaks = find_leaks("ติดต่อ นางสาวสมหญิง ทดสอบ")
    assert leaks, "no leak detected in a fixture containing an honorific + name"
