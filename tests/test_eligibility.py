"""src/analyze/eligibility.py — pure functions over a province: count mapping the
caller supplies. No database, no real corpus: the threshold-sweep logic itself is what
CLAUDE.md §7.5 specifies, and it is exactly as testable on synthetic counts as on real
ones.
"""

from __future__ import annotations

from src.analyze.eligibility import (
    HEADLINE_THRESHOLDS,
    THRESHOLDS,
    caption,
    eligible_provinces,
    headline,
    sweep,
)

COUNTS = {
    "TH-10": 40,  # Bangkok — clears every threshold
    "TH-50": 20,  # clears up to 20, not 25
    "TH-96": 8,  # clears up to 8, not 10
    "TH-95": 2,  # clears nothing in range
}


def test_eligible_provinces_is_the_boundary_inclusive_and_sorted() -> None:
    assert eligible_provinces(COUNTS, 20) == ["TH-10", "TH-50"]
    assert eligible_provinces(COUNTS, 21) == ["TH-10"]


def test_sweep_covers_5_to_30_inclusive() -> None:
    result = sweep(COUNTS)
    assert set(result) == set(THRESHOLDS)
    assert min(result) == 5
    assert max(result) == 30


def test_sweep_is_non_increasing_as_the_threshold_rises() -> None:
    result = sweep(COUNTS)
    values = [result[t] for t in sorted(result)]
    # A pairwise shift-by-one comparison is never equal-length, so strict=True (which
    # requires equal lengths) does not apply here — that is the point of the shift.
    assert all(a >= b for a, b in zip(values, values[1:], strict=False))


def test_headline_reports_exactly_10_15_25() -> None:
    result = headline(COUNTS)
    assert set(result) == set(HEADLINE_THRESHOLDS) == {10, 15, 25}
    assert result[10] == 2  # TH-10, TH-50 (TH-96's count of 8 does not clear 10)
    assert result[15] == 2  # TH-10, TH-50
    assert result[25] == 1  # TH-10 only


def test_caption_wording_and_default_threshold() -> None:
    text = caption(COUNTS, threshold=10)
    assert text == "n = 2 of 77 provinces"


def test_caption_uses_province_min_n_by_default() -> None:
    from src.config import PROVINCE_MIN_N

    assert caption(COUNTS) == caption(COUNTS, threshold=PROVINCE_MIN_N)


def test_an_empty_corpus_is_zero_everywhere_not_an_error() -> None:
    assert sweep({}) == {t: 0 for t in THRESHOLDS}
    assert caption({}) == "n = 0 of 77 provinces"
