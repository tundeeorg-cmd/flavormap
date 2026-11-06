"""The fallback ingredient reader in src/ingest/dcp_form.py.

Twenty official recipes had no ingredient lines: their §4 table breaks the row parser
(rows without numbers, a numbered benefits column, the row number on its own line below
the name, number and name sharing one x). The fallback reads the ingredient-name column
instead. It runs only when the row parser finds nothing, so documents the row parser
already reads cannot change. Synthetic runs below; the real-PDF tests skip when the raw
corpus is absent.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.config import RAW_DIR
from src.ingest.dcp_form import (
    _parse_ingredients,
    _parse_ingredients_fallback,
    parse_document,
    parse_pdf,
)
from src.ingest.pdf_layout import Document, TextRun

RAW = RAW_DIR / "dcp_food"
HEADER = [("ที่", 85, 300), ("ชื่อวัตถุดิบ/ เครื่องปรุง", 114, 300), ("สรรพคุณ", 313, 300),
          ("ที่มา", 494, 300)]


def _doc(rows: list[tuple[str, float, float]]) -> Document:
    runs = [TextRun(text=t, font="THSarabun", x=x, y=y, page=0) for t, x, y in rows]
    return Document(path=Path("synthetic.pdf"), runs=runs, raw_text="")


def test_unnumbered_rows_read_from_the_name_column_not_the_benefits_column() -> None:
    """The benefits column has more (wrapped) lines; the header cell picks the names."""
    doc = _doc(HEADER + [
        ("แป้งข้าวเหนียว", 112, 270), ("ให้คาร์โบไฮเดรตสูง", 225, 270),
        ("นุ่ม เหมาะสำหรับทำขนม", 225, 252),
        ("น้ำอ้อย", 112, 234), ("ให้ความหวานและกลิ่นหอม", 225, 234),
        ("ขนมมีสีน้ำตาลสวย", 225, 216),
        ("มะพร้าวขูด", 112, 197), ("เป็นแหล่งของใยอาหาร", 225, 197),
    ])
    assert _parse_ingredients(doc) == []
    assert [i.name_th for i in _parse_ingredients_fallback(doc)] == [
        "แป้งข้าวเหนียว", "น้ำอ้อย", "มะพร้าวขูด"]


def test_row_numbers_on_their_own_line_and_fused_numbers_are_stripped() -> None:
    doc = _doc(HEADER + [
        ("แป้งข้าวเหนียวดำ", 112, 270), ("1", 85, 262),
        ("๒.กะทิ", 112, 234),
        ("งาขาว ๑ ถ้วย", 112, 197), ("๓", 85, 189),
    ])
    names = [i.name_th for i in _parse_ingredients_fallback(doc)]
    assert names == ["แป้งข้าวเหนียวดำ", "กะทิ", "งาขาว"]


def test_fallback_stops_at_the_method_section() -> None:
    doc = _doc(HEADER + [
        ("พริก", 112, 270), ("กระเทียม", 112, 252),
        ("๓ วิธีการและขั้นตอนการปรุง", 85, 234), ("หอมแดง", 112, 216),
    ])
    assert [i.name_th for i in _parse_ingredients_fallback(doc)] == ["พริก", "กระเทียม"]


def test_a_benefits_only_result_is_discarded_rather_than_mapped() -> None:
    """When only health-claim text is readable, report nothing: a wrong list would map."""
    doc = _doc(HEADER + [
        ("ช่วยลดคอเลสเตอรอล", 120, 270), ("บำรุงสายตา", 120, 252),
        ("ป้องกันโรคหัวใจ", 120, 234), ("มีวิตามินสูง", 120, 216),
    ])
    assert _parse_ingredients_fallback(doc) == []


def test_fallback_does_not_run_when_the_row_parser_finds_rows() -> None:
    doc = _doc(HEADER + [
        ("๑", 85, 270), ("ใบขี้เหล็ก", 112, 270), ("ฟอสฟอรัส", 313, 270),
        ("ตลาดชุมชน", 494, 270),
        ("๒", 85, 252), ("หนังหมูเผา", 112, 252), ("แคลเซียม", 313, 252),
        ("ตลาดชุมชน", 494, 252),
    ])
    record = parse_document(doc)
    assert [i.name_th for i in record.ingredients] == ["ใบขี้เหล็ก", "หนังหมูเผา"]
    assert not any("fallback" in n for n in record.notes)


@pytest.mark.skipif(not RAW.exists(), reason="raw corpus not present")
@pytest.mark.parametrize(("ref", "expected"), [
    ("north_3_1.pdf", ["แป้งข้าวเหนียว", "แป้งข้าวเหนียวดำ", "น้ำอ้อย", "มะพร้าวขูด"]),
    ("northeast_14_2.pdf", ["ไก่ดำภูพาน", "พริกแห้ง", "พริกแดงจินดา", "เกลือ"]),
    ("south_14_1.pdf", ["ขี้ปลาโห๊ะที่ผ่านการหมักแล้ว", "กะทิ", "ใบมะกรูด"]),
    ("north_8_1.pdf", ["แป้ง"]),
])
def test_real_documents_that_had_no_ingredient_lines(ref: str, expected: list[str]) -> None:
    record = parse_pdf(RAW / ref)
    names = [i.name_th for i in record.ingredients]
    assert names[:len(expected)] == expected
    assert "ingredients read by the fallback name-column reader" in record.notes


@pytest.mark.skipif(not RAW.exists(), reason="raw corpus not present")
@pytest.mark.parametrize("ref", ["east_2_2.pdf", "north_12_3.pdf"])
def test_real_benefit_only_tables_stay_empty(ref: str) -> None:
    assert parse_pdf(RAW / ref).ingredients == []
