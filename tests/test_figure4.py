"""Figure 4's renderer, exercised on synthetic input.

Synthetic data here is legitimate and is not a measurement: it tests the plotting
machinery — prevalence arithmetic, point encoding, self-containment — without touching
the corpus. No synthetic row ever reaches a table or a published figure.
"""

from __future__ import annotations

import re

from src.viz.figure4 import Panel, ProvincePoint, render


def _point(km: float, n: int, hits: int, region: str = "Central") -> ProvincePoint:
    return ProvincePoint(
        province_code="TH-XX",
        name_en="Test",
        region=region,
        km_from_bangkok=km,
        n_recipes=n,
        n_with_ingredient=hits,
    )


def test_prevalence_is_a_share_not_a_count() -> None:
    assert _point(0, 3, 1).prevalence == 1 / 3
    assert _point(0, 2, 2).prevalence == 1.0
    assert _point(0, 0, 0).prevalence == 0.0      # no division by zero


def test_output_is_self_contained() -> None:
    """No CDN, no script tag, no external fetch — it must open from disk."""
    doc = render([Panel("x", "%x%", [_point(100, 3, 1)])], subtitle="s", caveats=["c"])
    assert "<script" not in doc
    assert "http://" not in doc.replace("http://www.w3.org/2000/svg", "")
    assert "cdn" not in doc.lower()


def test_point_area_encodes_recipe_count() -> None:
    """A province resting on one recipe must not read like one resting on many."""
    doc = render(
        [Panel("x", "%x%", [_point(100, 1, 1), _point(200, 9, 9)])],
        subtitle="s",
        caveats=[],
    )
    radii = sorted(float(r) for r in re.findall(r'<circle[^>]*r="([\d.]+)"', doc))
    assert len(radii) == 2
    # Area ∝ n, so radius ∝ √n: nine recipes give three times the radius increment.
    assert radii[1] > radii[0]


def test_every_panel_declares_its_matching_pattern() -> None:
    """HD-6 is open, so a reader must be able to see exactly what was counted."""
    doc = render(
        [Panel("pla ra", "%ปลาร้า%", [_point(500, 3, 2)], note="fermented fish")],
        subtitle="s",
        caveats=["provisional"],
    )
    assert "%ปลาร้า%" in doc
    assert "HD-6" in doc
    assert "fermented fish" in doc


def test_caveats_are_rendered_not_dropped() -> None:
    doc = render(
        [Panel("x", "%x%", [_point(0, 1, 0)])],
        subtitle="s",
        caveats=["n is 3 per province"],
    )
    assert "n is 3 per province" in doc


def test_control_panel_is_labelled() -> None:
    doc = render(
        [Panel("salt", "%เกลือ%", [_point(0, 3, 3)], is_control=True)],
        subtitle="s",
        caveats=[],
    )
    assert "(control)" in doc
