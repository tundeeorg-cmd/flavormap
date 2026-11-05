"""Dry run of the MThai parser: counts, fill rates, and duplicates against Kapook.

    uv run python -m scripts.parse_mthai          (make parse-mthai)

Evidence for HD-40 (sources), HD-41 (dedup) and HD-42 (balance). **Nothing is written
to the database**: MThai is not loaded until HD-40 is decided. The Kapook side is read
on a read-only connection.

**Duplicates.** For each MThai post, the Kapook recipe with the highest ingredient-set
Jaccard (``src.clean.dedupe.jaccard_similarity``) and that pair's title ratio
(``title_similarity``). Sets are built two ways: strings as keyed today (NFC and
whitespace), and with the HD-6 question 6 quantity-stripping prototype on. The lexicon
is empty, so neither is the canonical-ingredient set HD-41 refers to; both are reported
so the gap is visible.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from scripts.lexicon_worklist import QUERY as INGREDIENT_QUERY
from src.clean.dedupe import jaccard_similarity, title_similarity
from src.clean.lexicon import key
from src.db import get_connection
from src.ingest.mthai_food import MThaiRecord, read_csv

BINS = (0.0, 0.1, 0.3, 0.5, 0.7, 0.85, 0.9, 1.0)

TITLE_QUERY = """
SELECT r.recipe_id, r.name_th FROM recipes r
  JOIN raw_recipes rr ON rr.raw_id = r.raw_id
 WHERE rr.source_id = 'kapook_cooking'
"""


def ingredient_set(lines: list[str], strip: bool) -> set[str]:
    return set(k for k in (key(x, strip) for x in lines) if k)


def best_matches(
    mthai: list[MThaiRecord], kapook: dict[int, list[str]], strip: bool
) -> list[tuple[MThaiRecord, int | None, float]]:
    """Per MThai record: (record, best Kapook recipe_id, its Jaccard). Ties keep the
    lowest recipe_id, so the result is stable."""
    k_sets = {rid: ingredient_set(lines, strip) for rid, lines in sorted(kapook.items())}
    out = []
    for rec in mthai:
        m = ingredient_set(rec.ingredient_lines, strip)
        best_id, best = None, 0.0
        for rid, s in k_sets.items():
            if m and s and (j := jaccard_similarity(m, s)) > best:
                best_id, best = rid, j
        out.append((rec, best_id, best))
    return out


def histogram(values: list[float]) -> list[tuple[str, int]]:
    rows = []
    for lo, hi in zip(BINS, BINS[1:], strict=False):
        last = hi == BINS[-1]
        n = sum(1 for v in values if lo <= v < hi or (last and v == hi))
        rows.append((f"[{lo:.2f}, {hi:.2f}{']' if last else ')'}", n))
    return rows


def provinces_named(r: MThaiRecord, province_names: set[str]) -> set[str]:
    """Province names appearing inside any tag or the title (e.g. the tag
    อาหารจังหวัดชัยนาท names ชัยนาท). A measurement for HD-37, never a label."""
    return {p for p in province_names if p in r.title or any(p in t for t in r.tags)}


def fill_rates(records: list[MThaiRecord], province_names: set[str]) -> list[tuple[str, int]]:
    def has_province(r: MThaiRecord) -> bool:
        return bool(provinces_named(r, province_names))
    return [
        ("records", len(records)),
        ("distinct post_id", len({r.post_id for r in records})),
        ("title", sum(bool(r.title) for r in records)),
        ("published_at", sum(r.published_at is not None for r in records)),
        ("≥1 tag", sum(bool(r.tags) for r in records)),
        ("≥1 ingredient line", sum(bool(r.ingredient_lines) for r in records)),
        ("≥3 ingredient lines", sum(len(r.ingredient_lines) >= 3 for r in records)),
        ("Thai province name inside a tag or the title",
         sum(has_province(r) for r in records)),
        ("records with ≥1 PDPA redaction", sum(r.redaction.total > 0 for r in records)),
    ]


def main() -> int:
    records = read_csv()
    conn = get_connection()
    conn.read_only = True
    try:
        kapook: defaultdict[int, list[str]] = defaultdict(list)
        for source_id, _, recipe_id, name in conn.execute(INGREDIENT_QUERY):
            if source_id == "kapook_cooking" and name:
                kapook[recipe_id].append(name)
        titles: dict[int, str] = dict(conn.execute(TITLE_QUERY).fetchall())
        provinces = {n for (n,) in conn.execute("SELECT name_th FROM provinces")}
    finally:
        conn.close()

    print("mthai_food dry run: nothing written to the database\n")
    for label, n in fill_rates(records, provinces):
        print(f"  {label:58} {n}")
    named = Counter(p for r in records for p in provinces_named(r, provinces))
    print(f"  posts naming each province: {dict(named.most_common()) or 'none'}")
    lines = [len(r.ingredient_lines) for r in records]
    dates = sorted(r.published_at for r in records if r.published_at)
    print(f"  ingredient lines: total {sum(lines)}, median {sorted(lines)[len(lines) // 2]}")
    if dates:
        print(f"  published {dates[0]} to {dates[-1]}")
    redactions: Counter[str] = Counter()
    for r in records:
        for col in r.redaction.COLUMNS.values():
            redactions[col] += getattr(r.redaction, col)
    print(f"  redactions by class: {dict(+redactions) or 'none'}")
    print(f"\nKapook recipes compared: {len(kapook)}")

    for strip in (False, True):
        matches = best_matches(records, kapook, strip)
        js = [j for _, _, j in matches]
        label = "quantity stripping ON" if strip else "strings as keyed today"
        print(f"\nBest Kapook Jaccard per MThai post ({label}):")
        for b, n in histogram(js):
            print(f"  {b:14} {n}")
        a = sum(j > 0.9 for j in js)
        b2 = sum(j > 0.85 and rid is not None
                 and title_similarity(rec.title, titles.get(rid, "")) > 0.8
                 for rec, rid, j in matches)
        print(f"  option A (Jaccard > 0.9): {a}; option B (> 0.85 and title > 0.8): {b2}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
