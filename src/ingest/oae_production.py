"""Parse `flavormap_oae_production.csv` — crop production statistics from
สำนักงานเศรษฐกิจการเกษตร (OAE), 482 rows, 77 provinces, 11 commodities, years 2567/2568.

Supporting data only (docs/decisions.md, 2026-09-12 entry): it answers no research
question and backs no figure. Its job is a lexicon cross-reference and a Nan/Surin
interview-prep fact sheet. Keep this module correspondingly small — no aggregation
helpers, no analysis code.

**Task 1b — the province column is clean, unlike `flavormap_datago_catalog.csv`.**
That file's `province` is derived by substring match against free-text titles and
picks up traps like น่าน matching inside น่านน้ำ (`thai_province_match.py`'s whole
reason for existing). This file's `province_th` is a structured field: exactly 77
distinct values, all 77 validated against `data/reference/provinces.csv` with zero
mismatches. `validate_provinces` reuses `thai_province_match.official_provinces()`
rather than re-deriving the list, but does not need the trap/token machinery that
module built for text-derived province columns — there is no text to match against
here, only membership to check.

**Task 1c — region_th matches `flavormap_food67.csv` exactly.** Same six values
(ภาคกลาง/ภาคตะวันตก/ภาคตะวันออก/ภาคตะวันออกเฉียงเหนือ/ภาคเหนือ/ภาคใต้), confirmed by
set comparison against the real food67 file, not assumed.

**Task 2a — the unit trap.** `production_unit` is `'ตัน'` (tonnes) for every commodity
except มะพร้าวผลแก่ (mature coconut), which is `'ผล'` (individual fruits).
`check_unit_consistency` asserts one unit per commodity across the loaded rows — a
guard against future years silently introducing a mixed-unit commodity, not a
guarantee that summing is ever safe (it never is; see migration 028's own comment).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.ingest.thai_province_match import official_provinces

REQUIRED_COLUMNS: tuple[str, ...] = (
    "province_th",
    "region_th",
    "commodity_th",
    "subcommodity_th",
    "year_be",
    "year_ce",
    "planted_area_rai",
    "standing_area_rai",
    "harvested_area_rai",
    "bearing_area_rai",
    "tapped_area_rai",
    "production",
    "production_unit",
    "yield_per_rai",
    "yield_unit",
    "yield_basis",
    "source_dataset",
)

#: food67's own distinct region_th values, confirmed identical to this source's
#: (Task 1c). Kept as a literal rather than re-reading food67 at import time — this
#: module has no reason to depend on that file being present.
FOOD67_REGIONS: frozenset[str] = frozenset(
    {
        "ภาคกลาง",
        "ภาคตะวันตก",
        "ภาคตะวันออก",
        "ภาคตะวันออกเฉียงเหนือ",
        "ภาคเหนือ",
        "ภาคใต้",
    }
)

#: Which area column is valid for which yield_basis (Task 2b). Never treat the other
#: area columns as missing data for a given basis — they are structurally not
#: applicable, not unobserved.
AREA_COLUMN_BY_YIELD_BASIS: dict[str, tuple[str, str]] = {
    "harvested": ("planted_area_rai", "harvested_area_rai"),
    "bearing": ("standing_area_rai", "bearing_area_rai"),
    "tapped": ("standing_area_rai", "tapped_area_rai"),
}


def read_raw(path: Path) -> pd.DataFrame:
    """UTF-8 with a BOM, same as every other gdcatalog-family source."""
    return pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)


def validate_columns(df: pd.DataFrame) -> None:
    missing = tuple(c for c in REQUIRED_COLUMNS if c not in df.columns)
    if missing:
        raise ValueError(f"expected column(s) missing from source CSV: {missing}")


@dataclass(frozen=True)
class ProvinceValidationReport:
    total_rows: int
    distinct_provinces: int
    invalid_provinces: tuple[str, ...]  # values not in the official 77


def validate_provinces(df: pd.DataFrame) -> ProvinceValidationReport:
    official = official_provinces()
    values = set(df["province_th"])
    invalid = tuple(sorted(v for v in values if v not in official))
    return ProvinceValidationReport(
        total_rows=len(df), distinct_provinces=len(values), invalid_provinces=invalid
    )


def validate_regions(df: pd.DataFrame) -> tuple[str, ...]:
    """Returns any region_th value NOT in food67's own vocabulary. Empty means an
    exact match — one fewer mapping problem, per the brief."""
    values = set(df["region_th"])
    return tuple(sorted(values - FOOD67_REGIONS))


@dataclass(frozen=True)
class UnitConsistencyViolation:
    commodity_th: str
    units_seen: tuple[str, ...]


def check_unit_consistency(df: pd.DataFrame) -> tuple[UnitConsistencyViolation, ...]:
    """Asserts exactly one production_unit per commodity_th. Empty result means the
    guard held. This does not make cross-commodity aggregation safe — it only catches
    a commodity silently switching units between rows, which SUM(production) would
    hide even after grouping by commodity_th alone."""
    violations = []
    for commodity, group in df.groupby("commodity_th"):
        units = tuple(sorted(group["production_unit"].unique()))
        if len(units) > 1:
            violations.append(UnitConsistencyViolation(commodity, units))
    return tuple(violations)


def row_hash(province_th: str, commodity_th: str, subcommodity_th: str, year_be: str) -> str:
    """Natural key (province, commodity, subcommodity, year) is confirmed unique
    across all 482 real rows — no dataset_slug or resource_url exists in this source
    to hash on instead."""
    basis = f"{province_th}|{commodity_th}|{subcommodity_th}|{year_be}"
    return hashlib.sha256(basis.encode()).hexdigest()


def to_num(value: str) -> float | None:
    v = value.strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None
