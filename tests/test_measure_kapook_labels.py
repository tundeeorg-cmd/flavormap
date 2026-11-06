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


# ── T1.15: scripts/apply_labels.py writes HD-37 rules 1-2 ────────────────────

from scripts.apply_labels import OWNED, label_for  # noqa: E402

REGION_OF = {"TH-30": "Northeast", "TH-50": "North"}


def test_one_province_is_a_tier_1_high_label_with_its_region() -> None:
    lab = label_for({"a_strict": {"TH-30"}, "b_compound": set()}, REGION_OF)
    assert lab is not None
    assert (lab.province_code, lab.region, lab.tier, lab.confidence) == (
        "TH-30", "Northeast", 1, "high")
    assert lab.method_note.startswith(OWNED) and lab.conflict_note is None


def test_one_region_term_is_a_tier_2_high_label_with_no_province() -> None:
    lab = label_for({"a_strict": set(), "b_compound": {"South"}}, REGION_OF)
    assert lab is not None
    assert (lab.province_code, lab.region, lab.tier, lab.confidence) == (
        None, "South", 2, "high")


def test_ambiguity_is_no_label_never_a_pick() -> None:
    assert label_for({"a_strict": {"TH-30", "TH-50"}, "b_compound": set()}, REGION_OF) is None
    assert label_for({"a_strict": set(), "b_compound": {"North", "South"}}, REGION_OF) is None
    assert label_for({"a_strict": set(), "b_compound": set()}, REGION_OF) is None
    # Two provinces never fall back to a region term either.
    assert label_for({"a_strict": {"TH-30", "TH-50"}, "b_compound": {"North"}},
                     REGION_OF) is None


def test_a_province_keeps_precedence_and_a_disagreeing_region_is_noted() -> None:
    lab = label_for({"a_strict": {"TH-30"}, "b_compound": {"South"}}, REGION_OF)
    assert lab is not None and lab.province_code == "TH-30" and lab.region == "Northeast"
    assert lab.conflict_note is not None and "South" in lab.conflict_note


def test_the_database_holds_exactly_the_labels_the_rules_compute() -> None:
    """Read-only: the HD-37 rows in province_attribution equal what label_for() gives on
    the loaded kapook recipes (T1.15's done-when: counts match T1.13). Catches a write
    that silently did not commit."""
    from scripts.apply_labels import SOURCES, labels
    from scripts.measure_kapook_labels import load
    from scripts.measure_labelled_fraction import load_provinces
    from src.db import get_connection

    conn = get_connection()
    try:
        recipes, official = load(conn)
        source_of = dict(conn.execute(
            "SELECT r.recipe_id, rr.source_id FROM recipes r JOIN raw_recipes rr "
            "USING (raw_id)").fetchall())
        stored = {rid: (code, region, tier) for rid, code, region, tier in conn.execute(
            "SELECT recipe_id, province_code, region, tier FROM province_attribution "
            "WHERE method_note LIKE %s", (f"{OWNED}%",))}
    finally:
        conn.close()
    expected = labels([r for r in recipes if source_of.get(r.recipe_id) in SOURCES],
                      load_provinces(), official)
    assert stored == {rid: (lab.province_code, lab.region, lab.tier)
                      for rid, lab in expected.items()}
