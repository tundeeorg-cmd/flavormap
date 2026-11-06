"""The hand-authored lexicon: src/clean/lexicon.py and scripts/load_lexicon.py.

File-level tests write synthetic CSVs to a temp directory. Database tests use IDs of
the form ``_TEST_LEX_*``, which the ``ING_nnnn`` pattern can never produce, so their
cleanup cannot touch a real lexicon entry. Includes CLAUDE.md §13's
``test_conflation_guard``.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

import pytest

from scripts.load_lexicon import LEXICON_DIR, load
from src.clean.lexicon import (
    ALIAS_COLUMNS,
    ALIASES_FILE,
    CANONICAL_COLUMNS,
    CANONICAL_FILE,
    CATEGORIES,
    CONFLATION_COLUMNS,
    CONFLATION_VIOLATIONS,
    CONFLATIONS_FILE,
    Canonical,
    Conflation,
    Lexicon,
    LexiconError,
    read_lexicon,
)
from src.db import get_connection

GOOD = {
    CANONICAL_FILE: [
        "ING_0001,พริกขี้หนู,bird's eye chilli,chilli,false,,small and hot",
        "ING_0002,พริกชี้ฟ้า,spur chilli,chilli,false,,",
    ],
    ALIASES_FILE: ["พริกขี้หนูสวน,ING_0001", "พริกขี้หนู,ING_0001"],
    CONFLATIONS_FILE: ["ING_0002,ING_0001,different heat and use"],
}


def _with_provenance(line: str) -> str:
    """Entry rows written before the provenance columns get ``drafted_by = bo``."""
    return line + ",bo," if line.count(",") == 6 else line


def _write(tmp: Path, files: dict[str, list[str]]) -> Path:
    headers = {CANONICAL_FILE: CANONICAL_COLUMNS, ALIASES_FILE: ALIAS_COLUMNS,
               CONFLATIONS_FILE: CONFLATION_COLUMNS}
    for name, columns in headers.items():
        rows = files.get(name, [])
        if name == CANONICAL_FILE:
            rows = [_with_provenance(r) for r in rows]
        lines = [",".join(columns), *rows]
        (tmp / name).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return tmp


# ── files ─────────────────────────────────────────────────────────────────────

def test_valid_files(tmp_path: Path) -> None:
    lex = read_lexicon(_write(tmp_path, GOOD))
    assert [c.canonical_id for c in lex.canonicals] == ["ING_0001", "ING_0002"]
    # Each entry's own name is an alias of itself; the listed duplicate is harmless.
    assert lex.aliases == {
        "พริกขี้หนู": "ING_0001", "พริกชี้ฟ้า": "ING_0002", "พริกขี้หนูสวน": "ING_0001",
    }
    # Stored lower ID first, whichever order the file used.
    assert lex.conflations == [Conflation("ING_0001", "ING_0002", "different heat and use")]
    assert lex.canonicals[1].regional_note is None


def test_strings_are_nfc_and_whitespace_normalised(tmp_path: Path) -> None:
    import unicodedata

    decomposed = unicodedata.normalize("NFD", "น้ำปลา")
    lex = read_lexicon(_write(tmp_path, {
        CANONICAL_FILE: [f"ING_0001,  {decomposed} ,fish sauce,protein_fish,true,,"],
    }))
    assert lex.canonicals[0].name_th == "น้ำปลา"
    assert lex.canonicals[0].is_fermented is True


def test_categories_are_hd27s_sixteen() -> None:
    """HD-27's fifteen, plus `seasoning` (HD-27 amendment, 2026-11-06)."""
    assert len(CATEGORIES) == len(set(CATEGORIES)) == 16
    assert "seasoning" in CATEGORIES and "fermented" not in CATEGORIES
    assert {"coconut", "acid", "other"} <= set(CATEGORIES)
    assert CATEGORIES[-1] == "other"


def _entries(n: int, n_other: int) -> list[str]:
    return [f"ING_{i:04d},ทดสอบ{i},test {i},{'other' if i < n_other else 'herb'},false,,"
            for i in range(n)]


def test_other_at_exactly_five_percent_is_allowed(tmp_path: Path) -> None:
    read_lexicon(_write(tmp_path, {CANONICAL_FILE: _entries(20, 1)}))


def test_other_over_five_percent_stops_the_load(tmp_path: Path) -> None:
    with pytest.raises(LexiconError, match=r"2 of 20 entries \(10.0%\).*limitations.md"):
        read_lexicon(_write(tmp_path, {CANONICAL_FILE: _entries(20, 2)}))


@pytest.mark.parametrize(
    ("files", "message"),
    [
        ({CANONICAL_FILE: ["ING_1,พริก,chilli,chilli,false,,"]}, "not ING_ followed by 4 digits"),
        ({CANONICAL_FILE: ["ING_0001,พริก,chilli,chilli,false,,",
                           "ING_0001,ข่า,galangal,aromatic,false,,"]}, "used twice"),
        ({CANONICAL_FILE: ["ING_0001,พริก,,chilli,false,,"]}, "name_en is required"),
        ({CANONICAL_FILE: ["ING_0001,พริก,chilli,,false,,"]}, "category is required"),
        ({CANONICAL_FILE: ["ING_0001,พริก,chilli,chilli,false,,",
                           "ING_0002,พริก,chilli 2,chilli,false,,"]}, "already ING_0001"),
        ({CANONICAL_FILE: ["ING_0001,พริก,chilli,chilli,false,,"],
          ALIASES_FILE: ["พริกแห้ง,ING_0009"]}, "not an entry"),
        ({CANONICAL_FILE: ["ING_0001,พริก,chilli,chilli,false,,",
                           "ING_0002,ข่า,galangal,aromatic,false,,"],
          ALIASES_FILE: ["พริก,ING_0002"]}, "is the name of ING_0001"),
        ({CANONICAL_FILE: ["ING_0001,พริก,chilli,chilli,false,,",
                           "ING_0002,ข่า,galangal,aromatic,false,,"],
          ALIASES_FILE: ["x,ING_0001", "x,ING_0002"]}, "maps to both"),
        ({CANONICAL_FILE: ["ING_0001,พริก,chilli,chilli,false,,"],
          CONFLATIONS_FILE: ["ING_0001,ING_0001,same"]}, "conflated with itself"),
        ({CANONICAL_FILE: ["ING_0001,พริก,chilli,chilli,false,,",
                           "ING_0002,ข่า,galangal,aromatic,false,,"],
          CONFLATIONS_FILE: ["ING_0001,ING_0002,"]}, "reason is required"),
        ({CANONICAL_FILE: ["ING_0001,พริก,chilli,chilli,false,,นางสมหญิง ทดสอบ said so"]},
         "personal data"),
        ({CANONICAL_FILE: ["ING_0001,กะปิ,shrimp paste,condiment,true,,"]},
         "not in HD-27's list"),
        ({CANONICAL_FILE: ["ING_0001,ปลาร้า,fermented fish,fermented,true,,"]},
         "not in HD-27's list"),
        ({CANONICAL_FILE: ["ING_0001,พริก,chilli,chilli,,,"]}, "is_fermented must be"),
        ({CANONICAL_FILE: ["ING_0001,พริก,chilli,chilli,no,,"]}, "is_fermented must be"),
    ],
)
def test_invalid_lexicons_are_refused(
    tmp_path: Path, files: dict[str, list[str]], message: str
) -> None:
    with pytest.raises(LexiconError, match=message):
        read_lexicon(_write(tmp_path, files))


def test_every_problem_is_reported_at_once(tmp_path: Path) -> None:
    with pytest.raises(LexiconError) as exc:
        read_lexicon(_write(tmp_path, {
            CANONICAL_FILE: ["ING_1,พริก,chilli,chilli,false,,", "ING_0002,ข่า,,aromatic,false,,"],
        }))
    assert "ING_ followed by 4 digits" in str(exc.value)
    assert "name_en is required" in str(exc.value)


def test_a_wrong_header_is_refused(tmp_path: Path) -> None:
    _write(tmp_path, {})
    (tmp_path / ALIASES_FILE).write_text("canonical_id,alias\n", encoding="utf-8")
    with pytest.raises(LexiconError, match="header must be exactly"):
        read_lexicon(tmp_path)


def test_the_committed_lexicon_files_are_valid() -> None:
    read_lexicon(LEXICON_DIR)


# ── database ──────────────────────────────────────────────────────────────────

A, B = "_TEST_LEX_A", "_TEST_LEX_B"
NAME_A, NAME_B = "ทดสอบพริกก", "ทดสอบพริกข"


@pytest.fixture
def cleanup() -> Iterator[None]:
    yield
    conn = get_connection()
    try:
        conn.execute("DELETE FROM ingredient_aliases WHERE canonical_id IN (%s, %s)", (A, B))
        conn.execute("DELETE FROM ingredient_conflations WHERE canonical_id_a IN (%s, %s)",
                     (A, B))
        conn.execute("DELETE FROM canonical_ingredients WHERE canonical_id IN (%s, %s)",
                     (A, B))
        conn.commit()
    finally:
        conn.close()


def _lexicon(**aliases: str) -> Lexicon:
    return Lexicon(
        canonicals=[Canonical(A, NAME_A, "test a", "other", False, None, None),
                    Canonical(B, NAME_B, "test b", "other", False, None, "a note")],
        aliases={NAME_A: A, NAME_B: B, **aliases},
        conflations=[Conflation(A, B, "test pair")],
    )


def _db(sql: str, *params: object) -> list[tuple[object, ...]]:
    conn = get_connection()
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def test_load_marks_everything_human_approved_and_manual(cleanup: None) -> None:
    load(_lexicon(ทดสอบพริกกสวน=A))
    assert _db("SELECT approved_by_human, decision_note FROM canonical_ingredients "
               "WHERE canonical_id = %s", B) == [(True, "a note")]
    assert set(_db("SELECT alias, match_method, approved_by_human FROM ingredient_aliases "
                   "WHERE canonical_id = %s", A)) == {
        (NAME_A, "manual", True), ("ทดสอบพริกกสวน", "manual", True),
    }


def test_reloading_updates_in_place(cleanup: None) -> None:
    load(_lexicon())
    edited = _lexicon()
    edited.canonicals[0] = Canonical(A, NAME_A, "test a, edited", "other", False, None, None)
    load(edited)
    assert _db("SELECT name_en FROM canonical_ingredients WHERE canonical_id = %s", A) == [
        ("test a, edited",)
    ]


def test_conflation_guard_aborts_a_load_and_writes_nothing(cleanup: None) -> None:
    load(_lexicon())
    # An alias arriving by another route: B's own name, pointed at A, across the pair.
    conn = get_connection()
    try:
        conn.execute("UPDATE ingredient_aliases SET canonical_id = %s, match_method = 'llm' "
                     "WHERE alias = %s", (A, NAME_B))
        conn.commit()
    finally:
        conn.close()
    edited = _lexicon()
    edited.canonicals[0] = Canonical(A, NAME_A, "should not land", "other", False, None, None)
    edited.aliases.pop(NAME_B)  # the file no longer re-points it, so the DB row stands
    with pytest.raises(LexiconError, match="across a conflation pair"):
        load(edited)
    assert _db("SELECT name_en FROM canonical_ingredients WHERE canonical_id = %s", A) == [
        ("test a",)
    ]


def test_code_and_database_agree_on_the_categories() -> None:
    """The list lives in two places, src/clean/lexicon.py and the CHECK constraint
    (migration 023, replaced by 029)."""
    [(definition,)] = _db(
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE conname = 'canonical_ingredients_category_check'"
    )
    assert set(re.findall(r"'([a-z_]+)'::text", str(definition))) == set(CATEGORIES)


def test_is_fermented_has_no_default() -> None:
    assert _db(
        "SELECT column_default, is_nullable FROM information_schema.columns "
        "WHERE table_name = 'canonical_ingredients' AND column_name = 'is_fermented'"
    ) == [(None, "NO")]


def test_conflation_guard() -> None:
    """CLAUDE.md §13: no alias maps across an ingredient_conflations pair."""
    assert _db(CONFLATION_VIOLATIONS) == []


def test_check_categories_is_hd27_ordered_and_counts_other() -> None:
    from src.clean.lexicon import check_categories

    check = check_categories({"other": 1, "aromatic": 19, "condiment": 2})
    assert list(check.by_category) == list(CATEGORIES)
    assert check.by_category["chilli"] == 0
    assert check.total == 22 and check.other == 1
    assert check.unknown == ["condiment"]
    assert round(check.other_share, 4) == round(1 / 22, 4)
    assert not check.over_ceiling
    assert check_categories({"other": 2, "herb": 18}).over_ceiling
    assert check_categories({}).other_share == 0.0


# ── provenance (2026-11-06) ────────────────────────────────────────────────────

def test_provenance_columns_and_trusted(tmp_path: Path) -> None:
    lex = read_lexicon(_write(tmp_path, {CANONICAL_FILE: [
        "ING_0001,พริก,chilli,chilli,false,,,bo,",
        "ING_0002,ข่า,galangal,aromatic,false,,,claude,",
        "ING_0003,ตะไคร้,lemongrass,aromatic,false,,,claude,2026-11-07",
    ]}))
    by_id = {c.canonical_id: c for c in lex.canonicals}
    assert [by_id[i].drafted_by for i in ("ING_0001", "ING_0002")] == ["bo", "claude"]
    assert by_id["ING_0003"].reviewed_by_bo == "2026-11-07"
    assert [by_id[i].trusted for i in ("ING_0001", "ING_0002", "ING_0003")] == [
        True, False, True]


@pytest.mark.parametrize(("line", "message"), [
    ("ING_0001,พริก,chilli,chilli,false,,,,", "drafted_by must be"),
    ("ING_0001,พริก,chilli,chilli,false,,,agent,", "drafted_by must be"),
    ("ING_0001,พริก,chilli,chilli,false,,,claude,yesterday", "reviewed_by_bo must be"),
    ("ING_0001,พริก,chilli,chilli,false,,,claude,2026-13-01", "reviewed_by_bo must be"),
])
def test_bad_provenance_is_refused(tmp_path: Path, line: str, message: str) -> None:
    with pytest.raises(LexiconError, match=message):
        read_lexicon(_write(tmp_path, {CANONICAL_FILE: [line]}))


def test_committed_lexicon_marks_every_entry_with_provenance() -> None:
    lex = read_lexicon(LEXICON_DIR)
    assert {c.drafted_by for c in lex.canonicals} <= {"bo", "claude"}
    assert all(c.reviewed_by_bo is None or c.drafted_by == "claude" for c in lex.canonicals)


def test_database_has_the_provenance_columns() -> None:
    assert _db(
        "SELECT column_name, is_nullable FROM information_schema.columns "
        "WHERE table_name = 'canonical_ingredients' "
        "AND column_name IN ('drafted_by', 'reviewed_by_bo') ORDER BY 1"
    ) == [("drafted_by", "NO"), ("reviewed_by_bo", "YES")]
