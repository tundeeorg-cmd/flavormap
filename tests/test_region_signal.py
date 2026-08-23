"""RQ1's specified analysis cannot run on four units, so what replaces it must be honest.

A distance-decay curve with change-point detection needs pairs. Four regions give six,
and a Mantel test on a 4×4 matrix has 4! = 24 distinct permutations, so its smallest
achievable p-value is 1/24 ≈ 0.042 — at its floor before any data is seen. The replacement
tests whether region membership explains composition at all, at the recipe level, where n
is the number of labelled recipes rather than four.

These tests pin the two properties that make that replacement trustworthy: it finds a
planted signal, and it does not find one that is not there.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.analyze.region_signal import (
    cosine_distances,
    group_centroid_distances,
    ingredient_tokens,
    separation_test,
)

PERMUTATIONS = 999


def planted(
    n_per_group: int, groups: int, overlap: float, seed: int
) -> tuple[np.ndarray, list[str]]:
    """Groups with their own vocabulary block, plus a shared block of `overlap` weight."""
    rng = np.random.default_rng(seed)
    width = 12
    matrix = np.zeros((n_per_group * groups, width * groups + width))
    labels = []
    for g in range(groups):
        for i in range(n_per_group):
            row = g * n_per_group + i
            matrix[row, g * width:(g + 1) * width] = rng.random(width)
            matrix[row, -width:] = rng.random(width) * overlap
            labels.append(f"G{g}")
    return matrix, labels


def test_it_finds_a_planted_signal() -> None:
    matrix, labels = planted(15, 4, overlap=0.3, seed=1)
    result = separation_test(matrix, labels, PERMUTATIONS, seed=1)
    assert result.separation > 0
    assert result.p_value <= 0.01


def test_it_does_not_find_a_signal_in_noise() -> None:
    """The same machinery on labels that mean nothing must not clear alpha. Without this,
    a significant result on 58 recipes is not evidence of anything."""
    rng = np.random.default_rng(7)
    matrix = rng.random((60, 40))
    labels = [f"G{i % 4}" for i in range(60)]
    result = separation_test(matrix, labels, PERMUTATIONS, seed=7)
    assert result.p_value > 0.05


def test_the_p_value_can_never_be_zero() -> None:
    """A permutation test cannot support p = 0: the observed arrangement is itself one of
    the arrangements. Both terms carry the +1."""
    matrix, labels = planted(12, 3, overlap=0.0, seed=2)
    result = separation_test(matrix, labels, PERMUTATIONS, seed=2)
    assert result.p_value == pytest.approx(1 / (PERMUTATIONS + 1))
    assert result.p_value > 0


def test_it_is_deterministic_under_the_project_seed() -> None:
    """§1 rule 6 — every stochastic operation takes RANDOM_SEED and repeats exactly."""
    matrix, labels = planted(10, 3, overlap=0.4, seed=3)
    first = separation_test(matrix, labels, PERMUTATIONS, seed=42)
    second = separation_test(matrix, labels, PERMUTATIONS, seed=42)
    assert first.p_value == second.p_value and first.separation == second.separation


def test_a_zero_vector_does_not_divide_by_zero() -> None:
    """A recipe whose every token fell below min_df is an all-zero row, and it must not
    produce a nan that silently propagates through every distance in the matrix."""
    matrix = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
    distances = cosine_distances(matrix)
    assert not np.isnan(distances).any()


def test_centroids_give_one_distance_per_pair() -> None:
    """Four regions, six numbers. The shape is the argument against a decay curve."""
    matrix, labels = planted(5, 4, overlap=0.2, seed=4)
    names, centroids = group_centroid_distances(matrix, labels)
    assert names == ["G0", "G1", "G2", "G3"]
    off_diagonal = centroids[np.triu_indices(4, k=1)]
    assert off_diagonal.size == 6
    assert np.allclose(np.diag(centroids), 0.0)


def test_tokenisation_drops_measures_and_keeps_ingredients() -> None:
    """Provisional pending HD-6, but it must at least not treat a spoon as an ingredient."""
    tokens = ingredient_tokens("กะปิอย่างดี (ห่อใบตองปิ้งพอหอม) 2 ช้อนโต๊ะ")
    assert "กะปิ" in tokens
    assert "ช้อนโต๊ะ" not in tokens
    assert not any(character.isdigit() for token in tokens for character in token)


def test_a_parenthetical_brand_note_is_not_an_ingredient() -> None:
    """`(ตราจี้แซ จากนครสวรรค์)` is a soy sauce brand's home town. It is the reason four
    audit rows read as province labels, and it must not become composition either."""
    tokens = ingredient_tokens("ซีอิ๊วหวาน (ตราจี้แซ จากนครสวรรค์) 2 ช้อนโต๊ะ")
    assert "ซีอิ๊ว" in " ".join(tokens)
    assert "นครสวรรค์" not in tokens
