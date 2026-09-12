"""Parse and load a gdcatalog community dish-name survey (`อาหารพื้นถิ่น.csv`-shaped).

    uv run python -m scripts.parse_local_dish_inventory [--dry-run] [--csv PATH]
    uv run python -m scripts.parse_local_dish_inventory --report

Loads into `local_dish_inventory` (migration 023), never `recipes` — this source has
no ingredients and cannot join the ingredient-based analysis. See that migration and
`src/ingest/local_dish_inventory.py` for why.

**Not runnable end to end until the same two gaps as `scripts/parse_gdcatalog.py`
close:** the CSV must exist (this project does not fetch `gdcatalog.go.th` — ETHICS.md
records it as consulted by hand only), and `sources` needs a row for this source,
deliberately not seeded here for the same reason: seeding it would mean inventing an
audit that has not happened (see `docs/decisions.md`, 2026-09-12).

**Province is inferred, never stated by the source.** Every `อำเภอ` value is checked
against `PHETCHABURI_DISTRICTS` on every run — not trusted from one hand-check — and
the loader refuses to guess a province for any row whose district does not resolve.
`provenance_note` on every loaded row records the inference explicitly, so nothing
downstream can mistake it for a source-stated province.

`--report` runs Task 2's arithmetic against whatever is already loaded: how many
`recipes` rows the one-province-one-menu programme carries for Phetchaburi versus how
many dish rows this survey carries for the same province, plus how many of this
survey's dish names appear anywhere in that programme's register under any province.
It is exact-string-match on `dish_name` / `name_th`, which is a real limitation (the
two programmes may name the same dish slightly differently) — see LIMITATIONS.md L19.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from src.config import RAW_DIR
from src.db import get_connection
from src.ingest.local_dish_inventory import SOURCE_PROGRAMME, IngestReport, build_report

SOURCE_ID = "gdcatalog_local_dish_survey"
REGISTER = "official"
PHETCHABURI_CODE = "TH-76"
DEFAULT_CSV = RAW_DIR / "gdcatalog" / "อาหารพื้นถิ่น.csv"


def load(report: IngestReport, dry_run: bool) -> dict[str, int]:
    stats = {"communities": 0, "dishes": 0, "empty_menu_rows": len(report.empty_menu_rows)}

    if dry_run:
        stats["communities"] = report.total_rows
        stats["dishes"] = report.total_dishes
        return stats

    if not report.district_check.all_in_phetchaburi:
        raise SystemExit(
            "refusing to load: district(s) not in Phetchaburi's known set — "
            f"{report.district_check.unrecognised}. Stop and report per the brief, "
            "do not guess a province."
        )

    conn = get_connection()
    try:
        for community in report.communities:
            stats["communities"] += 1
            payload = {
                "row": community.row,
                "community": community.community,
                "moo": community.moo,
                "subdistrict": community.subdistrict,
                "district": community.district,
                "dish_names": community.dish_names,
                "featured_products": community.featured_products,
            }
            digest = hashlib.sha256(
                json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest()

            raw_id = conn.execute(
                """
                INSERT INTO raw_recipes (source_id, source_url, raw_path, parsed_json,
                                         content_hash, http_status)
                VALUES (%s, NULL, %s, %s, %s, NULL)
                ON CONFLICT (source_id, content_hash) DO UPDATE
                    SET parsed_json = EXCLUDED.parsed_json
                RETURNING raw_id
                """,
                (SOURCE_ID, str(DEFAULT_CSV), json.dumps(payload, ensure_ascii=False), digest),
            ).fetchone()[0]

            for dish_name in community.dish_names:
                conn.execute(
                    """
                    INSERT INTO local_dish_inventory
                        (raw_id, dish_name, community, moo, subdistrict, district,
                         province_code, provenance_note, register, source_programme,
                         featured_products)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        raw_id, dish_name, community.community, community.moo,
                        community.subdistrict, community.district, PHETCHABURI_CODE,
                        "province inferred from อำเภอ matching Phetchaburi's full "
                        "district set; not stated in the source CSV",
                        REGISTER, SOURCE_PROGRAMME, community.featured_products,
                    ),
                )
                stats["dishes"] += 1

        conn.commit()
    finally:
        conn.close()
    return stats


def report_task2_arithmetic() -> None:
    """RQ3's official-vs-community dish count for Phetchaburi, from whatever is
    already loaded. Prints zero, honestly, rather than a fabricated number, if either
    side has nothing loaded yet."""
    conn = get_connection()
    try:
        official_count = conn.execute(
            """
            SELECT count(*)
              FROM recipes r
              JOIN province_attribution pa USING (recipe_id)
             WHERE r.source_programme = 'one_province_one_menu'
               AND pa.province_code = %s
            """,
            (PHETCHABURI_CODE,),
        ).fetchone()[0]

        community_count = conn.execute(
            "SELECT count(*) FROM local_dish_inventory WHERE province_code = %s",
            (PHETCHABURI_CODE,),
        ).fetchone()[0]

        overlap_count = conn.execute(
            """
            SELECT count(DISTINCT ldi.dish_name)
              FROM local_dish_inventory ldi
              JOIN recipes r ON r.name_th = ldi.dish_name
             WHERE r.source_programme = 'one_province_one_menu'
               AND ldi.province_code = %s
            """,
            (PHETCHABURI_CODE,),
        ).fetchone()[0]

        print(
            f"one_province_one_menu dishes for Phetchaburi ({PHETCHABURI_CODE}): "
            f"{official_count}"
        )
        print(f"local_food_survey dishes for Phetchaburi: {community_count}")
        print(
            f"of those, exact dish_name matches anywhere in the 231-PDF register: "
            f"{overlap_count} (exact string match only — see LIMITATIONS.md L19)"
        )
        if official_count == 0 or community_count == 0:
            print(
                "\nAt least one side is zero — this is an empty-database result, not "
                "a real measurement. See docs/decisions.md for what is and isn't "
                "loaded in this environment."
            )
    finally:
        conn.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--csv", type=str, default=str(DEFAULT_CSV))
    ap.add_argument("--report", action="store_true", help="print Task 2's arithmetic and exit")
    args = ap.parse_args()

    if args.report:
        report_task2_arithmetic()
        return 0

    csv_path = DEFAULT_CSV if args.csv == str(DEFAULT_CSV) else Path(args.csv)
    if not csv_path.exists():
        raise SystemExit(
            f"{csv_path} not found. This source is not fetched automatically — see "
            "this module's docstring and ETHICS.md's gdcatalog.go.th entry."
        )

    report = build_report(csv_path)
    print(f"communities: {report.total_rows}, dish names: {report.total_dishes}")
    print(
        f"district check: all in Phetchaburi = {report.district_check.all_in_phetchaburi}"
        f" ({len(report.district_check.districts_in_file)} distinct districts seen)"
    )
    if report.district_check.unrecognised:
        print(
            "  UNRECOGNISED districts, stopping per the brief: "
            f"{report.district_check.unrecognised}"
        )
    if report.empty_menu_rows:
        print(
            "rows with zero parsed dishes (listed, not silently dropped): "
            f"{report.empty_menu_rows}"
        )

    stats = load(report, args.dry_run)
    print("\n" + "\n".join(f"{k:>14}: {v}" for k, v in stats.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
