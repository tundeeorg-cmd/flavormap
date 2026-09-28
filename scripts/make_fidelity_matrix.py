"""Build the pipeline-fidelity matrix (RQ4) from ``cook_along_log``.

    uv run python -m scripts.make_fidelity_matrix [--out figures/fidelity_matrix.png]

One column per logged cook-along, labelled with the recipe's Thai name and the cook
date. Until a cook-along is loaded (``make cook-along``) the figure renders empty and
says so, so ``make figures`` stays runnable end to end (rule 5).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from src.config import FIGURES_DIR
from src.db import get_connection
from src.viz.fidelity_matrix import CLASSES, DishRow, render

QUERY = f"""
SELECT r.name_th, c.cook_date, c.classifier_gets_wrong,
       {", ".join(f"c.fidelity_{cls}" for cls in CLASSES)}
  FROM cook_along_log c
  JOIN recipes r USING (recipe_id)
"""


def rows_from_db() -> list[DishRow]:
    conn = get_connection()
    try:
        records = conn.execute(QUERY).fetchall()
    finally:
        conn.close()
    return [
        DishRow(
            label=name_th,
            cook_date=cook_date,
            classifier_gets_wrong=wrong,
            cells=dict(zip(CLASSES, levels, strict=True)),
        )
        for name_th, cook_date, wrong, *levels in records
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=FIGURES_DIR / "fidelity_matrix.png")
    args = ap.parse_args()
    rows = rows_from_db()
    render(rows, args.out)
    print(f"wrote {args.out} ({len(rows)} dish(es))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
