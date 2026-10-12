"""scripts/measure_kapook_labels.py (T1.13): the rule families, on synthetic titles."""

from __future__ import annotations

from scripts.measure_kapook_labels import (
    BARE_REGION_TERMS,
    Recipe,
    classify,
    dish_matches,
    region_claims,
)
from scripts.measure_labelled_fraction import REGION_TERMS, Province

PROVINCES = [
    Province("TH-30", "นครราชสีมา", "Northeast"),
    Province("TH-42", "เลย", "Northeast"),
    Province("TH-73", "นครปฐม", "Central"),
]
OFFICIAL = {"แกงทดสอบ": {"TH-30"}, "ข้าวทดสอบ": {"TH-30", "TH-73"}}


def test_an_official_name_inside_a_longer_title_is_a_substring_match_only() -> None:
    title = "แกงทดสอบ สูตรเด็ด อร่อยง่าย ๆ"
    assert dish_matches(title, OFFICIAL, exact=True) == (set(), set())
    assert dish_matches(title, OFFICIAL, exact=False) == ({"TH-30"}, {"แกงทดสอบ"})


def test_an_exact_title_match_is_found() -> None:
    assert dish_matches("แกงทดสอบ", OFFICIAL, exact=True) == ({"TH-30"}, {"แกงทดสอบ"})


def test_a_dish_name_recorded_in_two_provinces_is_conflicting() -> None:
    codes, _ = dish_matches("ข้าวทดสอบ", OFFICIAL, exact=True)
    assert codes == {"TH-30", "TH-73"}


def test_bare_north_and_south_count_only_in_the_bare_variant() -> None:
    text = "น้ำพริกแกงใต้ สูตรเข้มข้น"
    assert region_claims(text, REGION_TERMS) == set()
    assert region_claims(text, BARE_REGION_TERMS) == {"South"}


def test_compound_region_terms_count_in_both_variants() -> None:
    text = "อาหารอีสาน แซ่บ ๆ"
    assert region_claims(text, REGION_TERMS) == region_claims(text, BARE_REGION_TERMS) == {
        "Northeast"
    }


def test_the_homograph_province_needs_a_marker_under_strict() -> None:
    """เลย is also 'at all'. It counts under permissive, not under strict or marker."""
    hits = classify(Recipe(1, "หมูทอด อร่อยมากเลย", ""), PROVINCES, OFFICIAL)
    assert hits["a_permissive"] == {"TH-42"}
    assert hits["a_strict"] == set() and hits["a_marker"] == set()


def test_the_category_path_is_examined_as_well_as_the_title() -> None:
    hits = classify(Recipe(1, "ผัดหมี่", "อาหารไทย > จังหวัดนครปฐม"), PROVINCES, OFFICIAL)
    assert hits["a_marker"] == {"TH-73"}
