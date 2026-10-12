"""src/analyze/rq1_registers.py (T1.19), on synthetic recipes. Canonical ids here are
invented placeholders (ing_a, ing_b, …), never lexicon entries."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from src.analyze.rq1_registers import (
    InputError,
    assemble,
    cosine_distance,
    per_source_distances,
    profiles,
    register_distances,
    split_by_source,
)

PROVINCES = pd.DataFrame({
    "province_code": ["TH-30", "TH-31", "TH-50"],
    "region4": ["Northeast", "Northeast", "North"],
})


def _data(recipes: list[tuple[int, str, str | None, str | None, list[str]]]) -> pd.DataFrame:
    clean = pd.DataFrame(
        [(rid, reg, prov, region) for rid, reg, prov, region, _ in recipes],
        columns=["recipe_id", "register", "province_code", "region"],
    )
    ingredients = pd.DataFrame(
        [(rid, ing) for rid, *_, ings in recipes for ing in ings],
        columns=["recipe_id", "canonical_id"],
    )
    return assemble(clean, ingredients, PROVINCES)


def test_identical_profiles_are_distance_zero_and_disjoint_ones_are_one() -> None:
    assert cosine_distance({"a": 1.0, "b": 0.5}, {"a": 2.0, "b": 1.0}) == pytest.approx(0.0)
    assert cosine_distance({"a": 1.0}, {"b": 1.0}) == pytest.approx(1.0)


def test_the_recipe_counts_sit_beside_every_distance() -> None:
    data = _data([
        (1, "official", "TH-30", None, ["ing_a", "ing_b"]),
        (2, "commercial", "TH-30", None, ["ing_a", "ing_b"]),
        (3, "commercial", "TH-30", None, ["ing_a", "ing_c"]),
    ])
    table = register_distances(data, "province", "prevalence")
    row = table.set_index("province").loc["TH-30"]
    assert (row["n_official"], row["n_commercial"]) == (1, 2)
    assert 0 < row["distance"] < 1


def test_a_unit_one_register_lacks_is_listed_with_zero_and_no_distance() -> None:
    data = _data([
        (1, "official", "TH-30", None, ["ing_a"]),
        (2, "official", "TH-50", None, ["ing_a"]),
        (3, "commercial", "TH-30", None, ["ing_a"]),
    ])
    row = register_distances(data, "province", "prevalence").set_index("province").loc["TH-50"]
    assert (row["n_official"], row["n_commercial"]) == (1, 0)
    assert math.isnan(row["distance"])


def test_prevalence_is_the_share_of_recipes_containing_each_ingredient() -> None:
    data = _data([
        (1, "official", "TH-30", None, ["ing_a", "ing_b"]),
        (2, "official", "TH-30", None, ["ing_a"]),
    ])
    (p,) = profiles(data, "province", "prevalence")
    assert p.vector == {"ing_a": 1.0, "ing_b": 0.5}


def test_tfidf_down_weights_an_ingredient_every_vector_shares() -> None:
    data = _data([
        (1, "official", "TH-30", None, ["ing_common", "ing_rare"]),
        (2, "commercial", "TH-30", None, ["ing_common"]),
    ])
    official = next(p for p in profiles(data, "province", "tfidf") if p.register == "official")
    assert official.vector["ing_rare"] > official.vector["ing_common"]


def test_region_comes_from_the_province_or_else_the_attribution() -> None:
    data = _data([
        (1, "official", "TH-30", None, ["ing_a"]),
        (2, "official", "TH-31", None, ["ing_a"]),
        (3, "commercial", None, "Northeast", ["ing_a"]),
    ])
    row = register_distances(data, "region", "prevalence").set_index("region").loc["Northeast"]
    assert (row["n_official"], row["n_commercial"]) == (2, 1)
    assert row["distance"] == pytest.approx(0.0)


def test_a_region_that_contradicts_its_province_is_an_error() -> None:
    with pytest.raises(InputError, match="disagrees"):
        _data([(1, "official", "TH-30", "North", ["ing_a"])])


def test_unmapped_ingredients_are_not_counted() -> None:
    clean = pd.DataFrame([(1, "official", "TH-30", None)],
                         columns=["recipe_id", "register", "province_code", "region"])
    ingredients = pd.DataFrame({"recipe_id": [1, 1], "canonical_id": ["ing_a", None]})
    (p,) = profiles(assemble(clean, ingredients, PROVINCES), "province", "prevalence")
    assert p.vector == {"ing_a": 1.0}


@pytest.mark.parametrize("unit, weighting", [("district", "prevalence"), ("province", "raw")])
def test_the_two_open_choices_have_no_fallback(unit: str, weighting: str) -> None:
    data = _data([(1, "official", "TH-30", None, ["ing_a"])])
    with pytest.raises(InputError):
        profiles(data, unit, weighting)  # type: ignore[arg-type]


def _sourced(recipes: list[tuple[int, str, str, str | None, list[str]]]) -> pd.DataFrame:
    """Like _data, with a source_id per recipe: (id, register, source, province, ings)."""
    clean = pd.DataFrame(
        [(rid, reg, prov, None, src) for rid, reg, src, prov, _ in recipes],
        columns=["recipe_id", "register", "province_code", "region", "source_id"],
    )
    ingredients = pd.DataFrame(
        [(rid, ing) for rid, *_, ings in recipes for ing in ings],
        columns=["recipe_id", "canonical_id"],
    )
    return assemble(clean, ingredients, PROVINCES)


def test_the_robustness_table_has_pooled_then_one_block_per_source() -> None:
    data = _sourced([
        (1, "official", "dcp_food", "TH-30", ["ing_a", "ing_b"]),
        (2, "commercial", "kapook_cooking", "TH-30", ["ing_a", "ing_b"]),
        (3, "commercial", "mthai_food", "TH-30", ["ing_c"]),
    ])
    table = per_source_distances(data, "province", "prevalence")
    assert table["commercial_source"].tolist() == ["pooled", "kapook_cooking", "mthai_food"]
    by = table.set_index("commercial_source")
    assert by.loc["pooled", "n_commercial_side"] == 2
    assert by.loc["kapook_cooking", "distance"] == pytest.approx(0.0)
    assert by.loc["mthai_food", "distance"] == pytest.approx(1.0)
    assert (table["n_official"] == 1).all()


def test_splitting_by_source_leaves_other_registers_alone() -> None:
    data = _sourced([
        (1, "official", "dcp_food", "TH-30", ["ing_a"]),
        (2, "commercial", "kapook_cooking", "TH-30", ["ing_a"]),
    ])
    assert sorted(split_by_source(data)["register"].unique()) == [
        "commercial:kapook_cooking", "official"]


def test_splitting_without_a_source_column_is_an_error() -> None:
    data = _data([(1, "commercial", "TH-30", None, ["ing_a"])])
    with pytest.raises(InputError, match="source_id"):
        split_by_source(data)
