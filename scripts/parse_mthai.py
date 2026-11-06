"""MThai: report (default) or load (``--load``).

    uv run python -m scripts.parse_mthai          (make parse-mthai)   report only
    uv run python -m scripts.parse_mthai --load   (make load-mthai)    write

The report (counts, fill rates, duplicates against Kapook) was the evidence for HD-40 to
HD-42 and writes nothing; the Kapook side is read on a read-only connection.

**Loading** (HD-40, decided 2026-11-06: Kapook + MThai). Per post: a ``raw_recipes`` row
(``parsed_json`` in Kapook's shape, ``src.ingest.mthai_food.payload``) and its
``redaction_log`` row; then, for single-section posts only (HD-22's rule, applied to
MThai by the researcher), a ``commercial`` ``recipes`` row. Multi-section posts are held
out, counted. ``content_hash`` is of the post's identity, so a re-run updates in place.

**Duplicates.** For each MThai post, the Kapook recipe with the highest ingredient-set
Jaccard (``src.clean.dedupe.jaccard_similarity``) and that pair's title ratio
(``title_similarity``). Sets are built two ways: strings as keyed today (NFC and
whitespace), and with the HD-6 question 6 quantity-stripping prototype on. The lexicon
is empty, so neither is the canonical-ingredient set HD-41 refers to; both are reported
so the gap is visible.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict

from scripts.lexicon_worklist import QUERY as INGREDIENT_QUERY
from scripts.measure_kapook_labels import BARE_REGION_TERMS, REGION_TERMS, region_claims
from src.clean.dedupe import jaccard_similarity, title_similarity
from src.clean.lexicon import key
from src.db import get_connection
from src.ingest.mthai_food import CSV_PATH, SOURCE_ID, MThaiRecord, payload, read_csv

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


def load(records: list[MThaiRecord]) -> dict[str, int]:
    """Write `records` in one transaction. Returns counts for the summary."""
    stats = {"posts": 0, "loaded": 0, "held_out_multi_section": 0, "redactions": 0}
    conn = get_connection()
    try:
        with conn.transaction():
            for rec in records:
                stats["posts"] += 1
                identity = f"{SOURCE_ID}:{rec.post_id}"
                raw_id = conn.execute(
                    """INSERT INTO raw_recipes (source_id, source_url, raw_path,
                           published_at, parsed_json, content_hash)
                       VALUES (%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (source_id, content_hash) DO UPDATE
                           SET parsed_json = EXCLUDED.parsed_json
                       RETURNING raw_id""",
                    (SOURCE_ID, rec.url, str(CSV_PATH), rec.published_at,
                     json.dumps(payload(rec), ensure_ascii=False),
                     hashlib.sha256(identity.encode()).hexdigest()),
                ).fetchone()[0]  # type: ignore[index]
                red = rec.redaction
                stats["redactions"] += red.total
                conn.execute(
                    """INSERT INTO redaction_log (raw_id, source_id, document_ref, n_names,
                           n_addresses, n_phone_numbers, n_emails, n_coordinates,
                           n_media_links, suspected_parser_failure, note)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,false,NULL)
                       ON CONFLICT (raw_id) DO UPDATE SET parsed_at = now(),
                           n_names = EXCLUDED.n_names, n_addresses = EXCLUDED.n_addresses,
                           n_phone_numbers = EXCLUDED.n_phone_numbers,
                           n_emails = EXCLUDED.n_emails,
                           n_coordinates = EXCLUDED.n_coordinates,
                           n_media_links = EXCLUDED.n_media_links""",
                    (raw_id, SOURCE_ID, identity, red.n_names, red.n_addresses,
                     red.n_phone_numbers, red.n_emails, red.n_coordinates,
                     red.n_media_links),
                )
                if not rec.is_single_section:
                    stats["held_out_multi_section"] += 1
                    continue
                conn.execute(
                    """INSERT INTO recipes (raw_id, name_th, register, dish_category_source,
                                            extraction_method)
                       VALUES (%s,%s,'commercial',%s,'parsed')
                       ON CONFLICT (raw_id) DO UPDATE SET name_th = EXCLUDED.name_th,
                           dish_category_source = EXCLUDED.dish_category_source""",
                    (raw_id, rec.title, " | ".join(rec.tags) or None),
                )
                stats["loaded"] += 1
        (n,) = conn.execute(
            "SELECT count(*) FROM recipes r JOIN raw_recipes rr USING (raw_id) "
            "WHERE rr.source_id = %s", (SOURCE_ID,)).fetchone()  # type: ignore[misc]
        stats["recipes_in_db"] = n
    finally:
        conn.close()
    return stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--load", action="store_true", help="write to the database")
    args = ap.parse_args()
    records = read_csv()
    if args.load:
        for k, v in load(records).items():
            print(f"  {k}: {v}")
        return 0
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
    for rule, terms in (("b_compound", REGION_TERMS), ("b_bare", BARE_REGION_TERMS)):
        regions: Counter[str] = Counter()
        for r in records:
            found = region_claims(" ".join([r.title, *r.tags]), terms)
            if len(found) == 1:
                regions[next(iter(found))] += 1
        print(f"  one region claimed in title/tags ({rule}, Kapook's rule): {dict(regions)}")
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
