"""scripts/cooking_sheet.py — the RQ4 cooking sheet shows the cleaned table and
nothing from the source (HD-26).

The most important assertion is the negative one: a recipe's raw_text never appears
on its sheet, however distinctive.
"""

from __future__ import annotations

import datetime
from collections.abc import Iterator

import pytest

from scripts.cooking_sheet import SheetIngredient, fetch, format_sheet, quantity_text

TODAY = datetime.date(2026, 9, 28)


def _ing(name: str, category: str = "herb", **kw: object) -> SheetIngredient:
    fields: dict[str, object] = {
        "name_en": "gloss", "quantity_g": None, "has_quantity": False,
        "acquisition_mode": None, **kw,
    }
    return SheetIngredient(name_th=name, category=category, **fields)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("ing", "expected"),
    [
        (_ing("ก", quantity_g=150.0, has_quantity=True), "150 g"),
        (_ing("ก", quantity_g=2.5, has_quantity=True), "2.5 g"),
        (_ing("ก", has_quantity=True), "quantity not converted"),
        (_ing("ก"), "no quantity"),
    ],
)
def test_quantity_reads_the_stored_fields_exactly(ing: SheetIngredient, expected: str) -> None:
    assert quantity_text(ing) == expected


def test_ingredients_are_listed_by_category_then_name_not_input_order() -> None:
    sheet = format_sheet(1, "ทดสอบ", [
        _ing("ตะไคร้", "herb"),
        _ing("กะทิ", "dairy_like"),
        _ing("ข่า", "herb"),
    ], TODAY)
    positions = [sheet.index(n) for n in ("กะทิ", "ข่า", "ตะไคร้")]
    assert positions == sorted(positions)


def test_sheet_shows_every_hd26_field() -> None:
    sheet = format_sheet(7, "แกงทดสอบ", [
        _ing("ข่า", name_en="galangal", quantity_g=20.0, has_quantity=True,
             acquisition_mode="grown"),
    ], TODAY)
    for text in ("แกงทดสอบ", "recipe_id 7", "2026-09-28", "ข่า", "galangal", "20 g", "grown"):
        assert text in sheet


def test_unmapped_acquisition_mode_is_a_dash_not_a_guess() -> None:
    assert "| no quantity | — |" in format_sheet(1, "ทดสอบ", [_ing("ข่า")], TODAY)


# ── database ──────────────────────────────────────────────────────────────────

_SOURCE_ID = "_test_cooking_sheet_src"
_CANONICAL = "_TEST_SHEET_ING"
_RAW_LINE = "ข่าแก่ๆ หั่นแว่นบาง ๆ 3 แว่น (SOURCE-ONLY-MARKER)"


@pytest.fixture
def recipe_id() -> Iterator[int]:
    from src.db import get_connection

    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO sources (source_id, source_type, base_url, robots_ok, audited_on)
               VALUES (%s, 'web_scraped', 'https://example.com', true, '2026-09-28')""",
            (_SOURCE_ID,),
        )
        raw_id = conn.execute(
            """INSERT INTO raw_recipes (source_id, source_url, raw_path, content_hash)
               VALUES (%s, 'https://example.com/1', '/tmp/_test', 'deadbeef')
               RETURNING raw_id""",
            (_SOURCE_ID,),
        ).fetchone()[0]
        rid = conn.execute(
            """INSERT INTO recipes (raw_id, name_th, register)
               VALUES (%s, 'แกงทดสอบ', 'commercial') RETURNING recipe_id""",
            (raw_id,),
        ).fetchone()[0]
        conn.execute(
            """INSERT INTO canonical_ingredients (canonical_id, name_th, name_en, category)
               VALUES (%s, 'ข่าทดสอบ', 'test galangal', 'herb')""",
            (_CANONICAL,),
        )
        conn.execute(
            """INSERT INTO recipe_ingredients (recipe_id, canonical_id, raw_text,
                   has_quantity, acquisition_raw, extraction_method)
               VALUES (%s, %s, %s, true, 'SOURCE-ACQ-MARKER', 'rule')""",
            (rid, _CANONICAL, _RAW_LINE),
        )
        conn.commit()
        yield rid
    finally:
        conn.rollback()
        conn.execute("DELETE FROM recipe_ingredients WHERE canonical_id = %s", (_CANONICAL,))
        conn.execute("DELETE FROM canonical_ingredients WHERE canonical_id = %s", (_CANONICAL,))
        conn.execute(
            """DELETE FROM recipes WHERE raw_id IN
                   (SELECT raw_id FROM raw_recipes WHERE source_id = %s)""",
            (_SOURCE_ID,),
        )
        conn.execute("DELETE FROM raw_recipes WHERE source_id = %s", (_SOURCE_ID,))
        conn.execute("DELETE FROM sources WHERE source_id = %s", (_SOURCE_ID,))
        conn.commit()
        conn.close()


def test_sheet_from_db_never_contains_source_text(recipe_id: int) -> None:
    found = fetch(recipe_id)
    assert found is not None
    dish, ingredients = found
    sheet = format_sheet(recipe_id, dish, ingredients, TODAY)
    assert "ข่าทดสอบ" in sheet and "test galangal" in sheet
    assert "quantity not converted" in sheet
    assert "SOURCE-ONLY-MARKER" not in sheet
    assert "SOURCE-ACQ-MARKER" not in sheet


def test_unknown_recipe_is_none() -> None:
    assert fetch(-1) is None
