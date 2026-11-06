"""HD-37 rule 3: region labels from body text the researcher read by hand.

    uv run python -m scripts.apply_body_text_labels [--sheet …] [--dry-run]
    (make labels-body, after make labels)

**HD-37, decided 2026-11-06 (C + D):** a province or region claim in body text counts once
it has been read by hand, at ``medium`` confidence. Unread claims are never written. The
reading sheet is `data/interim/hd37d_body_text_reading.csv`, one Kapook page per row, with
the researcher's ``genuine_dish_claim``. Only rows marked ``yes`` are used.

Each confirmed page labels the recipes loaded from it (``loaded_recipe_ids``, HD-22) at
tier 2 (region only), ``medium``, ``province_code`` NULL.

**Precedence.** Title/category labels (`scripts.apply_labels`, rules 1–2, ``high``) win: a
recipe that already has any attribution row this script does not own is left alone and
counted. Run `make labels` first.

**Rows it owns.** Only rows whose ``method_note`` starts with ``OWNED``. They are rebuilt on
every run, so a page changed to ``no`` loses its labels. The prefix differs from
`scripts.apply_labels`' ``HD-37 rule`` so neither script touches the other's rows.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

from src.config import INTERIM_DIR
from src.db import get_connection

SHEET = INTERIM_DIR / "hd37d_body_text_reading.csv"
OWNED = "HD-37 body"
REGIONS = ("North", "Northeast", "Central", "South")
YES = {"yes", "y", "true", "1", "ใช่"}


@dataclass(frozen=True)
class BodyLabel:
    recipe_id: int
    region: str
    page_id: str
    term: str


def confirmed_labels(rows: list[dict[str, str]]) -> list[BodyLabel]:
    """One label per loaded recipe on every page marked a genuine dish claim. A recipe
    that two confirmed pages put in different regions gets no label (CLAUDE.md §1 rule 2:
    never pick one)."""
    seen: dict[int, BodyLabel] = {}
    clash: set[int] = set()
    for row in rows:
        if row.get("genuine_dish_claim", "").strip().lower() not in YES:
            continue
        region = row["region"].strip()
        if region not in REGIONS:
            raise ValueError(f"{row['page_id']}: region {region!r} is not one of {REGIONS}")
        for rid in row.get("loaded_recipe_ids", "").split():
            label = BodyLabel(int(rid), region, row["page_id"], row["region_term"])
            if label.recipe_id in seen and seen[label.recipe_id].region != region:
                clash.add(label.recipe_id)
            seen.setdefault(label.recipe_id, label)
    return [lab for rid, lab in sorted(seen.items()) if rid not in clash]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sheet", type=Path, default=SHEET)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    with args.sheet.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    labels = confirmed_labels(rows)
    pages_yes = sum(r.get("genuine_dish_claim", "").strip().lower() in YES for r in rows)
    print(f"{pages_yes} of {len(rows)} pages confirmed; {len(labels)} loaded recipes on them")

    conn = get_connection()
    try:
        taken = {r[0] for r in conn.execute(
            "SELECT recipe_id FROM province_attribution "
            "WHERE recipe_id = ANY(%s) AND coalesce(method_note, '') NOT LIKE %s",
            ([lab.recipe_id for lab in labels], f"{OWNED}%")).fetchall()}
        write = [lab for lab in labels if lab.recipe_id not in taken]
        by_region: dict[str, int] = {}
        for lab in write:
            by_region[lab.region] = by_region.get(lab.region, 0) + 1
        print(f"{len(taken)} already labelled by another rule (left alone); "
              f"{len(write)} to write: {by_region}")
        if args.dry_run:
            print("dry run: nothing written")
            return 0
        conn.commit()  # end the read transaction so the block below is the real one
        with conn.transaction():
            conn.execute("DELETE FROM province_attribution WHERE method_note LIKE %s",
                         (f"{OWNED}%",))
            for lab in write:
                conn.execute(
                    """INSERT INTO province_attribution (recipe_id, province_code, region,
                           tier, confidence, method_note)
                       VALUES (%s, NULL, %s, 2, 'medium', %s)""",
                    (lab.recipe_id, lab.region,
                     f"{OWNED}: region term '{lab.term}' in body text of {lab.page_id}, "
                     "read by hand"))
        print(f"wrote {len(write)} rows")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
