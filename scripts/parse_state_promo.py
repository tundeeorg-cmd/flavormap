"""State-promotional register (HD-39): report (default), ``--load``, or ``--dedup``.

    uv run python -m scripts.parse_state_promo           (make parse-state)  report only
    uv run python -m scripts.parse_state_promo --load    (make load-state)   write
    uv run python -m scripts.parse_state_promo --dedup   (make dedup-state)  HD-41 sheet

**What loads** (HD-39 B, 2026-11-06; parsers in ``src.ingest.state_promotional``):
- **TAT rows with ingredients:** each becomes a ``raw_recipes`` row (with its
  ``redaction_log`` row) and a ``recipes`` row in the ``state_promotional`` register.
- **Rows naming a dish only,** from both sources: they go to ``state_dish_names``.
- **m-culture rows with ingredients:** none load. The researcher chose (2026-11-06) to
  skip them until the line-splitting question (``MC_SPLIT``) is decided; they are counted.

**Province** (researcher, 2026-11-06). Each TAT recipe gets a tier-1
``province_attribution`` row for the province its article lists:
- ``high`` for ``campaign``, ``signature_dish`` and ``dessert_guide`` rows;
- ``medium`` for ``restaurant_guide`` rows, so a robustness check can drop them.

Rows this script owns carry ``method_note`` starting ``HD-39 TAT``; it rewrites only
those. ``region`` is the province's ``region4``.

**Duplicates (HD-41 B: flagged for review, never dropped).** ``--dedup`` compares each
TAT recipe's canonical ingredient set (``recipe_ingredients``, so run ``make lexicon``
first) with every other recipe. It writes the pairs with Jaccard > 0.85 **and** title
ratio > 0.8 to ``data/coverage/dedup_state_YYYYMMDD.csv`` (gitignored). Deciding which
copy to keep is the researcher's.
"""

from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import json
from collections import Counter
from typing import Any

import psycopg

from src.clean.dedupe import jaccard_similarity, title_similarity
from src.config import DATA_DIR
from src.db import get_connection
from src.ingest.state_promotional import (
    MC,
    MC_SPLIT,
    TAT,
    TAT_CSV,
    StateRecord,
    payload,
    read_mc,
    read_tat,
)

REGISTER = "state_promotional"
OWNED = "HD-39 TAT"
# Researcher, 2026-11-06: restaurant guides list where a venue is, not where a dish is
# from, so they are medium; every other TAT list kind is high.
MEDIUM_KINDS = frozenset({"restaurant_guide"})
JACCARD_MIN, TITLE_MIN = 0.85, 0.8      # HD-41 B / CLAUDE.md §7.2 (both strict ">")


def confidence(list_kind: str | None) -> str:
    return "medium" if list_kind in MEDIUM_KINDS else "high"


def records() -> tuple[list[StateRecord], list[StateRecord]]:
    """(TAT, m-culture). m-culture is read with the newline split only to tell which rows
    carry ingredient text; with MC_SPLIT undecided none of its lines are used."""
    return read_tat(), read_mc(MC_SPLIT or "newline")


def report(tat: list[StateRecord], mc: list[StateRecord]) -> None:
    for name, recs in ((TAT, tat), (MC, mc)):
        with_ing = [r for r in recs if r.has_ingredients]
        print(f"{name}: {len(recs)} rows; with ingredients {len(with_ing)}; "
              f"name only {len(recs) - len(with_ing)}; PDPA redactions "
              f"{sum(r.redaction.total for r in recs)} in "
              f"{sum(r.redaction.total > 0 for r in recs)} rows")
    kinds = Counter(r.list_kind for r in tat if r.has_ingredients)
    print("TAT recipes by list kind: " + ", ".join(f"{k} {n}" for k, n in sorted(kinds.items()))
          + f" → high {sum(n for k, n in kinds.items() if confidence(k) == 'high')}, "
            f"medium {sum(n for k, n in kinds.items() if confidence(k) == 'medium')}")
    print(f"m-culture rows with ingredients not loaded (MC_SPLIT undecided): "
          f"{sum(r.has_ingredients for r in mc)}; collector-flagged duplicates "
          f"{sum(r.duplicate_of is not None for r in mc)}")


def _raw(conn: psycopg.Connection[Any], rec: StateRecord, path: str) -> int:
    identity = f"{rec.source_id}:{rec.key}"
    raw_id = conn.execute(
        """INSERT INTO raw_recipes (source_id, source_url, raw_path, published_at,
               parsed_json, content_hash)
           VALUES (%s,%s,%s,%s,%s,%s)
           ON CONFLICT (source_id, content_hash) DO UPDATE
               SET parsed_json = EXCLUDED.parsed_json
           RETURNING raw_id""",
        (rec.source_id, rec.url, path, rec.published_at,
         json.dumps(payload(rec), ensure_ascii=False),
         hashlib.sha256(identity.encode()).hexdigest())).fetchone()[0]  # type: ignore[index]
    red = rec.redaction
    conn.execute(
        """INSERT INTO redaction_log (raw_id, source_id, document_ref, n_names, n_addresses,
               n_phone_numbers, n_emails, n_coordinates, n_media_links,
               suspected_parser_failure, note)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,false,NULL)
           ON CONFLICT (raw_id) DO UPDATE SET parsed_at = now(),
               n_names = EXCLUDED.n_names, n_addresses = EXCLUDED.n_addresses,
               n_phone_numbers = EXCLUDED.n_phone_numbers, n_emails = EXCLUDED.n_emails,
               n_coordinates = EXCLUDED.n_coordinates,
               n_media_links = EXCLUDED.n_media_links""",
        (raw_id, rec.source_id, identity, red.n_names, red.n_addresses, red.n_phone_numbers,
         red.n_emails, red.n_coordinates, red.n_media_links))
    return int(raw_id)


def load(tat: list[StateRecord], mc: list[StateRecord]) -> dict[str, int]:
    stats: Counter[str] = Counter()
    conn = get_connection()
    try:
        provinces = {n: (c, r) for n, c, r in conn.execute(
            "SELECT name_th, province_code, region4 FROM provinces")}
        conn.commit()      # end the implicit read transaction (see scripts/apply_labels.py)
        with conn.transaction():
            conn.execute(
                """DELETE FROM province_attribution pa USING recipes r, raw_recipes rr
                    WHERE pa.recipe_id = r.recipe_id AND rr.raw_id = r.raw_id
                      AND rr.source_id = %s AND pa.method_note LIKE %s""",
                (TAT, f"{OWNED}%"))
            for rec in tat:
                if not rec.has_ingredients:
                    continue
                raw_id = _raw(conn, rec, str(TAT_CSV))
                (rid,) = conn.execute(
                    """INSERT INTO recipes (raw_id, name_th, name_en, register,
                           dish_category_source, extraction_method)
                       VALUES (%s,%s,%s,%s,%s,'parsed')
                       ON CONFLICT (raw_id) DO UPDATE SET name_th = EXCLUDED.name_th,
                           name_en = EXCLUDED.name_en,
                           dish_category_source = EXCLUDED.dish_category_source
                       RETURNING recipe_id""",
                    (raw_id, rec.name, rec.dish_en or None, REGISTER,
                     rec.list_kind)).fetchone()  # type: ignore[misc]
                stats["tat_recipes"] += 1
                code, region = provinces[rec.listed_province_th]
                conf = confidence(rec.list_kind)
                conn.execute(
                    """INSERT INTO province_attribution (recipe_id, province_code, region,
                           tier, confidence, method_note)
                       VALUES (%s,%s,%s,1,%s,%s)""",
                    (rid, code, region, conf,
                     f"{OWNED}: province the TAT article lists ({rec.list_kind})"))
                stats[f"attribution_{conf}"] += 1
            for rec in [*tat, *mc]:
                if rec.has_ingredients:
                    continue
                code = provinces.get(rec.listed_province_th, (None, None))[0]
                conn.execute(
                    """INSERT INTO state_dish_names (source_id, record_key,
                           listed_province_code, dish_name_th, dish_name_en, list_kind,
                           duplicate_of, published_at, source_url)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (source_id, record_key) DO UPDATE SET
                           listed_province_code = EXCLUDED.listed_province_code,
                           dish_name_th = EXCLUDED.dish_name_th,
                           dish_name_en = EXCLUDED.dish_name_en,
                           list_kind = EXCLUDED.list_kind,
                           duplicate_of = EXCLUDED.duplicate_of,
                           published_at = EXCLUDED.published_at,
                           source_url = EXCLUDED.source_url""",
                    (rec.source_id, rec.key, code, rec.dish_th or None, rec.dish_en or None,
                     rec.list_kind, rec.duplicate_of, rec.published_at, rec.url))
                stats[f"dish_names_{rec.source_id}"] += 1
            stats["mc_with_ingredients_skipped"] = sum(r.has_ingredients for r in mc)
        for name, sql in (
            ("recipes_in_db", "SELECT count(*) FROM recipes WHERE register = 'state_promotional'"),
            ("dish_names_in_db", "SELECT count(*) FROM state_dish_names"),
            ("attributions_in_db",
             f"SELECT count(*) FROM province_attribution WHERE method_note LIKE '{OWNED}%'"),
        ):
            stats[name] = conn.execute(sql).fetchone()[0]  # type: ignore[index]
    finally:
        conn.close()
    return dict(stats)


def candidates(sets: dict[int, frozenset[str]], titles: dict[int, str],
               focus: set[int]) -> list[tuple[int, int, float, float]]:
    """HD-41 B pairs (a in `focus`, b any other recipe): Jaccard > 0.85 and title > 0.8.
    Each unordered pair once."""
    out = []
    ids = sorted(sets)
    for a in sorted(focus):
        for b in ids:
            if b == a or (b in focus and b < a):
                continue
            if not sets[a] or not sets[b]:
                continue
            j = jaccard_similarity(set(sets[a]), set(sets[b]))
            if j > JACCARD_MIN:
                t = title_similarity(titles[a], titles[b])
                if t > TITLE_MIN:
                    out.append((a, b, j, t))
    return out


def dedup() -> int:
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT r.recipe_id, r.name_th, rr.source_id, ri.canonical_id
                 FROM recipes r JOIN raw_recipes rr USING (raw_id)
                 JOIN recipe_ingredients ri USING (recipe_id)""").fetchall()
    finally:
        conn.close()
    sets: dict[int, set[str]] = {}
    titles, source = {}, {}
    for rid, name, src, cid in rows:
        sets.setdefault(rid, set()).add(cid)
        titles[rid], source[rid] = name, src
    focus = {rid for rid, s in source.items() if s == TAT}
    pairs = candidates({k: frozenset(v) for k, v in sets.items()}, titles, focus)
    out = DATA_DIR / "coverage" / f"dedup_state_{datetime.date.today():%Y%m%d}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["recipe_a", "source_a", "recipe_b", "source_b", "jaccard", "title_ratio",
                    "decision"])
        for a, b, j, t in pairs:
            w.writerow([a, source[a], b, source[b], f"{j:.3f}", f"{t:.3f}", ""])
    by = Counter("within TAT" if source[b] == TAT else f"TAT vs {source[b]}"
                 for _, b, _, _ in pairs)
    print(f"{len(focus)} TAT recipes with mapped ingredients; {len(pairs)} HD-41 candidate pairs"
          + (" (" + ", ".join(f"{k} {n}" for k, n in sorted(by.items())) + ")" if by else ""))
    print(f"wrote {out} (decision column is the researcher's)")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--load", action="store_true", help="write to the database")
    mode.add_argument("--dedup", action="store_true", help="write the HD-41 review sheet")
    args = ap.parse_args(argv)
    if args.dedup:
        return dedup()
    tat, mc = records()
    report(tat, mc)
    if args.load:
        for k, v in sorted(load(tat, mc).items()):
            print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
