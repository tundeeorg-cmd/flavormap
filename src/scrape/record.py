"""Rules 4–7 (`docs/scraping_rules.md`) — what a scraped recipe may carry, enforced.

A site parser returns a :class:`ScrapedRecipe`: the only shape a scraper can hand to the
database. It has a field for everything rule 4 allows and **no field** for anything it
forbids — there is nowhere to put method prose, an author, a comment, a photo, a
register, a province label or a dish category. :func:`finalise` then:

1. **PDPA (rule 5).** Runs :func:`src.ingest.pdpa.redact` over every string, and refuses
   the record if :func:`~src.ingest.pdpa.find_leaks` still finds anything afterwards.
2. **Thai text (rule 7).** Keeps each string as found (after redaction) and adds an
   ``_norm`` twin: NFC plus the project's sara-am / PUA repair
   (:func:`src.clean.normalize_th.normalize_thai`). The original is never overwritten.
3. **Shape (rules 4 and 6).** Refuses links other than the page URL, image references,
   over-long lines (prose), and site claims whose text cannot be found where they say
   they were found.

The resulting payload is what :func:`insert_raw_recipe` writes to
``raw_recipes.parsed_json`` — the only table this package writes. It never touches
``recipes`` (so ``method_text`` stays empty), ``province_attribution`` or
``dish_categories``: those are decisions, and rule 6 leaves them to the loaders that
implement a decided HD gate.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Literal

from src.clean.normalize_th import normalize_thai
from src.ingest.pdpa import RedactionReport, find_leaks, redact

ClaimLocation = Literal["title", "tag", "category", "breadcrumb", "intro"]
CLAIM_LOCATIONS: tuple[str, ...] = ("title", "tag", "category", "breadcrumb", "intro")

# An ingredient line, not a paragraph — the same cap src/ingest/kapook_page.py measured
# on the kapook corpus. A claim is a span, not a passage.
MAX_LINE_CHARS = 150
MAX_CLAIM_CHARS = 200
MAX_TITLE_CHARS = 200
MAX_TAGS = 50

_LINK = re.compile(r"https?://|www\.", re.I)
_IMAGE = re.compile(r"\.(?:jpe?g|png|gif|webp|heic|avif)\b", re.I)


class RecordRefused(ValueError):
    """This record may not be stored. The message says which rule refused it."""


@dataclass(frozen=True)
class Claim:
    """A site's own claim of a region or province: the exact span, and where it was."""

    text: str
    location: ClaimLocation


@dataclass
class ScrapedRecipe:
    """Everything rule 4 allows from one recipe page, verbatim, and nothing else."""

    url: str
    title_th: str | None
    scraped_at: datetime
    published_at: date | None = None  # only if the page shows it; never guessed
    site_category: str | None = None
    site_tags: list[str] = field(default_factory=list)
    region_claim: Claim | None = None
    province_claim: Claim | None = None
    ingredient_lines: list[str] = field(default_factory=list)  # in page order
    servings: str | None = None


# The complete list of what may reach raw_recipes.parsed_json from a scraper. A key not
# on it — "method", "author", "register", "province" — is refused, so widening what is
# stored means editing this line and docs/scraping_rules.md together, in one reviewed diff.
ALLOWED_PAYLOAD_KEYS = frozenset({
    "url", "title_th", "title_th_norm", "published_at", "scraped_at",
    "site_category", "site_category_norm", "site_tags", "site_tags_norm",
    "region_claim", "province_claim", "ingredient_lines", "ingredient_lines_norm",
    "servings", "servings_norm",
})


@dataclass
class Finalised:
    payload: dict[str, Any]
    redaction: RedactionReport
    content_hash: str


def _merge(into: RedactionReport, other: RedactionReport) -> None:
    for name, value in vars(other).items():
        if isinstance(value, int):
            setattr(into, name, getattr(into, name) + value)


def _norm(text: str) -> str:
    repaired, _ = normalize_thai(unicodedata.normalize("NFC", text))
    return repaired


def _check_text(where: str, text: str, limit: int, errors: list[str]) -> None:
    if _LINK.search(text):
        errors.append(f"{where}: contains a link (rule 4 — no profile or media links)")
    if _IMAGE.search(text):
        errors.append(f"{where}: references an image file (rule 4 — no photos)")
    if len(text) > limit:
        errors.append(f"{where}: {len(text)} chars > {limit} — prose, not a field (rule 4)")


def _claim_found(claim: Claim, rec: ScrapedRecipe) -> bool:
    if claim.location == "title":
        return bool(rec.title_th) and claim.text in (rec.title_th or "")
    if claim.location == "tag":
        return any(claim.text in t for t in rec.site_tags)
    if claim.location == "category":
        return bool(rec.site_category) and claim.text in (rec.site_category or "")
    # breadcrumb and intro are not otherwise stored; the span itself is the evidence.
    return True


def finalise(rec: ScrapedRecipe) -> Finalised:
    """PDPA-redact, normalise and validate one record. Raises :class:`RecordRefused`."""
    errors: list[str] = []
    report = RedactionReport()

    if not rec.url.startswith(("http://", "https://")):
        errors.append(f"url: not an http(s) URL: {rec.url!r}")
    if rec.scraped_at.tzinfo is None:
        errors.append("scraped_at: must be timezone-aware UTC")
    if len(rec.site_tags) > MAX_TAGS:
        errors.append(f"site_tags: {len(rec.site_tags)} > {MAX_TAGS}")
    for name, claim in (("region_claim", rec.region_claim), ("province_claim", rec.province_claim)):
        if claim is None:
            continue
        if claim.location not in CLAIM_LOCATIONS:
            errors.append(f"{name}: unknown location {claim.location!r}")
        elif not _claim_found(claim, rec):
            # The claim text is not echoed: it has not been redacted yet.
            errors.append(f"{name}: text not found in the page's {claim.location} "
                          "— a claim is copied from the site, never composed (rule 6)")

    def clean(where: str, text: str | None, limit: int) -> str | None:
        if text is None:
            return None
        _check_text(where, text, limit, errors)  # before redaction can hide a link
        redacted, r = redact(text)
        _merge(report, r)
        return redacted

    title = clean("title_th", rec.title_th, MAX_TITLE_CHARS)
    category = clean("site_category", rec.site_category, MAX_TITLE_CHARS)
    servings = clean("servings", rec.servings, MAX_LINE_CHARS)
    tags = [clean(f"site_tags[{i}]", t, MAX_LINE_CHARS) or "" for i, t in enumerate(rec.site_tags)]
    lines = [clean(f"ingredient_lines[{i}]", line, MAX_LINE_CHARS) or ""
             for i, line in enumerate(rec.ingredient_lines)]

    def claim_payload(name: str, claim: Claim | None) -> dict[str, str] | None:
        if claim is None:
            return None
        text = clean(name, claim.text, MAX_CLAIM_CHARS) or ""
        return {"text": text, "text_norm": _norm(text), "location": claim.location}

    payload: dict[str, Any] = {
        "url": rec.url,
        "title_th": title,
        "title_th_norm": _norm(title) if title is not None else None,
        "published_at": rec.published_at.isoformat() if rec.published_at else None,
        "scraped_at": rec.scraped_at.isoformat(),
        "site_category": category,
        "site_category_norm": _norm(category) if category is not None else None,
        "site_tags": tags,
        "site_tags_norm": [_norm(t) for t in tags],
        "region_claim": claim_payload("region_claim", rec.region_claim),
        "province_claim": claim_payload("province_claim", rec.province_claim),
        "ingredient_lines": lines,
        "ingredient_lines_norm": [_norm(line) for line in lines],
        "servings": servings,
        "servings_norm": _norm(servings) if servings is not None else None,
    }

    if extra := set(payload) ^ ALLOWED_PAYLOAD_KEYS:
        errors.append(f"payload keys differ from ALLOWED_PAYLOAD_KEYS: {sorted(extra)} (rule 4)")

    # Belt and braces: normalisation can join characters, so scan what will be written.
    serialised = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    if leaks := find_leaks(serialised):
        errors.append(f"PDPA: personal data survives redaction: {sorted(leaks)} (rule 5)")
    if errors:
        raise RecordRefused(f"{rec.url}: " + "; ".join(errors))

    digest = hashlib.sha256(serialised.encode("utf-8")).hexdigest()
    return Finalised(payload, report, digest)


def insert_raw_recipe(
    conn: Any,
    source_id: str,
    fin: Finalised,
    *,
    raw_path: str,
    http_status: int,
    fetched_at: datetime,
) -> None:
    """Write one finalised record to ``raw_recipes`` — and nothing else.

    Accepts only a :class:`Finalised`, so nothing reaches this table without having
    passed :func:`finalise` (and so PDPA). Re-runs are idempotent on
    ``(source_id, content_hash)``. The caller commits.
    """
    if not isinstance(fin, Finalised):
        raise TypeError("insert_raw_recipe takes the output of finalise(), nothing else")
    if set(fin.payload) != ALLOWED_PAYLOAD_KEYS:
        raise RecordRefused("payload was altered after finalise() (rule 4)")
    published = fin.payload["published_at"]
    conn.execute(
        """
        INSERT INTO raw_recipes (source_id, source_url, fetched_at, http_status, raw_path,
                                 published_at, parsed_json, content_hash)
        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
        ON CONFLICT (source_id, content_hash) DO NOTHING
        """,
        (source_id, fin.payload["url"], fetched_at, http_status, raw_path,
         published, json.dumps(fin.payload, ensure_ascii=False), fin.content_hash),
    )
