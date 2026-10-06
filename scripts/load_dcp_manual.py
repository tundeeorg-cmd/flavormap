"""Load hand-transcribed DCP forms into the official register (HD-35).

    uv run python -m scripts.load_dcp_manual [--dir data/dcp_manual]

For each validated transcription (``src.ingest.dcp_manual``), in one transaction:

- a ``raw_recipes`` row of its own (source ``dcp_food``), keyed on the transcription's
  identity (``manual:east_5_1.pdf``), with ``raw_path`` pointing at the PDF it transcribes
  and the transcription in ``parsed_json``, using the parser's shape plus
  ``"extraction_method": "manual"``. It is a separate row from the PDF's parsed row, so
  re-running ``scripts/parse_dcp.py`` can never overwrite a transcription;
- a ``recipes`` row, ``register='official'``, ``extraction_method='manual'``;
- a tier-1, high-confidence ``province_attribution`` from §1.1's จังหวัด as transcribed.
  A province that matches no ``provinces.name_th`` aborts the load; it is never guessed.

**Refused, aborting the whole load:** a transcription whose PDF is not in
``data/raw/dcp_food/``, or one for a document the parser already loaded (two records of
one form would double-count it).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path

from src.config import DATA_DIR, RAW_DIR
from src.db import get_connection
from src.ingest.dcp_manual import ManualError, ManualRecord, manual_files, read_manual

MANUAL_DIR = DATA_DIR / "dcp_manual"
CORPUS = RAW_DIR / "dcp_food"
SOURCE_ID = "dcp_food"


def read_all(directory: Path) -> list[ManualRecord]:
    records: list[ManualRecord] = []
    errors: list[str] = []
    for path in manual_files(directory):
        try:
            records.append(read_manual(path))
        except ManualError as e:
            errors.append(str(e))
    if errors:
        raise ManualError("\n".join(errors))
    return records


def load(records: list[ManualRecord], corpus: Path = CORPUS) -> list[str]:
    """Write `records` in one transaction. Returns the documents loaded."""
    conn = get_connection()
    loaded: list[str] = []
    try:
        with conn.transaction():
            for rec in records:
                pdf = corpus / rec.document_ref
                if not pdf.exists():
                    raise ManualError(f"{rec.document_ref}: no such PDF in {corpus}")
                parsed = conn.execute(
                    """SELECT 1 FROM recipes r JOIN raw_recipes rr USING (raw_id)
                        WHERE rr.source_id = %s AND r.extraction_method = 'parsed'
                          AND rr.raw_path LIKE %s""",
                    (SOURCE_ID, f"%/{rec.document_ref}"),
                ).fetchone()
                if parsed:
                    raise ManualError(f"{rec.document_ref}: the parser already loaded this "
                                      "form; a transcription would count it twice")
                province = conn.execute(
                    "SELECT province_code FROM provinces WHERE name_th = %s",
                    (rec.province_th,),
                ).fetchone()
                if province is None:
                    raise ManualError(f"{rec.document_ref}: province_th {rec.province_th!r} "
                                      "matches no province name")
                identity = f"manual:{rec.document_ref}"
                payload = {**asdict(rec), "extraction_method": "manual"}
                raw_id = conn.execute(
                    """INSERT INTO raw_recipes (source_id, source_url, raw_path, parsed_json,
                           content_hash)
                       VALUES (%s, %s, %s, %s, %s)
                       ON CONFLICT (source_id, content_hash) DO UPDATE SET
                           raw_path = EXCLUDED.raw_path, parsed_json = EXCLUDED.parsed_json
                       RETURNING raw_id""",
                    (SOURCE_ID, identity, str(pdf), json.dumps(payload, ensure_ascii=False),
                     hashlib.sha256(identity.encode()).hexdigest()),
                ).fetchone()[0]  # type: ignore[index]
                recipe_id = conn.execute(
                    """INSERT INTO recipes (raw_id, name_th, dish_category_source, occasion,
                           endangerment, register, extraction_method)
                       VALUES (%s, %s, %s, %s, %s, 'official', 'manual')
                       ON CONFLICT (raw_id) DO UPDATE SET
                           name_th = EXCLUDED.name_th,
                           dish_category_source = EXCLUDED.dish_category_source,
                           occasion = EXCLUDED.occasion,
                           endangerment = EXCLUDED.endangerment
                       RETURNING recipe_id""",
                    (raw_id, rec.dish_name_th, rec.dish_category_source, rec.occasion_th,
                     rec.endangerment),
                ).fetchone()[0]  # type: ignore[index]
                conn.execute(
                    """INSERT INTO province_attribution (recipe_id, province_code, tier,
                           confidence, method_note)
                       VALUES (%s, %s, 1, 'high', '§1.1 จังหวัด, hand-transcribed (HD-35)')
                       ON CONFLICT (recipe_id) DO UPDATE SET
                           province_code = EXCLUDED.province_code""",
                    (recipe_id, province[0]),
                )
                loaded.append(rec.document_ref)
    finally:
        conn.close()
    return loaded


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", type=Path, default=MANUAL_DIR)
    args = ap.parse_args()
    try:
        loaded = load(read_all(args.dir))
    except ManualError as e:
        print(f"refused — nothing loaded:\n{e}", file=sys.stderr)
        return 1
    print(f"loaded {len(loaded)} hand-transcribed form(s): {', '.join(loaded) or '-'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
