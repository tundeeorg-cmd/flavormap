"""Thai normalisation, against a fixture read by hand from a real document.

The fixture strings below were transcribed from `data/raw/dcp_food/north_1_1.pdf`
(กำแพงเพชร, menu 1) by reading the rendered PDF, not by trusting any extractor. That is
the point: a test built from extractor output would pass while the extractor was wrong.
"""

from __future__ import annotations

import pytest

from src.clean.normalize_th import collapse_whitespace, normalize_thai

# ─── Defect 1: orphaned combining marks ───────────────────────────────────────
# Observed verbatim in extractor output. Left = damaged, right = what the page shows.
ORPHAN_CASES = [
    ("หม ู่ ๖", "หมู่ ๖"),          # north_1_1.pdf §1.3
    ("ท ี่", "ที่"),                 # northeast_15_1.pdf §4 table header
    ("ท่ ี", "ท่ี"),
]


@pytest.mark.parametrize("damaged,expected", ORPHAN_CASES)
def test_orphan_marks_are_joined(damaged, expected):
    out, report = normalize_thai(damaged)
    assert out == expected
    assert report.orphan_marks_joined >= 1


# ─── Defect 2: broken sara am, dictionary-arbitrated ──────────────────────────

RESOLVABLE = [
    ("ประจ าปีงบประมาณ", "ประจำปีงบประมาณ"),   # ประจา is not a word
    ("จ าเป็น", "จำเป็น"),                      # จาเป็น is not a word
    ("ต าบล", "ตำบล"),                          # ตาบล is not a word
]


@pytest.mark.parametrize("damaged,expected", RESOLVABLE)
def test_unambiguous_sara_am_is_repaired(damaged, expected):
    out, report = normalize_thai(damaged)
    assert out == expected
    assert report.sara_am_repaired >= 1


def test_ambiguous_sara_am_is_left_alone():
    """น้ำ (water) and น้า (aunt) are both real words.

    A recipe corpus makes "water" the tempting guess, and being right most of the time
    is exactly what makes a silent wrong repair dangerous. The site is left untouched
    and counted.
    """
    damaged = "น้ า"
    out, report = normalize_thai(damaged)
    assert out == damaged
    assert report.sara_am_ambiguous == 1
    assert report.sara_am_repaired == 0


def test_legitimate_spacing_is_preserved():
    """Thai uses spaces as phrase boundaries. Nothing may weld phrases together."""
    text = "แกงขี้เหล็ก จังหวัด กำแพงเพชร"
    out, report = normalize_thai(text)
    assert out == text
    assert report.total_repairs == 0


def test_clean_text_is_unchanged():
    for text in ["ประจำปีงบประมาณ", "หมู่", "อาหารคาว", "เชิดชูอาหารถิ่น", ""]:
        out, report = normalize_thai(text)
        assert out == text
        assert report.total_repairs == 0


def test_nfc_normalisation_is_applied():
    import unicodedata
    decomposed = unicodedata.normalize("NFD", "ก้")
    out, _ = normalize_thai(decomposed)
    assert out == unicodedata.normalize("NFC", "ก้")


def test_non_thai_text_untouched():
    text = "The Lost Taste 2568  ✓ ok"
    out, report = normalize_thai(text)
    assert out == text
    assert report.total_repairs == 0


def test_collapse_whitespace_preserves_lines():
    assert collapse_whitespace("a   b\n\n\n\nc") == "a b\n\nc"
