"""Parse the ``mthai_food`` export (``data/raw/mthai_food/mthai_food_recipes.csv``).

The 2026-10-07 collection wrote one CSV row per recipe post. ``ETHICS.md`` (researcher's
go, 2026-10-12) admits **ingredient lists only**: author names, intro and method prose
are dropped. They are dropped here by never being read. ``KEPT_FIELDS`` is the whole
list of columns this module touches, and ``tests/test_mthai_food.py`` holds it to that.

Every kept text value goes through ``src.ingest.pdpa.redact`` before it reaches a
record, and the per-class counts are kept on the record the way the DCP and Kapook
parsers keep theirs.

**Loading.** HD-40 (decided 2026-11-06) admits MThai to the commercial register. This
module parses and writes nothing; ``scripts/parse_mthai.py --load`` writes.

**Sections.** 7 posts have more than one ingredient section (``n_ingredient_sections``;
the collector's broader ``multi_section`` flag marks 13). Lines are returned in page
order. The researcher applied HD-22's rule to MThai (2026-11-06): only single-section
posts become recipes; the rest are held out, counted (``is_single_section``).
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
               "ingredients", "n_ingredient_sections")


@dataclass
class MThaiRecord:
    record_id: str
    post_id: str
    url: str
    title: str
    published_at: date | None
    tags: list[str]
    ingredient_lines: list[str]
    n_sections: int = 1
    redaction: RedactionReport = field(default_factory=RedactionReport)

    @property
    def is_single_section(self) -> bool:
        """HD-22's rule, applied to MThai by the researcher (2026-11-06): only posts with
        exactly one ingredient section become recipes."""
        return self.n_sections == 1 and bool(self.ingredient_lines) and bool(self.title)


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
        n_sections=int(kept["n_ingredient_sections"] or 1),
        redaction=report,
    )


def payload(record: MThaiRecord) -> dict[str, object]:
    """``raw_recipes.parsed_json``, in the shape the Kapook loader writes (``title_th``,
    ``category_source``, ``sections[].items[]``), so the lexicon worklist and the HD-37
    label rules read both sources the same way. Tags stand in for the site category."""
    return {
        "post_id": record.post_id,
        "title_th": record.title,
        "category_source": " | ".join(record.tags),
        "tags": record.tags,
        "published_at": record.published_at.isoformat() if record.published_at else None,
        "n_sections": record.n_sections,
        "sections": [{"heading": None, "items": record.ingredient_lines}],
    }


def read_csv(path: Path = CSV_PATH) -> list[MThaiRecord]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [parse_row(row) for row in csv.DictReader(f)]
