"""RQ1 end to end for DH2027: official↔commercial distance per region, with uncertainty.

    uv run python -m scripts.run_rq1 [--unit region] [--permutations 9999] [--bootstrap 9999]
                                     [--reviewed-only]
    (or: make rq1, which re-exports the Parquet first and draws Figure 6 after)

Runs every table the DH2027 outline's Section 4–5 needs, from the Parquet `make parquet`
writes, as soon as ``recipe_ingredients`` has rows (i.e. after `make lexicon`):

- **Unit:** region (HD-37 C, ``rq1_registers.ANALYSIS_UNIT``); ``--unit province`` shows
  the province rows where they exist.
- **Weighting:** TF-IDF primary, prevalence as the sensitivity check (HD-38).
- **Uncertainty (HD-44, revised 2026-11-06):** bias-corrected percentile bootstrap CI
  (9,999 resamples, 95%). **Primary:** the register-label shuffle, ``p_register_shuffle``
  and its Holm-adjusted value across the regions of each scope, ``p_register_holm`` (the
  reported p). **Secondary:** the region-label shuffle, ``p_unit_shuffle`` /
  ``p_unit_holm``. Each null is its own Holm family.
- **Per source:** pooled commercial, then each commercial source alone (T1.19; HD-42 A).
- **Counts:** the recipe count of each side beside every distance.
- **Lexicon:** all entries by default. ``--reviewed-only`` uses only entries the
  researcher drafted or reviewed (`rq1_registers.trusted_ids`), re-applies the 3–25
  ingredient bound, and writes ``rq1_registers_YYYYMMDD_reviewed.csv`` beside the
  all-entries file, so both can be reported.

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

from src.analyze.rq1_inference import holm, infer, interval_evidence
from src.analyze.rq1_registers import (
    ANALYSIS_UNIT,
    COMMERCIAL_MIN_N,
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
           "n_commercial_side", "distance", "ci_low", "ci_high", "p_register_shuffle",
           "p_register_holm", "p_unit_shuffle", "p_unit_holm", "below_min_n",
           "obs_outside_ci")


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
            results = infer(frame, unit, weighting, pair,  # type: ignore[arg-type]
                            n_boot=n_boot, n_perm=n_perm, seed=seed)
            # HD-44: Holm across the units of this scope, one family per null.
            adj_reg = holm([r.p_register for r in results])
            adj_unit = holm([r.p_unit for r in results])
            for r, p_reg_holm, p_holm in zip(results, adj_reg, adj_unit, strict=True):
                rows.append({
                    "weighting": weighting, "role": role, "scope": scope,
                    "unit_type": unit, "unit": r.unit, "n_official": r.n_a,
                    "n_commercial_side": r.n_b, "distance": r.distance,
                    "ci_low": r.ci_low, "ci_high": r.ci_high,
                    "p_register_shuffle": r.p_register, "p_register_holm": p_reg_holm,
                    "p_unit_shuffle": r.p_unit, "p_unit_holm": p_holm,
                    # HD-37 amendment (2026-11-06): flagged, never dropped.
                    "below_min_n": r.n_b < COMMERCIAL_MIN_N,
                    # HD-44 amendment (A): the footnote's cells, from the script.
                    "obs_outside_ci": (not math.isnan(r.ci_low)
                                       and not r.ci_low <= r.distance <= r.ci_high),
                })
    return rows


def _fmt(v: object) -> str:
    if isinstance(v, float):
        return "" if math.isnan(v) else f"{v:.4f}"
    return str(v)


def write(rows: list[dict], meta: dict, out_dir: Path, day: datetime.date,
          suffix: str = "") -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"rq1_registers_{day:%Y%m%d}{suffix}.csv"
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
                  f"{'95% CI (BC)':<17}{'p_reg':>8}{'p_reg_H':>8}{'p_unit_H':>9}  note")
        ci = (f"[{r['ci_low']:.3f}, {r['ci_high']:.3f}]"
              if not math.isnan(r["ci_low"]) else "")
        print(f"  {r['unit']:<14}{r['n_official']:>6}{r['n_commercial_side']:>6}  "
              f"{_fmt(r['distance']):>8}  {ci:<17}{_fmt(r['p_register_shuffle']):>8}"
              f"{_fmt(r['p_register_holm']):>8}{_fmt(r['p_unit_holm']):>9}"
              f"{'  below minimum n' if r['below_min_n'] else ''}"
              f"{'  observed outside CI' if r['obs_outside_ci'] else ''}")


INTERVAL_COLUMNS = ("scope", "unit", "n_official", "n_commercial_side", "distance",
                    "boot_mean", "bias", "boot_se", "share_below_obs", "bc_point",
                    "pct_low", "pct_high", "bc_low", "bc_high", "bca_low", "bca_high",
                    "basic_low", "basic_high", "obs_outside_bc")


def _interval_evidence(data: pd.DataFrame, args: argparse.Namespace) -> int:
    """`--interval-evidence`: one row per scope × unit, primary weighting only."""
    sources = sorted(data.loc[data["register"] == "commercial", "source_id"].dropna()
                     .astype(str).unique())
    split = split_by_source(data)
    scopes = [("pooled", data, ("official", "commercial"))]
    scopes += [(s, split, ("official", f"commercial:{s}")) for s in sources]
    rows = []
    for scope, frame, pair in scopes:
        counts = {r.unit: (r.n_a, r.n_b) for r in infer(
            frame, args.unit, PRIMARY_WEIGHTING, pair, n_boot=0, n_perm=0, seed=RANDOM_SEED)}
        for e in interval_evidence(frame, args.unit, PRIMARY_WEIGHTING, pair,
                                   n_boot=args.bootstrap, seed=RANDOM_SEED):
            n_a, n_b = counts[str(e["unit"])]
            d, lo, hi = float(e["distance"]), float(e["bc_low"]), float(e["bc_high"])
            rows.append({"scope": scope, "n_official": n_a, "n_commercial_side": n_b, **e,
                         "obs_outside_bc": not lo <= d <= hi})
    out = args.out_dir / f"rq1_intervals_{datetime.date.today():%Y%m%d}.csv"
    args.out_dir.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=INTERVAL_COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.4f}" if isinstance(v, float) else v) for k, v in r.items()})
    print(f"{'scope':<15}{'unit':<11}{'n_c':>4}{'obs':>8}{'bias':>8}{'BCpt':>8}  "
          f"{'percentile':<16}{'BC':<16}{'BCa':<16}{'basic':<16}")
    for r in rows:
        iv = "  ".join(f"[{r[k + '_low']:.3f},{r[k + '_high']:.3f}]"
                       for k in ("pct", "bc", "bca", "basic"))
        print(f"{r['scope']:<15}{r['unit']:<11}{r['n_commercial_side']:>4}"
              f"{r['distance']:>8.4f}{r['bias']:>8.4f}{r['bc_point']:>8.4f}  {iv}"
              f"{'  obs outside BC' if r['obs_outside_bc'] else ''}")
    print(f"wrote {out}")
    return 0


def _read_ids(path: Path) -> set[int]:
    """recipe_ids from `path`: one per line; blank lines and '#' comments ignored."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return {int(x) for ln in lines if (x := ln.split("#", 1)[0].strip())}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--unit", choices=UNITS, default=ANALYSIS_UNIT)
    ap.add_argument("--permutations", type=int, default=9_999)
    ap.add_argument("--bootstrap", type=int, default=9_999)
    ap.add_argument("--processed", type=Path, default=PROCESSED)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--reviewed-only", action="store_true",
                    help="use only entries drafted or reviewed by the researcher")
    ap.add_argument("--exclude-recipes", type=Path, default=None,
                    help="sensitivity run, evidence only: a file of recipe_ids (one per "
                         "line, '#' comments) to leave out; output gets the file's stem "
                         "as a suffix")
    ap.add_argument("--interval-evidence", action="store_true",
                    help="HD-44 open amendment: compare interval types per cell (primary "
                         "weighting) from the same bootstrap draws; writes "
                         "rq1_intervals_YYYYMMDD.csv, no permutations")
    args = ap.parse_args(argv)
    try:
        data = load_inputs(args.processed, reviewed_only=args.reviewed_only)
        if data.empty:
            raise InputError("no recipe in v_recipes_clean has mapped ingredients yet: "
                             "author the lexicon, then `make lexicon` and `make parquet`")
        excluded = _read_ids(args.exclude_recipes) if args.exclude_recipes else set()
        if excluded:
            data = data[~data["recipe_id"].isin(excluded)]
        if args.interval_evidence:
            return _interval_evidence(data, args)
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
        "seed": RANDOM_SEED, "ci": "bias-corrected percentile, 95% (HD-44)",
        "p_value": "one-sided, (1 + #null >= obs) / (1 + n). Primary (reported): "
                   "register-label shuffle, p_register_holm = Holm across units within "
                   "each scope. Secondary: region-label shuffle, p_unit_holm. "
                   "(HD-44, revised 2026-11-06)",
        "min_n_commercial": COMMERCIAL_MIN_N,
        "below_min_n": "n_commercial_side < min_n_commercial; flagged, not dropped, and "
                       "still inside its Holm family (HD-37 amendment, 2026-11-06)",
        "obs_outside_ci": "observed distance outside its own CI (HD-44 amendment A: "
                          "footnoted, see limitations L20)",
        "excluded_recipes": (f"{len(excluded)} from {args.exclude_recipes.name} "
                             "(sensitivity run, evidence only)") if excluded else None,
        "lexicon": "reviewed-only" if args.reviewed_only else "all entries",
        "lexicon_entries": len(entries),
        "lexicon_entries_used": int(data["canonical_id"].nunique()),
        "recipes": int(data["recipe_id"].nunique()),
        "recipes_by_register": {k: int(v) for k, v in
                                data.groupby("register")["recipe_id"].nunique().items()},
    }
    suffix = ("_reviewed" if args.reviewed_only else "") + \
        (f"_excl_{args.exclude_recipes.stem}" if excluded else "")
    path = write(rows, meta, args.out_dir, day, suffix)
    print_table(rows)
    print(f"\nwrote {path} and {path.with_suffix('.json').name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
