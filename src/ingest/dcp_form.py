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
# Fallback for layouts that break §1.1 across lines (south_1_2, south_1_3: the dish name
# and the จังหวัด value each sit on their own line between dot leaders). Used only when
# the single-line patterns above find nothing, and it reads strictly inside §1.1, from
# its label to the next field (ประเภท or 1.2), so it can never reach the §1.3 contact
# block, whose จังหวัด is the submitter's address, not the dish's province.
_SECTION_1_1 = re.compile(r"ชื่อเมนูอาหาร(.*?)(?=ประเภท|[1๑]\s*\.\s*[2๒])", re.DOTALL)
_BLOCK_PROVINCE = re.compile(r"จังหวัด[\s.…·]*([^\s.…·]+)")
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
# These end the table only once rows have started. They are the §4 checkbox options
# that follow the table: "(ไม่)มีส่วนผสมของวัตถุดิบ…", "เป็นอาหารที่ช่วยส่งเสริม…" and
# "อื่นๆ (ระบุ)". Matching only "ไม่มีส่วนผสม" let the ticked "มีส่วนผสม…" option through
# (south_7_1). Bare "มีส่วนผสม" is too short: south_1_1's สรรพคุณ cell reads
# "มีส่วนผสม คาร์โบไฮเดรท" and it cut the table after row 1. "ไม่มีส่วนผสม" stays for
# the truncated "/ไม่มีส่วนผสม…" some layouts print (central_6_3, north_3_3).
_TABLE_END_AFTER_ROWS = (
    "ไม่มีส่วนผสม",
    "มีส่วนผสมของวัตถุดิบ",
    "เป็นอาหารที่ช่วยส่งเสริม",
    "อื่นๆ (ระบุ)",
)
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

# §4 column ที่มา: kept verbatim in ``acquisition_raw``. The parser infers no mode: HD-15
# (decided 2026-11-06) maps the text by the researcher's hand coding only, applied by
# scripts/acquisition.py. The 13 keyword hints that stood here were never decided and
# were removed under that decision.


@dataclass
class Ingredient:
    position: int
    name_th: str
    quantity_value: str | None = None
    quantity_unit: str | None = None
    acquisition_raw: str | None = None
    # Always None from the parser (HD-15); kept so parsed_json keeps its shape.
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
        # Markers are matched on repaired text. The runs are raw, and in many documents
        # carry private-use tone marks — "ไมมีสวนผสม" never matches
        # "ไม่มีส่วนผสม" — so the checkbox options after the table were read as a
        # continuation of its last row and absorbed into that ingredient's name.
        text = normalize_thai("".join(r.text for r in line))[0]
        if any(m in text for m in _TABLE_END):
            break
        if last_row is not None and (
            any(m in text for m in _TABLE_END_AFTER_ROWS) or _opens_with_box(line)
        ):
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


def _opens_with_box(line: list[TextRun]) -> bool:
    """True when the line's leftmost run is a checkbox glyph.

    A table row opens with its index number and a continuation line with wrapped cell
    text; neither opens with a box. A line that does is a checkbox option, whatever its
    wording — the structural stop that does not depend on the option text matching.
    """
    return min(line, key=lambda r: r.x).is_box


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
            )
        )
    return out


# ── fallback reader for layouts the row parser cannot read ─────────────────────────
# Used only when `_parse_ingredients` returns nothing, so it can never change a document
# the row parser already reads. Twenty official recipes had no ingredient lines because
# their §4 table breaks the row parser's assumptions: rows without numbers (central_10_3),
# a benefits column with its own numbered list taken for the index column (north_12_3),
# numbers fused to names ("๑.ใบมะกรูด", northeast_14_3), number and name sharing one x
# (south_14_1), the number on its own line below the name (north_3_1), a 3-column
# index | name | quantity layout (central_13_2).
#
# What they share: ingredient names sit in one column, the leftmost column holding Thai
# text. The fallback finds that column's x and reads one ingredient per line in it.
_SECTION_STOP = re.compile(r"^\s*(?:[5๕]\s*\.|[0-9๐-๙.\s]*(?:วิธี|ขั้นตอน))")
# A name longer than this is a sentence (a method step or a note), not an ingredient.
_MAX_NAME_CHARS = 40
# Benefits-column (สรรพคุณ) vocabulary. A fallback result where this many of the lines
# read like health claims came from the wrong column and is discarded: an empty result
# is reported, a wrong one would be mapped.
_BENEFIT_WORDS = re.compile(r"ช่วย|ป้องกัน|บำรุง|วิตามิน|สาร|โรค|ร่างกาย|เลือด|ลดความ|ลดอาการ|"
                            r"อุดม|ประโยชน์|สรรพคุณ|ต้าน|ระบบ")
_MAX_BENEFIT_SHARE = 0.3
_LEADING_INDEX = re.compile(r"^\s*[0-9๐-๙]{1,2}\s*[.)]?\s*")
_THAI_LETTER = re.compile(r"[\u0E01-\u0E2E]")
_MAX_FALLBACK_LINES = 60


def _fallback_lines(doc: Document) -> tuple[list[list[TextRun]], float | None]:
    """Lines between the §4 header and the first stop marker, page artefacts removed,
    and the x of the header cell that names the ingredient column (ชื่อวัตถุดิบ…)."""
    lines = group_lines(doc.runs)
    header = next((i for i, line in enumerate(lines)
                   if any(h in "".join(r.text for r in line) for h in _TABLE_HEADER)), None)
    if header is None:
        return [], None
    head_cell = next((r for r in sorted(lines[header], key=lambda r: r.x)
                      if "วัตถ" in normalize_thai(r.text)[0]), None)
    header_x = head_cell.x if head_cell else None
    out: list[list[TextRun]] = []
    for line in lines[header + 1:]:
        text = normalize_thai("".join(r.text for r in line))[0].strip()
        if any(m in text for m in _TABLE_END) or _SECTION_STOP.match(text):
            break
        if out and (any(m in text for m in _TABLE_END_AFTER_ROWS) or _opens_with_box(line)):
            break
        body = [r for r in line if r.y > _PAGE_ARTEFACT_Y and not r.is_box]
        if body:
            out.append(body)
        if len(out) >= _MAX_FALLBACK_LINES:
            break
    return out, header_x


def _name_column_x(lines: list[list[TextRun]], header_x: float | None = None) -> float | None:
    """The ingredient-name column: among x positions where at least two lines' leftmost
    Thai-text run starts, the one nearest the header's ingredient cell. Taking the most
    frequent one instead picked the benefits column, whose wrapped prose has more lines
    (north_11_2, east_4_2). Without a header cell, the most frequent is used."""
    tally: dict[float, int] = {}
    for line in lines:
        thai = [r for r in sorted(line, key=lambda r: r.x)
                if _THAI_LETTER.search(_LEADING_INDEX.sub("", r.text))]
        if not thai:
            continue
        x = thai[0].x
        k = next((k for k in tally if abs(k - x) <= COLUMN_TOLERANCE), x)
        tally[k] = tally.get(k, 0) + 1
    columns = [k for k in tally if tally[k] >= 2]
    if not columns:
        return None
    if header_x is not None:
        return min(columns, key=lambda k: (abs(k - header_x), -tally[k]))
    return max(columns, key=lambda k: (tally[k], -k))


def _parse_ingredients_fallback(doc: Document) -> list[Ingredient]:
    lines, header_x = _fallback_lines(doc)
    name_x = _name_column_x(lines, header_x)
    if name_x is None:
        return []
    out: list[Ingredient] = []
    for line in lines:
        cell = " ".join(r.text.strip() for r in sorted(line, key=lambda r: r.x)
                        if abs(r.x - name_x) <= COLUMN_TOLERANCE)
        name = _LEADING_INDEX.sub("", cell)
        quantity = _QUANTITY.search(name)
        if quantity:
            name = _QUANTITY.sub(" ", name)
        name = re.sub(r"\s{2,}", " ", name).strip(" .")
        if (not _THAI_LETTER.search(name) or any(h in name for h in _TABLE_HEADER)
                or len(name) > _MAX_NAME_CHARS):
            continue
        out.append(Ingredient(
            position=len(out) + 1,
            name_th=normalize_thai(name)[0],
            quantity_value=thai_digits_to_arabic(quantity.group(1)) if quantity else None,
            quantity_unit=quantity.group(2) if quantity else None,
            acquisition_raw=None,
            acquisition_mode=None,
        ))
    if out and sum(bool(_BENEFIT_WORDS.search(i.name_th)) for i in out) / len(out) \
            >= _MAX_BENEFIT_SHARE:
        return []
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
    if (block := _SECTION_1_1.search(text)) and not (record.dish_name_th and record.province_th):
        body = block.group(1)
        name_part, _, after = body.partition("จังหวัด")
        if not record.dish_name_th:
            record.dish_name_th = _strip_leaders(" ".join(name_part.split()))
        if not record.province_th and (m := _BLOCK_PROVINCE.search("จังหวัด" + after)):
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
    if not record.ingredients:
        record.ingredients = _parse_ingredients_fallback(doc)
        if record.ingredients:
            record.notes.append("ingredients read by the fallback name-column reader")
    _scrub(record)
    if not record.ingredients:
        record.notes.append("no ingredient rows matched")

    return record


def parse_pdf(path: Path) -> DCPRecord:
    return parse_document(read_document(path))
