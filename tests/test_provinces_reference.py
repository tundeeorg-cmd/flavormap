"""`data/reference/provinces.csv`'s `region6` column — HD-23's decided
canonicalisation target (migration 029).

The food67 cross-check is conditional on the real file, which is gitignored raw data
(`data/raw/`) and won't exist on a fresh clone or in CI — see `test_checkboxes.py` for
the same pattern. The two unconditional tests below don't need it: they check the
tracked CSV's own internal consistency, which is what actually needs to hold for every
clone of this repo.
"""

from __future__ import annotations

import csv

import pytest

from src.config import RAW_DIR, REFERENCE_DIR

VALID_REGION6 = {
    "ภาคกลาง", "ภาคตะวันตก", "ภาคตะวันออก",
    "ภาคตะวันออกเฉียงเหนือ", "ภาคเหนือ", "ภาคใต้",
}

REGION4_TO_REGION6 = {
    "Northeast": "ภาคตะวันออกเฉียงเหนือ",
    "South": "ภาคใต้",
    # North and Central are deliberately absent from this map -- see
    # NORTH_REGION4_EXCEPTIONS below. Central splits into ภาคกลาง/ภาคตะวันตก/
    # ภาคตะวันออก under the six-way scheme with no single matching region6 value at
    # all, so it was never a candidate for this equality check.
}

#: Confirmed from flavormap_food67.csv's own real data, not an assumption: these five
#: "lower North" provinces carry region4='North' but food67 itself places them in
#: ภาคกลาง (four) or ภาคตะวันตก (Tak) -- food67's six-way scheme does not nest
#: cleanly inside region4 the way HD-23's original text assumed it would outside
#: Central. Discovered by this test failing against real data, not designed in.
NORTH_REGION4_EXCEPTIONS: dict[str, str] = {
    "Nakhon Sawan": "ภาคกลาง",
    "Uthai Thani": "ภาคกลาง",
    "Phitsanulok": "ภาคกลาง",
    "Phichit": "ภาคกลาง",
    "Tak": "ภาคตะวันตก",
}


def _read_provinces() -> list[dict[str, str]]:
    with (REFERENCE_DIR / "provinces.csv").open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_region6_populated_and_valid_for_all_77() -> None:
    rows = _read_provinces()
    assert len(rows) == 77
    assert all(r["region6"] for r in rows)
    invalid = [r["name_en"] for r in rows if r["region6"] not in VALID_REGION6]
    assert invalid == []


def test_region6_agrees_with_region4_for_northeast_and_south() -> None:
    """Unlike North (see the next test), every Northeast and South province's
    region6 matches region4 exactly -- confirmed against real food67 data, zero
    exceptions."""
    rows = _read_provinces()
    mismatches = [
        (r["name_en"], r["region4"], r["region6"])
        for r in rows
        if r["region4"] in REGION4_TO_REGION6 and r["region6"] != REGION4_TO_REGION6[r["region4"]]
    ]
    assert mismatches == []


def test_region6_north_exceptions_are_exactly_the_confirmed_five() -> None:
    """region4='North' provinces split between ภาคเหนือ and the five confirmed
    exceptions above -- nothing else. A province moving in or out of either bucket is
    exactly the kind of silent scheme drift this test exists to catch."""
    rows = _read_provinces()
    north_rows = {r["name_en"]: r["region6"] for r in rows if r["region4"] == "North"}
    for name, region6 in north_rows.items():
        expected = NORTH_REGION4_EXCEPTIONS.get(name, "ภาคเหนือ")
        assert region6 == expected, f"{name}: expected {expected!r}, got {region6!r}"
    assert set(NORTH_REGION4_EXCEPTIONS) <= set(north_rows)


FOOD67_CSV = RAW_DIR / "gdcatalog" / "flavormap_food67.csv"


@pytest.mark.skipif(not FOOD67_CSV.exists(), reason="food67 raw file not present")
def test_region6_matches_food67_for_covered_provinces() -> None:
    """The 48 provinces food67 actually states a region for must match verbatim --
    this is the real source region6 was calibrated against, not an inference."""
    provinces = {r["name_th"]: r["region6"] for r in _read_provinces()}
    with FOOD67_CSV.open(encoding="utf-8-sig", newline="") as f:
        food67 = list(csv.DictReader(f))
    food67_map = {
        r["province_th"].strip(): r["region_th"].strip()
        for r in food67
        if r["province_th"].strip()
    }
    mismatches = [
        (prov, food67_region, provinces[prov])
        for prov, food67_region in food67_map.items()
        if provinces.get(prov) != food67_region
    ]
    assert mismatches == []
