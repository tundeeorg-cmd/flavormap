"""The §4 ingredient table is read by column position, not by whitespace.

Whitespace is not a reliable column separator in this corpus: an extraction may put two
spaces between an ingredient and its quantity on one row and none on the next, and a row
whose text wraps continues on a line carrying no index number. Reading the table that
way recovered ingredients from only 75 of 231 documents; reading it by x-position
recovers 181.

Columns come from the data rather than the header, because header cells sit at a
different x than the data beneath them — "ชื่อวัตถุดิบ" is set at x≈137 above data at
x≈93, so header-derived boundaries put the ingredient name in the index column.
"""

from __future__ import annotations

import pytest

from src.config import RAW_DIR
from src.ingest.dcp_form import parse_pdf
from src.ingest.pdf_layout import TextRun, extract_table

RAW = RAW_DIR / "dcp_food"


def _run(text: str, x: float, y: float) -> TextRun:
    return TextRun(text=text, font="THSarabun", x=x, y=y, page=0)


def test_columns_are_inferred_from_data_not_from_the_header() -> None:
    """Header cells are offset from their data. Anchoring on them mis-assigns column 1."""
    runs = [
        # header: name cell at x=137, above data at x=93
        _run("ที่", 66, 230), _run("ชื่อวัตถุดิบ", 137, 230),
        _run("สรรพคุณ", 324, 230), _run("ที่มา", 453, 230),
        _run("๑", 66, 211), _run("ใบขี้เหล็ก", 93, 211),
        _run("ฟอสฟอรัส", 290, 211), _run("ตลาดชุมชน", 410, 211),
        _run("๒", 66, 193), _run("หนังหมูเผา", 93, 193),
        _run("แคลเซียม", 290, 193), _run("ตลาดชุมชน", 410, 193),
    ]
    rows = extract_table(runs, 4)
    assert [r.cell(1) for r in rows[-2:]] == ["ใบขี้เหล็ก", "หนังหมูเผา"]
    assert [r.cell(3) for r in rows[-2:]] == ["ตลาดชุมชน", "ตลาดชุมชน"]


def test_wrapped_row_is_joined_to_the_row_above() -> None:
    """A continuation line has no index number and must not become its own ingredient."""
    runs = [
        _run("๕", 66, 137), _run("เครื่องแกง (ข่า ตะไคร้", 93, 137),
        _run("ธาตุเหล็ก", 290, 137), _run("ปลูกเองที่บ้าน", 410, 137),
        _run("เกลือเม็ด) ทั้งหมด", 93, 119),
        _run("๖", 66, 100), _run("ปลาย่าง", 93, 100),
        _run("โปรตีน", 290, 100), _run("ตลาดชุมชน", 410, 100),
    ]
    rows = extract_table(runs, 4)
    assert len(rows) == 2
    assert "เกลือเม็ด" in rows[0].cell(1)
    assert rows[1].cell(1) == "ปลาย่าง"


def test_a_single_busy_row_does_not_invent_a_column() -> None:
    """Columns are scored by how many rows they appear on, not by run count."""
    runs = [
        _run("๑", 66, 200), _run("ก", 93, 200), _run("ข", 150, 200),
        _run("ค", 200, 200), _run("ง", 250, 200), _run("จ", 410, 200),
        _run("๒", 66, 180), _run("ฉ", 93, 180), _run("ช", 410, 180),
        _run("๓", 66, 160), _run("ซ", 93, 160), _run("ฌ", 410, 160),
    ]
    rows = extract_table(runs, 3)
    assert rows[1].cell(0) == "๒" and rows[1].cell(2) == "ช"


@pytest.mark.skipif(not RAW.exists(), reason="raw corpus not present")
def test_real_table_parses_with_quantities_and_acquisition() -> None:
    record = parse_pdf(RAW / "north_1_1.pdf")
    assert len(record.ingredients) == 8

    first = record.ingredients[0]
    assert first.name_th == "ใบขี้เหล็ก"
    assert (first.quantity_value, first.quantity_unit) == ("100", "กรัม")
    assert first.acquisition_mode == "foraged"       # ข้างริมคลองในชุมชน

    wrapped = record.ingredients[4]
    assert wrapped.position == 5
    assert wrapped.name_th.startswith("เครื่องแกง")

    # ปลุกเองที่บ้าน — a misspelling of ปลูกเอง that appears in the corpus
    assert record.ingredients[3].acquisition_mode == "grown"


@pytest.mark.skipif(not RAW.exists(), reason="raw corpus not present")
def test_scanned_documents_yield_no_ingredients_rather_than_junk() -> None:
    record = parse_pdf(RAW / "east_5_1.pdf")
    assert record.ingredients == []
    assert any("no ingredient rows" in n for n in record.notes)
