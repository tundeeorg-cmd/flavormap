"""Raw-page cache (docs/scraping_rules.md §3).

Every fetched page is saved under ``data/raw/<source_slug>/`` (gitignored, never
published) as ``<url_sha1>.html``, and every fetch, of any status, appends one row to
``manifest.csv``:

    url, url_sha1, fetched_at (UTC ISO 8601), http_status, bytes, content_sha256

Re-runs read from the cache. A page already cached is **never** re-fetched unless the
caller passes ``refresh=True`` (the ``--refresh`` flag). The manifest is append-only, so
a refresh adds a row rather than rewriting history.

Scrapers written before these rules (``dcp_food``, ``kapook_cooking``) keep their
existing manifests: ``data/raw/`` is read-only to everything but its fetcher, and those
files are not rewritten into the new format.
"""

from __future__ import annotations

import csv
import datetime
import hashlib
from dataclasses import dataclass
from pathlib import Path

from src.config import RAW_DIR
from src.scrape.conduct import PoliteFetcher

MANIFEST_COLUMNS = ("url", "url_sha1", "fetched_at", "http_status", "bytes", "content_sha256")


def url_sha1(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CachedPage:
    url: str
    http_status: int
    body: bytes
    content_sha256: str
    path: Path
    from_cache: bool

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")


class PageCache:
    def __init__(self, slug: str, root: Path = RAW_DIR) -> None:
        if not slug or "/" in slug or slug.startswith("."):
            raise ValueError(f"bad source slug: {slug!r}")
        self.dir = root / slug
        self.manifest = self.dir / "manifest.csv"

    def path_for(self, url: str) -> Path:
        return self.dir / f"{url_sha1(url)}.html"

    def _rows(self) -> list[dict[str, str]]:
        if not self.manifest.exists():
            return []
        with self.manifest.open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    def _append(self, row: dict[str, object]) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        new = not self.manifest.exists()
        with self.manifest.open("a", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS)
            if new:
                w.writeheader()
            w.writerow(row)

    def cached(self, url: str) -> CachedPage | None:
        """The cached copy of `url`, or None. Reads the latest manifest row for status."""
        path = self.path_for(url)
        if not path.exists():
            return None
        rows = [r for r in self._rows() if r["url"] == url]
        status = int(rows[-1]["http_status"]) if rows else 200
        body = path.read_bytes()
        return CachedPage(url, status, body, hashlib.sha256(body).hexdigest(), path, True)

    def fetch(self, fetcher: PoliteFetcher, url: str, refresh: bool = False) -> CachedPage | None:
        """The page for `url`: from the cache unless `refresh`, otherwise fetched politely.
        Every fetch is recorded in the manifest; only a 200 body is saved. Returns None
        when robots.txt disallows the URL."""
        if not refresh and (hit := self.cached(url)) is not None:
            return hit
        response = fetcher.get(url)
        if response is None:
            return None
        body = response.content
        digest = hashlib.sha256(body).hexdigest()
        path = self.path_for(url)
        if response.status_code == 200:
            self.dir.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
        self._append({
            "url": url,
            "url_sha1": url_sha1(url),
            "fetched_at": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
            "http_status": response.status_code,
            "bytes": len(body),
            "content_sha256": digest,
        })
        return CachedPage(url, response.status_code, body, digest, path, False)
