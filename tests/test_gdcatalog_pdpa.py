"""PDPA: no personal data from `thaitastetherapy.csv` survives parsing.

This is `gdcatalog`'s share of rule 8, and part of the ingester's definition of done
per the brief. `culture.gdcatalog.go.th`'s dataset is worse than the DCP PDFs for
personal data: every row carries a named individual (`ownerprefix`/`ownername`/
`ownersurname`), their address, GPS coordinates of their home or shop to six decimal
places, and two Google Drive links to photos of them and their premises.

All PII values below are INVENTED, never lifted from a real file — this project does
not have a copy of `thaitastetherapy.csv` (see `docs/decisions.md`, 2026-09-12).
Surname `ทดสอบ` ("test") marks every fixture as synthetic, matching the convention
`tests/test_pdpa.py` already uses for the DCP forms.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.ingest.gdcatalog import KEEP_COLUMNS, PII_COLUMNS, build_report, drop_pii, read_raw
from src.ingest.pdpa import find_leaks

FAKE_PREFIX = "นาง"
FAKE_GIVEN = "สมหญิง"
FAKE_SURNAME = "ทดสอบ"
FAKE_ADDRESS = "99/9 หมู่ 6 ตำบลทดสอบ อำเภอเมือง"
FAKE_GPS = "18.796432,100.783211"
FAKE_DRIVE_OWNER = "https://drive.google.com/file/d/FAKE1234567890abcdef/view"
FAKE_DRIVE_PREMISES = "https://drive.google.com/file/d/FAKE0987654321fedcba/view"

FORBIDDEN_STRINGS = (
    FAKE_GIVEN,
    FAKE_SURNAME,
    FAKE_ADDRESS,
    "99/9",
    "หมู่ 6",
    FAKE_GPS,
    FAKE_DRIVE_OWNER,
    FAKE_DRIVE_PREMISES,
    "drive.google.com",
)


def _fixture_csv(tmp_path: Path) -> Path:
    df = pd.DataFrame(
        [
            {
                "ownerprefix": FAKE_PREFIX,
                "ownername": FAKE_GIVEN,
                "ownersurname": FAKE_SURNAME,
                "address": FAKE_ADDRESS,
                "gps": FAKE_GPS,
                "picowner": FAKE_DRIVE_OWNER,
                "picadress": FAKE_DRIVE_PREMISES,
                "region": "ภาคเหนือ",
                "province": "น่าน",
                "foodname": "คั่วไก่",
                "originalfoodname": "คั่วไก่",
                "otherfoodname": "",
                "material": "ไก่ ตะไคร้ ข่า ใบมะกรูด พริก",
            }
        ]
    )
    path = tmp_path / "thaitastetherapy_fixture.csv"
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def test_pii_columns_absent_from_cleaned_frame(tmp_path: Path) -> None:
    clean, report = drop_pii(read_raw(_fixture_csv(tmp_path)))
    assert set(clean.columns) == set(KEEP_COLUMNS)
    for col in PII_COLUMNS:
        assert col not in clean.columns
    assert set(report.pii_columns_present) == set(PII_COLUMNS)


def test_no_pii_value_survives_in_any_serialisation(tmp_path: Path) -> None:
    """Covers the brief's own list: "no name, address, GPS value, or Drive URL
    survives into any table, Parquet file, CSV, or log line" — checked here against
    CSV and JSON, the two forms this parser and its loader actually produce
    (`raw_recipes.parsed_json` is JSON; pyarrow/Parquet is not yet a project
    dependency, so a Parquet round-trip is not exercised here)."""
    clean, _ = drop_pii(read_raw(_fixture_csv(tmp_path)))

    csv_text = clean.to_csv(index=False)
    json_text = clean.to_json(orient="records", force_ascii=False)

    for forbidden in FORBIDDEN_STRINGS:
        assert forbidden not in csv_text, f"leaked into CSV: {forbidden!r}"
        assert forbidden not in json_text, f"leaked into JSON: {forbidden!r}"

    for text in (csv_text, json_text):
        leaks = find_leaks(text)
        assert not leaks, f"pdpa leak detector found: {leaks}"


def test_build_report_records_never_carry_pii(tmp_path: Path) -> None:
    """The report is what a loader writes to raw_recipes.parsed_json — the log-line
    and JSONB-blob half of rule 8."""
    report = build_report(_fixture_csv(tmp_path))
    for record in report.parsed + report.unparsed:
        serialised = repr(record)
        for forbidden in FORBIDDEN_STRINGS:
            assert forbidden not in serialised, f"leaked into a record: {forbidden!r}"
        leaks = find_leaks(serialised)
        assert not leaks, f"pdpa leak detector found in a record: {leaks}"


@pytest.mark.parametrize(
    "poisoned",
    [
        f"พิกัด {FAKE_GPS} ใกล้ตลาด",
        f"ดูรูปได้ที่ {FAKE_DRIVE_OWNER}",
    ],
)
def test_leak_detector_catches_gps_and_drive_shapes_in_kept_text(poisoned: str) -> None:
    """Defense in depth for the two classes this source specifically introduces: even
    if PII-shaped text ended up inside a column this project does keep (`material`
    is free text and is never validated against this shape), the shared detector
    must still catch it."""
    leaks = find_leaks(poisoned)
    assert leaks, f"no leak detected in {poisoned!r}"
