"""scripts/lexicon_worklist.py — ranks strings for HD-6 without merging any of them.

Pure-function tests on synthetic rows; no database needed.
"""

from __future__ import annotations

import unicodedata

from scripts.lexicon_worklist import (
    CONFLICT,
    build_worklist,
    category_check,
    key,
    mapping_index,
    rank_reaching,
)

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
    wl = build_worklist(ROWS, mapped={})
    top = wl[0]
    assert (top.rank, top.name_th, top.n_recipes) == (1, "หอมแดง", 4)
    assert top.by_source == {"dcp_food": 3, "kapook_cooking": 1}


def test_variants_are_never_merged() -> None:
    names = [r.name_th for r in build_worklist(ROWS, mapped={})]
    assert "เกลือ" in names and "เกลือป่น" in names


def test_blank_and_null_names_are_dropped() -> None:
    assert len(build_worklist(ROWS, mapped={})) == 3


def test_ties_are_broken_by_string_for_a_stable_order() -> None:
    wl = build_worklist(ROWS, mapped={})
    assert [r.name_th for r in wl[1:]] == sorted(["เกลือ", "เกลือป่น"])


def test_cumulative_share_ends_at_one() -> None:
    wl = build_worklist(ROWS, mapped={})
    assert [round(r.cum_share, 4) for r in wl] == [round(4 / 6, 4), round(5 / 6, 4), 1.0]
    assert rank_reaching(wl, 0.5) == 1
    assert rank_reaching(wl, 0.99) == 3


def test_key_is_nfc_and_whitespace_only() -> None:
    decomposed = unicodedata.normalize("NFD", "น้ำปลา")
    assert key(f"  {decomposed}\t ") == "น้ำปลา"
    assert key("พริก  แห้ง") == "พริก แห้ง"  # collapsed, not removed


def test_mapped_flags_existing_aliases_after_normalisation() -> None:
    wl = build_worklist(ROWS, mapped=mapping_index([(" หอมแดง ", "ING_0001", "aromatic")]))
    assert {r.name_th: r.mapped for r in wl} == {
        "หอมแดง": True, "เกลือ": False, "เกลือป่น": False,
    }


def test_mapped_strings_carry_their_entry_and_category_unmapped_stay_blank() -> None:
    wl = build_worklist(ROWS, mapped=mapping_index([
        ("หอมแดง", "ING_0001", "aromatic"),
        ("เกลือป่น", "ING_0002", "other"),
    ]))
    by_name = {r.name_th: (r.canonical_id, r.category) for r in wl}
    assert by_name == {
        "หอมแดง": ("ING_0001", "aromatic"),
        "เกลือป่น": ("ING_0002", "other"),
        "เกลือ": (None, None),  # never a suggested category
    }


def test_a_string_mapped_to_two_entries_is_a_conflict() -> None:
    index = mapping_index([
        ("หอมแดง", "ING_0001", "aromatic"),
        ("หอมแดง", "ING_0001", "aromatic"),  # the same mapping twice is fine
        ("เกลือ", "ING_0002", "other"),
        ("เกลือ", "ING_0003", "other"),
    ])
    assert index["หอมแดง"] == ("ING_0001", "aromatic")
    assert index["เกลือ"] == (CONFLICT, CONFLICT)
    wl = build_worklist(ROWS, mapped=index)
    assert any("mapped to more than one entry: เกลือ" in line
               for line in category_check({"other": 2}, wl))


def test_category_check_with_no_entries() -> None:
    assert category_check({}, []) == [
        "lexicon: no entries yet, so there is nothing to check against HD-27"
    ]


def test_category_check_lists_hd27_order_and_the_other_share() -> None:
    lines = category_check({"aromatic": 19, "other": 1}, [])
    assert lines[0].startswith("lexicon entries by HD-27 category: aromatic 19, chilli 0,")
    assert lines[0].endswith("other 1")
    assert "'other': 1 of 20 entries (5.0%)" in lines[1]
    assert "ceiling" not in lines[1]  # exactly 5% is allowed


def test_category_check_flags_other_over_the_ceiling_and_unknown_categories() -> None:
    lines = category_check({"aromatic": 18, "other": 2, "seasoning": 1}, [])
    text = "\n".join(lines)
    assert "not in HD-27's list: seasoning" in text
    assert "(9.5%)" in text and "over HD-27's 5% ceiling" in text


def test_category_check_reports_corpus_coverage_by_category() -> None:
    wl = build_worklist(ROWS, mapped=mapping_index([
        ("หอมแดง", "ING_0001", "aromatic"), ("เกลือ", "ING_0002", "other"),
    ]))
    [coverage] = [line for line in category_check({"aromatic": 1, "other": 1}, wl)
                  if "cover" in line]
    # 6 (recipe, string) pairs: หอมแดง 4, เกลือ 1, เกลือป่น 1 (unmapped).
    assert "mapped strings cover 83.3%" in coverage
    assert "aromatic 66.7%, other 16.7%" in coverage
