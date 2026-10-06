"""What a scraper may store about a recipe (docs/scraping_rules.md §4, §5, §7).

`ScrapedRecipe` is the **only** shape a site scraper hands back, and it has a field for
each thing rule 4 allows and nothing else:

- url, title (verbatim), published_at (as shown, else None, never guessed), the site's
  category and tags (verbatim);
- the exact text spans that claim a region or province, with where each was found
  (title, tag, breadcrumb or intro sentence). These are claims copied from the page, not
  attributions (rule 6);
- ingredient lines verbatim (quantity + unit + name as written), in order;
- servings, if shown.

There is no field for method or instruction prose, author names or usernames, profile
links, comments, photos, phone numbers, emails or addresses, so none of them can be
stored by mistake. As a second guard, a single "ingredient line" over
`MAX_LINE_CHARS` characters is refused as probable prose.

`to_parsed_json` is the one door into the database. **Every text value is PDPA-redacted
first** (rule 5), then Thai-normalised (rule 7: NFC plus the sara-am repair). Both the
redacted original and the normalised form are kept. The per-class redaction counts come
back for ``redaction_log``.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field

from src.clean.normalize_th import normalize_thai
from src.ingest.pdpa import RedactionReport, redact

CLAIM_LOCATIONS = ("title", "tag", "breadcrumb", "intro")
MAX_LINE_CHARS = 200
MAX_TITLE_CHARS = 300
SCHEMA = "scraped_recipe/1"


class RecordRejected(ValueError):
    """A record that breaks the storage rules. It is never written."""


@dataclass(frozen=True)
class Claim:
    """An exact text span on the page that claims a region or province, and where."""

    text: str
    location: str  # one of CLAIM_LOCATIONS


@dataclass(frozen=True)
class ScrapedRecipe:
    url: str
    title_th: str
    published_at: datetime.date | None = None
    site_category: str | None = None
    site_tags: list[str] = field(default_factory=list)
    region_claim: Claim | None = None
    province_claim: Claim | None = None
    ingredient_lines: list[str] = field(default_factory=list)
    servings: str | None = None

    def validate(self) -> None:
        problems: list[str] = []
        if not self.title_th.strip():
            problems.append("title_th is empty")
        if len(self.title_th) > MAX_TITLE_CHARS:
            problems.append(f"title_th is {len(self.title_th)} characters")
        for n, line in enumerate(self.ingredient_lines, 1):
            if len(line) > MAX_LINE_CHARS:
                problems.append(f"ingredient line {n} is {len(line)} characters: "
                                "probably method prose, which is never stored")
        for name, claim in (("region_claim", self.region_claim),
                            ("province_claim", self.province_claim)):
            if claim is not None and claim.location not in CLAIM_LOCATIONS:
                problems.append(f"{name}.location must be one of {CLAIM_LOCATIONS}")
        if self.published_at is not None and not isinstance(self.published_at, datetime.date):
            problems.append("published_at must be a date or None")
        if problems:
            raise RecordRejected(f"{self.url}: " + "; ".join(problems))


def _merge(total: RedactionReport, part: RedactionReport) -> None:
    for column in RedactionReport.COLUMNS.values():
        setattr(total, column, getattr(total, column) + getattr(part, column))


def to_parsed_json(
    record: ScrapedRecipe, scraped_at: datetime.datetime
) -> tuple[dict[str, object], RedactionReport]:
    """The record as stored in ``raw_recipes.parsed_json``, redacted then normalised,
    plus the redaction counts. Raises `RecordRejected` if the record breaks the rules."""
    record.validate()
    report = RedactionReport()

    def text(value: str | None) -> dict[str, str] | None:
        if value is None:
            return None
        cleaned, found = redact(value)
        _merge(report, found)
        return {"original": cleaned, "normalised": normalize_thai(cleaned)[0]}

    def claim(c: Claim | None) -> dict[str, object] | None:
        return None if c is None else {"text": text(c.text), "location": c.location}

    lines = [text(line) for line in record.ingredient_lines]
    payload: dict[str, object] = {
        "schema": SCHEMA,
        "url": record.url,
        "title_th": text(record.title_th),
        "published_at": record.published_at.isoformat() if record.published_at else None,
        "scraped_at": scraped_at.isoformat(timespec="seconds"),
        "site_category": text(record.site_category),
        "site_tags": [text(t) for t in record.site_tags],
        "region_claim": claim(record.region_claim),
        "province_claim": claim(record.province_claim),
        "ingredient_lines": lines,
        # The shape the lexicon worklist and canonicalisation read for every source.
        "ingredients": [
            {"name_th": line["normalised"], "position": n}
            for n, line in enumerate(lines, 1) if line
        ],
        "servings": text(record.servings),
    }
    return payload, report
