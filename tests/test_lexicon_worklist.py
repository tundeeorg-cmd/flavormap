"""scripts/lexicon_worklist.py — ranks strings for HD-6 without merging any of them.

Pure-function tests on synthetic rows; no database needed.
"""

from __future__ import annotations

import unicodedata

from scripts.lexicon_worklist import build_worklist, key, rank_reaching

ROWS = [
    ("dcp_food", 1, "หอมแดง"),
    ("dcp_food", 2, "หอมแดง"),
    ("dcp_food", 3, "หอมแดง"),
    ("dcp_food", 1, "หอมแดง"),     # same recipe twice: counts once
    ("kapook_cooking", 9, "หอมแดง"),
    ("dcp_food", 1, "เกลือ"),
    ("dcp_food", 2, "เกลือป่น"),    # a variant: stays its own row (rule 4)
    ("dcp_food", 3, None),
    ("dcp_food", 3, "   "),
]


def test_ranked_by_distinct_recipes_with_per_source_counts() -> None:
    wl = build_worklist(ROWS, mapped=set())
    top = wl[0]
    assert (top.rank, top.name_th, top.n_recipes) == (1, "หอมแดง", 4)
    assert top.by_source == {"dcp_food": 3, "kapook_cooking": 1}


def test_variants_are_never_merged() -> None:
    names = [r.name_th for r in build_worklist(ROWS, mapped=set())]
    assert "เกลือ" in names and "เกลือป่น" in names


def test_blank_and_null_names_are_dropped() -> None:
    assert len(build_worklist(ROWS, mapped=set())) == 3


def test_ties_are_broken_by_string_for_a_stable_order() -> None:
    wl = build_worklist(ROWS, mapped=set())
    assert [r.name_th for r in wl[1:]] == sorted(["เกลือ", "เกลือป่น"])


def test_cumulative_share_ends_at_one() -> None:
    wl = build_worklist(ROWS, mapped=set())
    assert [round(r.cum_share, 4) for r in wl] == [round(4 / 6, 4), round(5 / 6, 4), 1.0]
    assert rank_reaching(wl, 0.5) == 1
    assert rank_reaching(wl, 0.99) == 3


def test_key_is_nfc_and_whitespace_only() -> None:
    decomposed = unicodedata.normalize("NFD", "น้ำปลา")
    assert key(f"  {decomposed}\t ") == "น้ำปลา"
    assert key("พริก  แห้ง") == "พริก แห้ง"  # collapsed, not removed


def test_mapped_flags_existing_aliases_after_normalisation() -> None:
    wl = build_worklist(ROWS, mapped={" หอมแดง "})
    assert {r.name_th: r.mapped for r in wl} == {
        "หอมแดง": True, "เกลือ": False, "เกลือป่น": False,
    }
