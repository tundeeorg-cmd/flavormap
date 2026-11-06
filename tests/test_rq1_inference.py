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



# --- HD-44 (decided 2026-11-06): Holm and the bias-corrected interval ---------------

def test_holm_matches_the_textbook_step_down() -> None:
    from src.analyze.rq1_inference import holm
    # m = 4: sorted 0.01, 0.02, 0.03, 0.04 -> 0.04, 0.06, 0.06, 0.06 (monotone).
    assert holm([0.03, 0.01, 0.04, 0.02]) == pytest.approx([0.06, 0.04, 0.06, 0.06])
    assert holm([0.5, 0.9]) == pytest.approx([1.0, 1.0])          # capped at 1
    out = holm([0.01, float("nan"), 0.02])                        # NaN not in the family
    assert out[0] == pytest.approx(0.02) and math.isnan(out[1]) and out[2] == pytest.approx(0.02)


def test_bias_corrected_equals_percentile_when_unbiased() -> None:
    from src.analyze.rq1_inference import bias_corrected_interval
    boot = np.random.default_rng(1).normal(0.5, 0.05, 20_000)
    lo, hi = bias_corrected_interval(boot, float(np.median(boot)), 0.05)
    assert lo == pytest.approx(np.quantile(boot, 0.025), abs=2e-3)
    assert hi == pytest.approx(np.quantile(boot, 0.975), abs=2e-3)


def test_bias_corrected_interval_removes_an_upward_bootstrap_bias() -> None:
    """The failure HD-44 named: bootstrap distances run above the observed one. The
    correction recentres the interval near 2·obs − mean(boot), i.e. shifts it down by
    twice the bias, so a moderately biased bootstrap no longer leaves the observed value
    at its lower edge."""
    from src.analyze.rq1_inference import bias_corrected_interval
    boot = np.random.default_rng(2).normal(0.65, 0.05, 20_000)
    obs = 0.60                                                    # bias = 0.05 = 1 SE
    plain = (np.quantile(boot, 0.025), np.quantile(boot, 0.975))
    lo, hi = bias_corrected_interval(boot, obs, 0.05)
    assert (lo + hi) / 2 == pytest.approx(2 * obs - 0.65, abs=0.01)
    assert lo < plain[0] and hi < plain[1]
    assert lo < obs < hi


def test_run_rq1_writes_the_holm_adjusted_p(tmp_path: Path) -> None:
    """HD-44 (revised): register shuffle primary, region shuffle secondary, each Holm-
    adjusted as its own family within a scope."""
    from src.analyze.rq1_inference import holm
    processed = _processed(tmp_path)
    assert run_rq1.main(["--processed", str(processed), "--out-dir", str(tmp_path),
                         "--permutations", "49", "--bootstrap", "49"]) == 0
    out = next(tmp_path.glob("rq1_registers_*.csv"))
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert list(rows[0])[10:14] == ["p_register_shuffle", "p_register_holm",
                                   "p_unit_shuffle", "p_unit_holm"]
    family = [r for r in rows if r["role"] == "primary" and r["scope"] == "pooled"
              and r["p_register_shuffle"]]
    assert family
    for raw, adj in (("p_register_shuffle", "p_register_holm"),
                     ("p_unit_shuffle", "p_unit_holm")):
        expected = holm([float(r[raw]) for r in family])
        assert [float(r[adj]) for r in family] == pytest.approx(expected, abs=1e-4)
    meta = json.loads(out.with_suffix(".json").read_text(encoding="utf-8"))
    assert "bias-corrected" in meta["ci"]
    assert "Primary (reported): register-label shuffle" in meta["p_value"]


def test_run_rq1_flags_cells_below_minimum_n_without_dropping_them(tmp_path: Path) -> None:
    """HD-37 amendment (2026-11-06): fewer than COMMERCIAL_MIN_N commercial recipes →
    `below_min_n` is true; the row is still written."""
    from src.analyze.rq1_registers import COMMERCIAL_MIN_N
    processed = _processed(tmp_path)
    assert run_rq1.main(["--processed", str(processed), "--out-dir", str(tmp_path),
                         "--permutations", "9", "--bootstrap", "9"]) == 0
    out = next(tmp_path.glob("rq1_registers_*.csv"))
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert list(rows[0])[-2:] == ["below_min_n", "obs_outside_ci"]
    for r in rows:
        assert (r["below_min_n"] == "True") == (int(r["n_commercial_side"]) < COMMERCIAL_MIN_N)
    meta = json.loads(out.with_suffix(".json").read_text(encoding="utf-8"))
    assert meta["min_n_commercial"] == COMMERCIAL_MIN_N == 5


def test_interval_evidence_matches_the_reported_bias_corrected_interval(tmp_path: Path) -> None:
    """HD-44 open amendment: the evidence table draws the same bootstrap as `infer`, so its
    BC interval is the reported one; BCa with zero acceleration equals BC."""
    from src.analyze.rq1_inference import bca_interval, bias_corrected_interval, interval_evidence
    from src.analyze.rq1_registers import load_inputs
    data = load_inputs(_processed(tmp_path))
    reported = {r.unit: r for r in infer(data, "region", "tfidf", n_boot=199, n_perm=0, seed=7)}
    for e in interval_evidence(data, "region", "tfidf", ("official", "commercial"),
                               n_boot=199, seed=7):
        r = reported[str(e["unit"])]
        assert (e["bc_low"], e["bc_high"]) == pytest.approx((r.ci_low, r.ci_high))
        assert e["bc_point"] == pytest.approx(2 * r.distance - float(e["boot_mean"]))
    rng = np.random.default_rng(0)
    boot = rng.normal(0.5, 0.05, 999)
    symmetric = np.array([0.4, 0.5, 0.6])  # acceleration 0
    assert bca_interval(boot, 0.52, symmetric, 0.05) == pytest.approx(
        bias_corrected_interval(boot, 0.52, 0.05))


def test_run_rq1_flags_observed_outside_ci_and_excludes_listed_recipes(tmp_path: Path) -> None:
    """HD-44 amendment A: `obs_outside_ci` comes from the script. `--exclude-recipes`
    drops the listed recipes and suffixes the output."""
    import pandas as pd
    processed = _processed(tmp_path)
    assert run_rq1.main(["--processed", str(processed), "--out-dir", str(tmp_path),
                         "--permutations", "9", "--bootstrap", "49"]) == 0
    rows = list(csv.DictReader(next(tmp_path.glob("rq1_registers_*.csv")).open(encoding="utf-8")))
    for r in rows:
        if r["ci_low"] and r["ci_low"] != "nan":
            inside = float(r["ci_low"]) <= float(r["distance"]) <= float(r["ci_high"])
            assert (r["obs_outside_ci"] == "True") == (not inside)
    clean = pd.read_parquet(processed / "v_recipes_clean.parquet")
    drop = clean.loc[clean["register"] == "commercial", "recipe_id"].iloc[:1].tolist()
    ids = tmp_path / "drop_one.txt"
    ids.write_text("# test\n" + "\n".join(map(str, drop)) + "\n", encoding="utf-8")
    out_dir = tmp_path / "excl"
    assert run_rq1.main(["--processed", str(processed), "--out-dir", str(out_dir),
                         "--permutations", "9", "--bootstrap", "9",
                         "--exclude-recipes", str(ids)]) == 0
    out = next(out_dir.glob("rq1_registers_*_excl_drop_one.csv"))
    meta = json.loads(out.with_suffix(".json").read_text(encoding="utf-8"))
    assert meta["excluded_recipes"].startswith("1 from drop_one.txt")
    full = sum(int(r["n_commercial_side"]) for r in rows
               if r["role"] == "primary" and r["scope"] == "pooled")
    rows2 = list(csv.DictReader(out.open(encoding="utf-8")))
    assert sum(int(r["n_commercial_side"]) for r in rows2
               if r["role"] == "primary" and r["scope"] == "pooled") == full - 1


# ── T1.24: scripts/paper_audit.py (the RQ1 → numbers.md → draft chain) ─────────────

_NUMBERS_MD = """
| Number | Value |
|---|---|
| Official recipes loaded | `203` · `make status` · commit abc1234 · 2026-11-06 |
| Distance | Central `0.568` [0.453, 0.592] · `rq1.csv` · commit abc1234 · 2026-11-06 |
| Coverage | `81.4%` (11,462 of 14,084) · file · commit abc1234 · 2026-11-06 |
| Not yet | [TBD: scripts.run_rq1] 999 |
"""

_DRAFT = """---
title: x
---
# Introduction

We loaded 203 official recipes (Ahn et al. 2011) and mapped 81.4% of mentions (11,462).
The Central distance was 0.57 [0.453, 0.592]; see Figure 6 and RQ1 and HD-44.
An invented 0.731 and 999 appear here.

| Table cell 12345 | not counted |
|---|---|

*Figure 6: Region × ingredient heatmap, 60 ingredients.*

<!-- hidden 777 -->

## References

- Ahn, Y.-Y. et al. (2011). Flavor network.
- Burrows, J. (2002). Delta.
"""


def test_paper_audit_counts_words_references_and_traces_numbers(tmp_path: Path) -> None:
    from scripts import paper_audit as pa
    draft = pa.split(_DRAFT)
    assert draft.excluded_tables == 2
    words, thai = pa.count_words(draft.counted)
    assert thai == 0
    assert words == sum(len(ln.split()) for ln in [
        "Introduction",
        "We loaded 203 official recipes (Ahn et al. 2011) and mapped 81.4% of mentions (11,462).",
        "The Central distance was 0.57 [0.453, 0.592]; see Figure 6 and RQ1 and HD-44.",
        "An invented 0.731 and 999 appear here.",
        "Figure 6: Region × ingredient heatmap, 60 ingredients."]) - 1  # "×" is no word
    assert pa.count_references(draft.references) == 2
    audit = pa.audit_numbers(draft.counted, pa.known_values(_NUMBERS_MD))
    assert {t for _, t, _ in audit.untraced} == {"0.731", "999", "60"}
    assert {"203", "81.4%", "11,462", "0.57", "0.453", "0.592"} <= set(audit.traced)
    assert "2011" in audit.years and "6" in audit.labels and "44" in audit.labels
    assert "12345" not in audit.traced + audit.labels and "777" not in audit.traced


def test_paper_audit_thai_is_counted_in_words_not_characters() -> None:
    from scripts import paper_audit as pa
    words, thai = pa.count_words(["Q9 asks อะไรที่คนจังหวัดอื่นใส่ในจานนี้"])
    assert thai > 3 and words == thai + 2


def test_paper_audit_writes_only_the_two_submission_rows(tmp_path: Path) -> None:
    from scripts import paper_audit as pa
    numbers = tmp_path / "numbers.md"
    numbers.write_text(
        "| Word count, captions included (1,000–1,250) | [TBD: scripts.paper_audit] |\n"
        "| References verified (count) | [TBD: scripts.paper_audit] |\n"
        "| Other | [TBD: x] |\n", encoding="utf-8")
    draft = tmp_path / "draft.md"
    draft.write_text("Hello world.\n", encoding="utf-8")
    assert pa.main(["--draft", str(draft), "--numbers", str(numbers), "--write"]) == 0
    lines = numbers.read_text(encoding="utf-8").splitlines()
    assert "`2`" in lines[0] and "draft.md" in lines[0] and "[TBD" not in lines[0]
    assert "`0` counted" in lines[1] and lines[2] == "| Other | [TBD: x] |"


def test_paper_audit_leaves_placeholders_out_and_reports_file_lines() -> None:
    from scripts import paper_audit as pa
    text = ("<!--\ncomment 999\n-->\n## 5. Results\n\n"
            "[ORIGIN STORY — about 80 words, written later.]\n"
            "We kept 203 recipes; see interview question 9. [TBD: a source.]\n\n"
            "## References\n\n- Real, A. (2011). One.\n\n[TBD: two more sources.]\n")
    draft = pa.split(text)
    assert [ln for ln, _ in draft.placeholders] == [6, 7, 13]
    assert pa.count_references(draft.references) == 1
    words, _ = pa.count_words(draft.counted)
    assert words == len("5. Results We kept 203 recipes; see interview question 9.".split())
    audit = pa.audit_numbers(draft.counted, set(), draft.counted_at)
    assert [(line, tok) for line, tok, _ in audit.untraced] == [(7, "203")]
    assert "5" in audit.labels and "9" in audit.labels
