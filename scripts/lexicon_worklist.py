"""Ranked worklist for authoring the canonical-ingredient lexicon (HD-6).

    uv run python -m scripts.lexicon_worklist [--out data/interim/lexicon_worklist.csv]

HD-6 — "author the first 100 canonical ingredients by hand" — is the researcher's. This
script only orders the work: every ingredient string in the parsed corpus, ranked by the
number of recipes it appears in, so the first entries authored cover the most recipes.

**Only recipes with a ``recipes`` row are counted.** ``recipe_ingredients`` keys on
``recipe_id``, so those are the only rows canonicalisation can ever fill.

**No grouping of variants.** Strings are compared after NFC normalisation and whitespace
collapsing only: ``พริกขี้หนู`` and ``พริกขี้หนูสวน`` stay separate rows. Deciding that
two strings are the same ingredient *is* the lexicon work, and rule 4 forbids automating
it. What a worklist can do honestly is put them in front of the researcher, ranked.

**Columns.**
  - ``rank``: by ``n_recipes`` descending, then string, for a stable order.
  - ``n_recipes``: distinct recipes containing the string, which is the coverage it buys.
  - ``n_<source_id>``: the same count per source. Sources are never pooled silently
    (§3.2); the ranking uses the total only because it is a to-do list, not an analysis.
  - ``cum_share``: running share of all (recipe, string) pairs covered by this row and
    those above it.
  - ``mapped``: ``yes`` when the string is already an ``ingredient_aliases`` alias or a
    ``canonical_ingredients`` Thai name, so it can be skipped; ``conflict`` when it maps
    to more than one entry, which the lexicon loader should have refused.
  - ``canonical_id``, ``category``: the entry a mapped string belongs to, and that
    entry's HD-27 category. Blank for unmapped strings. **No category is ever
    suggested**: assigning one is the researcher's call (HD-27's culinary-role rule).

**The category check.** After the table, the script prints the lexicon's entries per
HD-27 category, flags any category not on HD-27's list and an ``other`` share over the
5% ceiling, and shows how much of the corpus each category's mapped strings cover.

The output is derived from the DCP corpus, which HD-3 holds to reference-only, so it
goes to ``data/interim/`` (gitignored) and is never committed.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from src.clean.lexicon import OTHER_CEILING, check_categories, key
from src.config import INTERIM_DIR
from src.db import get_connection

QUERY = """
SELECT rr.source_id, r.recipe_id, i ->> 'name_th'
  FROM recipes r
  JOIN raw_recipes rr ON rr.raw_id = r.raw_id
  CROSS JOIN LATERAL jsonb_array_elements(
      COALESCE(rr.parsed_json -> 'ingredients', '[]'::jsonb)) AS i
"""

MAPPED_QUERY = """
SELECT a.alias, a.canonical_id, ci.category
  FROM ingredient_aliases a JOIN canonical_ingredients ci USING (canonical_id)
UNION
SELECT name_th, canonical_id, category FROM canonical_ingredients
"""

CATEGORY_QUERY = "SELECT category, count(*) FROM canonical_ingredients GROUP BY category"

CONFLICT = "conflict"

@dataclass(frozen=True)
class WorklistRow:
    rank: int
    name_th: str
    n_recipes: int
    by_source: dict[str, int]
    cum_share: float
    mapped: bool
    canonical_id: str | None = None
    category: str | None = None  # an HD-27 category, or CONFLICT


def mapping_index(
    mappings: Iterable[tuple[str, str, str]],
) -> dict[str, tuple[str, str]]:
    """`{string: (canonical_id, category)}` from `(alias, canonical_id, category)` rows.
    A string that maps to two different entries gets `(CONFLICT, CONFLICT)`."""
    index: dict[str, tuple[str, str]] = {}
    for alias, canonical_id, category in mappings:
        k = key(alias)
        if k in index and index[k][0] != canonical_id:
            index[k] = (CONFLICT, CONFLICT)
        elif k not in index:
            index[k] = (canonical_id, category)
    return index


def build_worklist(
    rows: Iterable[tuple[str, int, str | None]],
    mapped: dict[str, tuple[str, str]],
) -> list[WorklistRow]:
    """Rank strings from `(source_id, recipe_id, name_th)` rows by recipe count.
    `mapped` is `mapping_index()`'s output."""
    recipes: defaultdict[str, set[tuple[str, int]]] = defaultdict(set)
    for source_id, recipe_id, name in rows:
        if name and (k := key(name)):
            recipes[k].add((source_id, recipe_id))

    total_pairs = sum(len(v) for v in recipes.values())
    ordered = sorted(recipes.items(), key=lambda kv: (-len(kv[1]), kv[0]))

    out: list[WorklistRow] = []
    covered = 0
    for rank, (name, pairs) in enumerate(ordered, start=1):
        covered += len(pairs)
        canonical_id, category = mapped.get(name, (None, None))
        out.append(WorklistRow(
            rank=rank,
            name_th=name,
            n_recipes=len(pairs),
            by_source=dict(Counter(source for source, _ in pairs)),
            cum_share=covered / total_pairs,
            mapped=name in mapped,
            canonical_id=canonical_id,
            category=category,
        ))
    return out


def rank_reaching(worklist: list[WorklistRow], share: float) -> int | None:
    """The first rank at which cumulative coverage reaches `share`, if any."""
    return next((r.rank for r in worklist if r.cum_share >= share), None)


def category_check(
    entries_by_category: dict[str, int], worklist: list[WorklistRow]
) -> list[str]:
    """HD-27's category check, as printable lines: entries per category (HD-27's order),
    any category not on the list, the `other` share against its ceiling, and the share
    of all (recipe, string) pairs each category's mapped strings cover."""
    check = check_categories(entries_by_category)
    if check.total == 0:
        return ["lexicon: no entries yet, so there is nothing to check against HD-27"]

    lines = ["lexicon entries by HD-27 category: " + ", ".join(
        f"{c} {n}" for c, n in check.by_category.items()
    )]
    if check.unknown:
        lines.append(f"  ⚠ not in HD-27's list: {', '.join(check.unknown)}")
    flag = (f"  ⚠ over HD-27's {OTHER_CEILING:.0%} ceiling: the taxonomy needs revisiting "
            "(docs/limitations.md)") if check.over_ceiling else ""
    lines.append(f"  'other': {check.other} of {check.total} entries "
                 f"({check.other_share:.1%}){flag}")

    pairs = sum(r.n_recipes for r in worklist)
    by_category: Counter[str] = Counter()
    for r in worklist:
        if r.category:
            by_category[r.category] += r.n_recipes
    if pairs and by_category:
        mapped_share = sum(by_category.values()) / pairs
        lines.append(f"  mapped strings cover {mapped_share:.1%} of (recipe, string) pairs: "
                     + ", ".join(f"{c} {n / pairs:.1%}"
                                 for c, n in sorted(by_category.items(),
                                                    key=lambda kv: (-kv[1], kv[0]))))
    conflicts = [r.name_th for r in worklist if r.category == CONFLICT]
    if conflicts:
        lines.append(f"  ⚠ mapped to more than one entry: {', '.join(conflicts)}")
    return lines


def write_csv(worklist: list[WorklistRow], out: Path) -> None:
    sources = sorted({s for r in worklist for s in r.by_source})
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["rank", "name_th", "n_recipes", *(f"n_{s}" for s in sources),
                    "cum_share", "mapped", "canonical_id", "category"])
        for r in worklist:
            w.writerow([r.rank, r.name_th, r.n_recipes,
                        *(r.by_source.get(s, 0) for s in sources),
                        f"{r.cum_share:.4f}",
                        (CONFLICT if r.category == CONFLICT else "yes") if r.mapped else "",
                        "" if r.category == CONFLICT else (r.canonical_id or ""),
                        "" if r.category == CONFLICT else (r.category or "")])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=INTERIM_DIR / "lexicon_worklist.csv")
    args = ap.parse_args()

    conn = get_connection()
    try:
        rows = conn.execute(QUERY).fetchall()
        mapped = mapping_index(conn.execute(MAPPED_QUERY).fetchall())
        entries_by_category = {c: n for c, n in conn.execute(CATEGORY_QUERY)}
    finally:
        conn.close()

    worklist = build_worklist(rows, mapped)
    write_csv(worklist, args.out)

    n_recipes = len({(s, r) for s, r, _ in rows})
    print(f"wrote {args.out}")
    print(f"{len(worklist)} distinct strings across {n_recipes} recipes; "
          f"{sum(r.mapped for r in worklist)} already mapped")
    if worklist:
        top = worklist[min(100, len(worklist)) - 1]
        print(f"top {top.rank} strings cover {top.cum_share:.1%} of (recipe, string) pairs")
        for share in (0.5, 0.8, 0.9):
            print(f"  {share:.0%} coverage at rank {rank_reaching(worklist, share)}")
    for line in category_check(entries_by_category, worklist):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
