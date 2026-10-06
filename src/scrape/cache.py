"""Rule 3 (`docs/scraping_rules.md`) — every fetched page is cached, and a cached page is
never fetched again without ``--refresh``.

Layout, per source::

    data/raw/<source_slug>/<url_sha1>.html     the page, byte for byte as served
    data/raw/<source_slug>/_manifest.csv       one row per network response

``data/raw/`` is gitignored and never published. The manifest is append-only — a
``--refresh`` adds a row rather than rewriting history — and its latest row for a URL
is the one that counts. Its columns are exactly rule 3's:
``url, url_sha1, fetched_at, http_status, bytes, content_sha256``.

A response that is not a 200 with a body is recorded in the manifest but **not** cached,
so the next run asks again; a page that *is* cached is read from disk and the network is
never touched for it.
"""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from src.config import RAW_DIR

MANIFEST_NAME = "_manifest.csv"
MANIFEST_COLUMNS = ("url", "url_sha1", "fetched_at", "http_status", "bytes", "content_sha256")


def url_sha1(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CachedPage:
    url: str
    path: Path
    fetched_at: datetime
    http_status: int
    content_sha256: str

    def text(self) -> str:
        return self.path.read_bytes().decode("utf-8", errors="replace")


class PageCache:
    def __init__(self, source_slug: str, root: Path = RAW_DIR) -> None:
        if not source_slug or "/" in source_slug or source_slug.startswith("."):
            raise ValueError(f"bad source slug: {source_slug!r}")
        self.dir = root / source_slug
        self.manifest = self.dir / MANIFEST_NAME

    def path_for(self, url: str) -> Path:
        return self.dir / f"{url_sha1(url)}.html"

    def _latest(self) -> dict[str, dict[str, str]]:
        if not self.manifest.exists():
            return {}
        with self.manifest.open(encoding="utf-8", newline="") as handle:
            return {row["url"]: row for row in csv.DictReader(handle)}

    def get(self, url: str) -> CachedPage | None:
        """The cached page for `url`, or None if it has never been cached successfully."""
        row = self._latest().get(url)
        path = self.path_for(url)
        if row is None or row["http_status"] != "200" or not path.exists():
            return None
        return CachedPage(url, path, datetime.fromisoformat(row["fetched_at"]),
                          200, row["content_sha256"])

    def record(self, url: str, http_status: int, body: bytes) -> CachedPage | None:
        """Append a manifest row; write the page only for a 200 with a body."""
        self.dir.mkdir(parents=True, exist_ok=True)
        fetched_at = datetime.now(UTC)
        cacheable = http_status == 200 and bool(body)
        digest = hashlib.sha256(body).hexdigest() if body else ""
        path = self.path_for(url)
        if cacheable:
            path.write_bytes(body)
        new = not self.manifest.exists()
        with self.manifest.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            if new:
                writer.writerow(MANIFEST_COLUMNS)
            writer.writerow([url, url_sha1(url), fetched_at.isoformat(), http_status,
                             len(body), digest])
        if not cacheable:
            return None
        return CachedPage(url, path, fetched_at, http_status, digest)
