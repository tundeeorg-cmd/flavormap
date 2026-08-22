"""Parse one DCP submission form into a structured record.

Form structure, from ``แบบเสนอรายการอาหาร…`` (programme 1 จังหวัด 1 เมนู, FY 2568):

======  ==========================================================================
§1.1    dish name, province, and the ประเภท checkbox (คาว / หวาน / ว่าง)
§1.2    ช่วงเวลา checkbox — ประจำ / เทศกาล / ฤดูกาล / อื่นๆ
§1.3    informant: name and full contact block — **stripped entirely** (PDPA)
§1.4    restaurant or community source — business name kept, address stripped
§2      history, local wisdom, cooking method — prose, not stored (ETHICS.md)
§3      ด้านความเสี่ยงต่อการสูญหาย — four-level endangerment checkbox
§4      ingredient table: ที่ | ชื่อวัตถุดิบ/เครื่องปรุง | สรรพคุณ | ที่มา
§5–§7   dissemination, nutrition, photographs
======  ==========================================================================

Order of operations is load-bearing: text is extracted, **redacted**, and only then
parsed. Nothing that reaches a caller has passed through a stage where personal data
was still present.

Checkbox fields are resolved geometrically (see :mod:`src.ingest.pdf_layout`), never
from reading order. Fields the document does not supply are ``None`` — never a default
and never a guess. 14 of the 231 documents carry no checkbox glyph at all, so their
category, occasion and endangerment are legitimately unknown.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from src.clean.normalize_th import normalize_thai
from src.ingest.pdf_layout import (
    COLUMN_TOLERANCE,
    Document,
    TextRun,
    checkboxes,
    extract_table,
    group_lines,
    read_document,
    thai_digits_to_arabic,
)
from src.ingest.pdpa import RedactionReport, redact

# ── §1.1 dish category ────────────────────────────────────────────────────────
DISH_CATEGORIES = {
    "อาหารคาว": "savoury",
    "อาหารหวาน": "sweet",
    "อาหารว่าง": "snack",
}

# ── §1.2 occasion ─────────────────────────────────────────────────────────────
OCCASIONS = {
    "ประจำ": "everyday",
    "เทศกาล": "festival",
    "ฤดูกาล": "seasonal",
    "อื่นๆ": "other",
}

# ── §3 endangerment. Matched on a distinctive prefix: the full option text runs to
#      ~60 characters and varies in spacing between documents.
ENDANGERMENT = [
    ("สูญหายแล้ว", "lost"),
    ("ใกล้สูญหาย", "near_lost"),
    ("ใกล้จะสูญหาย", "near_lost"),
    ("สืบทอดจากรุ่นสู่รุ่น", "transmitted"),
]

# The forms use dot leaders as fill rules, so an unfilled or short answer arrives as
# "......ลำปาง..............". Stripping them recovered 88 province labels that an
# earlier version discarded as unmatched.
_LEADERS = re.compile(r"^[.\u2026_\-\s]+|[.\u2026_\-\s]+$")


def _strip_leaders(value: str | None) -> str | None:
    """Remove dot-leader fill from a captured field. Returns None if nothing remains."""
    if value is None:
        return None
    cleaned = _LEADERS.sub("", value).strip()
    return cleaned or None


_DISH_NAME = re.compile(r"ชื่อเมนูอาหาร\s*(.+?)(?:\s*จังหวัด|\n)")
_PROVINCE = re.compile(r"ชื่อเมนูอาหาร[^\n]*?จังหวัด\s*([^\s\n]+)")
_DISTRICT = re.compile(r"อำเภอ\s*/?\s*(?:เขต)?\s*([^\s\n]+)")
# §4 table boundaries. The header names the columns; the end markers are the checkbox
# options and the §5 heading that follow the table.
_TABLE_HEADER = ("ชื่อวัตถุดิบ", "ชื่อวัตถดิบ", "วัตถุดิบ/")
# Section headings that always end the table. §4's own checkbox options are NOT here:
# some layouts print "ไม่มีส่วนผสม…" and "อื่นๆ (ระบุ)" ABOVE the table rather than below,
# and treating them as hard stops truncated the body to nothing (central_15_2).
_TABLE_END = (
    "ด้านการเผยแพร่",
    "ด้านโภชนาการ",
    "ภาพถ่าย หรือคลิป",
)
# These end the table only once rows have started.
_TABLE_END_AFTER_ROWS = ("ไม่มีส่วนผสม", "อื่นๆ (ระบุ)")
_ROW_INDEX = re.compile(r"[0-9๐-๙]{1,2}[.)]?")
_MAX_INDEX_GAP = 3      # north_8_3 skips 44; a larger jump is a different list
_MAX_ROW_GAP = 150.0    # points between consecutive rows on one page
_PAGE_TOP = 640.0       # a table resuming after a page break starts above this y
_TABLE_COLUMNS = 4          # ที่ | ชื่อวัตถุดิบ/เครื่องปรุง | สรรพคุณ | ที่มา
_PAGE_ARTEFACT_Y = 5.0      # runs at y≈0 are footers/watermarks, not table content

_QUANTITY = re.compile(
    r"([0-9๐-๙]+(?:[./][0-9๐-๙]+)?)\s*"
    r"(กรัม|กก\.|กิโลกรัม|ขีด|ช้อนโต๊ะ|ช้อนชา|ถ้วย|ลูก|ใบ|หัว|แว่น|ต้น|ฟอง|ตัว|มล\.|ลิตร|ซีซี|กำ|ช่อ|ฝัก)"
)

# §4 column ที่มา -> acquisition mode. HD-15 owns the full mapping; this is the
# unambiguous subset, and anything unmatched stays NULL rather than being forced.
ACQUISITION_HINTS = [
    ("ปลูกเอง", "grown"),
    ("ปลุกเอง", "grown"),      # misspelling present in the corpus
    ("ปลูกในสวน", "grown"),
    ("สวนตัวเอง", "grown"),
    ("เก็บ", "foraged"),
    ("ป่า", "foraged"),
    ("ธรรมชาติ", "foraged"),
    ("ริมคลอง", "foraged"),
    ("ตลาด", "market"),
    ("ซื้อ", "market"),
    ("ร้านค้า", "market"),
    ("ห้าง", "packaged"),
    ("สำเร็จรูป", "packaged"),
]


@dataclass
class Ingredient:
    position: int
    name_th: str
    quantity_value: str | None = None
    quantity_unit: str | None = None
    acquisition_raw: str | None = None
    acquisition_mode: str | None = None


@dataclass
class DCPRecord:
    """One parsed form. Contains no personal data by construction."""

    document_ref: str
    province_th: str | None = None
    district_th: str | None = None
    dish_name_th: str | None = None
    dish_category_source: str | None = None
    dish_category: str | None = None
    occasion_th: str | None = None
    occasion: str | None = None
    endangerment: str | None = None
    ingredients: list[Ingredient] = field(default_factory=list)
    redaction: RedactionReport = field(default_factory=RedactionReport)
    has_checkbox_glyphs: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def is_usable(self) -> bool:
        """Enough to count toward the labelled-recipe fraction."""
        return bool(self.province_th and self.dish_name_th)


def _first_checked(labels: list[str], table: dict[str, str]) -> tuple[str | None, str | None]:
    for label in labels:
        for key, value in table.items():
            if label.startswith(key):
                return key, value
    return None, None


def _endangerment(labels: list[str]) -> str | None:
    for label in labels:
        for needle, value in ENDANGERMENT:
            if needle in label:
                return value
    return None


def _acquisition_mode(raw: str | None) -> str | None:
    if not raw:
        return None
    for needle, mode in ACQUISITION_HINTS:
        if needle in raw:
            return mode
    return None


def _table_runs(doc: Document) -> list[TextRun]:
    """Runs belonging to the §4 table body, trimmed to the rows themselves.

    Section markers alone are not a reliable end: some documents carry none that match,
    and the slice then runs to the end of the file. When that happened the column
    clustering locked onto URL fragments in §5–§7 and missed the index and name columns
    entirely (south_5_1).

    So the table is bounded by its own rows. The header's first cell (ที่) gives the
    index column; a line whose leftmost run sits there and reads as a number is a row.
    The body runs from the first such row to the last, plus any indented continuation
    lines trailing it.
    """
    lines = group_lines(doc.runs)
    header = next(
        (
            i
            for i, line in enumerate(lines)
            if any(h in "".join(r.text for r in line) for h in _TABLE_HEADER)
        ),
        None,
    )
    if header is None:
        return []
    index_x = _index_column_x(lines[header + 1 :], lines[header][0].x)

    # Rows are numbered upward from 1, and that is what bounds the table: a numeral in
    # the index column further down the page belongs to a numbered list in §5 or §6, and
    # following it swallowed the rest of the document.
    #
    # Not strictly consecutive, though — north_8_3 runs …43, 45, 46, 47, skipping 44. A
    # small forward gap is tolerated; a number that goes backwards, jumps far, or sits
    # far below the previous row on the same page ends the table.
    collected: list[list[TextRun]] = []
    last_row: list[TextRun] | None = None
    expected = 1

    for line in lines[header + 1 :]:
        text = "".join(r.text for r in line)
        if any(m in text for m in _TABLE_END):
            break
        if last_row is not None and any(m in text for m in _TABLE_END_AFTER_ROWS):
            break
        body = [r for r in line if r.y > _PAGE_ARTEFACT_Y]
        if not body:
            continue

        number = _row_number(body, index_x)
        if number is not None and expected <= number <= expected + _MAX_INDEX_GAP:
            if last_row is not None and _too_far_below(last_row, body):
                break
            collected.append(body)
            last_row, expected = body, number + 1
        elif last_row is not None and _is_continuation(body, last_row, index_x):
            collected.append(body)
        # Anything else — a stray numeral, a caption, a footer — is ignored rather than
        # treated as the end. north_8_3 has a lone "1" below row 12 and rows 15-47 after
        # it; breaking there lost three quarters of the table.

    return [r for line in collected for r in line]


def _index_column_x(lines: list[list[TextRun]], fallback: float) -> float:
    """Where the row-number column actually sits.

    Taking it from the header's leftmost cell assumes that cell is ที่, which holds for
    most layouts but not all: 13 documents put their numbering at a different x and read
    as having no rows at all. Preferring the x where numerals actually stack recovers
    them, with the header position as fallback when nothing stacks.
    """
    tally: dict[float, int] = {}
    for line in lines:
        first = min(line, key=lambda r: r.x)
        if not _ROW_INDEX.fullmatch(first.text.strip()):
            continue
        key = next((k for k in tally if abs(k - first.x) <= COLUMN_TOLERANCE), first.x)
        tally[key] = tally.get(key, 0) + 1
    if not tally:
        return fallback
    best = max(tally, key=lambda k: tally[k])
    return best if tally[best] >= 2 else fallback


def _is_continuation(line: list[TextRun], last_row: list[TextRun], index_x: float) -> bool:
    """Indented text close below a row is that row's wrapped remainder."""
    return (
        min(r.x for r in line) > index_x + COLUMN_TOLERANCE
        and not _too_far_below(last_row, line)
    )


def _too_far_below(previous: list[TextRun], candidate: list[TextRun]) -> bool:
    """True when the candidate is too far from the previous row to belong to it.

    A table may continue across a page break, but only by resuming near the top of the
    next page. Without that constraint a numbered list in §5 or §6 continues the row
    sequence — south_5_1 has rows ๑–๔ and then §5 content numbered ๕ onward, which
    chained the body to fifty lines and left the column clustering reading citations.
    """
    if previous[0].page != candidate[0].page:
        return candidate[0].y < _PAGE_TOP
    return (previous[0].y - candidate[0].y) > _MAX_ROW_GAP


def _row_number(line: list[TextRun], index_x: float) -> int | None:
    """The row's index number, if this line opens a table row."""
    first = min(line, key=lambda r: r.x)
    if abs(first.x - index_x) > COLUMN_TOLERANCE:
        return None
    text = thai_digits_to_arabic(first.text.strip()).rstrip(".)")
    return int(text) if text.isdigit() and len(text) <= 2 else None


def _is_row_start(line: list[TextRun], index_x: float) -> bool:
    """True when the line opens a table row: a number in the index column."""
    return _row_number(line, index_x) is not None


def _parse_ingredients(doc: Document) -> list[Ingredient]:
    """Read the §4 table by column position.

    Whitespace is not a reliable column separator here — see the note in
    :mod:`src.ingest.pdf_layout`. Rows are recovered from x-clusters, and a line whose
    index cell is empty is a continuation of the row above.
    """
    rows = extract_table(_table_runs(doc), _TABLE_COLUMNS)
    out: list[Ingredient] = []
    for row in rows:
        index = thai_digits_to_arabic(row.cell(0)).rstrip(".)")
        if not index.isdigit():
            continue
        name = row.cell(1)
        acquisition = row.cell(_TABLE_COLUMNS - 1) or None

        quantity = _QUANTITY.search(name)
        if quantity:
            name = _QUANTITY.sub(" ", name)
        name = re.sub(r"\s{2,}", " ", name).strip(" .")
        if not name:
            continue

        out.append(
            Ingredient(
                position=int(index),
                name_th=normalize_thai(name)[0],
                quantity_value=thai_digits_to_arabic(quantity.group(1)) if quantity else None,
                quantity_unit=quantity.group(2) if quantity else None,
                acquisition_raw=normalize_thai(acquisition)[0] if acquisition else None,
                acquisition_mode=_acquisition_mode(acquisition),
            )
        )
    return out


def _scrub(record: DCPRecord) -> None:
    """Final redaction pass over every string the record carries.

    The §4 table is read from the positioned runs, which are the RAW runs — that is the
    only way to recover columns geometrically, and it bypasses the redaction applied to
    the text stream. Without this pass, informant names appearing inside the table
    region and URLs in the ที่มา column reach parsed_json; the database-wide PDPA test
    caught exactly that. Every field is scrubbed again here so no route into a record
    can skip the stripper, whatever it was parsed from.
    """
    def clean(value: str | None) -> str | None:
        if not value:
            return value
        scrubbed, report = redact(value)
        for column in RedactionReport.COLUMNS.values():
            setattr(record.redaction, column,
                    getattr(record.redaction, column) + getattr(report, column))
        return scrubbed.strip() or None

    record.dish_name_th = clean(record.dish_name_th)
    record.province_th = clean(record.province_th)
    record.district_th = clean(record.district_th)
    for ingredient in record.ingredients:
        ingredient.name_th = clean(ingredient.name_th) or ""
        ingredient.acquisition_raw = clean(ingredient.acquisition_raw)
    record.ingredients = [i for i in record.ingredients if i.name_th]


def parse_document(doc: Document) -> DCPRecord:
    """Redact, then parse. Never the other way round."""
    record = DCPRecord(document_ref=doc.path.name)

    clean, redaction = redact(doc.raw_text)
    record.redaction = redaction
    if redaction.suspected_parser_failure:
        record.notes.append("zero redactions — contact block not located")

    text, _ = normalize_thai(clean)

    if m := _DISH_NAME.search(text):
        record.dish_name_th = _strip_leaders(m.group(1))
    if m := _PROVINCE.search(text):
        record.province_th = _strip_leaders(m.group(1))
    if m := _DISTRICT.search(text):
        record.district_th = _strip_leaders(m.group(1))

    record.has_checkbox_glyphs = doc.has_box_glyphs
    ticked = [c.label for c in checkboxes(doc) if c.checked and c.label]
    if ticked:
        # Labels come from the raw runs, so normalise them the same way.
        ticked = [normalize_thai(t)[0] for t in ticked]
        record.dish_category_source, record.dish_category = _first_checked(
            ticked, DISH_CATEGORIES
        )
        record.occasion_th, record.occasion = _first_checked(ticked, OCCASIONS)
        record.endangerment = _endangerment(ticked)
    else:
        record.notes.append("no checkbox glyphs — category/occasion/endangerment unknown")

    record.ingredients = _parse_ingredients(doc)
    _scrub(record)
    if not record.ingredients:
        record.notes.append("no ingredient rows matched")

    return record


def parse_pdf(path: Path) -> DCPRecord:
    return parse_document(read_document(path))
