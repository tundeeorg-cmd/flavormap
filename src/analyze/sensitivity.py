"""Data access for sensitivity analysis — CLAUDE.md §3.2, data-access half only.

§3.2: "All analysis reads v_recipes_clean: attribution confidence in (high, medium),
3-25 mapped ingredients. Low-confidence rows exist for sensitivity analysis only and
are pulled explicitly by src/analyze/sensitivity.py. Tier-4-low never enters the view."

This module pulls exactly the rows `v_recipes_clean`'s confidence filter excludes
(`db/migrations/021_v_recipes_low_confidence.sql`), in the same shape, so a caller can
compare a result computed on `v_recipes_clean` alone against the same result
recomputed with these rows included. Tier-4-low rows are returned here — the rule
above is that they never enter `v_recipes_clean`, not that no sensitivity check may
ever look at them.

**Deliberately not built here: what "sensitivity analysis" means.** Which comparison
to run, which statistic to recompute, what a meaningful shift looks like — none of
that is specified by §3.2, which names only the data this module must expose. Guessing
a methodology would be exactly the kind of analytical judgment call this project
reserves for the researcher, the same reason `src/analyze/eligibility.py`'s sibling
gap was filled but this one is only half-filled.

Until HD-6 (canonical ingredients) is decided, `recipe_ingredients` is empty and both
`v_recipes_clean` and `v_recipes_low_confidence` INNER JOIN it — so
`low_confidence_recipes()` returns `[]` regardless of how much raw data is loaded.
That is the existing `v_recipes_clean` constraint, not a new one.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from src.db import get_connection

_COLUMNS = (
    "recipe_id", "name_th", "dish_category_source", "province_code", "region",
    "confidence", "tier", "source_id", "source_type", "published_at",
    "n_ingredients", "register",
)


@dataclass(frozen=True)
class LowConfidenceRecipe:
    """One row of `v_recipes_low_confidence` — the same shape `v_recipes_clean`
    returns, for a row that view's confidence filter excludes."""

    recipe_id: int
    name_th: str
    dish_category_source: str | None
    province_code: str | None
    region: str | None
    confidence: str
    tier: int
    source_id: str
    source_type: str
    published_at: datetime.date | None
    n_ingredients: int
    register: str


def low_confidence_recipes() -> list[LowConfidenceRecipe]:
    """Every row `v_recipes_clean`'s confidence filter excludes — pulled explicitly,
    never silently folded into the main analysis. Includes tier-4-low."""
    conn = get_connection()
    try:
        rows = conn.execute(
            f"SELECT {', '.join(_COLUMNS)} FROM v_recipes_low_confidence"
        ).fetchall()
    finally:
        conn.close()
    return [LowConfidenceRecipe(*row) for row in rows]
