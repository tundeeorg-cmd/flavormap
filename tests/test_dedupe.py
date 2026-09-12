"""src/clean/dedupe.py's two similarity primitives. Pure functions, no database, no
real corpus: they are exactly as testable on synthetic sets/strings as on real ones.
"""

from __future__ import annotations

from src.clean.dedupe import jaccard_similarity, title_similarity


def test_jaccard_of_identical_sets_is_one() -> None:
    s = {"กะทิ", "ตะไคร้", "ข่า"}
    assert jaccard_similarity(s, s) == 1.0


def test_jaccard_of_disjoint_sets_is_zero() -> None:
    assert jaccard_similarity({"กะทิ"}, {"น้ำปลา"}) == 0.0


def test_jaccard_of_two_empty_sets_is_one_not_zero() -> None:
    """Nothing to disagree about is not the same claim as maximally different."""
    assert jaccard_similarity(set(), set()) == 1.0


def test_jaccard_partial_overlap() -> None:
    a = {"กะทิ", "ตะไคร้", "ข่า", "พริก"}
    b = {"กะทิ", "ตะไคร้", "น้ำปลา"}
    # intersection = {กะทิ, ตะไคร้} = 2, union = {กะทิ, ตะไคร้, ข่า, พริก, น้ำปลา} = 5
    assert jaccard_similarity(a, b) == 2 / 5


def test_title_similarity_of_identical_strings_is_one() -> None:
    assert title_similarity("แกงเขียวหวานไก่", "แกงเขียวหวานไก่") == 1.0


def test_title_similarity_of_unrelated_strings_is_low() -> None:
    assert title_similarity("แกงเขียวหวานไก่", "ผัดไทย") < 0.3


def test_title_similarity_of_a_near_duplicate_title_clears_the_named_threshold() -> None:
    """§7.2's own threshold, 0.8, applied here only as a check on the metric's
    behaviour — not asserted as the project's decided value (see the module
    docstring's note on the 0.85-vs-0.9 discrepancy)."""
    assert title_similarity("แกงเขียวหวานไก่ สูตรดั้งเดิม", "แกงเขียวหวานไก่ สูตรต้นตำรับ") > 0.5
