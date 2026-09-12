"""`src/ingest/thai_province_match.py` — word-boundary-aware province matching.

The two required negatives (standing rule: "a test for the Thai province matcher
using น่านน้ำ and เผยแพร่ as known negatives") plus the real title text found in
`flavormap_datago_catalog.csv` that exposed the bug in the first place.
"""

from __future__ import annotations

from src.ingest.thai_province_match import (
    VERDICT_CONFIRMED,
    VERDICT_EMPTY,
    VERDICT_INVALID_VALUE,
    VERDICT_NO_EVIDENCE,
    VERDICT_TRAP_MISMATCH,
    check_assignment,
    contains_known_trap,
    official_provinces,
    tokens_containing_official_province,
)

# The real dataset title that surfaced the bug (flavormap_datago_catalog.csv).
FISHING_VESSEL_TITLE = (
    "เรือประมงนอกน่านน้ำ และเรือขนถ่ายสัตว์น้ำนอกน่านน้ำที่ได้รับอนุญาตและมีการติดตั้ง"
    "ระบบอิเล็กทรอนิกส์ VMS ERS และ EM"
)


def test_official_provinces_has_77() -> None:
    assert len(official_provinces()) == 77


# ── the two required negatives ────────────────────────────────────────────────────

def test_nan_namnam_is_a_known_negative() -> None:
    """น่านน้ำ ("territorial waters") must never produce a น่าน token match."""
    assert "น่าน" not in tokens_containing_official_province(FISHING_VESSEL_TITLE)


def test_phrae_phoeiphrae_is_a_known_negative() -> None:
    """เผยแพร่ ("published") must never produce a แพร่ token match."""
    assert "แพร่" not in tokens_containing_official_province("เผยแพร่ข้อมูลผลผลิตทางการเกษตร")


# ── genuine positives, same words, unambiguous context ─────────────────────────────

def test_nan_matches_when_genuinely_present() -> None:
    assert "น่าน" in tokens_containing_official_province("อาหารพื้นถิ่นจังหวัดน่าน")


def test_phrae_matches_when_genuinely_present() -> None:
    assert "แพร่" in tokens_containing_official_province("ข้อมูลจังหวัดแพร่ ปี 2567")


def test_multiple_provinces_in_one_text() -> None:
    result = tokens_containing_official_province("เปรียบเทียบจังหวัดน่านกับจังหวัดแพร่")
    assert result == {"น่าน", "แพร่"}


def test_no_province_present() -> None:
    assert tokens_containing_official_province("จำนวนผลิตภัณฑ์ OTOP") == set()


def test_empty_text() -> None:
    assert tokens_containing_official_province("") == set()
    assert tokens_containing_official_province(None) == set()


# ── known trap substrings (option c) ────────────────────────────────────────────

def test_contains_known_trap_finds_namnam() -> None:
    assert contains_known_trap("น่าน", FISHING_VESSEL_TITLE) == "น่านน้ำ"


def test_contains_known_trap_finds_phoeiphrae() -> None:
    assert contains_known_trap("แพร่", "เผยแพร่ข้อมูล") == "เผยแพร่"


def test_contains_known_trap_none_for_clean_text() -> None:
    assert contains_known_trap("น่าน", "อาหารพื้นถิ่นจังหวัดน่าน") is None


def test_contains_known_trap_none_for_province_with_no_known_traps() -> None:
    assert contains_known_trap("สุรินทร์", "อะไรก็ได้") is None


# ── per-row verdicts (Task 1c) ──────────────────────────────────────────────────

def test_check_assignment_confirmed() -> None:
    result = check_assignment("น่าน", "อาหารพื้นถิ่นจังหวัดน่าน")
    assert result.verdict == VERDICT_CONFIRMED


def test_check_assignment_trap_mismatch_on_the_real_bug() -> None:
    result = check_assignment("น่าน", FISHING_VESSEL_TITLE)
    assert result.verdict == VERDICT_TRAP_MISMATCH
    assert result.evidence == "น่านน้ำ"


def test_check_assignment_no_evidence_is_distinct_from_trap_mismatch() -> None:
    """A structured-field-derived value with no province word in the title is
    unverifiable, not confirmed wrong — the two must never be conflated."""
    result = check_assignment("น่าน", "จำนวนผลิตภัณฑ์ OTOP")
    assert result.verdict == VERDICT_NO_EVIDENCE


def test_check_assignment_invalid_value() -> None:
    result = check_assignment("แปลง", "ข้อมูลเกษตรกร")
    assert result.verdict == VERDICT_INVALID_VALUE


def test_check_assignment_empty() -> None:
    result = check_assignment("", "อะไรก็ได้")
    assert result.verdict == VERDICT_EMPTY
    result = check_assignment(None, "อะไรก็ได้")
    assert result.verdict == VERDICT_EMPTY
