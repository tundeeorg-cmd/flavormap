"""src/analyze/rq1_inference.py, scripts/run_rq1.py and the region-level Figure 6, on
synthetic fixtures only. Canonical ids (ing_*) and recipes are invented; no real
distance is computed here."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import make_figure6, run_rq1
from src.analyze.rq1_inference import design, infer, observed, p_value
from src.analyze.rq1_registers import assemble, register_distances, split_by_source

PROVINCES = pd.DataFrame({
    "province_code": ["TH-30", "TH-31", "TH-50", "TH-90"],
    "name_en": ["Nakhon Ratchasima", "Buri Ram", "Chiang Mai", "Songkhla"],
    "region4": ["Northeast", "Northeast", "North", "South"],
})
COMMON = ["ing_salt", "ing_fishsauce", "ing_garlic"]


def _fixture(seed: int = 0, gap: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Official recipes (3 per province) and commercial recipes from two sources, mostly
    labelled by region. With `gap`, the registers draw from different ingredient pools."""
    rng = np.random.default_rng(seed)
    pool_off = COMMON + [f"ing_off_{i}" for i in range(8)]
    pool_com = COMMON + ([f"ing_com_{i}" for i in range(8)] if gap
                         else [f"ing_off_{i}" for i in range(8)])
    clean, ings, rid = [], [], 0
    for prov in PROVINCES["province_code"]:
        for _ in range(3):
            rid += 1
            clean.append((rid, "official", "dcp_food", prov, None))
            ings += [(rid, k) for k in rng.choice(pool_off, 5, replace=False)]
    for region, n in (("Northeast", 14), ("North", 9), ("South", 11), ("Central", 1)):
        for j in range(n):
            rid += 1
            source = "kapook_cooking" if j % 3 else "mthai_food"
            clean.append((rid, "commercial", source, None, region))
            ings += [(rid, k) for k in rng.choice(pool_com, 5, replace=False)]
    clean_df = pd.DataFrame(clean, columns=["recipe_id", "register", "source_id",
                                            "province_code", "region"])
    ing_df = pd.DataFrame(ings, columns=["recipe_id", "canonical_id"])
    return clean_df, ing_df


def _data(**kw: object) -> pd.DataFrame:
    clean, ings = _fixture(**kw)  # type: ignore[arg-type]
    return assemble(clean, ings, PROVINCES)


@pytest.mark.parametrize("weighting", ["tfidf", "prevalence"])
def test_observed_distances_equal_rq1_registers(weighting: str) -> None:
    data = _data()
    ours = observed(design(data, "region"), weighting, ("official", "commercial"))
    theirs = register_distances(data, "region", weighting)  # type: ignore[arg-type]
    for _, row in theirs.iterrows():
        a, b = ours[row["region"]], row["distance"]
        assert (math.isnan(a) and math.isnan(b)) or a == pytest.approx(b, abs=1e-9)
    split = split_by_source(data)
    pair = ("official", "commercial:mthai_food")
    ours = observed(design(split, "region"), weighting, pair)
    theirs = register_distances(split, "region", weighting, pair=pair)  # type: ignore[arg-type]
    for _, row in theirs.iterrows():
        a, b = ours[row["region"]], row["distance"]
        assert (math.isnan(a) and math.isnan(b)) or a == pytest.approx(b, abs=1e-9)


def test_counts_ci_and_p_values_sit_beside_every_distance() -> None:
    rows = infer(_data(), "region", "tfidf", n_boot=200, n_perm=199, seed=1)
    by_unit = {r.unit: r for r in rows}
    assert set(by_unit) == {"Northeast", "North", "South", "Central"}
    ne = by_unit["Northeast"]
    assert (ne.n_a, ne.n_b) == (6, 14)
    assert ne.ci_low <= ne.distance <= ne.ci_high
    assert 0 < ne.p_unit <= 1 and 0 < ne.p_register <= 1
    central = by_unit["Central"]               # no official recipes there
    assert central.n_a == 0 and math.isnan(central.distance) and math.isnan(central.p_unit)


def test_register_shuffle_separates_different_registers_from_the_same_one() -> None:
    different = {r.unit: r for r in infer(_data(gap=True), "region", "tfidf",
                                          n_boot=0, n_perm=499, seed=2)}
    same = {r.unit: r for r in infer(_data(gap=False), "region", "tfidf",
                                     n_boot=0, n_perm=499, seed=2)}
    assert different["Northeast"].p_register < 0.01
    assert same["Northeast"].p_register > 0.05


def test_results_are_reproducible_from_the_seed() -> None:
    a = infer(_data(), "region", "prevalence", n_boot=100, n_perm=99, seed=7)
    b = infer(_data(), "region", "prevalence", n_boot=100, n_perm=99, seed=7)
    assert a == b


def test_p_value_is_never_zero() -> None:
    assert p_value(np.array([0.1, 0.2, 0.3]), 0.9) == pytest.approx(1 / 4)
    assert p_value(np.array([0.5, 0.6]), 0.5) == pytest.approx(1.0)


# --- end to end on Parquet fixtures -------------------------------------------------

def _processed(tmp: Path, with_ingredients: bool = True) -> Path:
    clean, ings = _fixture()
    clean = clean.assign(source_type="web", confidence="high", tier=1, n_ingredients=5,
                         published_at=None)
    if not with_ingredients:
        ings = ings.iloc[0:0]
        clean = clean.iloc[0:0]
    clean.to_parquet(tmp / "v_recipes_clean.parquet")
    ings.to_parquet(tmp / "recipe_ingredients.parquet")
    PROVINCES.to_parquet(tmp / "provinces.parquet")
    ids = sorted(ings["canonical_id"].unique()) if len(ings) else []
    # Provenance: the commercial-only pool is agent-drafted, one entry reviewed.
    drafted = ["claude" if i.startswith("ing_com_") else "bo" for i in ids]
    reviewed = ["2026-11-07" if i == "ing_com_0" else None for i in ids]
    pd.DataFrame({"canonical_id": ids, "name_th": ids, "name_en": ids,
                  "drafted_by": drafted, "reviewed_by_bo": reviewed}).to_parquet(
        tmp / "canonical_ingredients.parquet")
    return tmp


def test_run_rq1_end_to_end(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    processed = _processed(tmp_path)
    code = run_rq1.main(["--processed", str(processed), "--out-dir", str(tmp_path),
                         "--permutations", "49", "--bootstrap", "49"])
    assert code == 0
    out = next(tmp_path.glob("rq1_registers_*.csv"))
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    combos = {(r["role"], r["weighting"], r["scope"]) for r in rows}
    assert combos == {(role, w, s) for role, w in (("primary", "tfidf"),
                                                   ("sensitivity", "prevalence"))
                      for s in ("pooled", "kapook_cooking", "mthai_food")}
    assert {r["unit_type"] for r in rows} == {"region"}
    meta = json.loads(out.with_suffix(".json").read_text(encoding="utf-8"))
    assert meta["permutations"] == 49 and meta["primary_weighting"] == "tfidf"
    assert "commercial = pooled" in capsys.readouterr().out


def test_run_rq1_says_why_when_there_is_no_lexicon(tmp_path: Path,
                                                   capsys: pytest.CaptureFixture[str]) -> None:
    processed = _processed(tmp_path, with_ingredients=False)
    assert run_rq1.main(["--processed", str(processed), "--out-dir", str(tmp_path)]) == 1
    assert "cannot run" in capsys.readouterr().out


@pytest.mark.parametrize("unit", ["region", "province"])
def test_figure6_end_to_end(tmp_path: Path, unit: str) -> None:
    processed = _processed(tmp_path)
    out = tmp_path / f"fig6_{unit}.png"
    assert make_figure6.main(["--processed", str(processed), "--out", str(out),
                              "--unit", unit]) == 0
    assert out.stat().st_size > 0



# --- reviewed-only (provenance, 2026-11-06) -----------------------------------------

def test_trusted_ids_are_bo_drafted_or_reviewed(tmp_path: Path) -> None:
    from src.analyze.rq1_registers import trusted_ids
    ids = trusted_ids(_processed(tmp_path))
    assert "ing_com_0" in ids and "ing_com_1" not in ids and "ing_salt" in ids


def test_restrict_to_trusted_reapplies_the_3_to_25_bound() -> None:
    from src.analyze.rq1_registers import restrict_to_trusted
    data = pd.DataFrame({"recipe_id": [1, 1, 1, 2, 2, 2, 2],
                         "canonical_id": ["a", "b", "x", "a", "b", "c", "x"]})
    kept = restrict_to_trusted(data, {"a", "b", "c"})
    assert set(kept["recipe_id"]) == {2}          # recipe 1 drops to 2 trusted entries
    assert "x" not in set(kept["canonical_id"])


def test_run_rq1_reviewed_only_writes_its_own_file(tmp_path: Path) -> None:
    processed = _processed(tmp_path)
    args = ["--processed", str(processed), "--out-dir", str(tmp_path),
            "--permutations", "19", "--bootstrap", "19"]
    assert run_rq1.main(args) == 0
    assert run_rq1.main([*args, "--reviewed-only"]) == 0
    full = next(tmp_path.glob("rq1_registers_*[0-9].json"))
    rev = next(tmp_path.glob("rq1_registers_*_reviewed.json"))
    m_full = json.loads(full.read_text(encoding="utf-8"))
    m_rev = json.loads(rev.read_text(encoding="utf-8"))
    assert m_full["lexicon"] == "all entries" and m_rev["lexicon"] == "reviewed-only"
    assert m_rev["lexicon_entries_used"] < m_full["lexicon_entries_used"]
    assert m_rev["recipes"] < m_full["recipes"]


def test_figure6_reviewed_only(tmp_path: Path) -> None:
    processed = _processed(tmp_path)
    out = tmp_path / "fig6_reviewed.png"
    assert make_figure6.main(["--processed", str(processed), "--out", str(out),
                              "--reviewed-only"]) == 0
    assert out.stat().st_size > 0
