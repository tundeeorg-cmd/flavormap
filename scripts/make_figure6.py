"""Figure 6: unit × ingredient TF-IDF heatmap by register (TIMELINE T1.20).

    uv run python -m scripts.make_figure6 [--unit region|province] [--threshold N]
                                          [--out figures/fig6_heatmap.png]

**Unit.** Default region, RQ1's analysis unit (HD-37 C); ``--unit province`` draws the
original province figure. At region level no commercial count threshold has been decided
(HD-23's applies to provinces), so the default there is 0: every region is drawn and each
panel title carries its recipe count. Pass ``--threshold`` to apply one.

Reads the Parquet that `make parquet` writes; `make figures` runs this. The design is
documented in `src/viz/figure6.py`.

**Which provinces appear.** HD-23: the count threshold applies to the commercial register
only. A commercial province enters with at least ``--threshold`` recipes in
``v_recipes_clean``. Official and domestic provinces always enter. The default threshold
is ``PROVINCE_MIN_N`` (10, HD-24), the lowest headline value; 15 and 25 are the others
(CLAUDE.md §7.5). The filter runs **before** TF-IDF, so a province not shown does not
shape the weights of those that are.

Labels: provinces by English name; ingredients by the lexicon's English gloss where one
exists, else the Thai name.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.analyze.eligibility import caption
from src.analyze.rq1_registers import (
    ANALYSIS_UNIT,
    COLUMN,
    PROCESSED,
    UNITS,
    InputError,
    load_inputs,
    profiles,
)
from src.config import FIGURES_DIR, PROVINCE_MIN_N
from src.viz.figure6 import TOP_N, build, render

OUT = FIGURES_DIR / "fig6_heatmap.png"


def commercial_filter(data: pd.DataFrame, threshold: int,
                      column: str = "province_code") -> pd.DataFrame:
    """Drop commercial recipes in units below `threshold` (HD-23 for provinces). Other
    registers pass untouched."""
    commercial = data["register"] == "commercial"
    counts = data[commercial].groupby(column)["recipe_id"].nunique()
    keep = set(counts[counts >= threshold].index)
    return data[~commercial | data[column].isin(keep)]


def labels(processed: Path = PROCESSED) -> tuple[dict[str, str], dict[str, str]]:
    provinces = pd.read_parquet(processed / "provinces.parquet")
    lexicon = pd.read_parquet(processed / "canonical_ingredients.parquet")
    province_label = dict(zip(provinces["province_code"], provinces["name_en"], strict=True))
    ingredient_label = {
        cid: (en if isinstance(en, str) and en else th)
        for cid, en, th in zip(lexicon["canonical_id"], lexicon["name_en"],
                               lexicon["name_th"], strict=True)
    }
    return province_label, ingredient_label


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--unit", choices=UNITS, default=ANALYSIS_UNIT)
    ap.add_argument("--threshold", type=int, default=None,
                    help=f"commercial minimum per unit (default: province {PROVINCE_MIN_N}, "
                         "region 0)")
    ap.add_argument("--top-n", type=int, default=TOP_N)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--processed", type=Path, default=PROCESSED)
    ap.add_argument("--reviewed-only", action="store_true",
                    help="use only entries drafted or reviewed by the researcher")
    args = ap.parse_args(argv)
    if args.reviewed_only and args.out == OUT:
        args.out = OUT.with_name(OUT.stem + "_reviewed" + OUT.suffix)
    try:
        data = load_inputs(args.processed, reviewed_only=args.reviewed_only)
    except InputError as e:
        raise SystemExit(f"{e}") from None
    unit, column = args.unit, COLUMN[args.unit]
    threshold = args.threshold if args.threshold is not None else (
        PROVINCE_MIN_N if unit == "province" else 0)
    data = commercial_filter(data, threshold, column)
    heatmap = build(profiles(data, unit, "tfidf"), top_n=args.top_n)
    counts = {r: data[data["register"] == r].dropna(subset=[column])
              .groupby(column)["recipe_id"].nunique()
              for r in ("official", "commercial", "domestic")}
    if unit == "province":
        text = (f"Official: {len(counts['official'])} of 77 provinces. "
                f"Commercial, at ≥ {threshold} recipes (HD-23): "
                f"{caption(counts['commercial'].to_dict(), threshold)}. "
                f"Domestic: {len(counts['domestic'])} of 77 provinces. ")
    else:
        text = "Recipes per region — " + "; ".join(
            f"{r}: " + (", ".join(f"{u} {n}" for u, n in counts[r].items()) or "none")
            for r in ("official", "commercial", "domestic")) + ". "
        if threshold:
            text += f"Commercial regions with < {threshold} recipes dropped. "
    text += f"Top {len(heatmap.ingredients)} ingredients by variance."
    if args.reviewed_only:
        text += " Reviewed lexicon entries only."
    province_label, ingredient_label = labels(args.processed)
    render(heatmap, args.out, province_label=province_label if unit == "province" else {},
           ingredient_label=ingredient_label, caption=text, unit_name=unit)
    print(f"wrote {args.out} ({len(heatmap.provinces)} {unit}s × "
          f"{len(heatmap.ingredients)} ingredients)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
