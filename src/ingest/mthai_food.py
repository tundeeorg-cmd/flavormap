"""Parse the ``mthai_food`` export (``data/raw/mthai_food/mthai_food_recipes.csv``).

The 2026-10-07 collection wrote one CSV row per recipe post. ``ETHICS.md`` (researcher's
go, 2026-10-12) admits **ingredient lists only**: author names, intro and method prose
are dropped. They are dropped here by never being read. ``KEPT_FIELDS`` is the whole
list of columns this module touches, and ``tests/test_mthai_food.py`` holds it to that.

Every kept text value goes through ``src.ingest.pdpa.redact`` before it reaches a
record, and the per-class counts are kept on the record the way the DCP and Kapook
parsers keep theirs.

**Not loaded.** Whether MThai joins the commercial register is HD-40 (open). This module
parses; ``scripts/parse_mthai.py`` reports on a dry run and writes nothing to the
database.

**Sections.** 13 posts carry more than one ingredient section (the collector's
``multi_section`` flag). Lines are returned in page order with no attempt to tell a
section heading from an ingredient, as the Kapook parser does; how a post maps to rows
in ``recipes`` is HD-22's kind of question, not a parsing detail.
"""

from __future__ import annotations

import csv
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from src.config import RAW_DIR
from src.ingest.pdpa import RedactionReport, redact

SOURCE_ID = "mthai_food"
CSV_PATH = RAW_DIR / SOURCE_ID / "mthai_food_recipes.csv"

# The only columns ever read. Not here, so never read: author, intro, method,
# credited_source, and the collector's bookkeeping columns.
KEPT_FIELDS = ("record_id", "post_id", "url", "title", "publish_date", "tags",
               "ingredients")


@dataclass
class MThaiRecord:
    record_id: str
    post_id: str
    url: str
    title: str
    published_at: date | None
    tags: list[str]
    ingredient_lines: list[str]
    redaction: RedactionReport = field(default_factory=RedactionReport)


def _clean(text: str, report: RedactionReport) -> str:
    cleaned, found = redact(unicodedata.normalize("NFC", text).strip())
    for column in RedactionReport.COLUMNS.values():
        setattr(report, column, getattr(report, column) + getattr(found, column))
    return cleaned


def _published(value: str) -> date | None:
    try:
        return datetime.fromisoformat(value.strip()).date()
    except ValueError:
        return None


def parse_row(row: dict[str, str]) -> MThaiRecord:
    """One export row → one record, holding only ``KEPT_FIELDS``, redacted."""
    report = RedactionReport()
    kept = {k: row.get(k) or "" for k in KEPT_FIELDS}
    tags = [t for t in (_clean(t, report) for t in kept["tags"].split("|")) if t]
    lines = [ln for ln in (_clean(x, report) for x in kept["ingredients"].splitlines())
             if ln]
    return MThaiRecord(
        record_id=kept["record_id"].strip(),
        post_id=kept["post_id"].strip(),
        url=kept["url"].strip(),
        title=_clean(kept["title"], report),
        published_at=_published(kept["publish_date"]),
        tags=tags,
        ingredient_lines=lines,
        redaction=report,
    )


def read_csv(path: Path = CSV_PATH) -> list[MThaiRecord]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [parse_row(row) for row in csv.DictReader(f)]
