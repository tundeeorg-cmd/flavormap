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


# ── HD-15 / T1.12: scripts/acquisition.py (fills acquisition_modes after a rebuild) ──

def test_dcp_parser_infers_no_acquisition_mode() -> None:
    """HD-15: the 13 undecided keyword hints are gone; the parser keeps ที่มา verbatim."""
    from src.ingest import dcp_form
    assert not hasattr(dcp_form, "ACQUISITION_HINTS")
    assert not hasattr(dcp_form, "_acquisition_mode")


def test_acquisition_never_reads_the_old_parsed_mode() -> None:
    from scripts import acquisition
    assert "acquisition_mode'" not in acquisition.LINES_QUERY
    assert "acquisition_raw" in acquisition.LINES_QUERY


def test_acquisition_modes_parse_and_refuse() -> None:
    import pytest as _pytest

    from scripts.acquisition import CodingError, parse_modes
    assert parse_modes("market", "x") == ("market",)
    assert parse_modes(" grown | market |grown", "x") == ("grown", "market")
    assert parse_modes("local", "x") == ("local",)
    assert parse_modes("NONE", "x") == ()
    for bad in ("mixed", "grown|bought", "|"):
        with _pytest.raises(CodingError):
            parse_modes(bad, "x")


def test_acquisition_sheet_regeneration_keeps_codes(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from scripts.acquisition import COLUMNS, Line, merge_sheet, read_map, write_sheet
    lines = [Line(1, "ข่า", "ปลูกเอง"), Line(2, "ข่า", "ปลูกเอง"), Line(2, "พริก", "ตลาด"),
             Line(3, "เกลือ", "")]
    existing = [{"rank": "9", "acquisition_raw": "ตลาด", "n_rows": "5", "n_recipes": "5",
                 "modes": "market", "note": "mine"},
                {"rank": "3", "acquisition_raw": "หายไป", "n_rows": "2", "n_recipes": "1",
                 "modes": "local", "note": ""}]
    sheet = merge_sheet(lines, existing)
    assert [r["acquisition_raw"] for r in sheet] == ["ปลูกเอง", "ตลาด", "หายไป"]
    assert sheet[0] == {"rank": "1", "acquisition_raw": "ปลูกเอง", "n_rows": "2",
                        "n_recipes": "2", "modes": "", "note": ""}
    assert (sheet[1]["rank"], sheet[1]["n_rows"], sheet[1]["modes"], sheet[1]["note"]) \
        == ("2", "1", "market", "mine")
    assert (sheet[2]["n_rows"], sheet[2]["modes"]) == ("0", "local")
    path = tmp_path / "map.csv"
    write_sheet(sheet, path)
    assert path.read_text(encoding="utf-8").splitlines()[0] == ",".join(COLUMNS)
    assert read_map(path) == {"ตลาด": ("market",), "หายไป": ("local",)}


def test_acquisition_modes_are_the_union_over_lines_and_skip_none() -> None:
    from scripts.acquisition import Line, coverage, modes_by_row
    lines = [Line(1, "ข่า", "ปลูกเอง"), Line(1, "ข่าแก่", "ตลาด"), Line(2, "ข่า", "กรัม"),
             Line(3, "ข่า", "ไม่รู้"), Line(4, "ไม่มี", "ตลาด")]
    coding = {"ปลูกเอง": ("grown",), "ตลาด": ("market",), "กรัม": ()}
    entries = {"ข่า": ("ING_A",), "ข่าแก่": ("ING_A",)}
    rows = modes_by_row(lines, coding, lambda t: entries.get(t, ()))
    assert rows == {(1, "ING_A"): ("grown", "market")}
    c = coverage(lines, coding, rows)
    assert (c.with_text, c.strings, c.coded_strings, c.coded_none, c.lines_coded) == \
        (5, 4, 3, 1, 4)
    assert c.multi_mode_rows == 1 and c.by_mode == {"grown": 1, "market": 1}


def test_database_refuses_an_undecided_mode_and_the_retired_column() -> None:
    import psycopg
    import pytest as _pytest

    from src.db import get_connection
    conn = get_connection()
    try:
        row = conn.execute("SELECT recipe_id, canonical_id FROM recipe_ingredients LIMIT 1"
                           ).fetchone()
        if row is None:
            _pytest.skip("no recipe_ingredients rows")
        for sql, value in (("acquisition_modes = %s", ["mixed"]),
                           ("acquisition_modes = %s", []),
                           ("acquisition_mode = %s", "grown")):
            with _pytest.raises(psycopg.errors.CheckViolation):
                conn.execute(f"UPDATE recipe_ingredients SET {sql} "
                             "WHERE recipe_id = %s AND canonical_id = %s", (value, *row))
            conn.rollback()
    finally:
        conn.rollback()
        conn.close()
