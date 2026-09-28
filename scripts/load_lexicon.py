"""Load the hand-authored lexicon into the database (HD-6, HD-10).

    uv run python -m scripts.load_lexicon [--dir data/reference/lexicon]

Reads the three CSV files ``src.clean.lexicon`` documents, validates them, and upserts
``canonical_ingredients``, ``ingredient_aliases`` and ``ingredient_conflations`` in one
transaction. Every row is ``approved_by_human``; every alias is ``match_method =
'manual'``. The files are the researcher's approval (rule 4).

All-or-nothing. File problems are all listed before anything is written. After the
writes, and before commit, the conflation guard runs against the whole database, so an
alias that reached ``ingredient_aliases`` by another route and now maps across a pair
aborts the load too.

**Nothing is deleted.** An entry, alias or pair that is in the database but no longer in
the files is reported, not removed: recipes may already be mapped to it, and what a
removal means is the researcher's call.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.clean.lexicon import CONFLATION_VIOLATIONS, Lexicon, LexiconError, read_lexicon
from src.config import REFERENCE_DIR
from src.db import get_connection

LEXICON_DIR = REFERENCE_DIR / "lexicon"

UPSERT_CANONICAL = """
INSERT INTO canonical_ingredients
    (canonical_id, name_th, name_en, category, is_fermented, regional_note,
     decision_note, approved_by_human)
VALUES (%s, %s, %s, %s, %s, %s, %s, true)
ON CONFLICT (canonical_id) DO UPDATE SET
    name_th = EXCLUDED.name_th, name_en = EXCLUDED.name_en,
    category = EXCLUDED.category, is_fermented = EXCLUDED.is_fermented,
    regional_note = EXCLUDED.regional_note,
    decision_note = EXCLUDED.decision_note, approved_by_human = true
"""

UPSERT_ALIAS = """
INSERT INTO ingredient_aliases (alias, canonical_id, match_method, match_score,
                                approved_by_human)
VALUES (%s, %s, 'manual', NULL, true)
ON CONFLICT (alias) DO UPDATE SET
    canonical_id = EXCLUDED.canonical_id, match_method = 'manual',
    match_score = NULL, approved_by_human = true
"""

UPSERT_CONFLATION = """
INSERT INTO ingredient_conflations (canonical_id_a, canonical_id_b, reason)
VALUES (%s, %s, %s)
ON CONFLICT (canonical_id_a, canonical_id_b) DO UPDATE SET reason = EXCLUDED.reason
"""


def load(lexicon: Lexicon) -> dict[str, list[str]]:
    """Upsert `lexicon` in one transaction. Returns what is in the database but not in
    the files, by table, for reporting."""
    conn = get_connection()
    try:
        with conn.transaction():
            for c in lexicon.canonicals:
                conn.execute(UPSERT_CANONICAL, (c.canonical_id, c.name_th, c.name_en,
                                                c.category, c.is_fermented,
                                                c.regional_note,
                                                c.decision_note))
            for alias, cid in lexicon.aliases.items():
                conn.execute(UPSERT_ALIAS, (alias, cid))
            for p in lexicon.conflations:
                conn.execute(UPSERT_CONFLATION, (p.canonical_id_a, p.canonical_id_b,
                                                 p.reason))
            violations = conn.execute(CONFLATION_VIOLATIONS).fetchall()
            if violations:
                raise LexiconError("\n".join(
                    f"alias {alias} maps to {to} but is the name of {own}, "
                    "across a conflation pair"
                    for alias, to, own in violations
                ))

        ids = {c.canonical_id for c in lexicon.canonicals}
        pairs = {(p.canonical_id_a, p.canonical_id_b) for p in lexicon.conflations}
        return {
            "canonical_ingredients": sorted(
                r[0] for r in conn.execute("SELECT canonical_id FROM canonical_ingredients")
                if r[0] not in ids),
            "ingredient_aliases (manual)": sorted(
                r[0] for r in conn.execute(
                    "SELECT alias FROM ingredient_aliases WHERE match_method = 'manual'")
                if r[0] not in lexicon.aliases),
            "ingredient_conflations": sorted(
                f"{a}/{b}" for a, b in conn.execute(
                    "SELECT canonical_id_a, canonical_id_b FROM ingredient_conflations")
                if (a, b) not in pairs),
        }
    finally:
        conn.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", type=Path, default=LEXICON_DIR)
    args = ap.parse_args()

    try:
        lexicon = read_lexicon(args.dir)
        not_in_files = load(lexicon)
    except LexiconError as e:
        print(f"refused — nothing loaded:\n{e}", file=sys.stderr)
        return 1

    print(f"loaded {len(lexicon.canonicals)} entries, {len(lexicon.aliases)} aliases "
          f"(entry names included), {len(lexicon.conflations)} conflation pairs")
    for table, keys in not_in_files.items():
        if keys:
            print(f"in {table} but not in the files (not removed): {', '.join(keys)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
