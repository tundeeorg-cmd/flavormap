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
    Document,
    checkboxes,
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
_INGREDIENT_ROW = re.compile(
    r"^\s*([0-9๐-๙]{1,2})\s+(.{2,}?)\s{2,}(.*)$",
)
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


def _parse_ingredients(text: str) -> list[Ingredient]:
    """Rows of the §4 table, between its header and the §5 heading."""
    start = text.find("ชื่อวัตถุดิบ")
    if start < 0:
        return []
    end = text.find("๕.", start)
    block = text[start : end if end > 0 else len(text)]

    out: list[Ingredient] = []
    for line in block.splitlines()[1:]:
        m = _INGREDIENT_ROW.match(line.rstrip())
        if not m:
            continue
        position = int(thai_digits_to_arabic(m.group(1)))
        name = m.group(2).strip()
        rest = m.group(3).strip()

        qty = _QUANTITY.search(name) or _QUANTITY.search(rest)
        if qty:
            name = _QUANTITY.sub("", name).strip()

        # The last whitespace-separated cell of the row is ที่มา (acquisition).
        cells = [c for c in re.split(r"\s{2,}", rest) if c.strip()]
        acquisition = cells[-1].strip() if cells else None

        out.append(
            Ingredient(
                position=position,
                name_th=name,
                quantity_value=thai_digits_to_arabic(qty.group(1)) if qty else None,
                quantity_unit=qty.group(2) if qty else None,
                acquisition_raw=acquisition,
                acquisition_mode=_acquisition_mode(acquisition),
            )
        )
    return out


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

    record.ingredients = _parse_ingredients(text)
    if not record.ingredients:
        record.notes.append("no ingredient rows matched")

    return record


def parse_pdf(path: Path) -> DCPRecord:
    return parse_document(read_document(path))
