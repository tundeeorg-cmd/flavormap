"""Figure 6: province × ingredient TF-IDF heatmap by register (TIMELINE T1.20).

    uv run python -m scripts.make_figure6 [--threshold 10] [--out figures/fig6_heatmap.png]

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
from src.analyze.rq1_registers import PROCESSED, InputError, load_inputs, profiles
from src.config import FIGURES_DIR, PROVINCE_MIN_N
from src.viz.figure6 import TOP_N, build, render

OUT = FIGURES_DIR / "fig6_heatmap.png"


def commercial_filter(data: pd.DataFrame, threshold: int) -> pd.DataFrame:
    """Drop commercial recipes in provinces below `threshold` (HD-23). Other registers
    pass untouched."""
    commercial = data["register"] == "commercial"
    counts = data[commercial].groupby("province_code")["recipe_id"].nunique()
    keep = set(counts[counts >= threshold].index)
    return data[~commercial | data["province_code"].isin(keep)]


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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--threshold", type=int, default=PROVINCE_MIN_N)
    ap.add_argument("--top-n", type=int, default=TOP_N)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    try:
        data = load_inputs()
    except InputError as e:
        raise SystemExit(f"{e}") from None
    data = commercial_filter(data, args.threshold)
    heatmap = build(profiles(data, "province", "tfidf"), top_n=args.top_n)
    counts = {r: data[data["register"] == r].groupby("province_code")["recipe_id"].nunique()
              for r in ("official", "commercial", "domestic")}
    text = (f"Official: {len(counts['official'])} of 77 provinces. "
            f"Commercial, at ≥ {args.threshold} recipes (HD-23): "
            f"{caption(counts['commercial'].to_dict(), args.threshold)}. "
            f"Domestic: {len(counts['domestic'])} of 77 provinces. "
            f"Top {len(heatmap.ingredients)} ingredients by variance.")
    province_label, ingredient_label = labels()
    render(heatmap, args.out, province_label=province_label,
           ingredient_label=ingredient_label, caption=text)
    print(f"wrote {args.out} ({len(heatmap.provinces)} provinces × "
          f"{len(heatmap.ingredients)} ingredients)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
