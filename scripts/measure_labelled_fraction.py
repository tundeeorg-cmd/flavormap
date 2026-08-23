"""Blocking item 1 — what share of a consumer-site corpus carries a usable province label?

    uv run python -m scripts.measure_labelled_fraction [--source kapook_cooking]

CLAUDE.md §11 makes this the number the project's shape depends on: above 35% it is a
province-level paper, below it a region-level paper or primarily a coverage paper. §11
also records that the "~300 SorKorPor recipes" the Bible assumed for this measurement do
not exist on this machine. `cooking.kapook.com` is the consumer source chosen in their
place, and it is the right kind of corpus for the question: unlike the DCP forms, which
are province-stamped by construction and would answer ~100%, nothing here obliges an
author to say where a dish is from.

Thai is unspaced, so a province name has no word boundary to anchor on and a bare
substring search is not a measurement — it is a homograph count. Three matching rules are
reported rather than one, because the choice between them moves the answer by an order of
magnitude and hiding it inside a single headline number would be the more misleading act:

``permissive``
    Any province name, anywhere, as a substring. The upper bound, and mostly noise.

``strict``
    Bare matching for names that are not ordinary Thai words; the AMBIGUOUS names below
    additionally require a ``จังหวัด`` or ``จ.`` marker. This is the reported figure.

``marker``
    Every name requires the marker. The floor: an explicit administrative claim only.

Scope is reported twice over: the whole article, and the title and section headings
alone. §7.2 admits three label sources — the source page, the dish name, and an explicit
regional claim — and the title carries the first two while the body carries the third.

Nothing here writes to the database. The unit of observation is unresolved for this
source: a kapook page may hold one dish or forty-six (see `src.ingest.kapook_page`), and
a fraction whose denominator is "pages" is not the same claim as one whose denominator is
"recipes". The denominator used below is pages carrying a readable ingredient list —
the pages that could become recipes at all — and the page count is reported beside it.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from dataclasses import dataclass

from src.config import DATA_DIR, RAW_DIR, REFERENCE_DIR
from src.ingest.kapook_page import KapookRecord, article_lines, parse_file

# Province names that are also ordinary Thai words or common substrings. Every entry was
# confirmed by reading its matches in this corpus, not assumed from the dictionary — the
# occurrence counts are from the 2,702 cached pages on 2026-08-23.
AMBIGUOUS = {
    "เลย": "the adverb 'at all' — 11,431 occurrences, overwhelmingly คลิกเลย",
    "ตาก": "the verb 'to sun-dry' — 324 occurrences, ตากแดด",
    "แพร่": "'to spread' — แพร่หลาย, เผยแพร่",
    "น่าน": "a substring of ทูน่า (tuna) and น่านน้ำ",
    "ตราด": "a substring of ตรา + a brand name — ตราดอกบัว, ตราดอยคำ",
    "กระบี่": "also 'sword'",
    "ยะลา": "a substring of ขนมเปี๊ยะลาวา",
}

# Names as they are written in running text rather than in the ISO register. Without
# these, Bangkok is unmatchable in a consumer corpus: nobody writes กรุงเทพมหานคร.
ALIASES = {
    "กรุงเทพ": "TH-10",
    "กทม": "TH-10",
    "อยุธยา": "TH-14",
    "โคราช": "TH-30",
}

MARKERS = ("จังหวัด", "จ.", "จ. ")

# Region-level claims, for the §11 fallback. Bare เหนือ and ใต้ mean 'above' and 'below'
# and are excluded; only the compounded forms are a claim about food.
REGION_TERMS = {
    "อีสาน": "Northeast",
    "ภาคตะวันออกเฉียงเหนือ": "Northeast",
    "ภาคเหนือ": "North",
    "อาหารเหนือ": "North",
    "เมืองเหนือ": "North",
    "ล้านนา": "North",
    "ภาคใต้": "South",
    "อาหารใต้": "South",
    "ปักษ์ใต้": "South",
    "ภาคกลาง": "Central",
}

RULES = ("permissive", "strict", "marker")


@dataclass(frozen=True)
class Province:
    code: str
    name_th: str
    region4: str


def load_provinces() -> list[Province]:
    with (REFERENCE_DIR / "provinces.csv").open(encoding="utf-8") as handle:
        return [
            Province(row["province_code"], row["name_th"], row["region4"])
            for row in csv.DictReader(handle)
        ]


def _marked(text: str, name: str) -> bool:
    return any(f"{marker}{name}" in text for marker in MARKERS)


def province_hits(text: str, provinces: list[Province], rule: str) -> set[str]:
    """Province codes claimed by `text` under one matching rule."""
    hits: set[str] = set()
    for province in provinces:
        name = province.name_th
        if name not in text:
            continue
        if rule == "marker" or (rule == "strict" and name in AMBIGUOUS):
            if not _marked(text, name):
                continue
        hits.add(province.code)
    for alias, code in ALIASES.items():
        if alias in text and (rule != "marker" or _marked(text, alias)):
            hits.add(code)
    return hits


def region_hits(text: str) -> set[str]:
    return {region for term, region in REGION_TERMS.items() if term in text}


def title_text(record: KapookRecord) -> str:
    """Title and section headings — the dish name and its qualifiers, without the body."""
    return "\n".join([record.title_th or "", *(s.heading for s in record.sections)])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", default="kapook_cooking")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    corpus = RAW_DIR / args.source
    paths = sorted(corpus.glob("view*.html"))[: args.limit]
    if not paths:
        raise SystemExit(f"no cached pages in {corpus} — run scripts.fetch_kapook first")

    provinces = load_provinces()
    pages = 0
    with_ingredients = 0
    labelled: dict[tuple[str, str], int] = Counter()
    unique: dict[tuple[str, str], int] = Counter()
    by_province: dict[str, Counter[str]] = {rule: Counter() for rule in RULES}
    regions: Counter[str] = Counter()
    pages_with_region = 0

    for path in paths:
        record = parse_file(path)
        pages += 1
        if not record.is_usable:
            continue
        with_ingredients += 1

        lines = article_lines(path.read_text(encoding="utf-8", errors="replace")) or []
        body = "\n".join(lines)
        scopes = {"article": body, "title": title_text(record)}

        for scope, text in scopes.items():
            for rule in RULES:
                hits = province_hits(text, provinces, rule)
                if hits:
                    labelled[(scope, rule)] += 1
                if len(hits) == 1:
                    unique[(scope, rule)] += 1
                if scope == "article":
                    by_province[rule].update(hits)

        found = region_hits(body)
        if found:
            pages_with_region += 1
            regions.update(found)

    denominator = with_ingredients or 1
    print(f"\ncorpus: {pages} pages, {with_ingredients} with a readable ingredient list")
    print(f"denominator for every percentage below: {with_ingredients}\n")
    print(f"{'scope':10}{'rule':12}{'any province':>14}{'':>4}{'exactly one':>13}")
    for scope in ("article", "title"):
        for rule in RULES:
            any_n, one_n = labelled[(scope, rule)], unique[(scope, rule)]
            print(
                f"{scope:10}{rule:12}{any_n:8} {any_n / denominator:5.1%}"
                f"{'':>4}{one_n:7} {one_n / denominator:5.1%}"
            )

    print(f"\nregion-level claim, article scope: {pages_with_region} "
          f"({pages_with_region / denominator:.1%})")
    for region, count in regions.most_common():
        print(f"  {region:12}{count:6}")

    print("\ntop provinces by rule (article scope):")
    for rule in RULES:
        top = ", ".join(
            f"{next(p.name_th for p in provinces if p.code == code)}={n}"
            for code, n in by_province[rule].most_common(6)
        )
        print(f"  {rule:12}{top or '(none)'}")

    out = DATA_DIR / "coverage" / f"labelled_fraction_{args.source}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["scope", "rule", "n_pages", "n_any_province", "pct_any_province",
                         "n_exactly_one", "pct_exactly_one"])
        for scope in ("article", "title"):
            for rule in RULES:
                any_n, one_n = labelled[(scope, rule)], unique[(scope, rule)]
                writer.writerow([scope, rule, with_ingredients, any_n,
                                 round(100 * any_n / denominator, 2), one_n,
                                 round(100 * one_n / denominator, 2)])
    print(f"\nwritten: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
