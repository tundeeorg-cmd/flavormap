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

# HD-23 (docs/decisions.md, 2026-09-28): the threshold applies to the commercial
# register only. Official (at most 3 dishes per province, by state selection) and
# domestic (the Nakhon Ratchasima and Buri Ram interviews, HD-32) are complete-by-design
# samples and enter analyses wherever they exist, without a count threshold.
THRESHOLD_REGISTERS: tuple[str, ...] = ("commercial",)

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


def sweep_by_register(
    counts_by_register: Mapping[str, Mapping[str, int]],
    thresholds: range = THRESHOLDS,
) -> list[tuple[str, int, int, list[str]]]:
    """The sweep run separately for each register, as long-format rows of
    `(register, threshold, n_eligible, eligible_province_codes)`.

    Registers are never summed: §3.2 forbids pooling corpora without a source
    indicator, and a province with 12 official plus 12 commercial recipes is not a
    province with 24 of anything. Whether an analysis needs a province to clear the
    threshold in one register, in each compared register, or in some combination is a
    per-analysis decision this function does not make — it reports every register and
    leaves the choice to the caller.
    """
    return [
        (register, t, len(codes), codes)
        for register in sorted(counts_by_register)
        for t in thresholds
        for codes in [eligible_provinces(counts_by_register[register], t)]
    ]


def caption(counts: Mapping[str, int], threshold: int = PROVINCE_MIN_N) -> str:
    """The exact wording every province-level figure caption must include:
    'n = {k} of 77 provinces'. Centralised so it is typed once, not once per figure."""
    k = len(eligible_provinces(counts, threshold))
    return f"n = {k} of {TOTAL_PROVINCES} provinces"
