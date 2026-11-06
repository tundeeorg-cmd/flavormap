"""scripts/lexicon_worklist.py — ranks strings for HD-6 without merging any of them.

Pure-function tests on synthetic rows; no database needed.
"""

from __future__ import annotations

import unicodedata

import pytest

from scripts.lexicon_worklist import (
    CONFLICT,
    SIMILARITY_THRESHOLD,
    build_worklist,
    category_check,
    key,
    mapping_index,
    rank_reaching,
    ranks_by_source,
    similar_strings,
)
from src import config
from src.clean.lexicon import strip_quantity

ROWS = [
    ("dcp_food", "official", 1, "หอมแดง"),
    ("dcp_food", "official", 2, "หอมแดง"),
    ("dcp_food", "official", 3, "หอมแดง"),
    ("dcp_food", "official", 1, "หอมแดง"),     # same recipe twice: counts once
    ("kapook_cooking", "commercial", 9, "หอมแดง"),
    ("dcp_food", "official", 1, "เกลือ"),
    ("dcp_food", "official", 2, "เกลือป่น"),    # a variant: stays its own row (rule 4)
    ("dcp_food", "official", 3, None),
    ("dcp_food", "official", 3, "   "),
]


def test_ranked_by_distinct_recipes_with_per_source_counts() -> None:
    wl = build_worklist(ROWS, mapped={})
    top = wl[0]
    assert (top.rank, top.name_th, top.n_recipes) == (1, "หอมแดง", 4)
    assert top.by_source == {"dcp_food": 3, "kapook_cooking": 1}
    assert top.by_register == {"official": 3, "commercial": 1}


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
    lines = category_check({"aromatic": 18, "other": 2, "condiment": 1}, [])
    text = "\n".join(lines)
    assert "not in HD-27's list: condiment" in text
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


# ── HD-33: similar strings, display only ──────────────────────────────────────

def test_the_threshold_is_hd33s() -> None:
    assert SIMILARITY_THRESHOLD == 0.8


def test_similar_strings_are_exactly_title_similarity_at_the_threshold() -> None:
    """The cheap bounds must never change the result: compare against a brute force."""
    from src.clean.dedupe import title_similarity

    names = ["หอมแดง", "หอมหัวแดง", "หอมแดงซอย", "หอมแดง 3 หัว", "กระเทียม", "กระทียม",
             "เกลือ", "เกลือป่น", "น้ำปลา", "น้ำเปล่า"]
    got = similar_strings(names, 0.8, only=set(names))
    for a in names:
        expected = sorted(((b, title_similarity(a, b)) for b in names
                           if b != a and title_similarity(a, b) >= 0.8),
                          key=lambda p: (-p[1], p[0]))
        assert got[a] == expected, a


def test_neighbours_are_listed_for_unmapped_strings_only_and_never_map() -> None:
    rows = [("dcp_food", "official", 1, "หอมแดง"), ("dcp_food", "official", 2, "หอมหัวแดง"),
            ("dcp_food", "official", 3, "กระเทียม"), ("dcp_food", "official", 4, "กระทียม")]
    wl = build_worklist(rows, mapped=mapping_index([("กระเทียม", "ING_0001", "aromatic")]))
    by = {r.name_th: r for r in wl}
    assert [n for n, _ in by["หอมแดง"].similar] == ["หอมหัวแดง"]
    assert by["กระเทียม"].similar == ()            # mapped: no neighbours listed
    assert [n for n, _ in by["กระทียม"].similar] == ["กระเทียม"]
    # Neighbours never become mappings, glosses or categories.
    assert by["กระทียม"].canonical_id is None and by["กระทียม"].category is None
    assert not by["หอมแดง"].mapped and not by["หอมหัวแดง"].mapped


def test_a_higher_threshold_shows_fewer_neighbours() -> None:
    names = ["หอมแดง", "หอมหัวแดง", "หอมแดงซอย"]
    assert len(similar_strings(names, 0.8, set(names))["หอมแดง"]) == 2
    assert similar_strings(names, 0.95, set(names))["หอมแดง"] == []


def test_rows_are_ordered_by_frequency_descending() -> None:
    wl = build_worklist(ROWS, mapped={})
    counts = [r.n_recipes for r in wl]
    assert counts == sorted(counts, reverse=True)


# ── the worklist never writes to the lexicon ──────────────────────────────────

def test_the_worklist_source_contains_no_write_statement() -> None:
    import re
    from pathlib import Path

    import scripts.lexicon_worklist as wl

    source = Path(wl.__file__).read_text(encoding="utf-8")
    assert not re.search(r"\b(INSERT|UPDATE|DELETE|TRUNCATE|MERGE|COPY)\b", source)


def test_running_the_worklist_leaves_the_lexicon_untouched(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Runs main() against the real database on a small slice (monkeypatched query) and
    checks that canonical_ingredients and ingredient_aliases are byte-for-byte unchanged,
    and that the session it used was read-only."""
    import sys

    import psycopg

    import scripts.lexicon_worklist as wl
    from src.db import get_connection

    def fingerprint() -> tuple[object, ...]:
        conn = get_connection()
        try:
            return tuple(conn.execute(q).fetchone()[0] for q in (  # type: ignore[index]
                "SELECT md5(coalesce(string_agg(t::text, '|' ORDER BY canonical_id), '')) "
                "FROM canonical_ingredients t",
                "SELECT md5(coalesce(string_agg(t::text, '|' ORDER BY alias), '')) "
                "FROM ingredient_aliases t",
            ))
        finally:
            conn.close()

    seen: list[psycopg.Connection] = []  # type: ignore[type-arg]

    def spying_connection() -> psycopg.Connection:  # type: ignore[type-arg]
        conn = get_connection()
        seen.append(conn)
        return conn

    before = fingerprint()
    monkeypatch.setattr(wl, "get_connection", spying_connection)
    monkeypatch.setattr(wl, "QUERY", wl.QUERY.replace("FROM recipes r",
                                                      "FROM (SELECT * FROM recipes LIMIT 20) r"))
    monkeypatch.setattr(sys, "argv", ["worklist", "--out", str(tmp_path / "w.csv")])
    assert wl.main() == 0
    assert fingerprint() == before
    assert (tmp_path / "w.csv").exists()

    # The connection main() used was read-only from its first statement, and that
    # setting makes Postgres refuse a write to the lexicon.
    [conn] = seen
    assert conn.read_only is True
    probe = get_connection()
    probe.read_only = True
    try:
        with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
            probe.execute("INSERT INTO canonical_ingredients (canonical_id, name_th, "
                          "name_en, category, is_fermented) VALUES ('_X','x','x','other',false)")
    finally:
        probe.rollback()
        probe.close()


# --- HD-6 question 6: the quantity-stripping prototype (OFF by default) ---------------

def test_quantity_stripping_is_off_by_default() -> None:
    assert config.STRIP_QUANTITIES is False
    assert key("ไข่ไก่ 2 ฟอง") == "ไข่ไก่ 2 ฟอง"


@pytest.mark.parametrize(("raw", "stripped"), [
    ("ไข่ไก่ 2 ฟอง", "ไข่ไก่"),
    ("เกลือ 1/4 ช้อนชา", "เกลือ"),
    ("ข้าวคั่ว 1 1/2 ช้อนโต๊ะ", "ข้าวคั่ว"),
    ("พริกขี้หนูสด จำนวน 20 เม็ด", "พริกขี้หนูสด"),     # สด stays: HD-6 question 2
    ("หัวกะทิ 2 ¾ ถ้วยตวง 605", "หัวกะทิ"),
    ("►กระเทียมจีนกลีบใหญ่ 10-12 กลีบ", "กระเทียมจีนกลีบใหญ่"),
    ("แป้งมันสำปะหลัง 1 ช้อนชา + 1/2 ช้อนชา", "แป้งมันสำปะหลัง"),
    ("เนยสด (อุณภูมิห้อง) 50 กรัม", "เนยสด (อุณภูมิห้อง)"),  # parentheses stay
    ("น้ำเปล่า 1,000 มล.", "น้ำเปล่า"),
    ("หัวปลี -๔", "หัวปลี"),                               # Thai digits
    ("เกลือนิดหน่อย", "เกลือ"),                              # amount word, no number
    ("กระเทียมสับ", "กระเทียมสับ"),                          # prep word stays
])
def test_strip_quantity_removes_amounts_only(raw: str, stripped: str) -> None:
    assert strip_quantity(raw) == stripped
    assert key(raw, strip_quantities=True) == stripped


@pytest.mark.parametrize("name", ["ใบมะกรูด", "หัวกะทิ", "ต้นหอม", "ไข่ไก่", "รากผักชี"])
def test_unit_words_without_a_number_are_never_stripped(name: str) -> None:
    assert strip_quantity(name) == name


def test_known_false_positive_a_number_inside_a_variety_name() -> None:
    # RD6 glutinous rice: the 6 is part of the name, and the prototype removes it.
    # Recorded as evidence for HD-6 question 6, not fixed by guessing.
    assert strip_quantity("ข้าวเหนียวพันธุ์ กข. 6") == "ข้าวเหนียวพันธุ์ กข."


def test_stripping_merges_lines_into_fewer_worklist_strings() -> None:
    rows = [("kapook_cooking", "commercial", 1, "ไข่ไก่ 2 ฟอง"),
            ("kapook_cooking", "commercial", 2, "ไข่ไก่ 3 ฟอง"),
            ("dcp_food", "official", 3, "ไข่ไก่")]
    assert len(build_worklist(rows, {})) == 3
    on = build_worklist(rows, {}, strip_quantities=True)
    assert [(r.name_th, r.n_recipes) for r in on] == [("ไข่ไก่", 3)]


def test_ranks_by_source_ranks_each_source_on_its_own() -> None:
    rows = [("a", "commercial", i, "x") for i in range(8)]
    rows += [("a", "commercial", 8, "y"), ("a", "commercial", 9, "z")]
    rows += [("b", "official", 1, "p 1 ช้อนชา"), ("b", "official", 2, "p 2 ช้อนชา")]
    off = ranks_by_source(rows, strip_quantities=False)
    assert off["a"] == (10, 3, [1, 2])
    assert off["b"] == (2, 2, [2, 2])
    assert ranks_by_source(rows, strip_quantities=True)["b"] == (2, 1, [1, 1])
