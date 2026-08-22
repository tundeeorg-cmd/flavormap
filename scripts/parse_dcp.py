"""Parse the DCP corpus into Postgres.

    uv run python -m scripts.parse_dcp [--limit N] [--dry-run]

Order of operations is the point: each document is extracted, **redacted**, parsed, and
only then written. Nothing reaches a table that has not passed through the stripper, and
`redaction_log` records per-class counts as evidence that it ran.

What is NOT loaded, and why. Ingredient rows are parsed and kept in
`raw_recipes.parsed_json`, but they are not written to `recipe_ingredients`: that table
requires `canonical_id` against `canonical_ingredients`, which is **HD-6** — the gate the
build plan calls the most important in the project. Minting canonical ids here would be
the agent making the project's central analytical decision by default. They wait.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from src.config import RAW_DIR
from src.db import get_connection
from src.ingest.dcp_form import DCPRecord, parse_pdf

SOURCE_ID = "dcp_food"
CORPUS = RAW_DIR / "dcp_food"


def _payload(record: DCPRecord) -> dict[str, object]:
    """JSON for raw_recipes.parsed_json. Contains no personal data by construction."""
    data = asdict(record)
    data.pop("redaction", None)
    return data


def load(records: list[tuple[Path, DCPRecord]], dry_run: bool) -> dict[str, int]:
    stats = {"documents": 0, "recipes": 0, "attributed": 0, "unattributed": 0, "flagged": 0}
    if dry_run:
        for _, rec in records:
            stats["documents"] += 1
            if rec.is_usable:
                stats["recipes"] += 1
            if rec.redaction.suspected_parser_failure:
                stats["flagged"] += 1
        return stats

    conn = get_connection()
    try:
        provinces = {
            name: code
            for code, name in conn.execute(
                "SELECT province_code, name_th FROM provinces"
            ).fetchall()
        }

        for path, rec in records:
            stats["documents"] += 1
            digest = hashlib.sha256(path.read_bytes()).hexdigest()

            raw_id = conn.execute(
                """
                INSERT INTO raw_recipes (source_id, source_url, raw_path, parsed_json,
                                         content_hash, http_status)
                VALUES (%s, %s, %s, %s, %s, 200)
                ON CONFLICT (source_id, content_hash) DO UPDATE
                    SET parsed_json = EXCLUDED.parsed_json
                RETURNING raw_id
                """,
                (
                    SOURCE_ID,
                    f"https://food.culture.go.th/food68/{path.stem}",
                    str(path),
                    json.dumps(_payload(rec), ensure_ascii=False),
                    digest,
                ),
            ).fetchone()[0]

            red = rec.redaction
            conn.execute(
                """
                INSERT INTO redaction_log (raw_id, source_id, document_ref, n_names,
                                           n_addresses, n_phone_numbers, n_emails,
                                           n_coordinates, n_media_links,
                                           suspected_parser_failure, note)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    raw_id, SOURCE_ID, path.name, red.n_names, red.n_addresses,
                    red.n_phone_numbers, red.n_emails, red.n_coordinates,
                    red.n_media_links, red.suspected_parser_failure,
                    "; ".join(rec.notes) or None,
                ),
            )
            if red.suspected_parser_failure:
                stats["flagged"] += 1

            if not rec.is_usable:
                continue

            recipe_id = conn.execute(
                """
                INSERT INTO recipes (raw_id, name_th, dish_category_source, occasion,
                                     endangerment)
                VALUES (%s,%s,%s,%s,%s) RETURNING recipe_id
                """,
                (
                    raw_id, rec.dish_name_th, rec.dish_category_source,
                    rec.occasion_th, rec.endangerment,
                ),
            ).fetchone()[0]
            stats["recipes"] += 1

            code = provinces.get((rec.province_th or "").strip())
            conn.execute(
                """
                INSERT INTO province_attribution (recipe_id, province_code, tier,
                                                  confidence, method_note)
                VALUES (%s,%s,1,%s,%s)
                ON CONFLICT (recipe_id) DO NOTHING
                """,
                (
                    recipe_id, code, "high" if code else "low",
                    "explicit จังหวัด field on the DCP form"
                    if code
                    else f"province string did not match provinces.name_th: "
                         f"{rec.province_th!r}",
                ),
            )
            stats["attributed" if code else "unattributed"] += 1

        conn.commit()
    finally:
        conn.close()
    return stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    paths = sorted(CORPUS.glob("*.pdf"))[: args.limit]
    if not paths:
        raise SystemExit(f"no PDFs in {CORPUS} — run scripts.fetch_dcp_food first")

    records: list[tuple[Path, DCPRecord]] = []
    for i, path in enumerate(paths, 1):
        try:
            records.append((path, parse_pdf(path)))
        except Exception as exc:  # noqa: BLE001 - a bad document must not stop the run
            print(f"  FAILED {path.name}: {type(exc).__name__}: {exc}")
        if i % 40 == 0:
            print(f"  parsed {i}/{len(paths)}")

    stats = load(records, args.dry_run)
    print("\n" + "\n".join(f"{k:>14}: {v}" for k, v in stats.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
