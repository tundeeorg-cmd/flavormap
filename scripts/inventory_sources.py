"""T1.13a: read-only inventory of the four folders collected on 6–7 Oct 2026.

    uv run python -m scripts.inventory_sources

For ``sanook_food``, ``mthai_food``, ``tat_food`` and ``m_culture`` (TIMELINE v3 §6.3 and
`docs/SCRAPER_PROMPTS.md` Prompt P, stage 1), reports per source: files by type, whether
a fetch manifest exists, the date range, pages against records, field fill rates, and
whether personal data is present. Writes ``data/coverage/sources_YYYYMMDD.md``.

**Read-only, and nothing personal is printed.** Nothing under ``data/raw/`` is changed and
nothing is fetched. Personal data is reported as **counts by class only**
(`src.ingest.pdpa.find_leaks`, plus a LINE-ID pattern and named author columns), never as
values. The examples for ``tat_food`` and ``m_culture`` show a dish name and its province
only, and only when both pass the leak scan.

These folders were produced by a separate collecting session as **CSV exports, not cached
pages**, so "pages" means distinct source URLs or article IDs as those exports record
them. Where a province or region column exists, the report says whether it is a claim
quoted from the text or a label the collecting session assigned (from the publishing
office or article). No register, label or decision is made here.
"""

from __future__ import annotations

import argparse
import datetime
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from src.config import DATA_DIR, RAW_DIR
from src.ingest.pdpa import find_leaks

OUT_DIR = DATA_DIR / "coverage"
# A LINE handle written as @name. The lookbehind keeps the @ inside an email address out.
LINE_ID = re.compile(r"(?i)line\s*id|ไลน์\s*ไอดี|ไอดีไลน์|ไลน์\s*[:：]|(?<![\w.])@\w{3,}")
MANIFEST_FIELDS = ("url", "fetched_at", "http_status", "hash")


@dataclass(frozen=True)
class Spec:
    slug: str
    table: str                       # the main CSV, relative to the source folder
    page: str                        # column identifying a source page
    record_unit: str                 # what one row is
    url: str | None
    fetched_at: str | None
    http_status: str | None
    hash: str | None
    fields: dict[str, str | None]    # report field -> column (None: not captured)
    field_notes: dict[str, str] = field(default_factory=dict)
    author_columns: tuple[str, ...] = ()
    never_load: tuple[str, ...] = ()  # columns the scraping rules forbid storing
    examples: tuple[str, str] | None = None  # (dish column, province column)


FIELDS = ("title", "published_at", "category_tags", "region_claim", "province_claim",
          "ingredient_lines", "servings")

SPECS = (
    Spec("sanook_food", "sanook_food_recipes.csv", page="article_id",
         record_unit="one recipe (articles split by recipe_index_in_article)",
         url="url", fetched_at=None, http_status=None, hash=None,
         fields={"title": "recipe_title", "published_at": "publish_date",
                 "category_tags": "tags", "region_claim": "region_claim",
                 "province_claim": "province_claim", "ingredient_lines": "ingredient_lines",
                 "servings": None},
         field_notes={"region_claim": "quoted from the article (claim_evidence)",
                      "province_claim": "quoted from the article (claim_evidence)"}),
    Spec("mthai_food", "mthai_food_recipes.csv", page="post_id",
         record_unit="one recipe post",
         url="url", fetched_at="scraped_at", http_status=None, hash=None,
         fields={"title": "title", "published_at": "publish_date", "category_tags": "tags",
                 "region_claim": None, "province_claim": None,
                 "ingredient_lines": "ingredients", "servings": None},
         field_notes={"region_claim": "no field; title and tags would have to be read "
                                      "(T1.13)",
                      "province_claim": "no field; as above"},
         author_columns=("author",), never_load=("author", "intro", "method")),
    Spec("tat_food", "tat_food.csv", page="source_url",
         record_unit="one dish x venue x article",
         url="source_url", fetched_at="captured_on", http_status=None, hash=None,
         fields={"title": "dish_th", "published_at": "page_date",
                 "category_tags": "list_kind", "region_claim": "region",
                 "province_claim": "province_th", "ingredient_lines": "ingredients_listed",
                 "servings": None},
         field_notes={"region_claim": "assigned by the collecting session, not quoted",
                      "province_claim": "the province the TAT article is about, "
                                        "assigned by the collecting session"},
         examples=("dish_th", "province_th")),
    Spec("m_culture", "dishes.csv", page="page_url",
         record_unit="one dish page on a provincial culture-office site",
         url="page_url", fetched_at=None, http_status=None, hash=None,
         fields={"title": "dish_name", "published_at": "page_date",
                 "category_tags": "menu_name", "region_claim": "region",
                 "province_claim": "province_th", "ingredient_lines": "ingredient_lines",
                 "servings": None},
         field_notes={"region_claim": "assigned from the office's province",
                      "province_claim": "the publishing office's province, not a claim "
                                        "in the text"},
         examples=("dish_name", "province_th")),
)


def filled(series: pd.Series) -> int:
    return int(series.fillna("").astype(str).str.strip().ne("").sum())


def leak_counts(frame: pd.DataFrame) -> Counter[str]:
    """Rows with at least one hit, per personal-data class, over every text column."""
    counts: Counter[str] = Counter()
    for _, row in frame.iterrows():
        classes: set[str] = set()
        for value in row.values:
            if isinstance(value, str) and value:
                classes |= set(find_leaks(value))
                if LINE_ID.search(value):
                    classes.add("line_id")
        counts.update(classes)
    return counts


def file_leak_counts(paths: list[Path]) -> tuple[int, Counter[str]]:
    """(files with any hit, files per class) over plain-text files."""
    per_class: Counter[str] = Counter()
    hit = 0
    for path in paths:
        classes = set(find_leaks(path.read_text(encoding="utf-8", errors="replace")))
        if classes:
            hit += 1
            per_class.update(classes)
    return hit, per_class


def date_range(series: pd.Series) -> str:
    dates = pd.to_datetime(series, errors="coerce", utc=True).dropna()
    if dates.empty:
        return "none parseable"
    return f"{dates.min():%Y-%m-%d} to {dates.max():%Y-%m-%d} ({len(dates)} parseable)"


def section(spec: Spec, folder: Path) -> list[str]:
    files = Counter(p.suffix.lstrip(".") or "(none)" for p in folder.rglob("*") if p.is_file())
    frame = pd.read_csv(folder / spec.table, encoding="utf-8-sig", dtype=str)
    n = len(frame)
    out = [f"## `{spec.slug}`", ""]
    out.append(f"- **Files:** {sum(files.values())} ("
               + ", ".join(f"{k} {v}" for k, v in files.most_common()) + ")")
    manifest = {"url": spec.url, "fetched_at": spec.fetched_at,
                "http_status": spec.http_status, "hash": spec.hash}
    have = [k for k in MANIFEST_FIELDS if manifest[k]]
    missing = [k for k in MANIFEST_FIELDS if not manifest[k]]
    out.append(f"- **Fetch manifest:** none as a file. The export carries "
               f"{', '.join(have) or 'none'} per row; missing: {', '.join(missing)}. "
               "No cached pages exist to build one from.")
    published = spec.fields["published_at"]
    out.append("- **Date range** (`" + str(published) + "`): "
               + (date_range(frame[published]) if published else "not captured"))
    out.append(f"- **Records:** {n} rows, each {spec.record_unit}; "
               f"**{frame[spec.page].nunique()} distinct pages** (`{spec.page}`)")
    out += ["", "| Field | Column | Filled | Note |", "|---|---|---:|---|"]
    for name in FIELDS:
        col = spec.fields[name]
        note = spec.field_notes.get(name, "")
        cell = f"{filled(frame[col])} of {n}" if col else "not captured"
        out.append(f"| {name} | {f'`{col}`' if col else '—'} | {cell} | {note} |")

    leaks = leak_counts(frame)
    out += ["", "**Personal data in the export** (rows with at least one hit; counts only):",
            ""]
    out.append("- " + (", ".join(f"{k} {v}" for k, v in sorted(leaks.items()))
                       if leaks else "no pattern hits"))
    for col in spec.author_columns:
        out.append(f"- `{col}` column filled in {filled(frame[col])} of {n} rows "
                   "(author names: never loaded)")
    if spec.never_load:
        out.append("- Columns the scraping rules forbid storing, present in the raw export: "
                   + ", ".join(f"`{c}`" for c in spec.never_load)
                   + ". Raw files stay local; a loader must drop them.")
    if spec.slug == "m_culture":
        txt = sorted(folder.rglob("*.txt"))
        pages = [p for p in txt if "pdf_text" not in p.parts]
        pdfs = [p for p in txt if "pdf_text" in p.parts]
        for label, group in (("page text", pages), ("PDF text", pdfs)):
            hit, per = file_leak_counts(group)
            out.append(f"- Raw {label} files: {hit} of {len(group)} contain personal data ("
                       + ", ".join(f"{k} {v}" for k, v in sorted(per.items())) + ")")
        if "duplicate_of" in frame:
            out.append(f"- Rows the collecting session flagged as duplicates: "
                       f"{filled(frame['duplicate_of'])}")

    if spec.examples:
        dish, prov = spec.examples
        ingr = spec.fields["ingredient_lines"]
        assert ingr is not None
        with_ingr = filled(frame[ingr])
        out += ["", f"**Recipes or dish lists?** {with_ingr} of {n} rows "
                f"({with_ingr / n:.0%}) carry any ingredient text; the rest name a dish only.",
                "", "Five examples (dish and province only, one per province; rows whose "
                "text passes the personal-data scan):", ""]
        shown = 0
        seen: set[str] = set()
        for _, row in frame.iterrows():
            d, p = str(row.get(dish) or ""), str(row.get(prov) or "")
            if p in seen:
                continue
            if d and p and not find_leaks(d) and not find_leaks(p) and not LINE_ID.search(d):
                seen.add(p)
                has = "with ingredient text" if str(row.get(ingr) or "").strip() else "dish only"
                out.append(f"- {d} ({p}): {has}")
                shown += 1
                if shown == 5:
                    break
    out.append("")
    return out


def build(raw_dir: Path = RAW_DIR) -> str:
    today = datetime.date.today()
    lines = [f"# New-source inventory, {today:%Y-%m-%d} (T1.13a)", "",
             "Generated by `scripts/inventory_sources.py`, read-only. Counts of personal "
             "data are by class; no value is shown. Nothing here assigns a register, a "
             "label or a decision.", ""]
    for spec in SPECS:
        lines += section(spec, raw_dir / spec.slug)
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = ap.parse_args()
    report = build()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    path = args.out_dir / f"sources_{datetime.date.today():%Y%m%d}.md"
    path.write_text(report + "\n", encoding="utf-8")
    print(report)
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
