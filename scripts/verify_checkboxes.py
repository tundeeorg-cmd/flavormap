"""Per-record checkbox report, for verifying extraction by eye against the PDFs.

    PYTHONPATH=. uv run python scripts/verify_checkboxes.py นครราชสีมา บุรีรัมย์

The endangerment level, dish category and occasion on a DCP form are read from checkbox
glyphs (Wingdings-style private-use characters), which CLAUDE.md flags as a
silent-failure risk. This script asserts nothing and claims nothing works. For each
document it prints what you need to check it yourself:

- what the database holds (``recipes``), or why there is no ``recipes`` row;
- what the parser reads from the PDF right now;
- the PDF's absolute path;
- **every** box glyph on the form, ticked or not, with its page, coordinates, the glyph's
  code point, the label beside it, and which field a ticked box feeds.

**Coordinates** are PDF points (1/72 inch) from the **bottom-left** of the page, taken
from the text matrix of the run carrying the glyph. Pages are numbered from 1, as a PDF
viewer shows them. y grows upward, so a box near the top of an A4 page has y ≈ 800.

**Which documents.** DCP files are named ``<region>_<province index>_<dish>.pdf``, three
per province. Documents are selected by that group, from the ones the database
attributes to each named province, so a document whose province field failed to parse
is still reported instead of silently dropped.

Box labels are form text, but each one is run through the PDPA check anyway and masked
if it looks personal. Read-only: nothing is written.
"""

from __future__ import annotations

import argparse
import re

from src.clean.normalize_th import normalize_thai
from src.config import RAW_DIR
from src.db import get_connection
from src.ingest.dcp_form import (
    DISH_CATEGORIES,
    ENDANGERMENT,
    OCCASIONS,
    parse_pdf,
)
from src.ingest.pdf_layout import checkboxes, read_document
from src.ingest.pdpa import personal_data_classes

CORPUS = RAW_DIR / "dcp_food"
GROUP = re.compile(r"^(.+_\d+)_\d+\.pdf$")


def _feeds(label: str) -> str:
    text = normalize_thai(label)[0]
    for needle, value in ENDANGERMENT:
        if needle in text:
            return f"endangerment = {value}"
    for key, value in DISH_CATEGORIES.items():
        if text.startswith(key):
            return f"dish_category = {value}"
    for key, value in OCCASIONS.items():
        if text.startswith(key):
            return f"occasion = {value}"
    return "(no field)"


def _safe(label: str) -> str:
    return "[masked: looks like personal data]" if personal_data_classes(label) else label


def report(provinces_th: list[str]) -> str:
    conn = get_connection()
    conn.execute("SET default_transaction_read_only = on")
    try:
        attributed = conn.execute(
            """SELECT p.name_th, split_part(rr.raw_path, '/', -1)
                 FROM recipes r JOIN province_attribution pa USING (recipe_id)
                 JOIN provinces p USING (province_code)
                 JOIN raw_recipes rr ON rr.raw_id = r.raw_id
                WHERE rr.source_id = 'dcp_food' AND p.name_th = ANY(%s)""",
            (provinces_th,),
        ).fetchall()
        groups: dict[str, str] = {}
        for province, name in attributed:
            if m := GROUP.match(name):
                groups[m.group(1)] = province
        documents = sorted(
            (groups[m.group(1)], p.name) for p in CORPUS.glob("*.pdf")
            if (m := GROUP.match(p.name)) and m.group(1) in groups
        )
        db = {
            name: row for name, *row in conn.execute(
                """SELECT split_part(rr.raw_path, '/', -1), r.recipe_id, r.name_th,
                          r.endangerment, r.dish_category_source, pa.province_code
                     FROM raw_recipes rr LEFT JOIN recipes r ON r.raw_id = rr.raw_id
                     LEFT JOIN province_attribution pa ON pa.recipe_id = r.recipe_id
                    WHERE rr.source_id = 'dcp_food'"""
            )
        }
    finally:
        conn.close()

    out: list[str] = []
    missing = [p for p in provinces_th if p not in groups.values()]
    if missing:
        out.append(f"No attributed documents found for: {', '.join(missing)}\n")
    for province, name in documents:
        path = (CORPUS / name).resolve()
        rec = parse_pdf(path)
        out.append("=" * 88)
        out.append(f"{name}   (group of {province})")
        out.append(f"PDF: {path}")
        row = db.get(name)
        if row is None:
            out.append("DATABASE: no raw_recipes row")
        elif row[0] is None:
            out.append("DATABASE: raw_recipes row only, NO recipes row. The loader skipped it "
                       f"(province parsed as {rec.province_th!r}), so it is not in the corpus.")
        else:
            recipe_id, name_th, endangerment, category_src, province_code = row
            out.append(f"DATABASE: recipe_id {recipe_id}  {name_th}  province {province_code}")
            out.append(f"          endangerment = {endangerment}   "
                       f"dish_category_source = {category_src}")
        out.append(f"PARSER NOW: dish {rec.dish_name_th!r}, province {rec.province_th!r}, "
                   f"district {rec.district_th!r}")
        out.append(f"            endangerment = {rec.endangerment}   dish_category = "
                   f"{rec.dish_category} ({rec.dish_category_source})   "
                   f"occasion = {rec.occasion}")
        doc = read_document(path)
        boxes = checkboxes(doc)
        glyphs = {(r.page, r.x, r.y): " ".join(f"U+{ord(c):04X}" for c in r.text if not c.isspace())
                  for r in doc.runs if r.is_box}
        if not boxes:
            out.append("BOXES: none drawn as glyphs. Category, occasion and endangerment are "
                       "unknowable from this PDF's text; check the page image.")
            continue
        out.append(f"BOXES ({len(boxes)}; page from 1; x, y in points from bottom-left):")
        for b in sorted(boxes, key=lambda b: (b.page, -b.y, b.x)):
            state = "TICKED " if b.checked else "empty  "
            out.append(
                f"  {state} p.{b.page + 1}  x={b.x:6.1f}  y={b.y:6.1f}  "
                f"{glyphs.get((b.page, b.x, b.y), '?'):<8} "
                f"{_safe(b.label)!r:<48}"
                + (f"  -> {_feeds(b.label)}" if b.checked else "")
            )
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("provinces", nargs="+", help="province names in Thai")
    print(report(ap.parse_args().provinces))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
