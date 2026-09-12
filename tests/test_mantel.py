"""src/analyze/mantel.py — CLAUDE.md §13's test_mantel_recovers_known and the
properties that make a permutation-based correlation test trustworthy: it finds a
planted signal, it does not find one that is not there, and it never reports p = 0.

No database, no real corpus: distance matrices are synthetic throughout, matching
tests/test_region_signal.py's approach to the same class of test.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.analyze.mantel import mantel_test

PERMUTATIONS = 999


def _symmetric_zero_diagonal(rng: np.random.Generator, n: int) -> np.ndarray:
    m = rng.random((n, n))
    m = (m + m.T) / 2
    np.fill_diagonal(m, 0.0)
    return m


def _matrices_with_planted_correlation(
    n: int, r_target: float, seed: int
) -> tuple[np.ndarray, np.ndarray]:
    """Two n x n distance-like matrices built so the correlation between them is
    approximately `r_target`, rather than merely hoped for."""
    rng = np.random.default_rng(seed)
    shared = _symmetric_zero_diagonal(rng, n)
    noise = _symmetric_zero_diagonal(rng, n)
    a = shared
    b = r_target * shared + (1 - r_target) * noise
    return a, b


def test_it_recovers_a_planted_signal() -> None:
    """CLAUDE.md §13's test_mantel_recovers_known, verbatim: planted r=0.5 -> p < 0.01."""
    a, b = _matrices_with_planted_correlation(n=20, r_target=0.5, seed=1)
    result = mantel_test(a, b, PERMUTATIONS, seed=1)
    assert result.r > 0.3
    assert result.p_value < 0.01


def test_it_does_not_find_a_signal_in_independent_matrices() -> None:
    rng = np.random.default_rng(9)
    a = _symmetric_zero_diagonal(rng, 20)
    b = _symmetric_zero_diagonal(rng, 20)
    result = mantel_test(a, b, PERMUTATIONS, seed=9)
    assert result.p_value > 0.05


def test_a_matrix_correlated_with_itself_is_r_one() -> None:
    rng = np.random.default_rng(2)
    a = _symmetric_zero_diagonal(rng, 10)
    result = mantel_test(a, a, PERMUTATIONS, seed=2)
    assert result.r == pytest.approx(1.0)
    assert result.p_value < 0.01


def test_the_p_value_can_never_be_zero() -> None:
    """A permutation test cannot support p = 0: the observed arrangement is itself one
    of the arrangements. Both terms carry the +1 (mirrors
    test_region_signal.py::test_the_p_value_can_never_be_zero)."""
    rng = np.random.default_rng(3)
    a = _symmetric_zero_diagonal(rng, 10)
    result = mantel_test(a, a, PERMUTATIONS, seed=3)
    assert result.p_value == pytest.approx(1 / (PERMUTATIONS + 1))
    assert result.p_value > 0


def test_it_is_deterministic_under_a_fixed_seed() -> None:
    a, b = _matrices_with_planted_correlation(n=15, r_target=0.4, seed=4)
    first = mantel_test(a, b, PERMUTATIONS, seed=42)
    second = mantel_test(a, b, PERMUTATIONS, seed=42)
    assert first.p_value == second.p_value
    assert first.r == second.r


def test_mismatched_shapes_are_rejected() -> None:
    with pytest.raises(ValueError):
        mantel_test(np.zeros((5, 5)), np.zeros((6, 6)))


def test_a_non_square_matrix_is_rejected() -> None:
    with pytest.raises(ValueError):
        mantel_test(np.zeros((5, 6)), np.zeros((5, 6)))
