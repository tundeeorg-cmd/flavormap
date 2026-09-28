"""scripts/cooking_sheet.py against every real recipe in the database, not a fixture.

tests/test_cooking_sheet.py proves the sheet's rules on synthetic rows. This file checks
the same rules hold on the actual corpus, recipe by recipe:

- **Every recipe either gets a sheet or is refused.** A recipe with no cleaned
  ingredients must never produce an empty sheet to cook from. Today that is every recipe:
  ``recipe_ingredients`` stays empty until HD-6.
- **For every recipe with cleaned ingredients** (dormant until HD-6, skipped until then):
  each ingredient appears exactly once, in category-then-name order, with its quantity
  read from the stored fields. The recipe's own source text (``raw_text``,
  ``acquisition_raw``) never appears (HD-26), and nothing personal-data-shaped does.

Source text is a leak only where the canonical fields do not explain it: a raw line
"ข่า" matching the canonical name "ข่า" is the pipeline working, not a leak.
Read-only: nothing here writes to the database.
"""

from __future__ import annotations

import datetime
import subprocess

import pytest

from scripts.cooking_sheet import fetch, format_sheet, quantity_text
from src.clean.lexicon import key
from src.config import REPO_ROOT
from src.db import get_connection
from src.ingest.pdpa import find_leaks

TODAY = datetime.date(2026, 9, 28)


def _query(sql: str, *params: object) -> list[tuple[object, ...]]:
    conn = get_connection()
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def _recipe_ids(with_ingredients: bool) -> list[int]:
    op = "EXISTS" if with_ingredients else "NOT EXISTS"
    return [
        int(r[0]) for r in _query(
            f"""SELECT recipe_id FROM recipes r
                 WHERE {op} (SELECT 1 FROM recipe_ingredients ri
                              WHERE ri.recipe_id = r.recipe_id)
                 ORDER BY recipe_id"""
        )
    ]


def test_every_real_recipe_is_accounted_for() -> None:
    total = _query("SELECT count(*) FROM recipes")[0][0]
    assert len(_recipe_ids(True)) + len(_recipe_ids(False)) == total


def test_every_recipe_without_cleaned_ingredients_is_refused_not_given_an_empty_sheet() -> None:
    ids = _recipe_ids(with_ingredients=False)
    if not ids:
        pytest.skip("every recipe has cleaned ingredients")
    for recipe_id in ids:
        found = fetch(recipe_id)
        assert found is not None, f"recipe {recipe_id} exists but fetch() lost it"
        assert found[1] == [], f"recipe {recipe_id}: fetch() invented ingredients"

    # The refusal itself, end to end, on one real recipe: exit 1, no sheet printed.
    result = subprocess.run(
        ["uv", "run", "python", "-m", "scripts.cooking_sheet", str(ids[0])],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=60, check=False,
    )
    assert result.returncode == 1
    assert "no cleaned ingredients yet" in result.stderr
    assert result.stdout == ""


def test_every_real_sheet_obeys_hd26() -> None:
    ids = _recipe_ids(with_ingredients=True)
    if not ids:
        pytest.skip("no recipe has cleaned ingredients yet — recipe_ingredients fills at HD-6")

    problems: list[str] = []
    for recipe_id in ids:
        found = fetch(recipe_id)
        assert found is not None
        dish, ingredients = found
        sheet = format_sheet(recipe_id, dish, ingredients, TODAY)
        rows = [line for line in sheet.splitlines() if line.startswith("| ") and "---" not in line]
        rows = rows[1:]  # drop the header row

        # Each cleaned ingredient exactly once, and the count line agrees.
        stored = _query("SELECT count(*) FROM recipe_ingredients WHERE recipe_id = %s",
                        recipe_id)[0][0]
        if len(rows) != stored or f"{stored} ingredient(s)" not in sheet:
            problems.append(f"{recipe_id}: {len(rows)} sheet rows for {stored} ingredients")

        # Category-then-name order, never the source's.
        expected = sorted(ingredients, key=lambda i: (i.category, i.name_th))
        if [r.split(" | ")[0].removeprefix("| ") for r in rows] != [
            i.name_th for i in expected
        ]:
            problems.append(f"{recipe_id}: ingredients not in category-then-name order")

        # Quantity column reads the stored fields.
        for row, ing in zip(rows, expected, strict=False):
            if f"| {quantity_text(ing)} |" not in row:
                problems.append(f"{recipe_id}: {ing.name_th} quantity misread")

        # No source text, except where the canonical fields account for it. "Explained"
        # comes straight from the lexicon tables, never from what fetch() returned: if
        # source text leaked into those fields, it must not be able to explain itself.
        explained = " ".join(
            " ".join(str(v) for v in row if v)
            for row in _query(
                """SELECT ci.name_th, ci.name_en, ci.category, ri.acquisition_mode
                     FROM recipe_ingredients ri JOIN canonical_ingredients ci
                          USING (canonical_id)
                    WHERE ri.recipe_id = %s""",
                recipe_id,
            )
        )
        for raw_text, acquisition_raw in _query(
            "SELECT raw_text, acquisition_raw FROM recipe_ingredients WHERE recipe_id = %s",
            recipe_id,
        ):
            for source in (raw_text, acquisition_raw):
                if not source:
                    continue
                text = key(str(source))
                if len(text) > 1 and text in sheet and text not in explained:
                    problems.append(f"{recipe_id}: source text reached the sheet")

        if find_leaks(sheet):
            problems.append(f"{recipe_id}: personal-data-shaped text on the sheet")

    assert not problems, "\n".join(problems[:20])
