"""Parse the two state-promotional exports: ``tat_food`` and ``m_culture`` (HD-39).

**HD-39, decided 2026-11-06: B.** Both sources form a **state-promotional** register, kept
apart from the DCP official register. Only rows with ingredient text become recipes. Rows
that only name a dish go to a separate dish-name list (``state_dish_names``, migration
032) for RQ3 / RQ5 matching and never become recipes. ``ETHICS.md``: researcher's go for
both (2026-10-12; m-culture with personal data stripped at parse time).

**Fields read** (``TAT_FIELDS``, ``MC_FIELDS``) are the only columns this module touches.
Never read, so never stored:
- TAT: ``venue`` (restaurant or person names) and the collector's ``note``.
- m-culture: page and PDF text, ``districts``, ``office``, attachments.

Every kept text value goes through ``src.ingest.pdpa.redact``, and the counts are kept per
record as the other parsers do.

**Ingredient lines.**
- TAT: the collector separated ingredients with ``;``, so each is one line.
- m-culture: ``ingredient_lines`` is free page text. How it is cut into lines is
  ``MC_SPLIT`` (see ``split_mc``), a parsing choice the researcher makes. This module
  measures every option and applies the one set.

**Province.** Each row carries the province the article (TAT) or the publishing office
(m-culture) is about. It is stored as ``listed_province_th`` in the payload. Whether it
becomes a ``province_attribution`` row, and at what confidence, is a separate decision;
this module writes none.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from src.config import RAW_DIR
from src.ingest.pdpa import RedactionReport, find_leaks, redact

TAT = "tat_food"
MC = "m_culture"
TAT_CSV = RAW_DIR / TAT / "tat_food.csv"
MC_CSV = RAW_DIR / MC / "dishes.csv"

TAT_FIELDS = ("record_id", "province_th", "province_en", "dish_th", "dish_en", "dish_type",
              "ingredients_listed", "list_kind", "campaign", "page_date", "source_url")
MC_FIELDS = ("province_th", "site_id", "item_id", "page_url", "dish_name", "page_date",
             "ingredient_lines", "duplicate_of")

Split = Literal["newline", "delimiters", "delimiters_and_spaces"]
SPLITS: tuple[Split, ...] = ("newline", "delimiters", "delimiters_and_spaces")
# Researcher's choice (asked 2026-11-06). None = not decided: loading refuses.
MC_SPLIT: Split | None = None

_DELIMS = re.compile(r"[,;\n、]+|\s-\s")


@dataclass
class StateRecord:
    source_id: str
    key: str                       # stable per row: TAT record_id; m-culture site:item
    url: str
    listed_province_th: str
    dish_th: str
    dish_en: str
    published_at: date | None
    ingredient_lines: list[str]
    list_kind: str | None = None   # TAT only
    campaign: str | None = None    # TAT only
    dish_type: str | None = None   # TAT only (collector's label)
    duplicate_of: str | None = None  # m-culture collector's flag (HD-41: review, not drop)
    redaction: RedactionReport = field(default_factory=RedactionReport)

    @property
    def has_ingredients(self) -> bool:
        return bool(self.ingredient_lines)

    @property
    def name(self) -> str:
        """Display name: the Thai name, else TAT's English name (60 TAT rows have no Thai
        name); the payload keeps both."""
        return self.dish_th or self.dish_en


def _clean(text: str, report: RedactionReport) -> str:
    cleaned, found = redact(unicodedata.normalize("NFC", text or "").strip())
    for column in RedactionReport.COLUMNS.values():
        setattr(report, column, getattr(report, column) + getattr(found, column))
    return " ".join(cleaned.split())


def _clean_url(url: str, report: RedactionReport) -> str:
    """A URL keeps its text: ``redact`` would blank every URL as a media link. Only the
    substrings ``find_leaks`` flags (the database scan's own check) are replaced, and
    counted as addresses. Measured 2026-11-06: one TAT article slug names a road
    (ถนนสิโรรส), in 12 rows."""
    url = unicodedata.normalize("NFC", (url or "").strip())
    for found in find_leaks(url).values():
        for text in found:
            if text in url:
                url = url.replace(text, "[REDACTED]")
                report.n_addresses += 1
    return url


def _date(value: str) -> date | None:
    try:
        return datetime.fromisoformat((value or "").strip()[:10]).date()
    except ValueError:
        return None


def split_mc(text: str, how: Split) -> list[str]:
    """m-culture's free ingredient text → lines, by `how`:

    ``newline``
        One line per line of page text, as published (HD-6 Q6's "raw strings").
    ``delimiters``
        Also cut at ``,``, ``;``, ``、`` and spaced hyphens.
    ``delimiters_and_spaces``
        Also cut at every space. Thai separates list items with spaces, but some names
        contain one (``ผักชี ลาว``).
    """
    if how == "newline":
        parts = text.splitlines()
    elif how == "delimiters":
        parts = _DELIMS.split(text)
    else:
        parts = [p for chunk in _DELIMS.split(text) for p in chunk.split()]
    return [p.strip() for p in parts if p.strip()]


def parse_tat(row: dict[str, str]) -> StateRecord:
    report = RedactionReport()
    kept = {k: row.get(k) or "" for k in TAT_FIELDS}
    lines = [x for x in (_clean(p, report) for p in kept["ingredients_listed"].split(";")) if x]
    return StateRecord(
        source_id=TAT, key=kept["record_id"].strip(), url=_clean_url(kept["source_url"], report),
        listed_province_th=kept["province_th"].strip(),
        dish_th=_clean(kept["dish_th"], report), dish_en=_clean(kept["dish_en"], report),
        published_at=_date(kept["page_date"]), ingredient_lines=lines,
        list_kind=kept["list_kind"].strip() or None,
        campaign=_clean(kept["campaign"], report) or None,
        dish_type=kept["dish_type"].strip() or None, redaction=report)


def parse_mc(row: dict[str, str], how: Split) -> StateRecord:
    report = RedactionReport()
    kept = {k: row.get(k) or "" for k in MC_FIELDS}
    # Redact the whole text first, then split: splitting first cuts phone numbers and
    # names into pieces redact() no longer recognises (measured 2026-11-06: 212 hits whole,
    # 145 after splitting at spaces).
    whole, found = redact(unicodedata.normalize("NFC", kept["ingredient_lines"]))
    for column in RedactionReport.COLUMNS.values():
        setattr(report, column, getattr(report, column) + getattr(found, column))
    lines = [" ".join(p.split()) for p in split_mc(whole, how)]
    lines = [x for x in lines if x]
    return StateRecord(
        source_id=MC, key=f"{kept['site_id'].strip()}:{kept['item_id'].strip()}",
        url=_clean_url(kept["page_url"], report), listed_province_th=kept["province_th"].strip(),
        dish_th=_clean(kept["dish_name"], report), dish_en="",
        published_at=_date(kept["page_date"]), ingredient_lines=lines,
        duplicate_of=kept["duplicate_of"].strip() or None, redaction=report)


def read_tat(path: Path = TAT_CSV) -> list[StateRecord]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [parse_tat(r) for r in csv.DictReader(f)]


def read_mc(how: Split, path: Path = MC_CSV) -> list[StateRecord]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [parse_mc(r, how) for r in csv.DictReader(f)]


def payload(rec: StateRecord) -> dict[str, object]:
    """``raw_recipes.parsed_json`` in the Kapook/MThai shape (``title_th``,
    ``sections[].items[]``), so the worklist and canonicalise read it unchanged."""
    return {
        "key": rec.key, "title_th": rec.name, "dish_th": rec.dish_th, "dish_en": rec.dish_en,
        "listed_province_th": rec.listed_province_th, "list_kind": rec.list_kind,
        "campaign": rec.campaign, "dish_type": rec.dish_type,
        "duplicate_of": rec.duplicate_of,
        "published_at": rec.published_at.isoformat() if rec.published_at else None,
        "sections": [{"heading": None, "items": rec.ingredient_lines}],
    }
