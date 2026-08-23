"""Parse one cached ``cooking.kapook.com`` page into a structured record.

The corpus spans roughly fifteen years of one CMS, and the markup is not stable across
it. Measured over the 2,702 cached pages (2026-08-23):

=========================================  ======
``div#main_article`` present                2,702
``<ul><li>`` used for the ingredient list     845
a ``•`` bullet character anywhere           1,103
schema.org ``Recipe`` node                       0
=========================================  ======

So the list cannot be read from list markup, from a bullet glyph, or from structured
data. What every layout does share is that the ingredient block is a run of short
lines under a heading, separated by ``<br>`` or block tags. This module therefore
flattens the article to text lines — turning ``<br>`` and block closers into newlines
first, which ``selectolax``'s own text extraction does not do — and reads the block
positionally from there.

**Headings.** ``ส่วนผสม`` covers 2,458 pages. Older layouts and the newer
"``สิ่งที่ต้องเตรียม``" template do not use it; adding that second heading recovered 244
pages that otherwise parsed to nothing, which is why the vocabulary is a list rather
than one string.

**What is not stored.** The page's JSON-LD carries an ``articleBody`` field holding the
full prose. It is never read into a record and never written anywhere — ``ETHICS.md``
permits ingredient lists, publication dates and derived labels from this source, not the
recipe text. Method steps are likewise dropped: they are what the stop vocabulary is for.

**Roundups.** A kapook page is not reliably one recipe. ``view159758`` carries 46
ingredient sections, one per dish in a listicle; other pages split a single dish across
``ส่วนผสม ตัวแป้ง`` and ``ส่วนผสม น้ำจิ้ม``. Sections are therefore returned as found and
never merged. Deciding how a page maps to rows in ``recipes`` is an analytical choice
about the unit of observation, not a parsing detail, and it is left to the caller.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from selectolax.parser import HTMLParser

from src.ingest.pdpa import RedactionReport, redact

ARTICLE_SELECTOR = "div#main_article"

# Headings that open an ingredient block. Order is irrelevant; a line qualifies if it
# starts with any of them and is short enough to be a heading rather than a sentence.
INGREDIENT_HEADINGS = (
    "ส่วนผสม",
    "สิ่งที่ต้องเตรียม",
    "เครื่องปรุง",
    "วัตถุดิบ",
)

# Headings that close one. ``เคล็ดลับ`` (tips) and ``ขอขอบคุณ`` (credits) are here because
# they are prose, and prose under an ingredient heading would otherwise be collected as
# ingredients.
METHOD_HEADINGS = (
    "วิธีทำ",
    "วิธีทํา",
    "วิธีการทำ",
    "วิธีปรุง",
    "ขั้นตอน",
    "เคล็ดลับ",
    "ขอขอบคุณ",
    "ที่มา",
)

# A heading, not a sentence. The longest genuine ingredient heading in the corpus is
# ``สิ่งที่ต้องเตรียม หมายเหตุ : ส่วนผสมต่าง ๆ เจ้าของสูตรใช้วิธีกะปริมาณเอา`` at 72 characters.
MAX_HEADING_CHARS = 80

# An ingredient line, not a paragraph. Set from the corpus: the longest hand-checked
# ingredient line runs to about 130 characters because of parenthetical brand notes,
# while method steps start at roughly twice that. A line over the cap ends the section
# rather than being skipped — prose under the heading means the block is over.
MAX_ITEM_CHARS = 150

_BR = re.compile(r"<br\s*/?>", re.I)
_BLOCK_CLOSE = re.compile(
    r"</(?:div|p|li|ul|ol|h[1-6]|tr|td|th|table|blockquote|section|article)>", re.I
)
# Zero-width and non-breaking characters. The CMS's editor emits runs of U+200B as
# indentation, and they survive text extraction as invisible content that defeats both
# `strip()` and a leading-bullet match.
_INVISIBLE = re.compile(r"[​-‏⁠﻿\xa0]")
# A leading list marker: a bullet glyph, or an arabic or Thai numeral with a separator.
_MARKER = re.compile(r"^(?:[•◦‣▪·*+\-–—]|\(?[0-9๐-๙]{1,2}[.)])\s*")
_WS_RUN = re.compile(r"\s{2,}")

_LD_JSON = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.I | re.S
)
_ARTICLE_TYPES = {"NewsArticle", "Article", "BlogPosting", "Recipe"}
_PAGE_ID = re.compile(r"view(\d+)")


@dataclass
class IngredientSection:
    """One ``ส่วนผสม``-style block: its heading, and the lines beneath it."""

    heading: str
    items: list[str] = field(default_factory=list)


@dataclass
class KapookRecord:
    """One parsed page. Carries no recipe prose and no personal data by construction."""

    page_id: str
    url: str
    title_th: str | None = None
    published_at: date | None = None
    sections: list[IngredientSection] = field(default_factory=list)
    redaction: RedactionReport = field(default_factory=RedactionReport)
    notes: list[str] = field(default_factory=list)

    @property
    def n_items(self) -> int:
        return sum(len(s.items) for s in self.sections)

    @property
    def is_usable(self) -> bool:
        """Enough to contribute an ingredient set. A title alone is not a recipe."""
        return self.n_items > 0


def _clean_line(raw: str) -> str:
    text = unicodedata.normalize("NFC", _INVISIBLE.sub(" ", raw))
    return _WS_RUN.sub(" ", text).strip()


def article_lines(html: str) -> list[str] | None:
    """The article body as text lines, or None if the page has no article container.

    ``<br>`` and block closers become newlines *before* extraction. Extracting text
    first and splitting afterwards loses every line boundary in the ``<br>``-delimited
    layouts, which is most of the corpus.
    """
    tree = HTMLParser(html)
    article = tree.css_first(ARTICLE_SELECTOR)
    if article is None:
        return None
    for tag in ("script", "style", "iframe", "noscript"):
        for node in article.css(tag):
            node.decompose()

    inner = _BLOCK_CLOSE.sub("\n", _BR.sub("\n", article.html or ""))
    text = HTMLParser(inner).text()
    return [line for line in (_clean_line(ln) for ln in text.split("\n")) if line]


def _is_heading(line: str, vocabulary: tuple[str, ...]) -> bool:
    return len(line) <= MAX_HEADING_CHARS and line.startswith(vocabulary)


def ingredient_sections(lines: list[str]) -> list[IngredientSection]:
    """Every ingredient block on the page, in document order.

    A section runs from its heading to the first thing that is not an ingredient line:
    a method heading, the next ingredient heading, or a line too long to be an item.
    Empty sections are dropped — a heading with an image beneath it instead of a list
    is common in the older layouts, and it yields no data.
    """
    sections: list[IngredientSection] = []
    current: IngredientSection | None = None

    for line in lines:
        if _is_heading(line, INGREDIENT_HEADINGS):
            current = IngredientSection(heading=line)
            sections.append(current)
            continue
        if current is None:
            continue
        if _is_heading(line, METHOD_HEADINGS):
            current = None
            continue

        item = _MARKER.sub("", line).strip()
        if not item:
            continue
        if len(item) > MAX_ITEM_CHARS:
            current = None
            continue
        current.items.append(item)

    return [section for section in sections if section.items]


def article_metadata(html: str) -> dict[str, object]:
    """``headline`` and ``datePublished`` from the page's JSON-LD.

    Only those two keys are returned. The node they come from also carries
    ``articleBody`` — the entire recipe prose — and reading the whole node into a record
    would put it one ``asdict()`` away from a database column.
    """
    for block in _LD_JSON.findall(html):
        try:
            payload = json.loads(block)
        except json.JSONDecodeError:
            continue
        for node in payload if isinstance(payload, list) else [payload]:
            if isinstance(node, dict) and node.get("@type") in _ARTICLE_TYPES:
                return {
                    "headline": node.get("headline"),
                    "datePublished": node.get("datePublished"),
                }
    return {}


def _published_date(value: object) -> date | None:
    """The date part of an ISO-8601 timestamp. Never a guess: unparseable is None."""
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def parse_html(html: str, url: str, page_id: str | None = None) -> KapookRecord:
    """Parse one page. Redaction runs before anything is placed on the record."""
    if page_id is None:
        match = _PAGE_ID.search(url)
        page_id = match.group(1) if match else ""

    record = KapookRecord(page_id=page_id, url=url)
    metadata = article_metadata(html)
    if not metadata:
        record.notes.append("no JSON-LD article node")

    raw_headline = metadata.get("headline")
    headline = raw_headline if isinstance(raw_headline, str) else None
    record.published_at = _published_date(metadata.get("datePublished"))
    if record.published_at is None:
        record.notes.append("no usable datePublished")

    lines = article_lines(html)
    if lines is None:
        record.notes.append(f"no {ARTICLE_SELECTOR} container")
        lines = []

    if headline is None and lines:
        headline = lines[0][:MAX_HEADING_CHARS]

    # Rule 8. Kapook credits contributors in the body — "โดย คุณ… สมาชิกเว็บไซต์พันทิป" —
    # and those names reach the headline and the section headings. Unlike the DCP forms,
    # a page with zero redactions is the normal case rather than a parser failure, so
    # `suspected_parser_failure` is not consulted for this source.
    report = RedactionReport()

    def scrub(text: str) -> str:
        cleaned, found = redact(text)
        for column in RedactionReport.COLUMNS.values():
            setattr(report, column, getattr(report, column) + getattr(found, column))
        return cleaned

    record.title_th = scrub(_clean_line(headline)) if headline else None
    record.sections = [
        IngredientSection(
            heading=scrub(section.heading),
            items=[scrub(item) for item in section.items],
        )
        for section in ingredient_sections(lines)
    ]
    record.redaction = report
    if not record.sections:
        record.notes.append("no ingredient section found")
    return record


def parse_file(path: Path) -> KapookRecord:
    """Parse a cached page from ``data/raw/kapook_cooking/``."""
    page_id = _PAGE_ID.search(path.stem)
    return parse_html(
        path.read_text(encoding="utf-8", errors="replace"),
        url=f"https://cooking.kapook.com/{path.name}",
        page_id=page_id.group(1) if page_id else "",
    )
