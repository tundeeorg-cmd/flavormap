"""Fill ``recipe_ingredients`` from the researcher's lexicon (HD-6 → RQ1).

    uv run python -m scripts.canonicalise        (also run by: make lexicon)

Reads every recipe's raw ingredient strings (the worklist's query) and the lexicon as
loaded in the database (entry names, ``ingredient_aliases``, ``ingredient_alias_splits``),
and rebuilds ``recipe_ingredients`` in one transaction. The mapping rules are in
`src.clean.canonicalise`; this script only reads and writes.

**Rebuild, not append.** Every row with ``human_validated = false`` is deleted and
rewritten, so a mapping the researcher changes or removes in the lexicon files is
reflected after the next ``make lexicon``. Rows marked ``human_validated = true`` are
never touched, and a rebuilt row that collides with one is skipped and counted.

Safe to run with an empty lexicon: it writes nothing and says so.
"""

from __future__ import annotations

import argparse

from scripts.lexicon_worklist import QUERY
from src.clean.canonicalise import canonicalise
from src.clean.lexicon import key
from src.db import get_connection

ENTRIES_QUERY = """
SELECT name_th, canonical_id FROM canonical_ingredients
UNION
SELECT alias, canonical_id FROM ingredient_aliases WHERE approved_by_human
"""
SPLITS_QUERY = """
SELECT alias, canonical_id FROM ingredient_alias_splits WHERE approved_by_human
 ORDER BY alias, canonical_id
"""

DELETE = "DELETE FROM recipe_ingredients WHERE NOT human_validated"
INSERT = """
INSERT INTO recipe_ingredients (recipe_id, canonical_id, raw_text, extraction_method)
VALUES (%s, %s, %s, %s)
ON CONFLICT (recipe_id, canonical_id) DO NOTHING
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="count, write nothing")
    args = ap.parse_args()

    conn = get_connection()
    try:
        lines = conn.execute(QUERY).fetchall()
        single: dict[str, str] = {}
        for alias, cid in conn.execute(ENTRIES_QUERY).fetchall():
            single.setdefault(key(alias), cid)
        splits: dict[str, list[str]] = {}
        for alias, cid in conn.execute(SPLITS_QUERY).fetchall():
            splits.setdefault(key(alias), []).append(cid)

        def entries_for(text: str) -> tuple[str, ...]:
            k = key(text)
            if k in single:
                return (single[k],)
            return tuple(splits.get(k, ()))

        outcome = canonicalise(lines, entries_for)
        print(f"{outcome.mapped_mentions} of {outcome.mentions} ingredient lines mapped "
              f"({outcome.split_mentions} through a split) → {len(outcome.rows)} "
              f"recipe_ingredients rows in "
              f"{len({r.recipe_id for r in outcome.rows})} recipes")
        if args.dry_run:
            print("dry run: nothing written")
            return 0
        # The reads above opened an implicit transaction, inside which conn.transaction()
        # is only a savepoint and closing the connection would roll everything back. End
        # it so the block below is the real, committed transaction (as apply_labels does).
        conn.commit()
        with conn.transaction():
            deleted = conn.execute(DELETE).rowcount
            skipped = 0
            for r in outcome.rows:
                cur = conn.execute(INSERT, (r.recipe_id, r.canonical_id, r.raw_text,
                                            r.extraction_method))
                skipped += cur.rowcount == 0
        print(f"replaced {deleted} rows; wrote {len(outcome.rows) - skipped}"
              + (f"; {skipped} skipped (a human-validated row exists)" if skipped else ""))
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
