"""src/analyze/sensitivity.py's data-access half — does it pull exactly what
v_recipes_clean excludes, and nothing else?

Requires the migrated database `make setup` provides, same as tests/test_smoke.py and
tests/test_pdpa.py's database-scan test — no raw corpus needed, so this is not
skipped. The fixture below inserts a full synthetic FK chain (source, raw_recipes,
recipes, province_attribution, canonical_ingredients, recipe_ingredients) and deletes
every row it created afterward, in dependency order, whether the test passes or not.
Surname/name fields use ทดสอบ ("test"), the same marker tests/test_pdpa.py uses for
synthetic fixtures — this data is invented, never lifted from a real document.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from src.analyze.sensitivity import low_confidence_recipes
from src.db import get_connection

_SOURCE_ID = "_test_sensitivity_src"
_N_INGREDIENTS = 4


@pytest.fixture
def low_confidence_recipe() -> Iterator[int]:
    conn = get_connection()
    canonical_ids = [f"_TEST_SENS_ING_{i}" for i in range(_N_INGREDIENTS)]
    try:
        conn.execute(
            """INSERT INTO sources (source_id, source_type, base_url, robots_ok, audited_on)
               VALUES (%s, 'web_scraped', 'https://example.com', true, '2026-09-12')""",
            (_SOURCE_ID,),
        )
        raw_id = conn.execute(
            """INSERT INTO raw_recipes (source_id, source_url, raw_path, content_hash)
               VALUES (%s, 'https://example.com/1', '/tmp/_test', 'deadbeef')
               RETURNING raw_id""",
            (_SOURCE_ID,),
        ).fetchone()[0]
        recipe_id = conn.execute(
            """INSERT INTO recipes (raw_id, name_th, register)
               VALUES (%s, 'ทดสอบ', 'commercial') RETURNING recipe_id""",
            (raw_id,),
        ).fetchone()[0]
        conn.execute(
            """INSERT INTO province_attribution
                   (recipe_id, province_code, tier, confidence, method_note)
               VALUES (%s, NULL, 4, 'low', 'test fixture — LLM guess, unverified')""",
            (recipe_id,),
        )
        for i, canonical_id in enumerate(canonical_ids):
            conn.execute(
                """INSERT INTO canonical_ingredients (canonical_id, name_th, name_en, category)
                   VALUES (%s, %s, 'test', 'test')""",
                (canonical_id, f"ทดสอบ{i}"),
            )
            conn.execute(
                """INSERT INTO recipe_ingredients
                       (recipe_id, canonical_id, raw_text, extraction_method)
                   VALUES (%s, %s, %s, 'rule')""",
                (recipe_id, canonical_id, f"ingredient {i}"),
            )
        conn.commit()
        yield recipe_id
    finally:
        conn.execute(
            "DELETE FROM recipe_ingredients WHERE canonical_id = ANY(%s)", (canonical_ids,)
        )
        conn.execute(
            "DELETE FROM canonical_ingredients WHERE canonical_id = ANY(%s)", (canonical_ids,)
        )
        conn.execute(
            """DELETE FROM province_attribution WHERE recipe_id IN
                   (SELECT recipe_id FROM recipes r JOIN raw_recipes rr ON rr.raw_id = r.raw_id
                    WHERE rr.source_id = %s)""",
            (_SOURCE_ID,),
        )
        conn.execute(
            """DELETE FROM recipes WHERE raw_id IN
                   (SELECT raw_id FROM raw_recipes WHERE source_id = %s)""",
            (_SOURCE_ID,),
        )
        conn.execute("DELETE FROM raw_recipes WHERE source_id = %s", (_SOURCE_ID,))
        conn.execute("DELETE FROM sources WHERE source_id = %s", (_SOURCE_ID,))
        conn.commit()
        conn.close()


def test_low_confidence_recipes_returns_the_fixture_row(low_confidence_recipe: int) -> None:
    rows = [r for r in low_confidence_recipes() if r.recipe_id == low_confidence_recipe]
    assert len(rows) == 1
    row = rows[0]
    assert row.confidence == "low"
    assert row.tier == 4  # tier-4-low: excluded from v_recipes_clean, present here
    assert row.register == "commercial"
    assert row.province_code is None
    assert row.n_ingredients == _N_INGREDIENTS
    assert row.source_id == _SOURCE_ID


def test_the_same_recipe_is_absent_from_v_recipes_clean(low_confidence_recipe: int) -> None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM v_recipes_clean WHERE recipe_id = %s", (low_confidence_recipe,)
        ).fetchone()
    finally:
        conn.close()
    assert row is None


def test_returns_no_stray_rows_once_the_fixture_is_gone() -> None:
    assert not any(r.source_id == _SOURCE_ID for r in low_confidence_recipes())
