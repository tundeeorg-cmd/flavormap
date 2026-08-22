"""Layout-aware text extraction for the DCP forms.

``extract_text()`` alone is not enough for this corpus. The forms encode their
checkboxes as **Wingdings glyphs** — no AcroForm, no annotations — and those glyphs
either vanish from a plain text extraction or arrive as private-use codepoints with no
Unicode meaning. Measured over all 231 documents:

===========================  =====  =========================================
glyph                        count  meaning
===========================  =====  =========================================
``U+F0A8`` (Wingdings)        2828  empty box
``U+F052`` (Wingdings 2)       747  checked box
``U+F0FE`` (Wingdings)         522  checked box (☑)
``U+F0FD`` (Wingdings)          17  checked box (☒)
``U+2713``                      19  literal tick, ordinary font
===========================  =====  =========================================

216 of 231 documents use Wingdings, 8 use a literal tick, and 14 contain no checkbox
glyph of any kind. Those 14 yield no checkbox fields and are reported as such — a
document with no detectable mark is never defaulted to the first option.

Position, not reading order. A box glyph sits immediately **left** of the label it
governs, on the same baseline::

    x=196.0  U+F052 (checked)  →  'อาหารคาว'   at x=217.6
    x=298.6  U+F0A8 (empty)    →  'อาหารหวาน'  at x=320.1
    x=407.6  U+F0A8 (empty)    →  'อาหารว่าง'  at x=429.2

Reading order alone is ambiguous and would be wrong: in one document the extracted
text reads ``ประจำ ✓ เทศกาล``, where the tick could plausibly attach to either
neighbour. Geometry settles it — the mark belongs to the label on its right.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader

# Wingdings/Wingdings 2 codepoints, plus the literal ticks some documents use instead.
CHECKED_GLYPHS = frozenset({"", "", "", "✓", "✔", "☑", "√"})
UNCHECKED_GLYPHS = frozenset({"", "¨", "", "☐"})
BOX_GLYPHS = CHECKED_GLYPHS | UNCHECKED_GLYPHS

# Baseline tolerance in points. The forms set option rows on a shared baseline; 3pt
# absorbs sub-pixel transform noise without merging adjacent rows (rows are >12pt apart).
BASELINE_TOLERANCE = 3.0

THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")


@dataclass(frozen=True)
class TextRun:
    """One positioned text run as the PDF content stream emitted it."""

    text: str
    font: str
    x: float
    y: float
    page: int

    @property
    def is_box(self) -> bool:
        return any(c in BOX_GLYPHS for c in self.text)

    @property
    def is_checked_box(self) -> bool:
        return any(c in CHECKED_GLYPHS for c in self.text)


@dataclass
class Checkbox:
    """A box glyph and the label it governs."""

    checked: bool
    label: str
    page: int
    x: float
    y: float


@dataclass
class Document:
    path: Path
    runs: list[TextRun] = field(default_factory=list)
    raw_text: str = ""

    @property
    def has_box_glyphs(self) -> bool:
        return any(r.is_box for r in self.runs)


def read_document(path: Path) -> Document:
    """Extract every positioned text run, plus the plain text, from one PDF."""
    reader = PdfReader(str(path))
    runs: list[TextRun] = []
    pages: list[str] = []

    for page_no, page in enumerate(reader.pages):
        def visit(
            text: str,
            cm: list[float],
            tm: list[float],
            font_dict: dict[str, object] | None,
            font_size: float,
            _p: int = page_no,
        ) -> None:
            if not text or not text.strip():
                return
            base = str((font_dict or {}).get("/BaseFont", ""))
            # Subset prefixes ("BCDEEE+THSarabunIT๙") carry no information.
            base = base.split("+")[-1].lstrip("/")
            runs.append(TextRun(text=text, font=base, x=float(tm[4]), y=float(tm[5]), page=_p))

        pages.append(page.extract_text(visitor_text=visit) or "")

    return Document(path=path, runs=runs, raw_text="\n".join(pages))


def _label_after(runs: list[TextRun], box: TextRun) -> str:
    """First substantive text run to the right of `box` on the same baseline."""
    same_line = [
        r
        for r in runs
        if r.page == box.page
        and abs(r.y - box.y) <= BASELINE_TOLERANCE
        and r.x > box.x
        and not r.is_box
        and r.text.strip()
    ]
    for run in sorted(same_line, key=lambda r: r.x):
        text = run.text.strip()
        if text:
            return text
    return ""


def checkboxes(doc: Document) -> list[Checkbox]:
    """Every box glyph in the document, paired with the label to its right.

    Returns an empty list for documents that draw no box glyphs at all — the caller
    must treat that as "unknown", never as "none selected".
    """
    out: list[Checkbox] = []
    for run in doc.runs:
        if not run.is_box:
            continue
        out.append(
            Checkbox(
                checked=run.is_checked_box,
                label=_label_after(doc.runs, run),
                page=run.page,
                x=run.x,
                y=run.y,
            )
        )
    return out


def checked_labels(doc: Document) -> list[str]:
    """Labels whose box is ticked, in page/reading order."""
    boxes = [b for b in checkboxes(doc) if b.checked and b.label]
    boxes.sort(key=lambda b: (b.page, -b.y, b.x))
    return [b.label for b in boxes]


def thai_digits_to_arabic(text: str) -> str:
    """๑๖๕ -> 165. The forms mix Thai and Arabic numerals freely."""
    return text.translate(THAI_DIGITS)


def normalise_spaces(text: str) -> str:
    return re.sub(r"[ \t ]+", " ", text).strip()
