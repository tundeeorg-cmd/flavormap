"""CLAUDE.md §13's test_clean_view_excludes_low, as a general database-level
invariant rather than a check on one specific fixture row: v_recipes_clean's
confidence filter must never let a 'low' row through, tier-4-low included.

Requires the migrated database `make setup` provides — no raw corpus needed, so this
is not skipped, matching tests/test_smoke.py and tests/test_pdpa.py's database-scan
test. The fixture inserts one high-confidence and one low-confidence recipe (full
synthetic FK chain) and deletes every row it created afterward, whether the test
passes or not. Name fields use ทดสอบ ("test"), the same marker tests/test_pdpa.py uses
for synthetic fixtures.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from src.db import get_connection

_SOURCE_ID = "_test_clean_view_src"
_N_INGREDIENTS = 4


@pytest.fixture
def one_high_and_one_low_confidence_recipe() -> Iterator[tuple[int, int]]:
    """Yields (high_confidence_recipe_id, low_confidence_recipe_id)."""
    conn = get_connection()
    canonical_ids = [f"_TEST_CLEAN_ING_{i}" for i in range(_N_INGREDIENTS)]
    try:
        conn.execute(
            """INSERT INTO sources (source_id, source_type, base_url, robots_ok, audited_on)
               VALUES (%s, 'web_scraped', 'https://example.com', true, '2026-09-12')""",
            (_SOURCE_ID,),
        )
        for i, canonical_id in enumerate(canonical_ids):
            conn.execute(
                """INSERT INTO canonical_ingredients (canonical_id, name_th, name_en, category)
                   VALUES (%s, %s, 'test', 'test')""",
                (canonical_id, f"ทดสอบ{i}"),
            )

        recipe_ids = []
        for confidence, tier in (("high", 1), ("low", 4)):
            raw_id = conn.execute(
                """INSERT INTO raw_recipes (source_id, source_url, raw_path, content_hash)
                   VALUES (%s, %s, '/tmp/_test', %s) RETURNING raw_id""",
                (_SOURCE_ID, f"https://example.com/{confidence}", f"deadbeef{confidence}"),
            ).fetchone()[0]
            recipe_id = conn.execute(
                """INSERT INTO recipes (raw_id, name_th, register)
                   VALUES (%s, 'ทดสอบ', 'commercial') RETURNING recipe_id""",
                (raw_id,),
            ).fetchone()[0]
            conn.execute(
                """INSERT INTO province_attribution
                       (recipe_id, province_code, tier, confidence, method_note)
                   VALUES (%s, NULL, %s, %s, 'test fixture')""",
                (recipe_id, tier, confidence),
            )
            for canonical_id in canonical_ids:
                conn.execute(
                    """INSERT INTO recipe_ingredients
                           (recipe_id, canonical_id, raw_text, extraction_method)
                       VALUES (%s, %s, 'ingredient', 'rule')""",
                    (recipe_id, canonical_id),
                )
            recipe_ids.append(recipe_id)
        conn.commit()
        yield recipe_ids[0], recipe_ids[1]
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


def test_clean_view_excludes_low_confidence(
    one_high_and_one_low_confidence_recipe: tuple[int, int],
) -> None:
    high_id, low_id = one_high_and_one_low_confidence_recipe
    conn = get_connection()
    try:
        ids_in_view = {
            row[0]
            for row in conn.execute(
                "SELECT recipe_id FROM v_recipes_clean WHERE recipe_id = ANY(%s)",
                ([high_id, low_id],),
            ).fetchall()
        }
    finally:
        conn.close()
    assert high_id in ids_in_view
    assert low_id not in ids_in_view


def test_no_confidence_low_row_ever_appears_in_the_view() -> None:
    """The general invariant, checked against the live view rather than one fixture
    row — a regression guard against a future edit to v_recipes_clean's WHERE clause."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT count(*) FROM v_recipes_clean WHERE confidence = 'low'"
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    assert row[0] == 0


def test_tier_4_low_never_enters_the_view(
    one_high_and_one_low_confidence_recipe: tuple[int, int],
) -> None:
    """CLAUDE.md §3.2's specific phrasing, checked directly rather than assumed to
    follow from the confidence check above."""
    _, low_id = one_high_and_one_low_confidence_recipe
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT count(*) FROM v_recipes_clean
               WHERE recipe_id = %s AND tier = 4""",
            (low_id,),
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    assert row[0] == 0
