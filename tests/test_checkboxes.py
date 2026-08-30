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

import pytest

from src.config import RAW_DIR
from src.ingest.dcp_form import parse_pdf
from src.ingest.pdf_layout import checkboxes, read_document

RAW = RAW_DIR / "dcp_food"
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


# ── §3 endangerment — the field RQ5 is built on ──────────────────────────────
# Until 2026-08-30 this field had no test asserting it recovers anything at all: the
# module covered dish_category and occasion, and covered endangerment only in the
# negative (glyph-less documents must report None). A field that nothing pins is a field
# that can silently start returning None for the whole corpus.


def test_endangerment_recovers_from_a_ticked_section() -> None:
    """north_6_1 ticks the 'transmitted' option in §3. It must come back."""
    record = parse_pdf(RAW / "north_6_1.pdf")
    assert record.endangerment == "transmitted"


def test_endangerment_is_none_when_section_three_is_untouched() -> None:
    """north_6_2 carries checkbox glyphs but no §3 tick. Unknown, never option one."""
    record = parse_pdf(RAW / "north_6_2.pdf")
    assert record.has_checkbox_glyphs
    assert record.endangerment is None


@pytest.mark.parametrize(
    ("document", "level"),
    [
        ("northeast_15_1.pdf", "transmitted"),
        ("northeast_15_2.pdf", "transmitted"),
        ("northeast_15_3.pdf", "transmitted"),
        ("north_6_1.pdf", "transmitted"),
    ],
)
def test_fieldwork_sample_is_pinned(document: str, level: str) -> None:
    """RQ5's entire official axis, pinned.

    §10 puts the domestic register in Nan and Surin and the state selected three dishes
    per province, so these four documents — plus two carrying no §3 tick — are the whole
    sample RQ5 compares cooks against. `docs/checkbox_extraction.md` reports that all
    four carry the same level, which is why Figure 5's agreement matrix cannot be built.

    This pins the finding, not a hand-verified ground truth: these are the values the
    extractor reads from a ticked box. If a parser change moves any of them, the go/no-go
    in `docs/decisions.md` rests on a different corpus than the one it was written from
    and has to be re-run rather than quietly inherited.
    """
    assert parse_pdf(RAW / document).endangerment == level


@pytest.mark.xfail(
    reason="Latin-1 mojibake truncates the §3 label; see docs/checkbox_extraction.md",
    strict=True,
)
def test_mojibake_document_loses_its_endangerment_level() -> None:
    """A known defect, pinned so it is visible rather than remembered.

    south_9_2 renders Thai combining marks as Latin-1 letters, so `ที` arrives as `ทีÉ`.
    Its raw text carries ` เป็นเมนูทีÉใกล้จะสูญหาย…` — U+F0FE is a *checked* box, so
    the document's true level is `near_lost`. Label binding truncates at 'เป็นเมนูที',
    before the needle, and the field comes back None.

    The larger cost is not this field: both mojibake documents also yield zero ingredient
    rows against a corpus mean of 4.9. Left unfixed inside the go/no-go deliberately — it
    cannot change the RQ5 answer, whose sample is Nan and Surin, not the South.
    """
    assert parse_pdf(RAW / "south_9_2.pdf").endangerment == "near_lost"
