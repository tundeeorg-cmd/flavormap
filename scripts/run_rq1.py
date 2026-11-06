"""RQ1 end to end for DH2027: official↔commercial distance per region, with uncertainty.

    uv run python -m scripts.run_rq1 [--unit region] [--permutations 9999] [--bootstrap 9999]
    (or: make rq1, which re-exports the Parquet first and draws Figure 6 after)

Runs every table the DH2027 outline's Section 4–5 needs, from the Parquet `make parquet`
writes, as soon as ``recipe_ingredients`` has rows (i.e. after `make lexicon`):

- **Unit:** region (HD-37 C, ``rq1_registers.ANALYSIS_UNIT``); ``--unit province`` shows
  the province rows where they exist.
- **Weighting:** TF-IDF primary, prevalence as the sensitivity check (HD-38).
- **Uncertainty:** percentile bootstrap CI and two permutation p-values per distance
  (`src.analyze.rq1_inference`; which null is reported is HD-44, open).
- **Per source:** pooled commercial, then each commercial source alone (T1.19; HD-42 A).
- **Counts:** the recipe count of each side beside every distance.

Writes ``data/coverage/rq1_registers_YYYYMMDD.csv`` (one row per weighting × scope ×
unit) and a ``.json`` beside it with the run's settings, the lexicon size and the git
commit, so every number in ``paper/dh2027/numbers.md`` traces to a file and a commit.
Both are counts and distances only, no ingredient strings; they are gitignored like the
rest of ``data/coverage/`` unless the researcher decides otherwise.
"""

from __future__ import annotations

import argparse
import csv
import datetime
import json
import math
import subprocess
from pathlib import Path

import pandas as pd

from src.analyze.rq1_inference import infer
from src.analyze.rq1_registers import (
    ANALYSIS_UNIT,
    PRIMARY_WEIGHTING,
    PROCESSED,
    SENSITIVITY_WEIGHTING,
    UNITS,
    InputError,
    load_inputs,
    split_by_source,
)
from src.config import DATA_DIR, RANDOM_SEED

OUT_DIR = DATA_DIR / "coverage"
COLUMNS = ("weighting", "role", "scope", "unit_type", "unit", "n_official",
           "n_commercial_side", "distance", "ci_low", "ci_high", "p_unit_shuffle",
           "p_register_shuffle")


def run(data: pd.DataFrame, unit: str, n_perm: int, n_boot: int, seed: int) -> list[dict]:
    rows: list[dict] = []
    sources = (sorted(data.loc[data["register"] == "commercial", "source_id"].dropna()
                      .astype(str).unique()) if "source_id" in data.columns else [])
    split = split_by_source(data) if sources else None
    for role, weighting in (("primary", PRIMARY_WEIGHTING),
                            ("sensitivity", SENSITIVITY_WEIGHTING)):
        scopes: list[tuple[str, pd.DataFrame, tuple[str, str]]] = [
            ("pooled", data, ("official", "commercial"))]
        if split is not None:
            scopes += [(s, split, ("official", f"commercial:{s}")) for s in sources]
        for scope, frame, pair in scopes:
            for r in infer(frame, unit, weighting, pair,  # type: ignore[arg-type]
                           n_boot=n_boot, n_perm=n_perm, seed=seed):
                rows.append({
                    "weighting": weighting, "role": role, "scope": scope,
                    "unit_type": unit, "unit": r.unit, "n_official": r.n_a,
                    "n_commercial_side": r.n_b, "distance": r.distance,
                    "ci_low": r.ci_low, "ci_high": r.ci_high,
                    "p_unit_shuffle": r.p_unit, "p_register_shuffle": r.p_register,
                })
    return rows


def _fmt(v: object) -> str:
    if isinstance(v, float):
        return "" if math.isnan(v) else f"{v:.4f}"
    return str(v)


def write(rows: list[dict], meta: dict, out_dir: Path, day: datetime.date) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"rq1_registers_{day:%Y%m%d}.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        w = csv.writer(handle)
        w.writerow(COLUMNS)
        for r in rows:
            w.writerow([_fmt(r[c]) for c in COLUMNS])
    path.with_suffix(".json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return path


def _commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def print_table(rows: list[dict]) -> None:
    current = None
    for r in rows:
        head = (r["role"], r["weighting"], r["scope"])
        if head != current:
            current = head
            print(f"\n{r['role']} ({r['weighting']}), commercial = {r['scope']}")
            print(f"  {'unit':<14}{'n_off':>6}{'n_com':>6}  {'distance':>8}  "
                  f"{'95% CI':<17}{'p_unit':>8}{'p_reg':>8}")
        ci = (f"[{r['ci_low']:.3f}, {r['ci_high']:.3f}]"
              if not math.isnan(r["ci_low"]) else "")
        print(f"  {r['unit']:<14}{r['n_official']:>6}{r['n_commercial_side']:>6}  "
              f"{_fmt(r['distance']):>8}  {ci:<17}{_fmt(r['p_unit_shuffle']):>8}"
              f"{_fmt(r['p_register_shuffle']):>8}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--unit", choices=UNITS, default=ANALYSIS_UNIT)
    ap.add_argument("--permutations", type=int, default=9_999)
    ap.add_argument("--bootstrap", type=int, default=9_999)
    ap.add_argument("--processed", type=Path, default=PROCESSED)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = ap.parse_args(argv)
    try:
        data = load_inputs(args.processed)
        if data.empty:
            raise InputError("no recipe in v_recipes_clean has mapped ingredients yet: "
                             "author the lexicon, then `make lexicon` and `make parquet`")
        rows = run(data, args.unit, args.permutations, args.bootstrap, RANDOM_SEED)
    except InputError as e:
        print(f"RQ1 cannot run: {e}")
        return 1
    entries = pd.read_parquet(args.processed / "canonical_ingredients.parquet") \
        if (args.processed / "canonical_ingredients.parquet").exists() else pd.DataFrame()
    day = datetime.date.today()
    meta = {
        "date": day.isoformat(), "git_commit": _commit(), "unit": args.unit,
        "primary_weighting": PRIMARY_WEIGHTING,
        "sensitivity_weighting": SENSITIVITY_WEIGHTING,
        "permutations": args.permutations, "bootstrap": args.bootstrap,
        "seed": RANDOM_SEED, "ci": "percentile, 95%",
        "p_value": "one-sided, (1 + #null >= obs) / (1 + n); no adjustment (HD-44 open)",
        "lexicon_entries": len(entries),
        "recipes": int(data["recipe_id"].nunique()),
        "recipes_by_register": {k: int(v) for k, v in
                                data.groupby("register")["recipe_id"].nunique().items()},
    }
    path = write(rows, meta, args.out_dir, day)
    print_table(rows)
    print(f"\nwrote {path} and {path.with_suffix('.json').name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
