"""Build Figure 4 from the database.

    uv run python -m scripts.make_figure4 [--out figures/figure4.html]

Reads province geometry and parsed ingredient lists, computes prevalence per province,
and writes a self-contained HTML file.

**Ingredient matching is provisional.** `canonical_ingredients` is empty and stays that
way until HD-6 — the gate CLAUDE.md §9 calls the most important in the project — so these
panels match on substrings of the raw ingredient string. That is adequate for a go/no-go
signal check and is NOT adequate for a published result. Every pattern is printed in the
figure so a reader can see exactly what was counted.

MSG (ผงชูรส) was specified as the flat null control in Bible §10. It does not occur in
this corpus under any spelling, which is itself consistent with L15 — the programme
selected dishes at risk of disappearing. Salt stands in as the expected-flat panel and
the absence is stated on the figure.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from src.config import FIGURES_DIR
from src.db import get_connection
from src.viz.figure4 import Panel, ProvincePoint, render

# (label, LIKE pattern, is_control, note)
PANELS: list[tuple[str, str, bool, str | None]] = [
    ("ปลาร้า (pla ra)", "%ปลาร้า%", False, "fermented fish — expected Northeast-heavy"),
    ("ข้าวเหนียว (sticky rice)", "%ข้าวเหนียว%", False, "expected Northeast/North"),
    ("กะทิ (coconut milk)", "%กะทิ%", False, "expected Central/South"),
    ("น้ำปลา (fish sauce)", "%น้ำปลา%", False, None),
    ("พริก (chilli)", "%พริก%", False, "any chilli — coarse by design"),
    ("ตะไคร้ (lemongrass)", "%ตะไคร้%", False, None),
    ("มะพร้าว (coconut)", "%มะพร้าว%", False, None),
    ("เกลือ (salt)", "%เกลือ%", True, "stands in for MSG, which does not occur"),
]

QUERY = """
WITH bangkok AS (SELECT geom FROM provinces WHERE name_en = 'Bangkok'),
usable AS (
    SELECT a.province_code, rr.parsed_json -> 'ingredients' AS ingredients
      FROM recipes r
      JOIN province_attribution a USING (recipe_id)
      JOIN raw_recipes rr ON rr.raw_id = r.raw_id
     WHERE a.province_code IS NOT NULL
       AND jsonb_array_length(rr.parsed_json -> 'ingredients') > 0
)
SELECT p.province_code,
       p.name_en,
       p.region4,
       ST_Distance(ST_PointOnSurface(p.geom)::geography,
                   ST_PointOnSurface(b.geom)::geography) / 1000.0 AS km,
       count(*) AS n_recipes,
       count(*) FILTER (
           WHERE EXISTS (
               SELECT 1 FROM jsonb_array_elements(u.ingredients) i
                WHERE i ->> 'name_th' LIKE %s
           )
       ) AS n_with
  FROM usable u
  JOIN provinces p USING (province_code)
  CROSS JOIN bangkok b
 GROUP BY p.province_code, p.name_en, p.region4, km
 ORDER BY km
"""


def build() -> tuple[list[Panel], int, int]:
    conn = get_connection()
    try:
        panels: list[Panel] = []
        provinces = recipes = 0
        for label, pattern, is_control, note in PANELS:
            rows = conn.execute(QUERY, (pattern,)).fetchall()
            points = [
                ProvincePoint(
                    province_code=code,
                    name_en=name,
                    region=region,
                    km_from_bangkok=float(km),
                    n_recipes=int(n_recipes),
                    n_with_ingredient=int(n_with),
                )
                for code, name, region, km, n_recipes, n_with in rows
            ]
            provinces = max(provinces, len(points))
            recipes = max(recipes, sum(p.n_recipes for p in points))
            panels.append(
                Panel(
                    label=label,
                    pattern=pattern,
                    points=points,
                    is_control=is_control,
                    note=note,
                )
            )
        return panels, provinces, recipes
    finally:
        conn.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=FIGURES_DIR / "figure4.html")
    args = ap.parse_args()

    panels, provinces, recipes = build()
    if not provinces:
        raise SystemExit("no province-attributed recipes with ingredients — nothing to plot")

    per_province = recipes / provinces if provinces else 0
    caveats = [
        f"Institutional corpus only (dcp_food): {recipes} recipes across {provinces} "
        f"provinces, {per_province:.1f} per province.",
        "The programme shortlists three menus per province by design, so a province's "
        "prevalence can only take the values 0, 1/3, 1/2, 2/3 or 1. Vertical spread is "
        "coarse for that reason, not because the signal is weak.",
        "The corpus is curated for dishes at risk of disappearing (L15), so it is not a "
        "sample of what people cook, and prevalence here is not consumption.",
        "MSG (ผงชูรส) does not occur in this corpus under any spelling, so the specified "
        "flat null control could not be drawn; salt is shown in its place.",
        "Ingredient matching is substring-based pending HD-6. Not a published result.",
    ]
    html = render(
        panels,
        subtitle=(
            f"{recipes} recipes · {provinces} of 77 provinces · institutional corpus "
            f"(food.culture.go.th) · generated from the local database"
        ),
        caveats=caveats,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html, encoding="utf-8")
    print(f"wrote {args.out} ({len(html):,} bytes)")
    for panel in panels:
        print(
            f"  {panel.label:<28} {panel.n_provinces:>3} provinces, "
            f"{panel.n_recipes_with:>3} recipes"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
