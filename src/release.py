"""T3.6 / T3.7: build the two release datasets locally. **Dry run only: nothing is
published, pushed or uploaded.**

    uv run python -m src.release            (make release-dry)

Writes into ``data/release/`` (gitignored):

- ``OpenFlavorTH-recipes/``
  - ``recipes.parquet``: one row per recipe.
  - ``fieldwork.csv``, ``cook_along_log.csv``, ``stated_absences.csv``.
- ``OpenFlavorTH-lexicon/ingredients_lexicon.csv``.
- ``DRYRUN.md``: the validation report, with counts, schema checks, the PDPA scan of
  every file, and what still blocks a real release.

**What is left out, and why** (existing decisions; none made here):
- **``dcp_food`` (the official register):** HD-3 is open. ETHICS.md says the source is
  "reference layer only, excluded from any public release". Its recipes are counted in
  the report, never written. Lexicon variants observed only in DCP text are withheld for
  the same reason.
- **``sanook_food``:** a no-go (ETHICS.md, 2026-10-12). It is never loaded, so it never
  appears.
- **``endangerment_comparison.csv``:** needs RQ5 (T4.4) and DCP's endangerment field.
  Not built; listed as a blocker.
- **Prose and personal data:** there is no dish name, raw ingredient text, method,
  ``conflict_note`` or free-text note. Fieldwork free text goes through ``redact``.
  Every string cell of every file is scanned with ``find_leaks``.

**recipes.parquet columns** (T3.6 order):
- ``recipe_id``, ``register``, ``ingredients`` (canonical ids), ``province_code``,
  ``district``, ``region``, ``dish_category``, ``endangerment``,
  ``acquisition_modes``;
- ``source_domain``, ``extraction_method``, ``label_rule``, ``label_confidence``,
  ``published_at``, ``collection_date``.

``district``, ``dish_category``, ``endangerment`` and ``acquisition_modes`` come from DCP
or from HD-9 / HD-15 work not done yet, so they are empty for every released row today.
The columns exist so the schema is fixed.
"""

from __future__ import annotations

import argparse
import csv
import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pandas as pd

from src.config import DATA_DIR
from src.db import get_connection
from src.ingest.pdpa import find_leaks, redact

RELEASE_DIR = DATA_DIR / "release"
RECIPES_DIR = "OpenFlavorTH-recipes"
LEXICON_DIR = "OpenFlavorTH-lexicon"
# HD-3 (open): reference-only, excluded from any public release.
WITHHELD_SOURCES = frozenset({"dcp_food"})

RECIPE_COLUMNS = ("recipe_id", "register", "ingredients", "province_code", "district",
                  "region", "dish_category", "endangerment", "acquisition_modes",
                  "source_domain", "extraction_method", "label_rule", "label_confidence",
                  "published_at", "collection_date")
LEXICON_COLUMNS = ("canonical_id", "name_th", "name_en", "category", "is_fermented",
                   "variants", "notes")
FIELDWORK_COLUMNS = ("informant_id", "province_code", "district", "role", "age_bracket",
                     "acquisition_mode", "dish_key", "stated_substitutions")
COOK_ALONG_COLUMNS = ("recipe_id", "cook_date", "fidelity_quantities", "fidelity_order",
                      "fidelity_technique", "fidelity_specificity", "fidelity_completeness",
                      "result_recognizable")
ABSENCE_COLUMNS = ("informant_id", "province_code", "dish_key", "stated_absence")

RECIPES_SQL = """
SELECT r.recipe_id, r.register, rr.source_id, s.base_url, r.extraction_method,
       r.endangerment, rr.published_at, r.collection_date,
       pa.province_code, pa.region, pa.method_note, pa.confidence
  FROM recipes r
  JOIN raw_recipes rr USING (raw_id)
  JOIN sources s ON s.source_id = rr.source_id
  LEFT JOIN province_attribution pa ON pa.recipe_id = r.recipe_id
 ORDER BY r.recipe_id
"""
INGREDIENTS_SQL = """
SELECT recipe_id, canonical_id, acquisition_modes FROM recipe_ingredients
 ORDER BY recipe_id, canonical_id
"""


@dataclass
class Report:
    files: dict[str, int] = field(default_factory=dict)        # file -> rows
    withheld: dict[str, int] = field(default_factory=dict)     # what and how many
    leaks: list[str] = field(default_factory=list)
    checks: list[tuple[str, bool, str]] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)


def _domain(url: str | None) -> str | None:
    return urlparse(url).hostname if url else None


def recipes_frame(conn: Any, report: Report) -> pd.DataFrame:
    rows = conn.execute(RECIPES_SQL).fetchall()
    ingredients: dict[int, list[str]] = {}
    for rid, cid, _modes in conn.execute(INGREDIENTS_SQL).fetchall():
        ingredients.setdefault(rid, []).append(cid)
    out, withheld = [], 0
    for (rid, register, source, base_url, method, endangerment, published, collected,
         province, region, note, confidence) in rows:
        if source in WITHHELD_SOURCES:
            withheld += 1
            continue
        out.append({
            "recipe_id": rid, "register": register, "ingredients": ingredients.get(rid, []),
            "province_code": province, "district": None, "region": region,
            "dish_category": None, "endangerment": endangerment, "acquisition_modes": None,
            "source_domain": _domain(base_url), "extraction_method": method,
            "label_rule": note, "label_confidence": confidence,
            "published_at": published, "collection_date": collected,
        })
    report.withheld["recipes from dcp_food (HD-3)"] = withheld
    return pd.DataFrame(out, columns=list(RECIPE_COLUMNS))


def lexicon_frame(conn: Any, report: Report) -> pd.DataFrame:
    """One row per entry. Variants: aliases whose normalised key (``lexicon.key``, as
    ``canonicalise`` matches) occurs in a released source's ingredient lines. An alias
    seen only in DCP text, or in no loaded line, is withheld (HD-3: nothing DCP-derived
    goes out, and an unseen alias cannot be shown not to be)."""
    from scripts.lexicon_worklist import QUERY
    from src.clean.lexicon import key
    released: set[str] = set()
    for source, _reg, _rid, raw in conn.execute(QUERY).fetchall():
        if raw and source not in WITHHELD_SOURCES:
            released.add(key(raw))
    aliases: dict[str, list[str]] = {}
    withheld = 0
    for alias, cid in conn.execute(
            "SELECT alias, canonical_id FROM ingredient_aliases ORDER BY alias").fetchall():
        if key(alias) not in released:
            withheld += 1
            continue
        aliases.setdefault(cid, []).append(alias)
    report.withheld["lexicon variants not seen in a released source (HD-3)"] = withheld
    rows = []
    for cid, th, en, cat, ferm, regional, decision in conn.execute(
            """SELECT canonical_id, name_th, name_en, category, is_fermented,
                      regional_note, decision_note
                 FROM canonical_ingredients ORDER BY canonical_id""").fetchall():
        notes = " | ".join(n for n in (regional, decision) if n)
        rows.append({"canonical_id": cid, "name_th": th, "name_en": en, "category": cat,
                     "is_fermented": ferm, "variants": " | ".join(aliases.get(cid, [])),
                     "notes": notes})
    return pd.DataFrame(rows, columns=list(LEXICON_COLUMNS))


def _redacted(text: str | None) -> str | None:
    return redact(text)[0] if text else text


def fieldwork_frames(conn: Any) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    fw = conn.execute(
        """SELECT i.informant_id, i.province_code, i.district, i.role, i.age_bracket,
                  i.acquisition_mode, d.dish_key, d.stated_substitutions, d.stated_absence
             FROM informants i LEFT JOIN interview_dishes d USING (informant_id)
            ORDER BY 1, 7""").fetchall()
    fieldwork = pd.DataFrame([r[:7] + (_redacted(r[7]),) for r in fw],
                             columns=list(FIELDWORK_COLUMNS))
    absences = pd.DataFrame([(r[0], r[1], r[6], _redacted(r[8])) for r in fw if r[8]],
                            columns=list(ABSENCE_COLUMNS))
    cook = pd.DataFrame(conn.execute(
        f"SELECT {', '.join(COOK_ALONG_COLUMNS)} FROM cook_along_log ORDER BY recipe_id"
    ).fetchall(), columns=list(COOK_ALONG_COLUMNS))
    return fieldwork, cook, absences


def scan(name: str, frame: pd.DataFrame, report: Report) -> None:
    """find_leaks on every string cell (list cells element by element)."""
    for col in frame.columns:
        for value in frame[col]:
            items = value if isinstance(value, list) else [value]
            for item in items:
                if isinstance(item, str) and (hits := find_leaks(item)):
                    report.leaks.append(f"{name}.{col}: {sorted(hits)}")


def build(out_dir: Path = RELEASE_DIR) -> Report:
    report = Report()
    conn = get_connection()
    try:
        recipes = recipes_frame(conn, report)
        lexicon = lexicon_frame(conn, report)
        fieldwork, cook, absences = fieldwork_frames(conn)
    finally:
        conn.close()
    rdir, ldir = out_dir / RECIPES_DIR, out_dir / LEXICON_DIR
    rdir.mkdir(parents=True, exist_ok=True)
    ldir.mkdir(parents=True, exist_ok=True)
    recipes.to_parquet(rdir / "recipes.parquet", index=False)
    for name, frame in (("fieldwork.csv", fieldwork), ("cook_along_log.csv", cook),
                        ("stated_absences.csv", absences)):
        frame.to_csv(rdir / name, index=False, encoding="utf-8")
    lexicon.to_csv(ldir / "ingredients_lexicon.csv", index=False, encoding="utf-8",
                   quoting=csv.QUOTE_MINIMAL)
    for name, frame in (("recipes.parquet", recipes), ("ingredients_lexicon.csv", lexicon),
                        ("fieldwork.csv", fieldwork), ("cook_along_log.csv", cook),
                        ("stated_absences.csv", absences)):
        report.files[name] = len(frame)
        scan(name, frame, report)
    # T3.7's done-when: schema, 100% glossed.
    glossed = lexicon["name_en"].fillna("").str.strip().ne("")
    report.checks += [
        ("recipes.parquet columns = T3.6 schema", list(recipes.columns) == list(RECIPE_COLUMNS),
         ", ".join(RECIPE_COLUMNS)),
        ("no withheld source in recipes.parquet",
         not set(recipes["source_domain"].dropna()) & {"food.culture.go.th"}, "dcp_food absent"),
        ("lexicon 100% glossed", bool(glossed.all()), f"{int(glossed.sum())} of {len(lexicon)}"),
        ("lexicon columns = T3.7 schema", list(lexicon.columns) == list(LEXICON_COLUMNS),
         ", ".join(LEXICON_COLUMNS)),
        ("PDPA scan of every file", not report.leaks, f"{len(report.leaks)} finding(s)"),
    ]
    report.blockers = [
        "HD-3 (dcp_food) open: the official register, endangerment, district and "
        "acquisition mode are withheld",
        "HD-20 final release review (the researcher reads the full export) not done",
        "T3.8 dataset cards, licence files and loading script not written",
        "endangerment_comparison.csv needs RQ5 (T4.4); not built",
        "built from the live database, not the frozen one (T2.10, 13 Dec)",
    ]
    (out_dir / "DRYRUN.md").write_text(render(report), encoding="utf-8")
    return report


def render(report: Report) -> str:
    day = datetime.date.today().isoformat()
    lines = [f"# Release dry run — {day}", "",
             "Built by `make release-dry` (`src/release.py`). **Not published.** Local only.",
             "", "## Files", "", "| file | rows |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in report.files.items()]
    lines += ["", "## Withheld", "", "| what | rows |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in report.withheld.items()]
    lines += ["", "## Checks", ""]
    lines += [f"- [{'ok' if ok else 'FAIL'}] {name}: {detail}"
              for name, ok, detail in report.checks]
    if report.leaks:
        lines += ["", "## PDPA findings", ""] + [f"- {x}" for x in report.leaks]
    lines += ["", "## Blocks a real release", ""] + [f"- {b}" for b in report.blockers]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=RELEASE_DIR)
    args = ap.parse_args(argv)
    report = build(args.out)
    print(render(report))
    return 0 if all(ok for _, ok, _ in report.checks) else 2


if __name__ == "__main__":
    raise SystemExit(main())
