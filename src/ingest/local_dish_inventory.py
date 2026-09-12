"""Parse a gdcatalog community dish-name survey (`อาหารพื้นถิ่น.csv`-shaped file).

Structurally distinct from `thaitastetherapy.csv` (`src/ingest/gdcatalog.py`) and
never loaded into the same table: one row per community/village, listing many dish
**names** with no ingredients at all. Written against the Phetchaburi file's
documented shape — 30 rows, 8 real columns plus `Unnamed:` padding, UTF-8 with a BOM,
~150 dish names total in one numbered-list column.

**Columns dropped, always.**

``Unnamed: *``
    Empty artifacts of however the source spreadsheet was exported. Never analytical.

``Url รูปภาพ``
    A link to `pic.in.th`, a third-party image host. Rule 8's spirit extends here even
    though it is not a name or address: never fetched, cached, or stored.

``ที่อยู่``
    A free-text village-level address. The brief confirms it is not a private
    residence and is safe to derive district/subdistrict from — but the file already
    carries that same information in structured form (``ตำบล``, ``อำเภอ``), so nothing
    needs to be parsed out of it. It is dropped rather than partially trusted.

**No individual names appear in this file** per the brief. This module does not
implement name-detection the way `src/ingest/pdpa.py` does for the DCP forms, because
there is no name-bearing field here to strip from in the first place — confirming
that holds is a test's job (`tests/test_local_dish_inventory_pdpa.py`), run against
this module's output using the same shared leak detector every other source uses.

**Dish-name extraction from `เมนูอาหารพื้นถิ่น`.** A numbered list, one dish per line,
with mixed ``\\r\\n`` / ``\\n`` line endings across rows. :func:`extract_dish_names`
splits on any of them, strips a leading ``N.`` marker, and drops empty lines. No
ingredient word is ever extracted from a dish name, even though several plainly
contain one (ปลาทู, ตาล, ชะคราม) — flagged in `docs/decisions.md` as a separate,
undecided step, not performed here.

**`ผลิตภัณฑ์เด่น`** is stored verbatim in its own column, mixed food and non-food
alike. Classifying the two is an explicit decision gate (`docs/decisions.md`), not
this module's call.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

SOURCE_PROGRAMME = "local_food_survey"

#: Columns this module keeps, by name — the file's structured sub-provincial fields,
#: the dish-name list, and the mixed featured-products field.
KEEP_COLUMNS: tuple[str, ...] = (
    "ชุมชน/หมู่บ้าน",
    "หมู่ที่",
    "ตำบล",
    "อำเภอ",
    "เมนูอาหารพื้นถิ่น",
    "ผลิตภัณฑ์เด่น",
)

#: Named columns dropped unconditionally, distinct from the `Unnamed:` padding
#: (matched by prefix in :func:`drop_non_analytical`).
DROPPED_ALWAYS: tuple[str, ...] = (
    "ที่อยู่",
    "Url รูปภาพ",
)

#: Phetchaburi's complete, official set of districts (8 of 8). Used only to verify the
#: brief's own claim that every `อำเภอ` value in the file belongs to this one
#: province — a check performed every time this runs, not trusted from one hand-check.
PHETCHABURI_DISTRICTS = frozenset(
    {
        "เขาย้อย",
        "บ้านแหลม",
        "ท่ายาง",
        "แก่งกระจาน",
        "เมืองเพชรบุรี",
        "บ้านลาด",
        "ชะอำ",
        "หนองหญ้าปล้อง",
    }
)


def _is_unnamed(column: str) -> bool:
    return column.startswith("Unnamed:")


@dataclass
class DropReport:
    source_columns: tuple[str, ...]
    kept_columns: tuple[str, ...]
    dropped_unnamed: tuple[str, ...]
    dropped_named: tuple[str, ...]


def read_raw(path: Path) -> pd.DataFrame:
    """UTF-8 with a BOM — same reason as `thaitastetherapy.csv`
    (`src/ingest/gdcatalog.py`): plain `"utf-8"` leaves the mark attached to the first
    column's first value."""
    return pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)


def drop_non_analytical(df: pd.DataFrame) -> tuple[pd.DataFrame, DropReport]:
    """Keep only :data:`KEEP_COLUMNS`. Raises if one of them is missing rather than
    silently loading a hole in the schema."""
    missing = tuple(c for c in KEEP_COLUMNS if c not in df.columns)
    if missing:
        raise ValueError(
            f"expected column(s) missing from source CSV, refusing to guess: {missing}"
        )
    clean = df[list(KEEP_COLUMNS)].copy()
    report = DropReport(
        source_columns=tuple(df.columns),
        kept_columns=KEEP_COLUMNS,
        dropped_unnamed=tuple(c for c in df.columns if _is_unnamed(c)),
        dropped_named=tuple(c for c in DROPPED_ALWAYS if c in df.columns),
    )
    return clean, report


# ── dish-name extraction ──────────────────────────────────────────────────────────

#: Any of CRLF, bare CR, or bare LF — the file mixes conventions across rows.
_LINE_SPLIT = re.compile(r"\r\n|\r|\n")
#: A numbered-list marker: Arabic or Thai digits, one to three of them, then "." or
#: ")". Anchored to the start of the (already-split) line.
_LEADING_NUMBER = re.compile(r"^\s*[0-9๐-๙]{1,3}[.)]\s*")


def extract_dish_names(text: str | None) -> list[str]:
    """One community's `เมนูอาหารพื้นถิ่น` field -> its list of dish names.

    Empty lines are dropped, never counted as a dish — including the trailing blank a
    final line break produces. A line with no leading number still counts as a dish
    if it survives stripping; nothing here requires every line to be numbered.
    """
    if not text:
        return []
    names = []
    for line in _LINE_SPLIT.split(text):
        cleaned = _LEADING_NUMBER.sub("", line).strip()
        if cleaned:
            names.append(cleaned)
    return names


@dataclass
class DistrictCheck:
    districts_in_file: tuple[str, ...]
    all_in_phetchaburi: bool
    unrecognised: tuple[str, ...]


def check_districts_are_phetchaburi(districts: list[str]) -> DistrictCheck:
    """Verify, don't assume, that every `อำเภอ` value belongs to Phetchaburi — rule
    2's spirit applied to a province inferred from geography rather than stated
    outright. Runs every time this module does, not just once by hand.
    """
    distinct = tuple(sorted({d.strip() for d in districts if d and d.strip()}))
    unrecognised = tuple(d for d in distinct if d not in PHETCHABURI_DISTRICTS)
    return DistrictCheck(
        districts_in_file=distinct,
        all_in_phetchaburi=not unrecognised,
        unrecognised=unrecognised,
    )


@dataclass
class CommunityRecord:
    row: int
    community: str
    moo: str
    subdistrict: str
    district: str
    dish_names: list[str]
    featured_products: str


@dataclass
class IngestReport:
    total_rows: int
    total_dishes: int
    district_check: DistrictCheck
    communities: list[CommunityRecord]
    empty_menu_rows: list[int]
    drop_report: DropReport


def build_report(path: Path) -> IngestReport:
    """Read, column-drop, verify districts, and extract dish names — the full pass
    over one community-survey CSV. A row whose menu field yields zero dishes is
    listed in `empty_menu_rows`, never silently absent from the count.
    """
    raw = read_raw(path)
    clean, drop_report = drop_non_analytical(raw)

    communities: list[CommunityRecord] = []
    empty_menu_rows: list[int] = []
    total_dishes = 0

    for idx, row in clean.iterrows():
        dishes = extract_dish_names(row["เมนูอาหารพื้นถิ่น"])
        if not dishes:
            empty_menu_rows.append(int(idx))
        total_dishes += len(dishes)
        communities.append(
            CommunityRecord(
                row=int(idx),
                community=row["ชุมชน/หมู่บ้าน"],
                moo=row["หมู่ที่"],
                subdistrict=row["ตำบล"],
                district=row["อำเภอ"],
                dish_names=dishes,
                featured_products=row["ผลิตภัณฑ์เด่น"],
            )
        )

    district_check = check_districts_are_phetchaburi([c.district for c in communities])

    return IngestReport(
        total_rows=len(clean),
        total_dishes=total_dishes,
        district_check=district_check,
        communities=communities,
        empty_menu_rows=empty_menu_rows,
        drop_report=drop_report,
    )
