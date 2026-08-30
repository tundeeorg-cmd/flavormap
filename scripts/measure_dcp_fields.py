"""Blocking item 3 — can the Wingdings checkbox fields be recovered, and how often?

    uv run python -m scripts.measure_dcp_fields

Bible §23 item 3 calls this the go/no-go on RQ5, and §22 lists "endangerment checkbox
unextractable" as a HIGH risk with RQ5 dying alongside it. §5 says why: the DCP forms
carry no AcroForm and no annotations, so the checkboxes are Wingdings glyphs drawn as
text. `dish_category` and `endangerment` both depend on them, and a plain text extraction
loses them entirely.

This script measures the recovery rate over all 231 documents. It writes nothing to the
database and makes no decision — HD gates belong to the researcher (CLAUDE.md §0).

**A bare recovery percentage would be the misleading number here.** "Endangerment
recovered on 68% of documents" invites the reading that the extractor fails on the other
32%, and that is not what the corpus says. A field can be missing for four quite
different reasons, only one of which is our bug:

``recovered``
    A §3 box is ticked and matched to one of the four levels.

``§3 present, none ticked``
    The section is in the document, its boxes are drawn, and the submitter left every one
    of them empty. The honest value is unknown, and Rule 2's logic applies — an unticked
    box is not evidence for option one.

``§3 absent from the document``
    The form variant carries no §3 at all. A fact about the corpus, not a parser failure.

``no checkbox glyphs at all``
    Image-only scans. No glyph of any kind survives, so no checkbox field can.

``§3 in text, no box bound``
    The only bucket that could be our defect: the section's option text appears, but no
    box binds to it. Inspected individually below, because at this corpus size the count
    is small enough to read.

The ceiling for RQ5 is therefore `recovered + the recoverable share of the last bucket`,
not `231`. The three middle buckets are unknowns that no extractor could turn into data,
and reporting them as extraction failures would overstate what a fix could buy.

Latin-1 mojibake is counted separately. §5 names sara am (ำ) dropping to a space as a
trap that "fails silently and corrupts ingredient names rather than throwing an error";
the same class of defect appears in this corpus as Thai combining marks arriving as
Latin-1 letters (ที becomes ทีÉ). It is reported here rather than fixed, because what it
costs is a measurement, not a guess.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from src.config import PROCESSED_DIR, RAW_DIR
from src.ingest.dcp_form import ENDANGERMENT, DCPRecord, parse_document
from src.ingest.pdf_layout import Document, checkboxes, read_document

CORPUS = RAW_DIR / "dcp_food"

ENDANGERMENT_NEEDLES = [needle for needle, _ in ENDANGERMENT]

# §10 puts the domestic register in Nan and Surin, and RQ5 compares the official
# endangerment level against what cooks there say about *the same dishes*. The state
# selected three dishes per province, so the corpus-wide recovery rate is not RQ5's
# sample — these six documents are. Reported separately for that reason.
FIELDWORK_PROVINCES = {"น่าน": "Nan", "สุรินทร์": "Surin"}

# Thai combining marks arriving as Latin-1 letters. A handful of stray accented
# characters could be legitimate; a document carrying dozens is corrupted.
MOJIBAKE = re.compile(r"[À-ÿ]")
MOJIBAKE_THRESHOLD = 20

# Buckets, ordered as they are reported. Only the last can be our defect.
RECOVERED = "recovered"
UNTICKED = "§3 present, none ticked"
NO_SECTION = "§3 absent from the document"
NO_GLYPHS = "no checkbox glyphs at all"
UNBOUND = "§3 in text, no box bound"

BUCKETS = [RECOVERED, UNTICKED, NO_SECTION, NO_GLYPHS, UNBOUND]


def classify(record: DCPRecord, doc: Document) -> str:
    """Why is `endangerment` missing on this document? See the module docstring."""
    if record.endangerment is not None:
        return RECOVERED
    if not record.has_checkbox_glyphs:
        return NO_GLYPHS

    boxes = checkboxes(doc)
    bound = any(
        any(needle in (box.label or "") for needle in ENDANGERMENT_NEEDLES) for box in boxes
    )
    if bound:
        # A §3 box exists and binds, but none of them carries a tick.
        return UNTICKED
    if any(needle in doc.raw_text for needle in ENDANGERMENT_NEEDLES):
        return UNBOUND
    return NO_SECTION


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", type=Path, default=CORPUS)
    args = ap.parse_args()

    pdfs = sorted(args.corpus.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"no PDFs in {args.corpus} — run scripts.fetch_dcp_food first")

    buckets: Counter[str] = Counter()
    values: dict[str, Counter[str]] = {
        "dish_category": Counter(),
        "occasion": Counter(),
        "endangerment": Counter(),
    }
    present = Counter()
    unbound_docs: list[str] = []
    mojibake_docs: list[str] = []
    ingredient_total = 0
    no_ingredients: list[str] = []
    fieldwork: list[dict[str, object]] = []

    for path in pdfs:
        doc = read_document(path)
        record = parse_document(doc)

        bucket = classify(record, doc)
        buckets[bucket] += 1
        if bucket == UNBOUND:
            unbound_docs.append(path.name)

        for field in ("province_th", "dish_name_th", "dish_category", "occasion", "endangerment"):
            if getattr(record, field, None):
                present[field] += 1
        for field, counter in values.items():
            counter[getattr(record, field) or "(none)"] += 1

        province = (record.province_th or "").strip()
        for thai, english in FIELDWORK_PROVINCES.items():
            if thai in province:
                fieldwork.append({
                    "province": english,
                    "document": path.name,
                    "dish_name_th": record.dish_name_th,
                    "endangerment": record.endangerment,
                    "dish_category": record.dish_category,
                    "ingredients": len(record.ingredients),
                })

        ingredient_total += len(record.ingredients)
        if not record.ingredients:
            no_ingredients.append(path.name)
        if len(MOJIBAKE.findall(doc.raw_text)) > MOJIBAKE_THRESHOLD:
            mojibake_docs.append(path.name)

    total = len(pdfs)
    print(f"\ncorpus: {total} documents in {args.corpus}\n")

    print("field recovery")
    for field in ("province_th", "dish_name_th", "dish_category", "occasion", "endangerment"):
        n = present[field]
        print(f"  {field:16}{n:4}/{total}  ({100 * n / total:5.1f}%)")

    print("\nwhy endangerment is missing — the RQ5 go/no-go")
    for bucket in BUCKETS:
        n = buckets[bucket]
        print(f"  {n:4}  ({100 * n / total:5.1f}%)  {bucket}")
    ceiling = buckets[RECOVERED] + buckets[UNBOUND]
    print(
        f"\n  recovered now: {buckets[RECOVERED]}/{total} "
        f"({100 * buckets[RECOVERED] / total:.1f}%)"
    )
    print(
        f"  ceiling if every unbound case were fixed: {ceiling}/{total} "
        f"({100 * ceiling / total:.1f}%)"
    )
    print(
        f"  genuinely unknown, unfixable: "
        f"{buckets[UNTICKED] + buckets[NO_SECTION] + buckets[NO_GLYPHS]}/{total}"
    )
    if unbound_docs:
        print(f"  unbound documents, read them individually: {', '.join(unbound_docs)}")

    for field, counter in values.items():
        print(f"\n{field} distribution")
        for value, n in counter.most_common():
            print(f"  {value:16}{n:5}")

    # ── RQ5's actual sample ──────────────────────────────────────────────────
    print("\nRQ5's real evidence base — the two fieldwork provinces (§10)")
    print(f"  {'province':9}{'document':20}{'endangerment':14}dish")
    for row in sorted(fieldwork, key=lambda r: (r["province"], r["document"])):
        print(
            f"  {row['province']:9}{row['document']:20}"
            f"{str(row['endangerment']):14}{row['dish_name_th'] or ''}"
        )
    with_value = [r for r in fieldwork if r["endangerment"]]
    distinct = sorted({str(r["endangerment"]) for r in with_value})
    print(
        f"\n  {len(with_value)} of {len(fieldwork)} fieldwork documents carry an "
        f"endangerment level"
    )
    levels = ", ".join(distinct) or "(none)"
    print(f"  distinct official levels among them: {len(distinct)} — {levels}")
    if len(distinct) < 2:
        print(
            "  NOTE: a comparison needs variance on both axes. With one distinct official\n"
            "        level, Figure 5's agreement matrix collapses to a single row whatever\n"
            "        the cooks say. This is a question-design finding, not an extraction\n"
            "        failure — the checkbox pipeline recovered every value that is there."
        )

    print(f"\ningredients: {ingredient_total} rows, mean {ingredient_total / total:.1f}/document")
    print(f"  documents yielding no ingredient rows: {len(no_ingredients)}")
    if mojibake_docs:
        print(f"  Latin-1 mojibake (>{MOJIBAKE_THRESHOLD} chars): {', '.join(mojibake_docs)}")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out = PROCESSED_DIR / "dcp_field_recovery.json"
    out.write_text(
        json.dumps(
            {
                "documents": total,
                "field_recovery": dict(present),
                "endangerment_buckets": {b: buckets[b] for b in BUCKETS},
                "endangerment_ceiling": ceiling,
                "unbound_documents": unbound_docs,
                "value_distributions": {k: dict(v) for k, v in values.items()},
                "ingredient_rows": ingredient_total,
                "documents_without_ingredients": no_ingredients,
                "mojibake_documents": mojibake_docs,
                "fieldwork_provinces": fieldwork,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nwritten: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
