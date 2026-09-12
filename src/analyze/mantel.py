"""Mantel test — permutation-based correlation between two distance matrices.

CLAUDE.md §5 ("Statistical corrections"): "Mantel significance. Permutation testing,
9,999 permutations. Distance-matrix entries are not independent observations; a
parametric p-value on them is meaningless." §13 names the regression test this module
exists to pass: `test_mantel_recovers_known` — a planted r=0.5 on synthetic data
should return p < 0.01.

This is the general-purpose statistical primitive, **not wired to any specific
research question**. RQ1's original application (a distance-decay curve over 77
provinces) is retired under Bible v4 — see `src.analyze.region_signal`'s docstring for
why the labelled fraction collapses that analysis to four regions, which cannot
support it either. The most likely future use is HD-14 ("choose the competing
boundary set for RQ1 and build the linguistic distance matrix"), still an open,
undecided gate. Building the test does not require that decision; applying it to a
specific pair of matrices does.

One-sided by construction, matching `src.analyze.region_signal.separation_test`: the
Mantel hypothesis of interest is that two distance matrices are *more* correlated than
chance, not merely differently correlated in either direction.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from src.config import RANDOM_SEED


@dataclass
class MantelResult:
    n: int  # number of objects (the matrices' shared side length)
    r: float  # observed Pearson correlation between the two distance vectors
    p_value: float
    n_permutations: int
    #: every permuted r, in permutation order — kept for the same reason
    #: SeparationResult.null is: a non-significant result needs the null shown, not
    #: just a p-value.
    null: list[float] = field(default_factory=list)


def _upper_triangle(matrix: np.ndarray) -> np.ndarray:
    n = matrix.shape[0]
    return matrix[np.triu_indices(n, k=1)]


def _pearson(a: np.ndarray, b: np.ndarray) -> float:
    a_centered = a - a.mean()
    b_centered = b - b.mean()
    denom = np.sqrt((a_centered**2).sum() * (b_centered**2).sum())
    if denom == 0:
        return 0.0
    return float((a_centered * b_centered).sum() / denom)


def mantel_test(
    matrix_a: np.ndarray,
    matrix_b: np.ndarray,
    n_permutations: int = 9_999,
    seed: int = RANDOM_SEED,
) -> MantelResult:
    """Permutation-based correlation between two square distance matrices of the same
    objects, in the same order (row/column `i` must refer to the same object in both).

    Rows and columns of one matrix are permuted *jointly* on each draw — a valid
    Mantel permutation relabels which object is which without disturbing either
    matrix's own internal distance structure, which a naive per-cell shuffle would
    destroy and which is exactly why a Mantel test exists rather than a plain
    correlation test on the flattened matrices (§5's rule against
    `scipy.stats.pearsonr` on flattened matrices).
    """
    if matrix_a.shape != matrix_b.shape or matrix_a.shape[0] != matrix_a.shape[1]:
        raise ValueError("both matrices must be square and share the same shape")

    n = matrix_a.shape[0]
    vec_a = _upper_triangle(matrix_a)
    vec_b = _upper_triangle(matrix_b)
    observed = _pearson(vec_a, vec_b)

    rng = np.random.default_rng(seed)
    order = np.arange(n)
    null: list[float] = []
    at_least_as_extreme = 0
    for _ in range(n_permutations):
        rng.shuffle(order)
        permuted_b = matrix_b[np.ix_(order, order)]
        permuted_r = _pearson(vec_a, _upper_triangle(permuted_b))
        null.append(permuted_r)
        if permuted_r >= observed:
            at_least_as_extreme += 1

    # +1 in both terms: the observed arrangement is itself one of the possible ones,
    # and omitting it can report p = 0, which no permutation test can support (the
    # same correction src.analyze.region_signal.separation_test applies).
    p_value = (at_least_as_extreme + 1) / (n_permutations + 1)
    return MantelResult(
        n=n, r=observed, p_value=p_value, n_permutations=n_permutations, null=null
    )
