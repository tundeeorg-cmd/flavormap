"""Load fieldwork interview files into the database (HD-29, HD-30).

    uv run python -m scripts.load_interviews [--dir data/interviews]

For each validated interview (``src.ingest.interview``), in one transaction:

- ``informants``: one row per file.
- Per dish, the domestic register, written exactly as the other sources are written:
  a ``raw_recipes`` row (source ``fieldwork_interviews``), whose ``parsed_json`` holds
  the ingredient lines as recorded, in the same ``{"ingredients": [{"name_th": …}]}``
  shape the DCP and kapook rows use, so the lexicon worklist and canonicalisation (HD-6)
  treat all three registers alike. Then a ``recipes`` row with ``register='domestic'``
  and a tier-1, high-confidence ``province_attribution``: the cook was interviewed in
  that province.
- ``interview_dishes``: the Q4 and Q9 answers, the cook's endangerment view (verbatim,
  plus the HD-11 level if coded), and the researcher-entered official-dish link.

**The raw row's key.** ``raw_recipes`` deduplicates on ``(source_id, content_hash)``.
For a scraped page that is a hash of the page; interview notes are edited by the
researcher, so hashing the content would give every edit a new row. The hash is instead
of the dish's stable identity (``interview:INT_BRM_001/2``), so an edit updates the dish
in place.

**Checked against the database before commit:** every ``official_recipe_id`` must exist
and be ``register='official'``; anything else aborts the whole load. A link to an
official dish from a *different* province is allowed (cooks talk about neighbours'
food) and is listed in the summary, so it is never silent.

Nothing is deleted. Interviews or dishes in the database but no longer in the files are
reported, not removed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from src.config import DATA_DIR
from src.db import get_connection
from src.ingest.interview import Interview, InterviewError, interview_files, read_interview

INTERVIEWS_DIR = DATA_DIR / "interviews"
SOURCE_ID = "fieldwork_interviews"


def read_all(directory: Path) -> list[Interview]:
    """Validate every file; raise one ``InterviewError`` listing all failures."""
    interviews: list[Interview] = []
    errors: list[str] = []
    for path in interview_files(directory):
        try:
            interviews.append(read_interview(path))
        except InterviewError as e:
            errors.append(str(e))
    if errors:
        raise InterviewError("\n".join(errors))
    return interviews


def load(interviews: list[Interview], directory: Path) -> dict[str, list[str]]:
    """Write `interviews` in one transaction. Returns notes for the summary."""
    notes: dict[str, list[str]] = {"cross_province_links": [], "not_in_files": []}
    conn = get_connection()
    try:
        with conn.transaction():
            for iv in interviews:
                conn.execute(
                    """INSERT INTO informants (informant_id, province_code, district,
                           acquisition_mode, age_bracket, role, consent_form,
                           consent_date, interview_date)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (informant_id) DO UPDATE SET
                           province_code = EXCLUDED.province_code,
                           district = EXCLUDED.district,
                           acquisition_mode = EXCLUDED.acquisition_mode,
                           age_bracket = EXCLUDED.age_bracket, role = EXCLUDED.role,
                           consent_form = EXCLUDED.consent_form,
                           consent_date = EXCLUDED.consent_date,
                           interview_date = EXCLUDED.interview_date""",
                    (iv.informant_id, iv.province_code, iv.district, iv.acquisition_mode,
                     iv.age_bracket, iv.role, iv.consent_form, iv.consent_date,
                     iv.interview_date),
                )
                for dish in iv.dishes:
                    dish_key = iv.dish_key(dish)
                    if dish.official_recipe_id is not None:
                        row = conn.execute(
                            """SELECT r.register, pa.province_code FROM recipes r
                                 LEFT JOIN province_attribution pa USING (recipe_id)
                                WHERE r.recipe_id = %s""",
                            (dish.official_recipe_id,),
                        ).fetchone()
                        if row is None or row[0] != "official":
                            raise InterviewError(
                                f"{dish_key}: official_recipe_id {dish.official_recipe_id} "
                                "is not an official recipe"
                            )
                        if row[1] != iv.province_code:
                            notes["cross_province_links"].append(
                                f"{dish_key} -> recipe {dish.official_recipe_id} ({row[1]})")

                    identity = f"interview:{dish_key}"
                    parsed = {
                        "dish_key": dish_key,
                        "name_th": dish.name_th,
                        "ingredients": [{"name_th": t, "position": n}
                                        for n, t in enumerate(dish.ingredients, 1)],
                    }
                    raw_id = conn.execute(
                        """INSERT INTO raw_recipes (source_id, source_url, raw_path,
                               parsed_json, content_hash)
                           VALUES (%s,%s,%s,%s,%s)
                           ON CONFLICT (source_id, content_hash) DO UPDATE SET
                               raw_path = EXCLUDED.raw_path,
                               parsed_json = EXCLUDED.parsed_json
                           RETURNING raw_id""",
                        (SOURCE_ID, identity, str(directory / f"{iv.informant_id}.toml"),
                         json.dumps(parsed, ensure_ascii=False),
                         hashlib.sha256(identity.encode()).hexdigest()),
                    ).fetchone()[0]  # type: ignore[index]
                    recipe_id = conn.execute(
                        """INSERT INTO recipes (raw_id, name_th, register)
                           VALUES (%s,%s,'domestic')
                           ON CONFLICT (raw_id) DO UPDATE SET name_th = EXCLUDED.name_th
                           RETURNING recipe_id""",
                        (raw_id, dish.name_th),
                    ).fetchone()[0]  # type: ignore[index]
                    conn.execute(
                        """INSERT INTO province_attribution
                               (recipe_id, province_code, tier, confidence, method_note)
                           VALUES (%s,%s,1,'high','cook interviewed in this province')
                           ON CONFLICT (recipe_id) DO UPDATE SET
                               province_code = EXCLUDED.province_code""",
                        (recipe_id, iv.province_code),
                    )
                    conn.execute(
                        """INSERT INTO interview_dishes (dish_key, informant_id, recipe_id,
                               dish_name_th, official_recipe_id, cook_status_verbatim,
                               cook_status_level, distinctiveness_claim, stated_absence,
                               stated_substitutions, differs_from_bangkok,
                               validation_notes)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                           ON CONFLICT (dish_key) DO UPDATE SET
                               recipe_id = EXCLUDED.recipe_id,
                               dish_name_th = EXCLUDED.dish_name_th,
                               official_recipe_id = EXCLUDED.official_recipe_id,
                               cook_status_verbatim = EXCLUDED.cook_status_verbatim,
                               cook_status_level = EXCLUDED.cook_status_level,
                               distinctiveness_claim = EXCLUDED.distinctiveness_claim,
                               stated_absence = EXCLUDED.stated_absence,
                               stated_substitutions = EXCLUDED.stated_substitutions,
                               differs_from_bangkok = EXCLUDED.differs_from_bangkok,
                               validation_notes = EXCLUDED.validation_notes""",
                        (dish_key, iv.informant_id, recipe_id, dish.name_th,
                         dish.official_recipe_id, dish.cook_status_verbatim,
                         dish.cook_status_level, dish.distinctiveness_claim,
                         dish.stated_absence, dish.stated_substitutions,
                         dish.differs_from_bangkok, dish.validation_notes),
                    )

        in_files = {iv.dish_key(d) for iv in interviews for d in iv.dishes}
        notes["not_in_files"] = sorted(
            k for (k,) in conn.execute("SELECT dish_key FROM interview_dishes")
            if k not in in_files
        )
    finally:
        conn.close()
    return notes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", type=Path, default=INTERVIEWS_DIR)
    args = ap.parse_args()
    try:
        interviews = read_all(args.dir)
        notes = load(interviews, args.dir)
    except InterviewError as e:
        print(f"refused — nothing loaded:\n{e}", file=sys.stderr)
        return 1

    n_dishes = sum(len(iv.dishes) for iv in interviews)
    print(f"loaded {len(interviews)} interview(s), {n_dishes} dish(es) from {args.dir}")
    if notes["cross_province_links"]:
        print("official-dish links to another province (allowed, listed): "
              + "; ".join(notes["cross_province_links"]))
    if notes["not_in_files"]:
        print("in interview_dishes but not in the files (not removed): "
              + ", ".join(notes["not_in_files"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
