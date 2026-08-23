"""Figure 2's renderer, exercised on synthetic input.

Synthetic data here is not a measurement: it tests the plotting machinery — the
significance encoding, the null band, the file that comes out — without touching the
corpus. No synthetic point ever reaches a published figure.

The property worth defending is the one the figure exists for. A non-significant pair must
render as a hollow point inside its band rather than as an absence, because three of the
six pairs are undetermined rather than null and a reader who cannot tell the difference
draws the wrong conclusion from the panel.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.viz.figure2 import ALPHA, PairPoint, render


def pair(label: str, km: float, separation: float, p_holm: float, n: int = 30) -> PairPoint:
    rng = np.random.default_rng(len(label) + int(km))
    return PairPoint(
        label=label, km=km, separation=separation, p_holm=p_holm, n=n,
        null=list(rng.normal(0.0, 0.02, 999)),
    )


def test_significance_drives_the_fill_and_the_colour() -> None:
    significant = pair("NE–S", 955.0, 0.059, 0.0006)
    other = pair("C–N", 542.0, -0.005, 0.8294)
    assert significant.significant and not other.significant
    assert significant.colour != other.colour


def test_the_alpha_boundary_is_not_inclusive() -> None:
    """A pair at exactly 0.05 is not significant. Holm-adjusted values land on round
    numbers more often than raw ones do, so the boundary case is reachable."""
    assert not pair("X–Y", 500.0, 0.01, ALPHA).significant
    assert pair("X–Y", 500.0, 0.01, ALPHA - 1e-9).significant


def test_it_writes_a_figure(tmp_path) -> None:
    points = [
        pair("C–NE", 369.2, 0.0790, 0.0012, n=35),
        pair("N–NE", 431.8, 0.0803, 0.0006, n=37),
        pair("C–N", 541.7, -0.0052, 0.8294, n=16),
        pair("C–S", 587.2, 0.0019, 0.8294, n=21),
        pair("NE–S", 955.0, 0.0592, 0.0006, n=42),
        pair("N–S", 1038.1, 0.0117, 0.2538, n=23),
    ]
    out = render(points, tmp_path / "figure2.png", cohort_n=58, permutations=999)
    assert out.exists() and out.stat().st_size > 20_000


def test_a_negative_separation_is_drawn_not_clipped(tmp_path) -> None:
    """Central–North is −0.0052. A y-axis starting at zero would hide it, and a pair that
    sits fractionally on the wrong side of zero is exactly what the reader needs to see."""
    points = [pair("C–N", 541.7, -0.02, 0.83), pair("N–NE", 431.8, 0.08, 0.0006)]
    out = render(points, tmp_path / "neg.png", cohort_n=58, permutations=999)
    assert out.exists()


def test_the_null_interval_comes_from_the_null_not_the_estimate() -> None:
    """The band is the permutation null, centred on zero — not a confidence interval on
    the point. Drawn as an error bar it would assert the opposite: that the estimate is
    uncertain, rather than that the null is."""
    point = pair("NE–S", 955.0, 0.059, 0.0006)
    low, high = np.percentile(point.null, [2.5, 97.5])
    assert low < 0.0 < high
    assert not low <= point.separation <= high


def test_it_refuses_nothing_to_draw(tmp_path) -> None:
    with pytest.raises((ValueError, IndexError)):
        render([], tmp_path / "empty.png", cohort_n=0, permutations=999)
