"""Checkbox fields are resolved by geometry, never by reading order.

The forms carry no AcroForm and no annotations. Their checkboxes are Wingdings glyphs
drawn as text, which is why a plain extraction loses them: 172 of 231 documents contain
no tick character at all in `extract_text()` output.

Reading order is not sufficient even where a tick does survive. In `north_1_1.pdf` the
extracted text reads ``ประจำ ✓ เทศกาล`` — the tick could attach to either neighbour.
Geometry settles it: a box sits immediately left of the label it governs, so the answer
is เทศกาล. These tests pin that down against documents verified by hand.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.ingest.dcp_form import parse_pdf
from src.ingest.pdf_layout import checkboxes, read_document

RAW = Path("data/raw/dcp_food")
pytestmark = pytest.mark.skipif(not RAW.exists(), reason="raw corpus not present")


def test_ticks_are_lost_from_plain_text_but_found_by_font() -> None:
    """The premise of the whole module: central_10_1 has no tick character at all."""
    doc = read_document(RAW / "central_10_1.pdf")
    assert not any(c in doc.raw_text for c in "✓✔☑√")
    assert doc.has_box_glyphs
    assert any(b.checked for b in checkboxes(doc))


def test_category_row_resolves_left_to_right() -> None:
    """One checked box, two empty, each bound to the label on its right."""
    doc = read_document(RAW / "central_10_1.pdf")
    row = {b.label: b.checked for b in checkboxes(doc) if b.label in
           {"อาหารคาว", "อาหารหวาน", "อาหารว่าง"}}
    assert row == {"อาหารคาว": True, "อาหารหวาน": False, "อาหารว่าง": False}


def test_reading_order_ambiguity_is_resolved_by_position() -> None:
    """north_1_1 extracts as 'ประจำ ✓ เทศกาล'. The tick belongs to เทศกาล."""
    doc = read_document(RAW / "north_1_1.pdf")
    occasion = {b.label: b.checked for b in checkboxes(doc) if b.label in
                {"ประจำ", "เทศกาล", "ฤดูกาล"}}
    assert occasion["เทศกาล"] is True
    assert occasion["ประจำ"] is False


def test_documents_without_glyphs_report_unknown_not_a_default() -> None:
    """9 documents are image-only scans. Their fields must be None, never option one."""
    record = parse_pdf(RAW / "east_5_1.pdf")
    assert not record.has_checkbox_glyphs
    assert record.dish_category is None
    assert record.occasion is None
    assert record.endangerment is None
    assert any("no checkbox glyphs" in n for n in record.notes)


@pytest.mark.parametrize(
    ("document", "category", "occasion"),
    [
        ("north_1_1.pdf", "savoury", "festival"),
        ("central_10_1.pdf", "savoury", "everyday"),
    ],
)
def test_parsed_categories_match_hand_reading(
    document: str, category: str, occasion: str
) -> None:
    record = parse_pdf(RAW / document)
    assert record.dish_category == category
    assert record.occasion == occasion
