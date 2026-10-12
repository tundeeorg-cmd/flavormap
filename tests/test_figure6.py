"""Figure 6 (T1.20): selection, seriation and layout, on synthetic profiles. Ingredient
ids are invented placeholders, never lexicon entries."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from scripts.make_figure6 import commercial_filter
from src.analyze.rq1_registers import Profile
from src.viz.figure6 import build, render, seriate


def _p(register: str, unit: str, vector: dict[str, float], n: int = 5) -> Profile:
    return Profile(register, unit, n, vector)


def test_seriation_keeps_similar_rows_together_where_alphabetical_would_not() -> None:
    # Rows 0 and 2 are alike, as are 1 and 3: alphabetical order (0,1,2,3) interleaves them.
    m = np.array([[1, 0, 0], [0, 1, 1], [0.9, 0.1, 0], [0, 1, 0.9]])
    order = seriate(m)
    pos = {row: i for i, row in enumerate(order)}
    assert abs(pos[0] - pos[2]) == 1 and abs(pos[1] - pos[3]) == 1


def test_all_zero_rows_go_last() -> None:
    m = np.array([[0, 0], [1, 0], [0, 0], [0.9, 0.1], [0.1, 1]])
    assert seriate(m)[-2:] == [0, 2]


def test_the_top_n_ingredients_by_variance_are_kept() -> None:
    heat = build([
        _p("official", "TH-30", {"ing_flat": 0.5, "ing_varies": 1.0}),
        _p("official", "TH-50", {"ing_flat": 0.5, "ing_varies": 0.0}),
    ], top_n=1)
    assert heat.ingredients == ["ing_varies"]


def test_a_register_without_recipes_in_a_province_is_no_data_not_zero() -> None:
    heat = build([
        _p("official", "TH-30", {"ing_a": 1.0, "ing_b": 0.2}),
        _p("official", "TH-50", {"ing_a": 0.1, "ing_b": 1.0}),
        _p("commercial", "TH-30", {"ing_a": 0.5}),
    ])
    row = heat.provinces.index("TH-50")
    assert np.isnan(heat.values["commercial"][row]).all()
    assert not np.isnan(heat.values["official"][row]).any()
    th30 = heat.provinces.index("TH-30")
    col_b = heat.ingredients.index("ing_b")
    assert heat.values["commercial"][th30, col_b] == 0.0, "absent ingredient is zero, not NaN"


def test_every_panel_shares_one_province_and_one_ingredient_order() -> None:
    heat = build([
        _p("official", "TH-30", {"ing_a": 1.0}),
        _p("domestic", "TH-30", {"ing_b": 1.0}),
    ])
    assert {v.shape for v in heat.values.values()} == {(1, 2)}


def test_the_threshold_filters_the_commercial_register_only() -> None:
    data = pd.DataFrame({
        "recipe_id": [1, 2, 3, 4],
        "register": ["commercial", "commercial", "commercial", "official"],
        "province_code": ["TH-30", "TH-30", "TH-50", "TH-50"],
        "canonical_id": ["ing_a"] * 4,
    })
    kept = commercial_filter(data, threshold=2)
    assert sorted(kept["recipe_id"]) == [1, 2, 4]


def test_render_writes_the_figure_and_an_honest_empty_state(tmp_path: Path) -> None:
    heat = build([
        _p("official", "TH-30", {"ing_a": 1.0, "ing_b": 0.3}),
        _p("official", "TH-50", {"ing_a": 0.2, "ing_b": 1.0}),
        _p("commercial", "TH-30", {"ing_a": 0.7}),
    ])
    full = render(heat, tmp_path / "f.png", province_label={}, ingredient_label={},
                  caption="synthetic")
    empty = render(build([]), tmp_path / "e.png", province_label={}, ingredient_label={},
                   caption="synthetic")
    assert full.stat().st_size > 0 and empty.stat().st_size > 0
