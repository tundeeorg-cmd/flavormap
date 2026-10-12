"""§1.1 of the DCP form: dish name and the dish's province (T0.3, 2026-10-06).

One test per layout pattern found among the 30 documents that failed to load. All text
here is synthetic. Field values are invented, and the §1.3 contact block uses the
ทดสอบ ("test") marker, as in tests/test_pdpa.py.

The rule these pin: the dish's province comes from §1.1 and nowhere else. §1.3's
จังหวัด is the submitter's address. It agreed with §1.1 in 192 of 192 loaded documents,
but it said เชียงราย on Suphan Buri's forms, and using it is an undecided attribution
choice (docs/decisions.md), not a parsing fix.
"""

from __future__ import annotations

from pathlib import Path

from src.ingest.dcp_form import parse_document
from src.ingest.pdf_layout import Document

ADDRESS = (
    "1.3 ชื่อผู้ให้ข้อมูล นางสมหญิง ทดสอบ\n"
    "ที่อยู่ เลขที่ ๙๙/๙ ตำบล ทดสอบ อำเภอ ทดสอบ\n"
    "จังหวัด {province} รหัสไปรษณีย์ ๑๐๑๐๐\n"
)


def _parse(section_1_1: str, address_province: str = "เชียงราย"):  # type: ignore[no-untyped-def]
    text = section_1_1 + "ประเภท อาหารคาว อาหารหวาน อาหารว่าง\n" + ADDRESS.format(
        province=address_province
    )
    return parse_document(Document(path=Path("synthetic.pdf"), raw_text=text))


def test_single_line_layout_is_read_as_before() -> None:
    rec = _parse("ชื่อเมนูอาหาร แกงทดสอบ จังหวัด ลำปาง\n")
    assert (rec.dish_name_th, rec.province_th) == ("แกงทดสอบ", "ลำปาง")


def test_section_1_1_broken_across_lines_is_read() -> None:
    """The Krabi layout (south_1_2, south_1_3): label, dish and province on separate
    lines between dot leaders."""
    rec = _parse("ชื่อเมนูอาหาร\n.......\nกุ้งทดสอบ\n...........\n\n"
                 "จังหวัด.........................\nกระบี่\n.....\n")
    assert (rec.dish_name_th, rec.province_th) == ("กุ้งทดสอบ", "กระบี่")


def test_no_province_in_section_1_1_is_none_even_with_an_address() -> None:
    """The Pattern A layout: §1.1 has no จังหวัด at all; only §1.3 names a province.
    The address is never used."""
    rec = _parse("ชื่อเมนูอาหาร ข้าวทดสอบ\n", address_province="นครพนม")
    assert rec.dish_name_th == "ข้าวทดสอบ"
    assert rec.province_th is None


def test_blank_section_1_1_is_none_not_the_submitters_province() -> None:
    """The Suphan Buri layout: §1.1's fields are dot leaders only, and the address is
    in another province entirely."""
    rec = _parse("ชื่อเมนูอาหาร..................................................จังหวัด"
                 "....................\n", address_province="เชียงราย")
    assert rec.dish_name_th is None
    assert rec.province_th is None


def test_the_fallback_never_overrides_a_single_line_match() -> None:
    rec = _parse("ชื่อเมนูอาหาร แกงทดสอบ จังหวัด ลำปาง\n.....\nจังหวัด\nน่าน\n")
    assert rec.province_th == "ลำปาง"


def test_a_dish_with_a_blank_province_field_has_no_province() -> None:
    """The east_8_1 layout: the dish name is filled in, the จังหวัด field is dot leaders."""
    rec = _parse("ชื่อเมนูอาหาร.......แกงทดสอบ..........จังหวัด..................\n",
                 address_province="สมุทรปราการ")
    assert rec.dish_name_th == "แกงทดสอบ"
    assert rec.province_th is None


def test_a_province_named_in_later_prose_is_not_the_dishs_province() -> None:
    """The north_10_3 layout: §1.1 has no จังหวัด; a province is named only in the
    narrative further down the form."""
    text = (
        "ชื่อเมนูอาหาร ข้าวทดสอบ\nประเภท อาหารคาว\n"
        "๒. ประวัติ เมนูนี้นิยมทำกันในจังหวัด เลย มาแต่เดิม\n"
    )
    rec = parse_document(Document(path=Path("synthetic.pdf"), raw_text=text))
    assert rec.dish_name_th == "ข้าวทดสอบ"
    assert rec.province_th is None


def test_no_section_1_1_label_means_no_dish_and_no_province() -> None:
    """The south_1_1 layout: a partial text layer with no §1.1 label at all."""
    text = "การผัด\nข้าวเหนียว\nจังหวัด กระบี่\n"
    rec = parse_document(Document(path=Path("synthetic.pdf"), raw_text=text))
    assert (rec.dish_name_th, rec.province_th) == (None, None)


def test_a_corrupted_section_label_is_not_read() -> None:
    """The south_9_2 / south_9_3 layout: Latin-1 mojibake turns ่ into É, so the label
    reads ชืÉอเมนูอาหาร. Its province is legible, but repairing mojibake is not this
    parser's job (CLAUDE.md §7.1: no blanket regex over Thai text), so it stays out."""
    rec = _parse("๑.๑ ชืÉอเมนูอาหาร แกงทดสอบ  จังหวัด ภูเก็ต\n")
    assert (rec.dish_name_th, rec.province_th) == (None, None)


def test_a_document_with_no_text_layer_yields_nothing() -> None:
    """The image-scan layout (east_5_*, and six others): the text layer is empty."""
    rec = parse_document(Document(path=Path("synthetic.pdf"), raw_text="\n\n\n"))
    assert (rec.dish_name_th, rec.province_th) == (None, None)
    assert rec.ingredients == []


def test_the_programme_title_is_not_a_province() -> None:
    """Every form's title reads “๑ จังหวัด ๑ เมนู”. That จังหวัด names no province."""
    title = "แบบเสนอรายการอาหาร\n“๑ จังหวัด ๑ เมนู เชิดชูอาหารถิ่น”\n"
    rec = parse_document(Document(path=Path("synthetic.pdf"), raw_text=title))
    assert rec.province_th is None
