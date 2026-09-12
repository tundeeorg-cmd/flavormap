"""Threshold-sweep province eligibility (Bible §7.5) — replaces a single fixed minimum.

CLAUDE.md §7.5: "`src/analyze/eligibility.py` computes eligible provinces at every
threshold 5–30, not at a single pinned value. Headline results reported at 10 / 15 /
25. Every province-level figure caption auto-includes `n = {k} of 77 provinces`."

`PROVINCE_MIN_N` (`src/config.py`) is retained only as `caption()`'s default
threshold — never as a gate that decides which provinces enter an analysis. Nothing
here queries the database: callers compute a per-province count (typically from
`v_recipes_clean`, grouped by `province_code`) and pass it in, the same separation
`src/viz/figure2.py`/`figure4.py` already keep between a pure, testable render/compute
function and the DB-querying script that calls it.
"""

from __future__ import annotations

from collections.abc import Mapping

from src.config import PROVINCE_MIN_N

# Bible §7.5's sweep range and headline thresholds, verbatim.
THRESHOLDS: range = range(5, 31)
HEADLINE_THRESHOLDS: tuple[int, ...] = (10, 15, 25)

# Thailand's province count. Not configurable — it is not a modelling choice.
TOTAL_PROVINCES = 77


def eligible_provinces(counts: Mapping[str, int], threshold: int) -> list[str]:
    """Province codes whose count meets or exceeds `threshold`, sorted for determinism."""
    return sorted(code for code, n in counts.items() if n >= threshold)


def sweep(counts: Mapping[str, int], thresholds: range = THRESHOLDS) -> dict[int, int]:
    """Eligible-province *count* at every threshold in `thresholds`.

    The full sweep, not a single pinned value — this is the function the rule in
    §7.5 is actually about. `headline()` and `caption()` both build on it rather than
    re-implementing the same filter.
    """
    return {t: len(eligible_provinces(counts, t)) for t in thresholds}


def headline(counts: Mapping[str, int]) -> dict[int, int]:
    """Eligible-province count at exactly the three thresholds every headline result
    is reported at: 10, 15, and 25."""
    return {t: len(eligible_provinces(counts, t)) for t in HEADLINE_THRESHOLDS}


def caption(counts: Mapping[str, int], threshold: int = PROVINCE_MIN_N) -> str:
    """The exact wording every province-level figure caption must include:
    'n = {k} of 77 provinces'. Centralised so it is typed once, not once per figure."""
    k = len(eligible_provinces(counts, threshold))
    return f"n = {k} of {TOTAL_PROVINCES} provinces"
