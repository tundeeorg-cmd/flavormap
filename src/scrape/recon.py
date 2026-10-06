"""Audit-stage reconnaissance: what a site *is*, before any recipe page is fetched
(docs/scraping_rules.md §1, §8).

Two things, both through the `PoliteFetcher` (paced, robots-checked, identified):

- `policy_text`: the readable text of a policy page (terms, copyright notice, footer),
  with ``<script>``, ``<style>`` and ``<noscript>`` removed first. A page's embedded
  JavaScript data is not a clause, and the 2026-10-06 Wongnai audit showed it being
  flagged as one.
- `probe_sitemaps`: reads **only sitemaps**, never a recipe page: the sitemap index
  (from robots.txt's ``Sitemap:`` lines, else the usual WordPress locations), then the
  category, tag, course and cuisine sitemaps it lists. That shows the site's recipe index
  pages and whether any regional tags exist. It is capped at `MAX_PROBE_REQUESTS`
  requests.

Region terms are found by keyword in the term's URL slug. **That is a hint for the
researcher, not a claim**: a tag called ``northern`` may not mean Northern Thailand.
"""

from __future__ import annotations

import re
import urllib.robotparser
from dataclasses import dataclass, field

from selectolax.parser import HTMLParser

from src.scrape.conduct import PoliteFetcher

MAX_PROBE_REQUESTS = 6
SITEMAP_FALLBACKS = ("/sitemap_index.xml", "/wp-sitemap.xml", "/sitemap.xml")
TAXONOMY_MARKERS = ("category", "tag", "taxonom", "course", "cuisine", "region")
REGION_KEYWORDS = (
    "isan", "isaan", "issan", "esan", "isarn", "northeast", "north", "lanna", "chiang",
    "south", "central", "bangkok", "region",
    "อีสาน", "เหนือ", "ใต้", "ภาคกลาง",
)
_LOC = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>")


def policy_text(html: str) -> str:
    """Readable text of a page, with script/style/noscript removed first."""
    tree = HTMLParser(html)
    for node in tree.css("script, style, noscript"):
        node.decompose()
    body = tree.body
    return body.text(separator="\n") if body else tree.text(separator="\n")


@dataclass
class SitemapProbe:
    index_url: str | None = None
    child_sitemaps: list[str] = field(default_factory=list)
    taxonomy_sitemaps: list[str] = field(default_factory=list)
    terms: list[str] = field(default_factory=list)          # category/tag/... page URLs
    requests_used: int = 0
    notes: list[str] = field(default_factory=list)

    @property
    def region_terms(self) -> list[str]:
        return [t for t in self.terms if any(k in _slug(t) for k in REGION_KEYWORDS)]

    @property
    def recipe_index_pages(self) -> list[str]:
        return [t for t in self.terms if "recipe" in _slug(t)]


def _slug(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1].lower()


def probe_sitemaps(
    fetcher: PoliteFetcher, base_url: str, robots: urllib.robotparser.RobotFileParser
) -> SitemapProbe:
    probe = SitemapProbe()

    def get(url: str) -> str | None:
        if probe.requests_used >= MAX_PROBE_REQUESTS:
            probe.notes.append(f"request cap ({MAX_PROBE_REQUESTS}) reached before {url}")
            return None
        if not fetcher.allowed(url):
            probe.notes.append(f"disallowed by robots.txt: {url}")
            return None
        probe.requests_used += 1
        r = fetcher.get(url)
        if r is None:  # allowed, so this was a transport error (counted by the fetcher)
            probe.notes.append(f"request failed (connection error): {url}")
            return None
        if r.status_code != 200:
            probe.notes.append(f"HTTP {r.status_code}: {url}")
            return None
        return r.text

    candidates = list(robots.site_maps() or []) or [base_url + p for p in SITEMAP_FALLBACKS]
    index_xml = None
    for url in candidates:
        index_xml = get(url)
        if index_xml is not None:
            probe.index_url = url
            break
    if index_xml is None:
        probe.notes.append("no sitemap found")
        return probe

    locs = _LOC.findall(index_xml)
    if "<sitemapindex" in index_xml:
        probe.child_sitemaps = locs
    else:  # a single flat sitemap: its locs are pages, terms included
        probe.terms = [u for u in locs if any(m in u.lower() for m in TAXONOMY_MARKERS)]
        return probe

    probe.taxonomy_sitemaps = [
        u for u in probe.child_sitemaps if any(m in u.lower() for m in TAXONOMY_MARKERS)
    ]
    for url in probe.taxonomy_sitemaps:
        xml = get(url)
        if xml is not None:
            probe.terms.extend(_LOC.findall(xml))
    return probe
