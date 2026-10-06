"""scripts/eligibility_sweep.py's database half — does it count exactly the
`v_recipes_clean` rows that carry a province, per register, and nothing else?

Requires the migrated database `make setup` provides, like tests/test_sensitivity.py,
whose fixture pattern this follows: a synthetic FK chain inserted under a test-only
source_id and deleted afterward in dependency order, pass or fail. Names use ทดสอบ
("test"), the marker tests/test_pdpa.py uses for synthetic fixtures.

Five recipes, one per case, all with 3 ingredients:
  - commercial, TH-55, high confidence   → counted
  - commercial, TH-55, medium confidence → counted
  - commercial, NULL province, high      → excluded (rule 2)
  - commercial, TH-55, low confidence    → excluded (not in the view)
  - official,   TH-55, high confidence   → excluded (HD-23: threshold is commercial-only)
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from scripts.eligibility_sweep import province_counts_by_register
from src.analyze.eligibility import THRESHOLD_REGISTERS
from src.db import get_connection

_SOURCE_ID = "_test_eligibility_src"
_CANONICAL_IDS = [f"_TEST_ELIG_ING_{i}" for i in range(3)]
_PROVINCE = "TH-55"  # Nan

# (register, province_code, confidence)
_CASES: list[tuple[str, str | None, str]] = [
    ("commercial", _PROVINCE, "high"),
    ("commercial", _PROVINCE, "medium"),
    ("commercial", None, "high"),
    ("commercial", _PROVINCE, "low"),
    ("official", _PROVINCE, "high"),
]


@pytest.fixture
def fixture_recipes() -> Iterator[None]:
    conn = get_connection()
    # Provinces are loaded by scripts/load_geometry.py, not by a migration, so a fresh
    # database (make verify) has none. Create Nan's row only if it is missing, and remove
    # only a row this fixture created. The live row, when present, is never touched.
    created_province = conn.execute(
        """INSERT INTO provinces (province_code, name_th, name_en, region4,
                                 centroid_lat, centroid_lon)
           VALUES (%s, 'น่าน', 'Nan', 'North', 18.8, 100.8)
           ON CONFLICT (province_code) DO NOTHING RETURNING province_code""",
        (_PROVINCE,),
    ).fetchone() is not None
    conn.commit()
    try:
        conn.execute(
            """INSERT INTO sources (source_id, source_type, base_url, robots_ok, audited_on)
               VALUES (%s, 'web_scraped', 'https://example.com', true, '2026-09-28')""",
            (_SOURCE_ID,),
        )
        for i, canonical_id in enumerate(_CANONICAL_IDS):
            conn.execute(
                """INSERT INTO canonical_ingredients
                   (canonical_id, name_th, name_en, category, is_fermented)
                   VALUES (%s, %s, 'test', 'other', false)""",
                (canonical_id, f"ทดสอบ{i}"),
            )
        for n, (register, province_code, confidence) in enumerate(_CASES):
            raw_id = conn.execute(
                """INSERT INTO raw_recipes (source_id, source_url, raw_path, content_hash)
                   VALUES (%s, %s, '/tmp/_test', %s) RETURNING raw_id""",
                (_SOURCE_ID, f"https://example.com/{n}", f"deadbeef{n}"),
            ).fetchone()[0]
            recipe_id = conn.execute(
                """INSERT INTO recipes (raw_id, name_th, register, extraction_method)
                   VALUES (%s, 'ทดสอบ', %s, 'parsed') RETURNING recipe_id""",
                (raw_id, register),
            ).fetchone()[0]
            conn.execute(
                """INSERT INTO province_attribution
                       (recipe_id, province_code, tier, confidence, method_note)
                   VALUES (%s, %s, 1, %s, 'test fixture')""",
                (recipe_id, province_code, confidence),
            )
            for canonical_id in _CANONICAL_IDS:
                conn.execute(
                    """INSERT INTO recipe_ingredients
                           (recipe_id, canonical_id, raw_text, extraction_method)
                       VALUES (%s, %s, 'ingredient', 'rule')""",
                    (recipe_id, canonical_id),
                )
        conn.commit()
        yield
    finally:
        conn.rollback()
        conn.execute(
            "DELETE FROM recipe_ingredients WHERE canonical_id = ANY(%s)", (_CANONICAL_IDS,)
        )
        conn.execute(
            "DELETE FROM canonical_ingredients WHERE canonical_id = ANY(%s)", (_CANONICAL_IDS,)
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
        if created_province:
            conn.execute("DELETE FROM provinces WHERE province_code = %s", (_PROVINCE,))
        conn.commit()
        conn.close()


def test_counts_only_high_and_medium_rows_that_carry_a_province(fixture_recipes: None) -> None:
    conn = get_connection()
    try:
        others = conn.execute(
            """SELECT count(*) FROM v_recipes_clean
                WHERE register = 'commercial' AND province_code = %s
                  AND source_id <> %s""",
            (_PROVINCE, _SOURCE_ID),
        ).fetchone()[0]
    finally:
        conn.close()
    counts = province_counts_by_register()["commercial"]
    assert counts[_PROVINCE] == others + 2
    # The high-confidence NULL-province fixture row is in the view but never counted.
    assert None not in counts


def test_only_threshold_registers_are_counted(fixture_recipes: None) -> None:
    # The official fixture row is in v_recipes_clean, but HD-23 keeps the official
    # register out of the threshold entirely.
    assert set(province_counts_by_register()) == set(THRESHOLD_REGISTERS) == {"commercial"}
