"""Print the cooking sheet for one recipe: exactly what the cleaned dataset holds (RQ4).

    uv run python -m scripts.cooking_sheet RECIPE_ID [--out sheet.md]

RQ4 cooks each dish "from the cleaned dataset's ingredient list, not the original source
page" (CLAUDE.md §7.4). This sheet is that list, and nothing else. **HD-26** fixes what
it shows: per ingredient, the canonical Thai name, the English gloss, ``quantity_g``
when convertible, and acquisition mode. It never shows ``raw_text``, the source's own
line, because printing it would let the source page back into a test of the pipeline.

**Order carries no information from the source.** ``recipe_ingredients`` has no
position column, so the cleaned dataset does not store the order the source listed
ingredients in. The sheet lists them by category, then Thai name, so it cannot
reintroduce an order the pipeline threw away.

Until HD-6 fills ``recipe_ingredients``, every recipe has an empty cleaned list. The
script then says so and exits non-zero rather than printing an empty sheet to cook from.

The quantity column reads the stored fields exactly:
  - ``quantity_g`` set               → "150 g"
  - ``has_quantity`` but no grams    → "quantity not converted"
  - neither                          → "no quantity" (e.g. ตามชอบ, rule 3)
"""

from __future__ import annotations

import argparse
import datetime
import sys
from dataclasses import dataclass
from pathlib import Path

from src.db import get_connection


@dataclass(frozen=True)
class SheetIngredient:
    name_th: str
    name_en: str
    category: str
    quantity_g: float | None
    has_quantity: bool
    acquisition_mode: str | None


RECIPE_QUERY = "SELECT name_th FROM recipes WHERE recipe_id = %s"

# raw_text and acquisition_raw are deliberately absent: both are source text (HD-26).
INGREDIENTS_QUERY = """
SELECT ci.name_th, ci.name_en, ci.category,
       ri.quantity_g, ri.has_quantity, ri.acquisition_mode
  FROM recipe_ingredients ri
  JOIN canonical_ingredients ci USING (canonical_id)
 WHERE ri.recipe_id = %s
"""


def quantity_text(ing: SheetIngredient) -> str:
    if ing.quantity_g is not None:
        return f"{ing.quantity_g:g} g"
    if ing.has_quantity:
        return "quantity not converted"
    return "no quantity"


def format_sheet(
    recipe_id: int,
    dish_name_th: str,
    ingredients: list[SheetIngredient],
    generated: datetime.date,
) -> str:
    """The sheet as Markdown: a table that prints legibly and reads fine as plain text."""
    ordered = sorted(ingredients, key=lambda i: (i.category, i.name_th))
    lines = [
        f"# {dish_name_th}",
        "",
        f"recipe_id {recipe_id} · sheet generated {generated:%Y-%m-%d} · "
        f"{len(ordered)} ingredient(s)",
        "",
        "Cook from this list only, not the source page. Listed by category, then name: "
        "the cleaned dataset does not store the source's ingredient order.",
        "",
        "| ingredient | gloss | quantity | acquisition |",
        "|---|---|---|---|",
    ]
    for ing in ordered:
        lines.append(
            f"| {ing.name_th} | {ing.name_en} | {quantity_text(ing)} | "
            f"{ing.acquisition_mode or '—'} |"
        )
    lines += [
        "",
        f"Log this cook in data/cook_along/ with recipe_id = {recipe_id}.",
        "",
    ]
    return "\n".join(lines)


def fetch(recipe_id: int) -> tuple[str, list[SheetIngredient]] | None:
    """The dish's Thai name and cleaned ingredients, or None if the recipe does not exist."""
    conn = get_connection()
    try:
        row = conn.execute(RECIPE_QUERY, (recipe_id,)).fetchone()
        if row is None:
            return None
        ingredients = [
            SheetIngredient(*r) for r in conn.execute(INGREDIENTS_QUERY, (recipe_id,))
        ]
    finally:
        conn.close()
    return row[0], ingredients


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("recipe_id", type=int)
    ap.add_argument("--out", type=Path, help="write the sheet here instead of stdout")
    args = ap.parse_args()

    found = fetch(args.recipe_id)
    if found is None:
        print(f"recipe_id {args.recipe_id} is not in recipes", file=sys.stderr)
        return 1
    dish, ingredients = found
    if not ingredients:
        print(
            f"recipe_id {args.recipe_id} ({dish}) has no cleaned ingredients yet — "
            "recipe_ingredients is filled by canonicalisation (HD-6). "
            "There is nothing from the cleaned dataset to cook from.",
            file=sys.stderr,
        )
        return 1

    sheet = format_sheet(args.recipe_id, dish, ingredients, datetime.date.today())
    if args.out:
        args.out.write_text(sheet, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(sheet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
