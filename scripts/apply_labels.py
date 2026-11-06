"""T1.15: write the HD-37 labels for the commercial register into ``province_attribution``.

    uv run python -m scripts.apply_labels [--dry-run]        (make labels)

**HD-37, decided 2026-11-06: C + D.** Province and region labels, each at its own
confidence, with body text admitted once each claim is read by hand. This script applies
the two **title/category** rules to Kapook and MThai (HD-40), using exactly the rules
``scripts.measure_kapook_labels`` measured (T1.13), so the counts match. For MThai the
post's tags stand in for the category:

- **Rule 1**: one province named in the title or category (``a_strict``) → tier 1,
  ``high``. ``region`` is that province's ``region4``.
- **Rule 2**: otherwise, one compound region term (``b_compound``) → tier 2, ``high``,
  ``province_code`` NULL.

More than one province, or more than one region, is **no label**: rule 2 of CLAUDE.md
§1 forbids picking one. A rule-1 province whose region disagrees with a rule-2 term keeps
the province and records the term in ``conflict_note``.

**Not written here:** body-text claims (rule 3, ``medium``), which wait for the hand
reading HD-37 requires.

**Rows it owns.** Only rows whose ``method_note`` starts with ``HD-37 rule``. A recipe
that already carries any other attribution is left alone and reported.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from scripts.measure_kapook_labels import Recipe, classify, load
from scripts.measure_labelled_fraction import Province, load_provinces
from src.db import get_connection

OWNED = "HD-37 rule"
# Commercial sources the HD-37 rules run on (HD-40: Kapook + MThai). MThai tags are
# stored as `category_source` (src.ingest.mthai_food.payload), so the rules read them.
SOURCES = ("kapook_cooking", "mthai_food")


@dataclass(frozen=True)
class Label:
    province_code: str | None
    region: str
    tier: int
    method_note: str
    conflict_note: str | None = None
    confidence: str = "high"


def label_for(hits: dict[str, set[str]], region_of: dict[str, str]) -> Label | None:
    """The HD-37 title/category label for one recipe's rule hits, or None."""
    provinces, regions = hits.get("a_strict", set()), hits.get("b_compound", set())
    if len(provinces) == 1:
        code = next(iter(provinces))
        region = region_of[code]
        others = regions - {region}
        conflict = (f"title/category also claims region {', '.join(sorted(others))}"
                    if others else None)
        return Label(code, region, 1,
                     f"{OWNED} 1: province named in title/category (a_strict)", conflict)
    if not provinces and len(regions) == 1:
        return Label(None, next(iter(regions)), 2,
                     f"{OWNED} 2: region term in title/category (b_compound)")
    return None


def labels(recipes: list[Recipe], provinces: list[Province],
           official: dict[str, set[str]]) -> dict[int, Label]:
    region_of = {p.code: p.region4 for p in provinces}
    out = {}
    for r in recipes:
        if (lab := label_for(classify(r, provinces, official), region_of)) is not None:
            out[r.recipe_id] = lab
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="report counts, write nothing")
    args = ap.parse_args()

    provinces = load_provinces()
    conn = get_connection()
    try:
        recipes, official = load(conn)
        source_of: dict[int, str] = dict(conn.execute(
            "SELECT r.recipe_id, rr.source_id FROM recipes r JOIN raw_recipes rr "
            "USING (raw_id) WHERE r.register = 'commercial'").fetchall())
        recipes = [r for r in recipes if source_of.get(r.recipe_id) in SOURCES]
        found = labels(recipes, provinces, official)
        foreign = {rid for (rid,) in conn.execute(
            "SELECT recipe_id FROM province_attribution "
            "WHERE recipe_id = ANY(%s) AND coalesce(method_note, '') NOT LIKE %s",
            (list(found), f"{OWNED}%"))}

        by_rule: dict[str, int] = {}
        for lab in found.values():
            unit = lab.province_code or lab.region
            by_rule[f"tier {lab.tier} {unit}"] = by_rule.get(f"tier {lab.tier} {unit}", 0) + 1
        print(f"{len(recipes)} commercial recipes ({', '.join(SOURCES)}); "
              f"{len(found)} labelled by HD-37 rules 1-2")
        for k in sorted(by_rule):
            print(f"  {k}: {by_rule[k]}")
        conflicts = sum(lab.conflict_note is not None for lab in found.values())
        print(f"  with a conflict_note: {conflicts}; skipped (other attribution): {len(foreign)}")
        if args.dry_run:
            return 0

        # The SELECTs above opened an implicit transaction, inside which
        # conn.transaction() is only a savepoint. End it so the block below is the real
        # transaction and commits on exit (the first run printed success and wrote nothing).
        conn.commit()
        with conn.transaction():
            conn.execute(
                """DELETE FROM province_attribution pa USING recipes r, raw_recipes rr
                    WHERE pa.recipe_id = r.recipe_id AND rr.raw_id = r.raw_id
                      AND rr.source_id = ANY(%s) AND pa.method_note LIKE %s""",
                (list(SOURCES), f"{OWNED}%"))
            for rid, lab in found.items():
                if rid in foreign:
                    continue
                conn.execute(
                    """INSERT INTO province_attribution (recipe_id, province_code, region,
                           tier, confidence, method_note, conflict_note)
                       VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                    (rid, lab.province_code, lab.region, lab.tier, lab.confidence,
                     lab.method_note, lab.conflict_note))
        (n,) = conn.execute(
            "SELECT count(*) FROM province_attribution WHERE method_note LIKE %s",
            (f"{OWNED}%",)).fetchone()  # type: ignore[misc]
        print(f"province_attribution now holds {n} HD-37 rows (read back after commit)")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
