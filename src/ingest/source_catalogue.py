"""Classify and track `culture.gdcatalog.go.th` catalogue entries — a source
*inventory*, not recipe data. Rows from `flavormap_gdcatalog_sources_full.csv` /
`..._tierA_core.csv` become `source_catalogue` rows (migration 025): what was seen,
how it was classified, and whether/why it was harvested — a methods-section artifact
in its own right (Task 1's brief).

**The tier column is not trusted as a curated shortlist.** The brief's own keyword
scan found 124 tier-A titles containing "อาหาร", most of them ร้านอาหาร (restaurant
certification registries — Clean Food Good Taste, Thaiselect, Q Restaurant, ธงฟ้า) —
business directories with no culinary content. Tier A/B is carried through as
provenance, never used as the content filter; :func:`classify_content` reads the
title and description, not the tier.

**Classification is a mechanical first pass, not a content judgement.** The closed
vocabulary below is applied by keyword/phrase matching against `dataset_title_th`
(and `description_th` as a fallback) — cheap, reproducible, and exactly as reliable
as that: a title containing "ร้านอาหาร" is confidently `restaurant_registry`, but a
title with no matching keyword at all becomes `irrelevant` by default, which folds
"genuinely irrelevant" and "not caught by any keyword yet" into one bucket. That is a
real limitation of a keyword classifier, not hidden here: `harvest_status` staying
`not_assessed` alongside a mechanical `content_class` is what keeps the two apart
downstream — a human re-reading `irrelevant` titles before treating the class
distribution as a finding is still Task 1's own to do, not something this module
claims to have done for them.

**Restaurant registries are checked first, deliberately.** "ร้านอาหาร" contains
"อาหาร" — without an ordered, first-match-wins rule list, a naive "does the title
contain a food word" check would misclassify most restaurant registries as
food-content classes. The brief's own finding (124 tier-A "อาหาร" titles, mostly
restaurant registries) is exactly the failure mode this ordering exists to avoid.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS: tuple[str, ...] = (
    "tier",
    "dataset_title_th",
    "province_th",
    "publisher_th",
    "description_th",
    "formats",
    "n_resources",
    "last_modified",
    "dataset_slug",
    "resource_url",
)

# ── content classification ──────────────────────────────────────────────────────

CLASS_LOCAL_DISH_INVENTORY = "local_dish_inventory"
CLASS_GI_REGISTRATION = "gi_registration"
CLASS_RESTAURANT_REGISTRY = "restaurant_registry"
CLASS_AGRICULTURAL_PRODUCTION = "agricultural_production"
CLASS_CULTURAL_HERITAGE = "cultural_heritage"
CLASS_TOURISM = "tourism"
CLASS_IRRELEVANT = "irrelevant"

CONTENT_CLASSES: tuple[str, ...] = (
    CLASS_LOCAL_DISH_INVENTORY,
    CLASS_GI_REGISTRATION,
    CLASS_RESTAURANT_REGISTRY,
    CLASS_AGRICULTURAL_PRODUCTION,
    CLASS_CULTURAL_HERITAGE,
    CLASS_TOURISM,
    CLASS_IRRELEVANT,
)

#: (class, keywords) in match-priority order — FIRST match wins. Restaurant-registry
#: keywords are checked before any general food keyword for the reason the module
#: docstring gives. Within a class, any one keyword matching is enough.
_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        CLASS_RESTAURANT_REGISTRY,
        (
            "ร้านอาหาร",
            "clean food good taste",
            "thaiselect",
            "q restaurant",
            "ธงฟ้า",
        ),
    ),
    (
        CLASS_GI_REGISTRATION,
        (
            "สิ่งบ่งชี้ทางภูมิศาสตร์",
            "ผู้ขอใช้",
            "ผู้ผลิตที่ใช้",
            " gi ",
        ),
    ),
    (
        CLASS_LOCAL_DISH_INVENTORY,
        (
            "อาหารพื้นเมือง",
            "อาหารพื้นถิ่น",
            "เมนูอาหารท้องถิ่น",
        ),
    ),
    (
        CLASS_CULTURAL_HERITAGE,
        (
            "มรดกภูมิปัญญา",
            "ภูมิปัญญา",
        ),
    ),
    (
        CLASS_TOURISM,
        (
            "ท่องเที่ยวโดยชุมชน",
            "การท่องเที่ยว",
            "แหล่งท่องเที่ยว",
        ),
    ),
    (
        CLASS_AGRICULTURAL_PRODUCTION,
        (
            "ผลผลิตทางการเกษตร",
            "การเกษตร",
            "ปศุสัตว์",
            "ประมง",
            "เกษตรกร",
        ),
    ),
)


def _normalise(text: str | None) -> str:
    return (text or "").strip().lower()


def classify_content(dataset_title_th: str, description_th: str | None = None) -> str:
    """First-match-wins keyword classification against the closed vocabulary above.

    Checked against the title first; a title with no match falls back to the
    description. Neither matching anything returns `irrelevant` — the default bucket,
    not a claim that the row was read and judged irrelevant.
    """
    title = _normalise(dataset_title_th)
    for cls, keywords in _RULES:
        if any(kw in title for kw in keywords):
            return cls

    desc = _normalise(description_th)
    if desc:
        for cls, keywords in _RULES:
            if any(kw in desc for kw in keywords):
                return cls

    return CLASS_IRRELEVANT


# ── harvest tracking ────────────────────────────────────────────────────────────

STATUS_NOT_ASSESSED = "not_assessed"
STATUS_REJECTED = "rejected"
STATUS_QUEUED = "queued"
STATUS_HARVESTED = "harvested"
STATUS_FAILED = "failed"

HARVEST_STATUSES: tuple[str, ...] = (
    STATUS_NOT_ASSESSED,
    STATUS_REJECTED,
    STATUS_QUEUED,
    STATUS_HARVESTED,
    STATUS_FAILED,
)

#: Standing rule (brief): restaurant registries are out of scope regardless of tier.
#: A row classified restaurant_registry is auto-rejected with this reason rather than
#: left `not_assessed` for a human to reject one-by-one across ~124+ rows.
AUTO_REJECT_CLASSES: dict[str, str] = {
    CLASS_RESTAURANT_REGISTRY: (
        "business directory / certification registry — no recipes, ingredients, or "
        "culinary content; out of scope for all five research questions per the brief"
    ),
}


@dataclass
class CatalogueRow:
    tier: str
    dataset_title_th: str
    province_th: str
    publisher_th: str
    description_th: str
    formats: str
    n_resources: str
    last_modified: str
    dataset_slug: str
    resource_url: str
    content_class: str
    harvest_status: str
    rejection_reason: str | None


def read_raw(path: Path) -> pd.DataFrame:
    """UTF-8 with a BOM — same reason as every other gdcatalog source in this
    project: plain `"utf-8"` corrupts the first column's first value."""
    return pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)


def validate_columns(df: pd.DataFrame) -> None:
    missing = tuple(c for c in REQUIRED_COLUMNS if c not in df.columns)
    if missing:
        raise ValueError(f"expected column(s) missing from source CSV: {missing}")


def build_catalogue_rows(df: pd.DataFrame) -> list[CatalogueRow]:
    validate_columns(df)
    rows: list[CatalogueRow] = []
    for _, row in df.iterrows():
        cls = classify_content(row["dataset_title_th"], row["description_th"])
        status = STATUS_REJECTED if cls in AUTO_REJECT_CLASSES else STATUS_NOT_ASSESSED
        reason = AUTO_REJECT_CLASSES.get(cls)
        rows.append(
            CatalogueRow(
                tier=row["tier"],
                dataset_title_th=row["dataset_title_th"],
                province_th=row["province_th"],
                publisher_th=row["publisher_th"],
                description_th=row["description_th"],
                formats=row["formats"],
                n_resources=row["n_resources"],
                last_modified=row["last_modified"],
                dataset_slug=row["dataset_slug"],
                resource_url=row["resource_url"],
                content_class=cls,
                harvest_status=status,
                rejection_reason=reason,
            )
        )
    return rows


def class_distribution(rows: list[CatalogueRow]) -> dict[str, int]:
    counts: dict[str, int] = {c: 0 for c in CONTENT_CLASSES}
    for r in rows:
        counts[r.content_class] = counts.get(r.content_class, 0) + 1
    return counts


def distinct_domains(df: pd.DataFrame) -> list[str]:
    """Task 2a — the distinct hosts `resource_url` points at, for the licence audit.
    Robust to a missing scheme and to trailing paths; returns lowercased hostnames."""
    domains: set[str] = set()
    pattern = re.compile(r"^(?:https?://)?([^/]+)")
    for url in df["resource_url"]:
        if not url:
            continue
        m = pattern.match(url.strip())
        if m:
            domains.add(m.group(1).lower())
    return sorted(domains)


# ── Task 0c — core is an exact subset of full ─────────────────────────────────────

@dataclass
class SubsetCheckResult:
    core_count: int
    full_count: int
    core_slugs_not_in_full: list[str]
    rows_differing: list[str]  # dataset_slug values present in both but with different field values


def verify_core_is_subset_of_full(core: pd.DataFrame, full: pd.DataFrame) -> SubsetCheckResult:
    """Task 0c: does `tierA_core` match `full`'s tier-A rows exactly, by
    `dataset_slug`, with no field drift between the two copies of a shared row?
    Reports every discrepancy rather than a bare True/False — 259/259 matching by
    slug alone would not catch a row that exists in both but was edited in one copy.
    """
    validate_columns(core)
    validate_columns(full)

    full_by_slug = {row["dataset_slug"]: row for _, row in full.iterrows()}
    core_slugs_not_in_full = [
        slug for slug in core["dataset_slug"] if slug not in full_by_slug
    ]

    rows_differing: list[str] = []
    for _, core_row in core.iterrows():
        slug = core_row["dataset_slug"]
        full_row = full_by_slug.get(slug)
        if full_row is None:
            continue
        if any(core_row[c] != full_row[c] for c in REQUIRED_COLUMNS):
            rows_differing.append(slug)

    return SubsetCheckResult(
        core_count=len(core),
        full_count=len(full),
        core_slugs_not_in_full=core_slugs_not_in_full,
        rows_differing=rows_differing,
    )
