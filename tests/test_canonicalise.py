"""src/clean/canonicalise.py: raw lines → recipe_ingredients rows. Synthetic ids."""

from __future__ import annotations

import pytest

from src.clean.canonicalise import RAW_JOIN, canonicalise
from src.clean.lexicon import key

TABLE = {"เกลือ": ("ING_A",), "เกลือป่น 1 ช้อนชา": ("ING_A",),
         "ปลาร้าหรือปลาเค็ม": ("ING_B", "ING_C")}


def entries_for(text: str) -> tuple[str, ...]:
    return TABLE.get(key(text), ())


def test_aliases_splits_and_unmapped_lines() -> None:
    out = canonicalise([
        ("dcp_food", "official", 1, "เกลือ"),
        ("dcp_food", "official", 1, "ปลาร้าหรือปลาเค็ม"),
        ("dcp_food", "official", 1, "ไม่มีในพจนานุกรม"),
        ("kapook_cooking", "commercial", 2, "เกลือป่น 1 ช้อนชา"),
        ("kapook_cooking", "commercial", 2, "   "),
    ], entries_for)
    assert [(r.recipe_id, r.canonical_id) for r in out.rows] == [
        (1, "ING_A"), (1, "ING_B"), (1, "ING_C"), (2, "ING_A")]
    assert (out.mentions, out.mapped_mentions, out.split_mentions) == (4, 3, 1)
    assert {r.recipe_id: r.extraction_method for r in out.rows} == {
        1: "institutional_pdf", 2: "rule"}


def test_two_lines_for_one_entry_make_one_row_keeping_both_texts() -> None:
    out = canonicalise([("k", "commercial", 3, "เกลือ"),
                        ("k", "commercial", 3, "เกลือป่น 1 ช้อนชา")], entries_for)
    assert len(out.rows) == 1
    assert out.rows[0].raw_text == f"เกลือ{RAW_JOIN}เกลือป่น 1 ช้อนชา"


def test_an_unknown_register_is_an_error() -> None:
    with pytest.raises(ValueError, match="unknown register"):
        canonicalise([("x", "imaginary", 1, "เกลือ")], entries_for)
