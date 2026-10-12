"""Export the analysis tables from the database to Parquet (TIMELINE T1.18).

    uv run python -m scripts.export_parquet        (or: make parquet)

Writes one file per table to ``data/processed/<table>.parquet``. These are the analysis
inputs, not the public release: the release is CLAUDE.md §12's separate, gated step
(HD-20). The files are gitignored, because they carry DCP-derived rows (reference-only
under HD-3) and fieldwork rows (local-only until HD-20).

**No personal data, checked twice.**

1. Every table is exported through an explicit column list, never ``SELECT *``, so a
   column added later cannot leak out unnoticed. Recipe method prose
   (`recipes.method_text`) and attribution free text are not exported.
2. Every file is written to a staging folder and scanned with
   `src.ingest.pdpa.scan_parquet`, the same patterns as the database scan. **Only if every
   file is clean** are they moved into ``data/processed/``. Any hit deletes the whole
   batch and exits non-zero, so a file with personal data never lands.

``ingredient_lines`` is derived, not a table. It holds each recipe's ingredient strings as
the parsers stored them: DCP and interview rows keep bare names
(``ingredients[].name_th``, ``shape = 'name'``), and kapook keeps whole lines with their
quantities (``sections[].items[]``, ``shape = 'line'``). It is the same read
`scripts/lexicon_worklist.py` does, plus order and section heading.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import pandas as pd

from src.config import DATA_DIR
from src.db import get_connection
from src.ingest.pdpa import scan_parquet

OUT_DIR = DATA_DIR / "processed"

QUERIES: dict[str, str] = {
    "recipes": """
        SELECT r.recipe_id, r.register, r.extraction_method, rr.source_id, s.source_type,
               r.name_th, r.dish_category_source, r.occasion, r.endangerment,
               r.cooking_methods, rr.published_at, r.collection_date
          FROM recipes r
          JOIN raw_recipes rr USING (raw_id)
          LEFT JOIN sources s ON s.source_id = rr.source_id
         ORDER BY r.recipe_id""",
    "province_attribution": """
        SELECT recipe_id, province_code, region, tier, confidence
          FROM province_attribution ORDER BY recipe_id""",
    "provinces": """
        SELECT province_code, name_th, name_en, region4, dialect_group, border_country,
               centroid_lat, centroid_lon
          FROM provinces ORDER BY province_code""",
    "ingredient_lines": """
        SELECT r.recipe_id, r.register, rr.source_id, 'name' AS shape,
               NULL::text AS section_heading, i.n::int AS position,
               i.v ->> 'name_th' AS raw_text
          FROM recipes r
          JOIN raw_recipes rr USING (raw_id)
          CROSS JOIN LATERAL jsonb_array_elements(
              COALESCE(rr.parsed_json -> 'ingredients', '[]'::jsonb))
              WITH ORDINALITY AS i(v, n)
        UNION ALL
        SELECT r.recipe_id, r.register, rr.source_id, 'line',
               sec.v ->> 'heading', (sec.n * 1000 + item.n)::int, item.v #>> '{}'
          FROM recipes r
          JOIN raw_recipes rr USING (raw_id)
          CROSS JOIN LATERAL jsonb_array_elements(
              COALESCE(rr.parsed_json -> 'sections', '[]'::jsonb))
              WITH ORDINALITY AS sec(v, n)
          CROSS JOIN LATERAL jsonb_array_elements(COALESCE(sec.v -> 'items', '[]'::jsonb))
              WITH ORDINALITY AS item(v, n)
         ORDER BY 1, 6""",
    "recipe_ingredients": """
        SELECT recipe_id, canonical_id, raw_text, quantity_g, has_quantity,
               acquisition_raw, acquisition_mode, extraction_method, human_validated
          FROM recipe_ingredients ORDER BY recipe_id""",
    "canonical_ingredients": """
        SELECT canonical_id, name_th, name_en, category, is_fermented, approved_by_human
          FROM canonical_ingredients ORDER BY canonical_id""",
    "ingredient_aliases": """
        SELECT alias, canonical_id, match_method, approved_by_human
          FROM ingredient_aliases ORDER BY alias""",
    "v_recipes_clean": """
        SELECT recipe_id, register, source_id, source_type, province_code, region,
               confidence, tier, n_ingredients, published_at
          FROM v_recipes_clean ORDER BY recipe_id""",
    "informants": """
        SELECT informant_id, province_code, district, age_bracket, role, acquisition_mode,
               interview_date
          FROM informants ORDER BY informant_id""",
    "interview_dishes": """
        SELECT dish_key, informant_id, recipe_id, dish_name_th, official_recipe_id,
               cook_status_verbatim, cook_status_level, distinctiveness_claim,
               stated_absence, stated_substitutions
          FROM interview_dishes ORDER BY dish_key""",
    "cook_along_log": """
        SELECT log_key, recipe_id, cook_date, result_recognizable, classifier_gets_wrong,
               fidelity_quantities, fidelity_order, fidelity_technique,
               fidelity_specificity, fidelity_completeness
          FROM cook_along_log ORDER BY log_key""",
}


def fetch(conn, sql: str) -> pd.DataFrame:  # type: ignore[no-untyped-def]
    cur = conn.execute(sql)
    columns = [d.name for d in cur.description]
    return pd.DataFrame(cur.fetchall(), columns=columns)


def export(out_dir: Path = OUT_DIR) -> dict[str, int]:
    """Write every table, scan, and publish into `out_dir` only if all are clean.
    Returns rows per table. Raises `SystemExit` (non-zero) on any personal-data hit."""
    staging = out_dir / ".staging"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    rows: dict[str, int] = {}
    try:
        with get_connection() as conn:
            conn.read_only = True
            for table, sql in QUERIES.items():
                frame = fetch(conn, sql)
                frame.to_parquet(staging / f"{table}.parquet", index=False)
                rows[table] = len(frame)
        offenders = [hit for f in sorted(staging.glob("*.parquet")) for hit in scan_parquet(f)]
        if offenders:
            raise SystemExit(
                f"refused: {len(offenders)} personal-data hit(s); nothing written.\n"
                + "\n".join(o.split(": ", 1)[0] for o in offenders[:20]))
        for f in staging.glob("*.parquet"):
            f.replace(out_dir / f.name)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    args = ap.parse_args()
    rows = export(args.out)
    width = max(map(len, rows))
    for table, n in rows.items():
        print(f"  {table:<{width}}  {n:>6} rows")
    print(f"wrote {len(rows)} Parquet files to {args.out}; PDPA scan clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
