"""Parse and load `flavormap_food67.csv` — the 2567 one-province-one-menu book.

    uv run python -m scripts.parse_food67 [--dry-run]
    uv run python -m scripts.parse_food67 --report

Provenance for this file is **unresolved** — see `src/ingest/food67.py`'s module
docstring and `docs/decisions.md`'s Task 0 note. This loader does not resolve that; it
loads what the brief specifies, with the provenance caveat carried as a
`raw_recipes.parsed_json` note on every row, so it is visible wherever the data is
inspected, not just in a document someone has to know to go read.

**Not runnable end to end until:**

1. `data/raw/gdcatalog/flavormap_food67.csv` exists — not present in this environment
   (`docs/decisions.md`).
2. `sources` carries a row for this source. Not seeded here, for the same reason
   `scripts/parse_gdcatalog.py` and `scripts/parse_local_dish_inventory.py` don't seed
   theirs: no completed, dated source audit exists to transcribe from, and this file's
   own provenance is undocumented on top of that (Task 0).

`--report` runs the full quality pass (`src.ingest.food67.build_quality_report`)
against the CSV without touching the database: ingredient-count mismatches, sara-am
corruption, dish-name artifacts, null method_th/benefits_th rows, Khmer/gloss splits,
top-100 ingredients, and variant candidates. This is what Task 4's report is built
from, and it works the moment the CSV exists, independent of the database gaps above.

**PDPA.** `source_info_th` is free-text source attribution from a government
publication — the same shape of field the DCP forms carry contact detail in. It is
run through `src.ingest.pdpa.redact` (the existing DCP-forms stripper, not a new one)
before being written, and a `redaction_log` row records the result the same way
`scripts/parse_dcp.py` does. A row with a genuinely empty `source_info_th` is not a
parser failure the way a DCP form's contact block is (this field's presence isn't
guaranteed the way the forms' contact block is), so `suspected_parser_failure` reads
differently here — see `load()`.

**Never published**, per Task 3c: `method_th`, `history_th`, `benefits_th`,
`source_info_th` are written to the local database only. See migration 024's column
comments — this restriction is documented on the schema itself, not only here, so it
survives whoever builds the eventual export script not having read this docstring.
"""

from __future__ import annotations

import argparse
import hashlib
import json

import pandas as pd

from src.config import RAW_DIR
from src.db import get_connection
from src.ingest.food67 import (
    PROGRAMME_YEAR,
    SOURCE_PROGRAMME,
    build_quality_report,
    read_raw,
    split_ingredients,
    validate_columns,
)
from src.ingest.pdpa import redact

SOURCE_ID = "gdcatalog_food67"
REGISTER = "official"
DEFAULT_CSV = RAW_DIR / "gdcatalog" / "flavormap_food67.csv"

#: Task 0 — no extraction script, commit, or decision entry for this file exists
#: anywhere in this repository (docs/decisions.md). Carried into parsed_json on every
#: row rather than left to a document someone must separately know to check.
PROVENANCE_NOTE = (
    "flavormap_food67.csv is of undocumented provenance: no extraction script, "
    "commit, or decision entry in this repository records how it was produced. "
    "See docs/decisions.md, Task 0."
)


def load(df: pd.DataFrame, dry_run: bool) -> dict[str, int]:
    stats = {"rows": 0, "recipes": 0, "attributed": 0, "unattributed": 0, "khmer_glossed": 0}

    if dry_run:
        stats["rows"] = len(df)
        stats["recipes"] = len(df)
        return stats

    conn = get_connection()
    try:
        provinces = {
            name: code
            for code, name in conn.execute(
                "SELECT province_code, name_th FROM provinces"
            ).fetchall()
        }

        for _, row in df.iterrows():
            stats["rows"] += 1

            clean_source_info, red = redact(row["source_info_th"] or "")

            payload = {
                "source_dish_id": row["dish_id"],
                "region_th_raw": row["region_th"],  # region mapping is an open gate — see HD-23
                "province_th_raw": row["province_th"],
                "ingredients_th_raw": row["ingredients_th"],
                "ingredients_split": split_ingredients(row["ingredients_th"]),
                "ingredient_count_stated": row["ingredient_count"],
                "method_step_count_stated": row["method_step_count"],
                "provenance_note": PROVENANCE_NOTE,
            }
            digest = hashlib.sha256(
                json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest()

            raw_id = conn.execute(
                """
                INSERT INTO raw_recipes (source_id, source_url, raw_path, parsed_json,
                                         content_hash, http_status)
                VALUES (%s,%s,%s,%s,%s,NULL)
                ON CONFLICT (source_id, content_hash) DO UPDATE
                    SET parsed_json = EXCLUDED.parsed_json
                RETURNING raw_id
                """,
                (
                    SOURCE_ID, row["source_url"], str(DEFAULT_CSV),
                    json.dumps(payload, ensure_ascii=False), digest,
                ),
            ).fetchone()[0]

            # Unlike a DCP form, this field is not guaranteed to carry contact detail
            # in the first place — zero redactions here means "nothing to strip",
            # not necessarily "the parser missed it". suspected_parser_failure is
            # therefore only set when the field had content but nothing was retained
            # after redaction (which would itself be a stripping bug, not a miss).
            conn.execute(
                """
                INSERT INTO redaction_log (raw_id, source_id, document_ref, n_names,
                                           n_addresses, n_phone_numbers, n_emails,
                                           n_coordinates, n_media_links,
                                           suspected_parser_failure, note)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (raw_id) DO UPDATE
                    SET parsed_at = now(),
                        n_names = EXCLUDED.n_names,
                        n_addresses = EXCLUDED.n_addresses,
                        n_phone_numbers = EXCLUDED.n_phone_numbers,
                        n_emails = EXCLUDED.n_emails,
                        n_coordinates = EXCLUDED.n_coordinates,
                        n_media_links = EXCLUDED.n_media_links,
                        suspected_parser_failure = EXCLUDED.suspected_parser_failure,
                        note = EXCLUDED.note
                """,
                (
                    raw_id, SOURCE_ID, row["dish_id"], red.n_names, red.n_addresses,
                    red.n_phone_numbers, red.n_emails, red.n_coordinates,
                    red.n_media_links, False, "source_info_th redaction pass",
                ),
            )

            recipe_id = conn.execute(
                """
                INSERT INTO recipes (raw_id, name_th, register, source_programme,
                                     programme_year, source_dish_id, book_page,
                                     pdf_pages, method_th, method_step_count,
                                     benefits_th, history_th, source_info_th)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (raw_id) DO UPDATE
                    SET name_th = EXCLUDED.name_th,
                        register = EXCLUDED.register,
                        source_programme = EXCLUDED.source_programme,
                        programme_year = EXCLUDED.programme_year,
                        source_dish_id = EXCLUDED.source_dish_id,
                        book_page = EXCLUDED.book_page,
                        pdf_pages = EXCLUDED.pdf_pages,
                        method_th = EXCLUDED.method_th,
                        method_step_count = EXCLUDED.method_step_count,
                        benefits_th = EXCLUDED.benefits_th,
                        history_th = EXCLUDED.history_th,
                        source_info_th = EXCLUDED.source_info_th
                RETURNING recipe_id
                """,
                (
                    raw_id, row["dish_name_th"], REGISTER, SOURCE_PROGRAMME,
                    PROGRAMME_YEAR, row["dish_id"], row["book_page"], row["pdf_pages"],
                    row["method_th"] or None,
                    int(row["method_step_count"]) if row["method_step_count"] else None,
                    row["benefits_th"] or None, row["history_th"] or None,
                    clean_source_info or None,
                ),
            ).fetchone()[0]
            stats["recipes"] += 1

            code = provinces.get((row["province_th"] or "").strip())
            conn.execute(
                """
                INSERT INTO province_attribution (recipe_id, province_code, tier,
                                                  confidence, method_note)
                VALUES (%s,%s,1,%s,%s)
                ON CONFLICT (recipe_id) DO NOTHING
                """,
                (
                    recipe_id, code, "high" if code else "low",
                    "explicit province_th field on flavormap_food67.csv"
                    if code
                    else f"province string did not match provinces.name_th: "
                         f"{row['province_th']!r}",
                ),
            )
            stats["attributed" if code else "unattributed"] += 1

        conn.commit()
    finally:
        conn.close()
    return stats


def print_report(df: pd.DataFrame) -> None:
    report = build_quality_report(df)
    print(f"rows: {report.total_rows}")
    print(f"ingredient_count mismatches: {len(report.count_mismatches)}")
    for m in report.count_mismatches[:20]:
        print(f"  {m.dish_id} {m.dish_name_th!r}: stated={m.stated_count} split={m.split_count}")
    print(f"\nsara-am corruption instances: {len(report.sara_am_instances)}")
    for s in report.sara_am_instances[:30]:
        print(f"  [{s.pattern}] {s.field}/{s.row_id}: {s.match!r} in ...{s.context!r}...")
    print(f"\ndish-name artifacts: {len(report.dish_name_artifacts)}")
    for a in report.dish_name_artifacts:
        print(f"  {a.dish_id}: {a.dish_name_th!r} — {a.issue}")
    print(f"\nnull method_th rows: {report.null_method_rows}")
    print(f"null benefits_th rows: {report.null_benefits_rows}")
    print(f"\nKhmer/gloss splits found: {len(report.khmer_glosses)}")
    for g in report.khmer_glosses:
        print(f"  {g.dish_id}: {g.khmer_name!r} ({g.thai_gloss!r})")
    print(f"\ntop {len(report.top_ingredients)} ingredients:")
    for name, count in report.top_ingredients:
        print(f"  {count:>4}  {name}")
    print(f"\nvariant candidates: {len(report.variant_candidates)}")
    for c in report.variant_candidates[:50]:
        print(f"  [{c.relation}, {c.score:.2f}] {c.a!r} ({c.count_a}) <-> {c.b!r} ({c.count_b})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--report", action="store_true", help="print the Task 4 quality report and exit"
    )
    args = ap.parse_args()

    if not DEFAULT_CSV.exists():
        raise SystemExit(
            f"{DEFAULT_CSV} not found. Not fetched automatically — see this module's "
            "docstring and docs/decisions.md's Task 0 provenance note."
        )

    df = read_raw(DEFAULT_CSV)
    validate_columns(df)

    if args.report:
        print_report(df)
        return 0

    stats = load(df, args.dry_run)
    print("\n" + "\n".join(f"{k:>14}: {v}" for k, v in stats.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
