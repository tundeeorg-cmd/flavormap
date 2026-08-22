"""The three ways Thai text breaks when extracted from these PDFs.

Two were named in the project brief; the third was found by measuring the corpus.

1. **Broken sara am** — ``น้ำปลา`` extracts as ``น้ ปลา``. Repaired by segmentation
   arbitration in :mod:`src.clean.normalize_th`.
2. **Orphaned combining marks** — ``หมู่`` extracts as ``หม ู่``.
3. **Private-use tone marks** — some fonts encode marks in U+F700 rather than the Thai
   block, so ``ด้าน`` extracts as ``ดาน``. 14 of 231 documents, 3,930 occurrences.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.clean.normalize_th import normalize_thai, repair_pua
from src.ingest.pdf_layout import read_document

RAW = Path("data/raw/dcp_food")


# ── defect 3: private-use tone marks ──────────────────────────────────────────

@pytest.mark.parametrize(
    ("broken", "expected"),
    [
        ("าน".join(["ด", ""]), "ด้าน"),          # U+F70B -> ้
        ("แหลง", "แหล่ง"),                        # U+F70A -> ่
        ("เปน", "เป็น"),                          # U+F712 -> ็
        ("ลักษณ", "ลักษณ์"),                      # U+F70E -> ์
        ("ปญญา", "ปัญญา"),                        # U+F710 -> ั
        ("ฟา", "ฟ้า"),                            # U+F706 -> ้
        ("กะป", "กะปิ"),                          # U+F701 -> ิ
        ("เปยก", "เปียก"),                        # U+F702 -> ี
    ],
)
def test_pua_marks_are_mapped(broken: str, expected: str) -> None:
    got, mapped, _ = repair_pua(broken)
    assert got == expected
    assert mapped >= 1


def test_unmapped_pua_is_left_visible_not_guessed() -> None:
    """U+F705 and U+F70C are too rare to verify. A wrong mark is worse than a visible one."""
    got, mapped, unmapped = repair_pua("กข")
    assert "" in got
    assert mapped == 0
    assert unmapped == 1


@pytest.mark.skipif(not RAW.exists(), reason="raw corpus not present")
def test_pua_documents_normalise_clean() -> None:
    """south_1_1 is the worst PUA case in the corpus."""
    text = read_document(RAW / "south_1_1.pdf").raw_text
    assert "" in text, "fixture no longer exercises the defect"
    cleaned, report = normalize_thai(text)
    assert report.pua_marks_mapped > 100
    assert "ข้าว" in cleaned


# ── defect 1: broken sara am ──────────────────────────────────────────────────

def test_sara_am_repaired_where_segmentation_is_decisive() -> None:
    got, report = normalize_thai("ประจ าปีงบประมาณ")
    assert got == "ประจำปีงบประมาณ"
    assert report.sara_am_repaired == 1


def test_sara_am_left_alone_when_genuinely_ambiguous() -> None:
    """น้ำ (water) and น้า (aunt) score identically. Guessing 'water' in a recipe
    corpus would be right often enough to be dangerous."""
    got, report = normalize_thai("น้ า")
    assert report.sara_am_ambiguous == 1
    assert "น้ า" in got


# ── defect 2: orphaned combining marks ────────────────────────────────────────

def test_orphan_mark_is_rejoined() -> None:
    got, report = normalize_thai("หม ู่")
    assert got == "หมู่"
    assert report.orphan_marks_joined >= 1
