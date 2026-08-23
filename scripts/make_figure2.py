"""Build Figure 2 from the database and the kapook corpus.

    uv run python -m scripts.make_figure2 [--out figures/figure2.png] [--permutations N]

Geography comes from `provinces.geom`, loaded from GADM v4.1 by `scripts.load_geometry`.
A **region** centroid is `ST_PointOnSurface` of the region's dissolved polygon, matching
the province rule in that script: a true centroid can fall outside a concave or multi-part
shape, and a Central-region centre in the Gulf of Thailand would bend every distance
without ever looking wrong.

Distances are computed on `geography`, so they are great-circle metres on the spheroid
rather than degrees.

Everything else — the labelled cohort, the tokenisation, the permutation tests — comes
from `scripts.rq1_region_level`, so the figure and the numbers in
`docs/rq1_region_level.md` cannot drift apart.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from scripts.rq1_region_level import COHORTS, build_corpus
from src.analyze.region_signal import holm_adjust, separation_test
from src.config import FIGURES_DIR, RANDOM_SEED
from src.db import get_connection
from src.viz.figure2 import PairPoint, render

ABBREVIATION = {"Central": "C", "North": "N", "Northeast": "NE", "South": "S"}

REGION_DISTANCES = """
WITH region AS (
  SELECT region4, ST_PointOnSurface(ST_Union(geom))::geography AS centre
  FROM provinces
  WHERE geom IS NOT NULL
  GROUP BY region4
)
SELECT a.region4, b.region4, ST_Distance(a.centre, b.centre) / 1000.0
FROM region a JOIN region b ON a.region4 < b.region4
"""


def region_distances() -> dict[frozenset[str], float]:
    connection = get_connection()
    try:
        rows = connection.execute(REGION_DISTANCES).fetchall()
    finally:
        connection.close()
    if not rows:
        raise SystemExit(
            "no province geometry in the database — run `uv run python -m "
            "scripts.load_geometry` first. Panel A's X axis is great-circle distance and "
            "there is nothing to compute it from; nothing is drawn rather than drawn "
            "against an invented axis."
        )
    return {frozenset((a, b)): float(km) for a, b, km in rows}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=FIGURES_DIR / "figure2.png")
    ap.add_argument("--permutations", type=int, default=9_999)
    args = ap.parse_args()

    distances = region_distances()
    records = build_corpus()
    vectorizer = TfidfVectorizer(analyzer=lambda tokens: tokens, min_df=2)
    matrix = vectorizer.fit_transform([r["tokens"] for r in records]).toarray()
    index = {r["page_id"]: i for i, r in enumerate(records)}

    cohort = [r for r in records if r["region"] and r["n_sections"] <= COHORTS["single"]]
    regions = sorted({str(r["region"]) for r in cohort})
    print(f"cohort: {len(cohort)} single-dish recipes across {len(regions)} regions")

    results = {}
    for i, first in enumerate(regions):
        for second in regions[i + 1:]:
            pair = [r for r in cohort if r["region"] in (first, second)]
            rows = np.array([index[r["page_id"]] for r in pair])
            results[(first, second)] = separation_test(
                matrix[rows], [str(r["region"]) for r in pair], args.permutations, RANDOM_SEED
            )

    adjusted = holm_adjust({f"{a}|{b}": r.p_value for (a, b), r in results.items()})
    points = []
    for (first, second), result in results.items():
        km = distances.get(frozenset((first, second)))
        if km is None:
            raise SystemExit(f"no centroid distance for {first}–{second}")
        points.append(PairPoint(
            label=f"{ABBREVIATION[first]}–{ABBREVIATION[second]}",
            km=km,
            separation=result.separation,
            p_holm=adjusted[f"{first}|{second}"],
            n=result.n_recipes,
            null=result.null,
        ))

    for point in sorted(points, key=lambda p: p.km):
        mark = "*" if point.significant else " "
        print(f"  {point.label:>6}  {point.km:7.1f} km  sep {point.separation:+.4f}  "
              f"Holm {point.p_holm:.4f} {mark}")

    out = render(points, args.out, cohort_n=len(cohort), permutations=args.permutations)
    print(f"\nwritten: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
