"""Parse and load `culture.gdcatalog.go.th`'s `thaitastetherapy.csv` into Postgres.

    uv run python -m scripts.parse_gdcatalog [--dry-run]

Government-published (Ministry of Culture open-data catalogue), but a distinct
programme from the 231 one-province-one-menu PDFs, with different selection criteria —
never pooled with them under a bare `register='official'`. Every row this loader
writes carries `register='official'`, `source_programme='thai_taste_therapy'`
(migration 022).

**Not runnable end to end until two things outside this script's control are true:**

1. ``data/raw/gdcatalog/thaitastetherapy.csv`` exists. This project does not fetch it:
   `ETHICS.md`'s `gdcatalog.go.th` row predates this loader and records the catalogue
   as "consulted manually only". The CSV is the researcher's own manual download,
   moved into place, gitignored like every other raw source.
2. `sources` carries a `gdcatalog_thaitastetherapy` row — the FK `raw_recipes.source_id`
   requires it, the same gap migrations 017 and 018 closed for `dcp_food` and
   `kapook_cooking`. No such migration exists yet, because the dated source audit rule
   7 requires has not been completed: this session's sandbox could not reach
   `gdcatalog.go.th` or `culture.gdcatalog.go.th` at all (egress policy denial, not a
   robots.txt-based finding — see `docs/decisions.md`, note dated 2026-09-12). Seeding
   a `sources` row with an unverified `robots_ok` value would be inventing evidence
   this loader's own docstring exists to avoid.

Region is deliberately **not** written to `province_attribution.region`. The source's
own four-way scheme merges Central and East into one label
(``ภาคกลางและตะวันออก``); mapping it onto this project's canonical `provinces.region4`
is an open decision (`docs/decisions.md`, region-mapping gate). The raw string
survives unchanged in `raw_recipes.parsed_json` so nothing is lost while the gate is
open.

Ingredient extraction from `material` only covers the two structured shapes
(`clean_list`, `numbered_list`) — see `src/ingest/gdcatalog.py`. Prose rows still get a
`recipes` row (the dish name and province are real data, usable for RQ3's dish-level
overlap on their own) but no `ingredients` list; `stats["unparsed_ingredients"]`
reports how many.
"""

from __future__ import annotations

import argparse
import hashlib
import json

from src.config import RAW_DIR
from src.db import get_connection
from src.ingest.gdcatalog import SOURCE_PROGRAMME, IngestReport, build_report

SOURCE_ID = "gdcatalog_thaitastetherapy"
REGISTER = "official"
CSV_PATH = RAW_DIR / "gdcatalog" / "thaitastetherapy.csv"


def load(report: IngestReport, dry_run: bool) -> dict[str, int]:
    stats = {
        "rows": 0,
        "recipes": 0,
        "attributed": 0,
        "unattributed": 0,
        "unparsed_ingredients": 0,
    }
    all_records = report.parsed + report.unparsed

    if dry_run:
        stats["rows"] = len(all_records)
        stats["recipes"] = len(all_records)
        stats["unparsed_ingredients"] = len(report.unparsed)
        return stats

    conn = get_connection()
    try:
        provinces = {
            name: code
            for code, name in conn.execute(
                "SELECT province_code, name_th FROM provinces"
            ).fetchall()
        }

        pii = report.drop_report
        # Column-shaped PDPA removal, not per-row regex redaction (contrast
        # src/ingest/pdpa.py) — every row of one file had the same columns dropped,
        # so the same counts apply to each redaction_log row. A file where none of the
        # expected PII columns were even present is schema drift worth flagging, the
        # same way a zero-redaction DCP document is: `suspected_parser_failure`.
        n_names = sum(
            c in pii.pii_columns_present for c in ("ownerprefix", "ownername", "ownersurname")
        )
        n_addresses = sum(c in pii.pii_columns_present for c in ("address",))
        n_coordinates = sum(c in pii.pii_columns_present for c in ("gps",))
        n_media_links = sum(c in pii.pii_columns_present for c in ("picowner", "picadress"))
        suspected_failure = not pii.pii_columns_present

        for record in all_records:
            stats["rows"] += 1
            digest = hashlib.sha256(
                json.dumps(record, ensure_ascii=False, sort_keys=True).encode("utf-8")
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
                (
                    SOURCE_ID,
                    str(CSV_PATH),
                    json.dumps(record, ensure_ascii=False),
                    digest,
                ),
            ).fetchone()[0]

            conn.execute(
                """
                INSERT INTO redaction_log (raw_id, source_id, document_ref, n_names,
                                           n_addresses, n_phone_numbers, n_emails,
                                           n_coordinates, n_media_links,
                                           suspected_parser_failure, note)
                VALUES (%s,%s,%s,%s,%s,0,0,%s,%s,%s,%s)
                ON CONFLICT (raw_id) DO UPDATE
                    SET parsed_at = now(),
                        n_names = EXCLUDED.n_names,
                        n_addresses = EXCLUDED.n_addresses,
                        n_coordinates = EXCLUDED.n_coordinates,
                        n_media_links = EXCLUDED.n_media_links,
                        suspected_parser_failure = EXCLUDED.suspected_parser_failure,
                        note = EXCLUDED.note
                """,
                (
                    raw_id, SOURCE_ID, f"thaitastetherapy.csv row {record['row']}",
                    n_names, n_addresses, n_coordinates, n_media_links,
                    suspected_failure,
                    f"columns dropped: {', '.join(pii.dropped_columns)}",
                ),
            )

            recipe_id = conn.execute(
                """
                INSERT INTO recipes (raw_id, name_th, register, source_programme)
                VALUES (%s,%s,%s,%s)
                ON CONFLICT (raw_id) DO UPDATE
                    SET name_th = EXCLUDED.name_th,
                        register = EXCLUDED.register,
                        source_programme = EXCLUDED.source_programme
                RETURNING recipe_id
                """,
                (raw_id, record["foodname"], REGISTER, SOURCE_PROGRAMME),
            ).fetchone()[0]
            stats["recipes"] += 1
            if "ingredients" not in record:
                stats["unparsed_ingredients"] += 1

            code = provinces.get(str(record.get("province") or "").strip())
            conn.execute(
                """
                INSERT INTO province_attribution (recipe_id, province_code, tier,
                                                  confidence, method_note)
                VALUES (%s,%s,1,%s,%s)
                ON CONFLICT (recipe_id) DO NOTHING
                """,
                (
                    recipe_id, code, "high" if code else "low",
                    "explicit province field on thaitastetherapy.csv"
                    if code
                    else f"province string did not match provinces.name_th: "
                         f"{record.get('province')!r}",
                ),
            )
            stats["attributed" if code else "unattributed"] += 1

        conn.commit()
    finally:
        conn.close()
    return stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not CSV_PATH.exists():
        raise SystemExit(
            f"{CSV_PATH} not found. This source is not fetched automatically — see "
            "this module's docstring and ETHICS.md's gdcatalog.go.th entry. Move the "
            "manually downloaded CSV there first."
        )

    report = build_report(CSV_PATH)
    stats = load(report, args.dry_run)

    print(f"material format counts: {report.format_counts}")
    print(f"distinct region strings (raw, unmapped): {report.distinct_regions}")
    if report.unparsed:
        print(f"\n{len(report.unparsed)} row(s) held out pending hand review (prose material):")
        for rec in report.unparsed:
            print(f"  - {rec['foodname']!r} ({rec['province']}): {rec['note']}")
    print("\n" + "\n".join(f"{k:>20}: {v}" for k, v in stats.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
