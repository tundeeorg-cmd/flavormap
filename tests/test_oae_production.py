"""`src/ingest/oae_production.py` — province/region validation and the unit-consistency
guard for `flavormap_oae_production.csv`.

Small synthetic fixtures, not the full 482-row file — the real file's own numbers
(77/77 clean provinces, exact region_th match, two production units) are reported by
`scripts/load_crop_production.py --report` and recorded in `docs/decisions.md`.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.ingest.oae_production import (
    REQUIRED_COLUMNS,
    check_unit_consistency,
    row_hash,
    to_num,
    validate_columns,
    validate_provinces,
    validate_regions,
)


def _df(rows: list[dict[str, str]]) -> pd.DataFrame:
    base = {c: "" for c in REQUIRED_COLUMNS}
    return pd.DataFrame([{**base, **r} for r in rows])


def test_validate_columns_raises_on_missing() -> None:
    with pytest.raises(ValueError):
        validate_columns(pd.DataFrame([{"province_th": "x"}]))


def test_validate_provinces_flags_unofficial_value() -> None:
    df = _df([{"province_th": "น่าน"}, {"province_th": "ไม่มีจังหวัดนี้"}])
    report = validate_provinces(df)
    assert report.distinct_provinces == 2
    assert report.invalid_provinces == ("ไม่มีจังหวัดนี้",)


def test_validate_provinces_clean_when_all_official() -> None:
    df = _df([{"province_th": "น่าน"}, {"province_th": "สุรินทร์"}])
    assert validate_provinces(df).invalid_provinces == ()


def test_validate_regions_flags_value_outside_food67_vocabulary() -> None:
    df = _df([{"region_th": "ภาคเหนือ"}, {"region_th": "ภาคเหนือตอนบน"}])
    assert validate_regions(df) == ("ภาคเหนือตอนบน",)


def test_validate_regions_clean_when_matching_food67() -> None:
    df = _df([{"region_th": "ภาคเหนือ"}, {"region_th": "ภาคใต้"}])
    assert validate_regions(df) == ()


def test_check_unit_consistency_flags_commodity_with_mixed_units() -> None:
    """The real trap this guards against: มะพร้าวผลแก่ reports in ผล (fruits) while
    every other commodity reports in ตัน (tonnes). A future year silently mixing units
    within one commodity must not pass silently."""
    df = _df(
        [
            {"commodity_th": "มะพร้าวผลแก่", "production_unit": "ผล"},
            {"commodity_th": "มะพร้าวผลแก่", "production_unit": "ตัน"},
            {"commodity_th": "ข้าว", "production_unit": "ตัน"},
        ]
    )
    violations = check_unit_consistency(df)
    assert len(violations) == 1
    assert violations[0].commodity_th == "มะพร้าวผลแก่"
    assert set(violations[0].units_seen) == {"ผล", "ตัน"}


def test_check_unit_consistency_clean_when_one_unit_per_commodity() -> None:
    df = _df(
        [
            {"commodity_th": "มะพร้าวผลแก่", "production_unit": "ผล"},
            {"commodity_th": "ข้าว", "production_unit": "ตัน"},
            {"commodity_th": "กระเทียม", "production_unit": "ตัน"},
        ]
    )
    assert check_unit_consistency(df) == ()


def test_row_hash_deterministic_and_key_sensitive() -> None:
    a = row_hash("น่าน", "ข้าว", "ข้าวนาปี", "2567")
    b = row_hash("น่าน", "ข้าว", "ข้าวนาปี", "2567")
    c = row_hash("น่าน", "ข้าว", "ข้าวนาปรัง", "2567")
    assert a == b
    assert a != c


def test_to_num_blank_is_none_not_zero() -> None:
    """Sparse area columns are structurally not-applicable, never a fabricated 0
    (rule 2's spirit: an absent value must stay absent)."""
    assert to_num("") is None
    assert to_num("  ") is None
    assert to_num("1234") == 1234.0
