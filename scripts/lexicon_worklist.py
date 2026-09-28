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
  - ``mapped``: the string is already an ``ingredient_aliases`` alias or a
    ``canonical_ingredients`` Thai name, so it can be skipped.

The output is derived from the DCP corpus, which HD-3 holds to reference-only, so it
goes to ``data/interim/`` (gitignored) and is never committed.
"""

from __future__ import annotations

import argparse
import csv
import re
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

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
SELECT alias FROM ingredient_aliases
UNION
SELECT name_th FROM canonical_ingredients
"""

_WS = re.compile(r"\s+")


def key(text: str) -> str:
    """NFC plus whitespace collapsing. Deliberately nothing more (see module docstring)."""
    return _WS.sub(" ", unicodedata.normalize("NFC", text)).strip()


@dataclass(frozen=True)
class WorklistRow:
    rank: int
    name_th: str
    n_recipes: int
    by_source: dict[str, int]
    cum_share: float
    mapped: bool


def build_worklist(
    rows: Iterable[tuple[str, int, str | None]], mapped: set[str]
) -> list[WorklistRow]:
    """Rank strings from `(source_id, recipe_id, name_th)` rows by recipe count."""
    recipes: defaultdict[str, set[tuple[str, int]]] = defaultdict(set)
    for source_id, recipe_id, name in rows:
        if name and (k := key(name)):
            recipes[k].add((source_id, recipe_id))

    total_pairs = sum(len(v) for v in recipes.values())
    mapped_keys = {key(m) for m in mapped}
    ordered = sorted(recipes.items(), key=lambda kv: (-len(kv[1]), kv[0]))

    out: list[WorklistRow] = []
    covered = 0
    for rank, (name, pairs) in enumerate(ordered, start=1):
        covered += len(pairs)
        out.append(WorklistRow(
            rank=rank,
            name_th=name,
            n_recipes=len(pairs),
            by_source=dict(Counter(source for source, _ in pairs)),
            cum_share=covered / total_pairs,
            mapped=name in mapped_keys,
        ))
    return out


def rank_reaching(worklist: list[WorklistRow], share: float) -> int | None:
    """The first rank at which cumulative coverage reaches `share`, if any."""
    return next((r.rank for r in worklist if r.cum_share >= share), None)


def write_csv(worklist: list[WorklistRow], out: Path) -> None:
    sources = sorted({s for r in worklist for s in r.by_source})
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["rank", "name_th", "n_recipes", *(f"n_{s}" for s in sources),
                    "cum_share", "mapped"])
        for r in worklist:
            w.writerow([r.rank, r.name_th, r.n_recipes,
                        *(r.by_source.get(s, 0) for s in sources),
                        f"{r.cum_share:.4f}", "yes" if r.mapped else ""])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=INTERIM_DIR / "lexicon_worklist.csv")
    args = ap.parse_args()

    conn = get_connection()
    try:
        rows = conn.execute(QUERY).fetchall()
        mapped = {m for (m,) in conn.execute(MAPPED_QUERY)}
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
