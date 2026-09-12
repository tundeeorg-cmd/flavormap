"""`src/ingest/source_catalogue.py` — content classification, domain extraction, and
the core-is-subset-of-full check.

Examples are drawn from the task brief's own findings: the four confirmed
local-food-inventory titles, the named restaurant-certification schemes, and the GI
example (ข้าวหอมมะลิสุรินทร์). None of this is drawn from the real
`flavormap_gdcatalog_sources_full.csv`, which this project does not have a copy of —
see `docs/decisions.md`.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.ingest.source_catalogue import (
    AUTO_REJECT_CLASSES,
    CLASS_AGRICULTURAL_PRODUCTION,
    CLASS_CULTURAL_HERITAGE,
    CLASS_GI_REGISTRATION,
    CLASS_IRRELEVANT,
    CLASS_LOCAL_DISH_INVENTORY,
    CLASS_RESTAURANT_REGISTRY,
    CLASS_TOURISM,
    REQUIRED_COLUMNS,
    STATUS_NOT_ASSESSED,
    STATUS_REJECTED,
    build_catalogue_rows,
    class_distribution,
    classify_content,
    distinct_domains,
    validate_columns,
    verify_core_is_subset_of_full,
)

# ── content classification ──────────────────────────────────────────────────────

#: The brief's own four confirmed local-food-inventory datasets.
LOCAL_DISH_EXAMPLES = [
    ("เพชรบุรี", "อาหารพื้นถิ่น"),
    ("กาญจนบุรี", "อาหารพื้นเมือง"),
    ("เชียงราย", "อาหารพื้นเมือง"),
    ("นครศรีธรรมราช", "เมนูอาหารท้องถิ่น"),
]


@pytest.mark.parametrize("province,title", LOCAL_DISH_EXAMPLES)
def test_local_dish_inventory_titles_classified_correctly(province: str, title: str) -> None:
    assert classify_content(title) == CLASS_LOCAL_DISH_INVENTORY


@pytest.mark.parametrize(
    "title",
    [
        "ร้านอาหาร Clean Food Good Taste จังหวัดทดสอบ",
        "ทำเนียบร้าน Thaiselect",
        "รายชื่อร้าน Q Restaurant",
        "ร้านค้าธงฟ้าประชารัฐ",
    ],
)
def test_restaurant_registries_classified_and_not_confused_with_food_content(title: str) -> None:
    assert classify_content(title) == CLASS_RESTAURANT_REGISTRY


def test_restaurant_wins_over_local_dish_keyword_when_both_present() -> None:
    """"ร้านอาหารพื้นเมือง" (a restaurant *branded* as local food) literally contains
    both a restaurant_registry keyword (ร้านอาหาร) and a local_dish_inventory one
    (อาหารพื้นเมือง). Restaurant-registry is checked first — the brief's own warning
    is that "อาหาร" is noisy specifically because of this shape of title."""
    assert classify_content("ร้านอาหารพื้นเมืองตำบลทดสอบ") == CLASS_RESTAURANT_REGISTRY


def test_gi_registration_by_title() -> None:
    assert classify_content("สิ่งบ่งชี้ทางภูมิศาสตร์ ข้าวหอมมะลิทุ่งกุลาร้องไห้") == CLASS_GI_REGISTRATION


def test_gi_registration_by_description_fallback() -> None:
    """A product-named title with no GI keyword in it, but the description carries
    the registration language."""
    result = classify_content(
        "ข้าวหอมมะลิสุรินทร์", description_th="ทะเบียนสิ่งบ่งชี้ทางภูมิศาสตร์ (GI) ประจำจังหวัดสุรินทร์"
    )
    assert result == CLASS_GI_REGISTRATION


def test_gi_registrant_list_titles_also_classify_as_gi() -> None:
    """Task 4b's point is about what gets HARVESTED, not classified — a registrant
    list is still a GI-programme dataset, just one whose rows must never be stored."""
    assert classify_content("บัญชีผู้ขอใช้ตราสัญลักษณ์สิ่งบ่งชี้ทางภูมิศาสตร์") == CLASS_GI_REGISTRATION


def test_cultural_heritage() -> None:
    assert classify_content("มรดกภูมิปัญญาทางวัฒนธรรมด้านอาหาร") == CLASS_CULTURAL_HERITAGE


def test_tourism() -> None:
    assert classify_content("การท่องเที่ยวโดยชุมชนจังหวัดน่าน") == CLASS_TOURISM


def test_agricultural_production() -> None:
    assert classify_content("ผลผลิตทางการเกษตรจังหวัดสุรินทร์ ปี 2567") == CLASS_AGRICULTURAL_PRODUCTION


def test_no_keyword_match_falls_back_to_irrelevant() -> None:
    assert classify_content("งบประมาณประจำปีขององค์การบริหารส่วนจังหวัด") == CLASS_IRRELEVANT


def test_empty_title_is_irrelevant() -> None:
    assert classify_content("") == CLASS_IRRELEVANT


# ── auto-reject ──────────────────────────────────────────────────────────────────

def test_restaurant_registry_is_in_auto_reject_classes() -> None:
    assert CLASS_RESTAURANT_REGISTRY in AUTO_REJECT_CLASSES
    assert CLASS_LOCAL_DISH_INVENTORY not in AUTO_REJECT_CLASSES
    assert CLASS_GI_REGISTRATION not in AUTO_REJECT_CLASSES


# ── whole-file report ────────────────────────────────────────────────────────────

def _fixture_csv(tmp_path: Path, rows: list[dict[str, str]]) -> Path:
    base = {c: "" for c in REQUIRED_COLUMNS}
    path = tmp_path / "fixture.csv"
    pd.DataFrame([{**base, **r} for r in rows]).to_csv(path, index=False, encoding="utf-8-sig")
    return path


def test_build_catalogue_rows_auto_rejects_restaurant_registries(tmp_path: Path) -> None:
    rows = [
        {"dataset_slug": "s1", "dataset_title_th": "ร้านอาหาร Clean Food Good Taste", "tier": "A"},
        {"dataset_slug": "s2", "dataset_title_th": "อาหารพื้นเมืองจังหวัดกาญจนบุรี", "tier": "A"},
    ]
    df = pd.read_csv(
        _fixture_csv(tmp_path, rows), encoding="utf-8-sig", dtype=str, keep_default_na=False
    )
    catalogue = build_catalogue_rows(df)

    restaurant_row = next(r for r in catalogue if r.dataset_slug == "s1")
    assert restaurant_row.content_class == CLASS_RESTAURANT_REGISTRY
    assert restaurant_row.harvest_status == STATUS_REJECTED
    assert restaurant_row.rejection_reason

    dish_row = next(r for r in catalogue if r.dataset_slug == "s2")
    assert dish_row.content_class == CLASS_LOCAL_DISH_INVENTORY
    assert dish_row.harvest_status == STATUS_NOT_ASSESSED
    assert dish_row.rejection_reason is None


def test_class_distribution_counts() -> None:
    rows = [
        {"dataset_slug": "s1", "dataset_title_th": "ร้านอาหาร Thaiselect", "tier": "A"},
        {"dataset_slug": "s2", "dataset_title_th": "ร้านอาหาร Q Restaurant", "tier": "A"},
        {"dataset_slug": "s3", "dataset_title_th": "อาหารพื้นถิ่นจังหวัดเพชรบุรี", "tier": "A"},
    ]
    df = pd.DataFrame([{**{c: "" for c in REQUIRED_COLUMNS}, **r} for r in rows])
    catalogue = build_catalogue_rows(df)
    dist = class_distribution(catalogue)
    assert dist[CLASS_RESTAURANT_REGISTRY] == 2
    assert dist[CLASS_LOCAL_DISH_INVENTORY] == 1
    assert dist[CLASS_IRRELEVANT] == 0


def test_validate_columns_raises_on_missing() -> None:
    with pytest.raises(ValueError):
        validate_columns(pd.DataFrame([{"dataset_slug": "s1"}]))


# ── domain extraction (Task 2a) ────────────────────────────────────────────────

def test_distinct_domains() -> None:
    df = pd.DataFrame(
        {
            "resource_url": [
                "https://phetchaburi.gdcatalog.go.th/dataset/x/resource/y.csv",
                "https://kanchanaburi.gdcatalog.go.th/dataset/z",
                "https://data.thaihealth.or.th/dataset/food",
                "https://catalog.qsds.go.th/dataset/gi",
                "",
                "not a url",
            ]
        }
    )
    domains = distinct_domains(df)
    assert domains == [
        "catalog.qsds.go.th",
        "data.thaihealth.or.th",
        "kanchanaburi.gdcatalog.go.th",
        "not a url",
        "phetchaburi.gdcatalog.go.th",
    ]


# ── Task 0c — core-is-subset-of-full ───────────────────────────────────────────

def _catalogue_df(rows: list[dict[str, str]]) -> pd.DataFrame:
    base = {c: "" for c in REQUIRED_COLUMNS}
    return pd.DataFrame([{**base, **r} for r in rows])


def test_verify_core_is_exact_subset() -> None:
    full = _catalogue_df(
        [
            {"dataset_slug": "a", "tier": "A", "dataset_title_th": "x"},
            {"dataset_slug": "b", "tier": "B", "dataset_title_th": "y"},
        ]
    )
    core = _catalogue_df([{"dataset_slug": "a", "tier": "A", "dataset_title_th": "x"}])
    result = verify_core_is_subset_of_full(core, full)
    assert result.core_count == 1
    assert result.full_count == 2
    assert result.core_slugs_not_in_full == []
    assert result.rows_differing == []


def test_verify_core_flags_slug_missing_from_full() -> None:
    full = _catalogue_df([{"dataset_slug": "a", "tier": "A", "dataset_title_th": "x"}])
    core = _catalogue_df([{"dataset_slug": "a", "tier": "A", "dataset_title_th": "x"},
                           {"dataset_slug": "ghost", "tier": "A", "dataset_title_th": "z"}])
    result = verify_core_is_subset_of_full(core, full)
    assert result.core_slugs_not_in_full == ["ghost"]


def test_verify_core_flags_a_differing_row() -> None:
    full = _catalogue_df([{"dataset_slug": "a", "tier": "A", "dataset_title_th": "original title"}])
    core = _catalogue_df([{"dataset_slug": "a", "tier": "A", "dataset_title_th": "edited title"}])
    result = verify_core_is_subset_of_full(core, full)
    assert result.rows_differing == ["a"]
