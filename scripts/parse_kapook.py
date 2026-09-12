"""Parse the cached kapook_cooking corpus into Postgres — HD-22 option C only.

    uv run python -m scripts.parse_kapook [--limit N] [--dry-run]

HD-22 (docs/decisions.md) is open on how a kapook *page* maps to `recipes` *rows*:
pages carry 1 to 46 ingredient sections, and nothing in the markup tells a listicle
(many unrelated dishes on one page) apart from one dish split across sections (batter,
dipping sauce). The researcher decided option C for now (session, 2026-09-12): load
only pages with **exactly one** ingredient section, where the page is unambiguously one
dish. Every other outcome is a legitimate, counted result — never guessed.

`raw_recipes` is written for every fetched page regardless of outcome, so multi-section
and unusable pages are not lost: their full parsed content sits in `parsed_json`,
ready for whenever HD-22's remaining shapes get a rule of their own.

**No `province_attribution` row is written for any kapook recipe.** HD-3's kapook
decision (2026-08-23) already found only ~1.3% of pages carry a reliable province claim
and settled kapook as a coverage corpus, not an attribution one — "answers RQ3 well and
RQ1 not at all." `province_attribution.tier` has no value for "no attempt was made";
writing one anyway would mean claiming an attribution attempt this source cannot
honestly support. These recipes load with `register='commercial'` and simply have no
province_attribution row, which is why `v_recipes_clean`'s inner join excludes them —
correctly: they are not yet attributed, not attributed to nothing.

PDPA: `src.ingest.kapook_page.parse_file` redacts before returning a record — see its
own docstring. Nothing here reads raw HTML text directly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from src.config import RAW_DIR
from src.db import get_connection
from src.ingest.kapook_page import KapookRecord, parse_file

SOURCE_ID = "kapook_cooking"
CORPUS = RAW_DIR / "kapook_cooking"

# kapook is the commercial register (Bible v4 §3) — a fact about the source, not a
# judgment about any individual page.
REGISTER = "commercial"


def _payload(record: KapookRecord) -> dict[str, object]:
    """JSON for raw_recipes.parsed_json. Contains no personal data by construction —
    parse_file() redacts before this function ever sees the record."""
    data = asdict(record)
    data.pop("redaction", None)
    if record.published_at is not None:
        data["published_at"] = record.published_at.isoformat()
    return data


def load(records: list[tuple[Path, KapookRecord]], dry_run: bool) -> dict[str, int]:
    stats = {
        "pages": 0,
        "unusable": 0,
        "single_section_loaded": 0,
        "held_out_multi_section": 0,
        "flagged": 0,
    }
    if dry_run:
        for _, rec in records:
            stats["pages"] += 1
            if not rec.is_usable:
                stats["unusable"] += 1
            elif len(rec.sections) == 1 and (rec.title_th or rec.sections[0].heading):
                stats["single_section_loaded"] += 1
            else:
                stats["held_out_multi_section"] += 1
            if rec.redaction.suspected_parser_failure:
                stats["flagged"] += 1
        return stats

    conn = get_connection()
    try:
        for path, rec in records:
            stats["pages"] += 1
            digest = hashlib.sha256(path.read_bytes()).hexdigest()

            raw_id = conn.execute(
                """
                INSERT INTO raw_recipes (source_id, source_url, raw_path, published_at,
                                         parsed_json, content_hash, http_status)
                VALUES (%s,%s,%s,%s,%s,%s,200)
                ON CONFLICT (source_id, content_hash) DO UPDATE
                    SET parsed_json = EXCLUDED.parsed_json
                RETURNING raw_id
                """,
                (
                    SOURCE_ID, rec.url, str(path), rec.published_at,
                    json.dumps(_payload(rec), ensure_ascii=False), digest,
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
            # Unlike the DCP forms, a kapook page with zero redactions is the normal
            # case, not a parser failure (src.ingest.kapook_page's own docstring) — the
            # flag is still recorded factually, just not treated as evidence of a miss.
            if red.suspected_parser_failure:
                stats["flagged"] += 1

            if not rec.is_usable:
                stats["unusable"] += 1
                continue

            name = rec.title_th or (rec.sections[0].heading if rec.sections else None)
            if len(rec.sections) != 1 or not name:
                # HD-22 option C: everything that is not unambiguously one dish, one
                # section stays out of `recipes` — held out, not dropped. Its content
                # is already in raw_recipes.parsed_json above.
                stats["held_out_multi_section"] += 1
                continue

            conn.execute(
                """
                INSERT INTO recipes (raw_id, name_th, register)
                VALUES (%s,%s,%s)
                ON CONFLICT (raw_id) DO UPDATE
                    SET name_th = EXCLUDED.name_th,
                        register = EXCLUDED.register
                """,
                (raw_id, name, REGISTER),
            )
            stats["single_section_loaded"] += 1

        conn.commit()
    finally:
        conn.close()
    return stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    paths = sorted(CORPUS.glob("view*.html"))[: args.limit]
    if not paths:
        raise SystemExit(f"no cached pages in {CORPUS} — run scripts.fetch_kapook first")

    records: list[tuple[Path, KapookRecord]] = []
    for i, path in enumerate(paths, 1):
        try:
            records.append((path, parse_file(path)))
        except Exception as exc:  # noqa: BLE001 - a bad document must not stop the run
            print(f"  FAILED {path.name}: {type(exc).__name__}: {exc}")
        if i % 200 == 0:
            print(f"  parsed {i}/{len(paths)}")

    stats = load(records, args.dry_run)
    print("\n" + "\n".join(f"{k:>24}: {v}" for k, v in stats.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
