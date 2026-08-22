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


# ── Table extraction ──────────────────────────────────────────────────────────
#
# The §4 ingredient table cannot be read from the text stream. Whitespace between
# columns is not reliable — an extraction may separate "หนังหมูเผา" from "100" by two
# spaces on one row and by none on the next — and a row whose text wraps continues on a
# line with no index number. Reading it by whitespace recovered ingredients from only
# 75 of 231 documents.
#
# Columns are instead recovered from the data. Run x-positions form tight vertical
# clusters across the rows of a table; the clusters appearing on the most rows are the
# columns. The header is deliberately not used as the anchor: its cells sit at different
# x than the data beneath them (header "ชื่อวัตถุดิบ" at x=137 over data at x=93), so
# header-derived boundaries put the ingredient name in the index column.

COLUMN_TOLERANCE = 14.0   # points; runs within this share a column
LINE_TOLERANCE = 2.5      # points; runs within this share a baseline


@dataclass
class TableRow:
    """One logical row. `cells` is per column, already joined across wrapped lines."""

    cells: list[str]
    y: float

    def cell(self, index: int) -> str:
        return self.cells[index].strip() if 0 <= index < len(self.cells) else ""


def group_lines(runs: list[TextRun]) -> list[list[TextRun]]:
    """Runs grouped into visual lines, top to bottom, each sorted left to right."""
    buckets: dict[tuple[int, float], list[TextRun]] = {}
    for run in runs:
        if not run.text.strip():
            continue
        key = next(
            (k for k in buckets if k[0] == run.page and abs(k[1] - run.y) <= LINE_TOLERANCE),
            (run.page, run.y),
        )
        buckets.setdefault(key, []).append(run)
    return [
        sorted(buckets[k], key=lambda r: r.x)
        for k in sorted(buckets, key=lambda k: (k[0], -k[1]))
    ]


def _column_anchors(lines: list[list[TextRun]], expected: int) -> list[float]:
    """Left edges of the table's columns, inferred from where runs actually start.

    Scored by the number of distinct rows a cluster appears on, not by how many runs
    fall in it: a single row containing several short runs must not invent a column.
    """
    clusters: list[list[float]] = []
    rows_seen: list[set[int]] = []
    for index, line in enumerate(lines):
        for run in line:
            for c, seen in zip(clusters, rows_seen, strict=True):
                if abs(c[0] - run.x) <= COLUMN_TOLERANCE:
                    c.append(run.x)
                    seen.add(index)
                    break
            else:
                clusters.append([run.x])
                rows_seen.append({index})

    ranked = sorted(zip(clusters, rows_seen, strict=True), key=lambda p: -len(p[1]))
    keep = [sum(c) / len(c) for c, _ in ranked[:expected]]
    return sorted(keep)


def extract_table(
    runs: list[TextRun], expected_columns: int, index_column_is_numeric: bool = True
) -> list[TableRow]:
    """Read a positioned table into logical rows.

    A line whose first column holds a number starts a new row; any other line is a
    continuation and its cells are appended to the row above. That is what recovers
    multi-line ingredients such as ``เครื่องแกง (ข่า ตะไคร้ …`` / ``เกลือเม็ด) …``.
    """
    lines = group_lines(runs)
    if not lines:
        return []
    anchors = _column_anchors(lines, expected_columns)
    if len(anchors) < 2:
        return []

    rows: list[TableRow] = []
    for line in lines:
        cells = [""] * len(anchors)
        for run in line:
            # Nearest anchor at or to the left of the run.
            column = max(
                (i for i, a in enumerate(anchors) if run.x >= a - COLUMN_TOLERANCE),
                default=0,
            )
            cells[column] += run.text
        first = cells[0].strip()
        if index_column_is_numeric:
            starts_row = bool(re.fullmatch(r"[0-9๐-๙]{1,2}[.)]?", first))
        else:
            starts_row = bool(first)

        if starts_row or not rows:
            rows.append(TableRow(cells=cells, y=line[0].y))
        else:
            for i, value in enumerate(cells):
                if value.strip():
                    rows[-1].cells[i] = (rows[-1].cells[i] + " " + value).strip()
    return rows
