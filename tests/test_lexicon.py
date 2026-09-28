"""The hand-authored lexicon: src/clean/lexicon.py and scripts/load_lexicon.py.

File-level tests write synthetic CSVs to a temp directory. Database tests use IDs of
the form ``_TEST_LEX_*``, which the ``ING_nnnn`` pattern can never produce, so their
cleanup cannot touch a real lexicon entry. Includes CLAUDE.md §13's
``test_conflation_guard``.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from scripts.load_lexicon import LEXICON_DIR, load
from src.clean.lexicon import (
    ALIAS_COLUMNS,
    ALIASES_FILE,
    CANONICAL_COLUMNS,
    CANONICAL_FILE,
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
        "ING_0001,พริกขี้หนู,bird's eye chilli,chilli,,small and hot",
        "ING_0002,พริกชี้ฟ้า,spur chilli,chilli,,",
    ],
    ALIASES_FILE: ["พริกขี้หนูสวน,ING_0001", "พริกขี้หนู,ING_0001"],
    CONFLATIONS_FILE: ["ING_0002,ING_0001,different heat and use"],
}


def _write(tmp: Path, files: dict[str, list[str]]) -> Path:
    headers = {CANONICAL_FILE: CANONICAL_COLUMNS, ALIASES_FILE: ALIAS_COLUMNS,
               CONFLATIONS_FILE: CONFLATION_COLUMNS}
    for name, columns in headers.items():
        lines = [",".join(columns), *files.get(name, [])]
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
        CANONICAL_FILE: [f"ING_0001,  {decomposed} ,fish sauce,condiment,,"],
    }))
    assert lex.canonicals[0].name_th == "น้ำปลา"


@pytest.mark.parametrize(
    ("files", "message"),
    [
        ({CANONICAL_FILE: ["ING_1,พริก,chilli,chilli,,"]}, "not ING_ followed by 4 digits"),
        ({CANONICAL_FILE: ["ING_0001,พริก,chilli,chilli,,",
                           "ING_0001,ข่า,galangal,rhizome,,"]}, "used twice"),
        ({CANONICAL_FILE: ["ING_0001,พริก,,chilli,,"]}, "name_en is required"),
        ({CANONICAL_FILE: ["ING_0001,พริก,chilli,,,"]}, "category is required"),
        ({CANONICAL_FILE: ["ING_0001,พริก,chilli,chilli,,",
                           "ING_0002,พริก,chilli 2,chilli,,"]}, "already ING_0001"),
        ({CANONICAL_FILE: ["ING_0001,พริก,chilli,chilli,,"],
          ALIASES_FILE: ["พริกแห้ง,ING_0009"]}, "not an entry"),
        ({CANONICAL_FILE: ["ING_0001,พริก,chilli,chilli,,",
                           "ING_0002,ข่า,galangal,rhizome,,"],
          ALIASES_FILE: ["พริก,ING_0002"]}, "is the name of ING_0001"),
        ({CANONICAL_FILE: ["ING_0001,พริก,chilli,chilli,,",
                           "ING_0002,ข่า,galangal,rhizome,,"],
          ALIASES_FILE: ["x,ING_0001", "x,ING_0002"]}, "maps to both"),
        ({CANONICAL_FILE: ["ING_0001,พริก,chilli,chilli,,"],
          CONFLATIONS_FILE: ["ING_0001,ING_0001,same"]}, "conflated with itself"),
        ({CANONICAL_FILE: ["ING_0001,พริก,chilli,chilli,,",
                           "ING_0002,ข่า,galangal,rhizome,,"],
          CONFLATIONS_FILE: ["ING_0001,ING_0002,"]}, "reason is required"),
        ({CANONICAL_FILE: ["ING_0001,พริก,chilli,chilli,,นางสมหญิง ทดสอบ said so"]},
         "personal data"),
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
            CANONICAL_FILE: ["ING_1,พริก,chilli,chilli,,", "ING_0002,ข่า,,rhizome,,"],
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
        canonicals=[Canonical(A, NAME_A, "test a", "test", None, None),
                    Canonical(B, NAME_B, "test b", "test", None, "a note")],
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
    edited.canonicals[0] = Canonical(A, NAME_A, "test a, edited", "test", None, None)
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
    edited.canonicals[0] = Canonical(A, NAME_A, "should not land", "test", None, None)
    edited.aliases.pop(NAME_B)  # the file no longer re-points it, so the DB row stands
    with pytest.raises(LexiconError, match="across a conflation pair"):
        load(edited)
    assert _db("SELECT name_en FROM canonical_ingredients WHERE canonical_id = %s", A) == [
        ("test a",)
    ]


def test_conflation_guard() -> None:
    """CLAUDE.md §13: no alias maps across an ingredient_conflations pair."""
    assert _db(CONFLATION_VIOLATIONS) == []
