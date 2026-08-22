"""Compare PDF text extractors on Thai, and pick one on evidence.

    uv run python -m scripts.compare_extractors [--n 10]

Thai text extraction from PDFs fails in ways that are invisible unless you look for
them. Two known modes:

  * **Broken sara am** — ``ประจำปี`` extracted as ``ประจ าปี``. The ``ำ`` is dropped and
    replaced by a space. This is the failure the project brief predicted.
  * **Orphaned combining marks** — ``หมู่`` extracted as ``หม ู่``. The vowel is
    preserved but detached from its consonant by a space.

Both corrupt tokenisation silently: PyThaiNLP will happily segment the damaged string
and produce ingredient tokens that match nothing in the lexicon, and the failure shows
up ten steps later as an unexplained drop in mapping coverage.

The temptation is a blanket regex that deletes spaces before Thai vowels. That would
also destroy legitimately spaced text, which in Thai is meaningful — Thai does not use
spaces between words, so a space is usually a phrase or clause boundary. The right move
is to pick an extractor that does not introduce the damage in the first place.

Scoring is defect counts per 1,000 Thai characters, lower is better, plus an exact-match
check against tokens read by hand from a document (see FIXTURE).
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

RAW_DIR = Path("data/raw/dcp_food")
REPORT = Path("docs/extractor_comparison.md")

# Thai combining marks: above/below vowels and tone marks. A space immediately before
# one of these means the mark has been detached from its base consonant.
COMBINING = "ัิีึืฺุู็่้๊๋์ํ๎"
THAI_CONSONANT = "ก-ฮ"

ORPHAN_MARK = re.compile(f"\\s[{COMBINING}]")
# A consonant, a space, then sara aa — the signature of a dropped sara am (ำ).
BROKEN_SARA_AM = re.compile(f"[{THAI_CONSONANT}]\\s+า")
THAI_CHAR = re.compile("[฀-๿]")

# Tokens read by hand from north_1_1.pdf page 1. Any extractor that returns this
# document must reproduce these exactly.
FIXTURE = {
    "file": "north_1_1.pdf",
    "must_contain": [
        "ประจำปีงบประมาณ",   # sara am mid-word
        "ตำบล",               # sara am
        "กำแพงเพชร",          # sara am, and the province
        "จำเป็น",             # sara am
        "หมู่",               # vowel below + tone mark, the detachment case
        "อาหารคาว",           # a checkbox label
        "เชิดชูอาหารถิ่น",     # programme name
    ],
}


def extract_pdfplumber(path: Path) -> str:
    import pdfplumber
    with pdfplumber.open(path) as pdf:
        return "\n".join((p.extract_text() or "") for p in pdf.pages)


def extract_pypdf(path: Path) -> str:
    from pypdf import PdfReader
    return "\n".join((p.extract_text() or "") for p in PdfReader(str(path)).pages)


def extract_pdfminer(path: Path) -> str:
    from pdfminer.high_level import extract_text
    from pdfminer.layout import LAParams
    # char_margin tuned up: the default splits Thai clusters aggressively because Thai
    # glyphs are narrow and combining marks are placed with small advances.
    return extract_text(str(path), laparams=LAParams(char_margin=2.5, word_margin=0.1))


EXTRACTORS = {
    "pdfplumber": extract_pdfplumber,
    "pypdf": extract_pypdf,
    "pdfminer.six": extract_pdfminer,
}


def score(text: str) -> dict[str, float | int]:
    text = unicodedata.normalize("NFC", text)
    thai = len(THAI_CHAR.findall(text))
    orphans = len(ORPHAN_MARK.findall(text))
    broken_am = len(BROKEN_SARA_AM.findall(text))
    per_k = (lambda n: round(n / thai * 1000, 2)) if thai else (lambda n: 0.0)
    return {
        "thai_chars": thai,
        "orphan_marks": orphans,
        "broken_sara_am": broken_am,
        "orphans_per_1k": per_k(orphans),
        "broken_am_per_1k": per_k(broken_am),
        "total_defects_per_1k": per_k(orphans + broken_am),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=10, help="documents to compare")
    args = ap.parse_args()

    # A spread across regions, not the first N alphabetically.
    all_pdfs = sorted(RAW_DIR.glob("*.pdf"))
    if not all_pdfs:
        raise SystemExit(f"no PDFs in {RAW_DIR} — run scripts.fetch_dcp_food first")
    step = max(1, len(all_pdfs) // args.n)
    sample = all_pdfs[::step][: args.n]

    print(f"comparing {len(EXTRACTORS)} extractors on {len(sample)} documents\n")

    totals: dict[str, dict[str, int]] = {
        n: {"thai": 0, "orphan": 0, "am": 0, "fail": 0} for n in EXTRACTORS
    }
    per_doc: list[dict] = []

    for path in sample:
        row = {"file": path.name}
        for name, fn in EXTRACTORS.items():
            try:
                text = fn(path)
            except Exception as e:
                row[name] = {"error": f"{type(e).__name__}: {e}"}
                totals[name]["fail"] += 1
                continue
            s = score(text)
            row[name] = s
            totals[name]["thai"] += int(s["thai_chars"])
            totals[name]["orphan"] += int(s["orphan_marks"])
            totals[name]["am"] += int(s["broken_sara_am"])
        per_doc.append(row)
        print(f"  {path.name}")

    # Fixture check on the hand-read document.
    fixture_path = RAW_DIR / FIXTURE["file"]
    fixture_results: dict[str, list[str]] = {}
    if fixture_path.exists():
        for name, fn in EXTRACTORS.items():
            try:
                text = unicodedata.normalize("NFC", fn(fixture_path))
            except Exception as e:
                fixture_results[name] = [f"ERROR {type(e).__name__}"]
                continue
            fixture_results[name] = [t for t in FIXTURE["must_contain"] if t not in text]

    print("\n" + "=" * 74)
    print(
        f"{'extractor':<16}{'thai chars':>12}{'orphans/1k':>13}"
        f"{'broken ำ/1k':>14}{'failures':>10}"
    )
    print("=" * 74)
    ranking = []
    for name, t in totals.items():
        o = round(t["orphan"] / t["thai"] * 1000, 2) if t["thai"] else 0
        a = round(t["am"] / t["thai"] * 1000, 2) if t["thai"] else 0
        ranking.append((o + a, name))
        print(f"{name:<16}{t['thai']:>12,}{o:>13}{a:>14}{t['fail']:>10}")

    print("\nfixture — tokens MISSING from north_1_1.pdf (fewer is better):")
    for name, missing in fixture_results.items():
        print(f"  {name:<16}{'none — all 7 present' if not missing else missing}")

    ranking.sort()
    winner = ranking[0][1]
    print(f"\nlowest defect rate: {winner}")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "# Thai PDF extractor comparison\n\n"
        f"Generated by `scripts/compare_extractors.py` on {len(sample)} DCP documents.\n"
        "Regenerate rather than editing by hand.\n\n"
        "`pdftotext -layout` is not in this comparison: it needs poppler, which is not\n"
        "installed and cannot be without adding a system package manager to the machine.\n"
        "`pdfminer.six` is substituted as the third extractor.\n\n"
        "## Defect rates, per 1,000 Thai characters\n\n"
        "| extractor | thai chars | orphan marks /1k | broken sara am /1k | failures |\n"
        "|---|---:|---:|---:|---:|\n"
        + "".join(
            f"| `{n}` | {t['thai']:,} | "
            f"{round(t['orphan']/t['thai']*1000,2) if t['thai'] else 0} | "
            f"{round(t['am']/t['thai']*1000,2) if t['thai'] else 0} | {t['fail']} |\n"
            for n, t in totals.items()
        )
        + (
            "\n## Fixture check\n\nTokens read by hand from `north_1_1.pdf` "
            "that each extractor fails to reproduce:\n\n"
        )
        + "".join(
            f"- `{n}`: {'**all present**' if not m else '**MISSING** ' + ', '.join(m)}\n"
            for n, m in fixture_results.items()
        )
        + f"\n## Selected\n\n**`{winner}`** — lowest combined defect rate.\n",
        encoding="utf-8",
    )
    print(f"report -> {REPORT}")

    Path("data/processed").mkdir(parents=True, exist_ok=True)
    Path("data/processed/extractor_comparison.json").write_text(
        json.dumps(
            {"per_doc": per_doc, "totals": totals, "fixture": fixture_results},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
