"""Rule 3 of docs/scraping_rules.md — the page cache and its manifest."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import pytest

from src.scrape.cache import MANIFEST_COLUMNS, PageCache, url_sha1

URL = "https://new.example/recipe/1"


def _rows(cache: PageCache) -> list[dict[str, str]]:
    with cache.manifest.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_a_200_is_cached_with_exactly_rule_3s_manifest(tmp_path: Path) -> None:
    cache = PageCache("newsite", tmp_path)
    body = "<html>ส่วนผสม</html>".encode()
    page = cache.record(URL, 200, body)
    assert page is not None
    assert page.path == tmp_path / "newsite" / f"{url_sha1(URL)}.html"
    assert page.path.read_bytes() == body
    with cache.manifest.open(encoding="utf-8") as handle:
        assert tuple(next(csv.reader(handle))) == MANIFEST_COLUMNS
    row = _rows(cache)[0]
    assert row["url"] == URL
    assert row["url_sha1"] == hashlib.sha1(URL.encode()).hexdigest()
    assert row["http_status"] == "200"
    assert row["bytes"] == str(len(body))
    assert row["content_sha256"] == hashlib.sha256(body).hexdigest()
    assert row["fetched_at"].endswith("+00:00"), "fetched_at is UTC ISO"
    assert cache.get(URL) is not None


@pytest.mark.parametrize("status,body", [(404, b"gone"), (200, b""), (503, b"")])
def test_a_failure_is_logged_but_not_cached(tmp_path: Path, status: int, body: bytes) -> None:
    cache = PageCache("newsite", tmp_path)
    assert cache.record(URL, status, body) is None
    assert cache.get(URL) is None
    assert _rows(cache)[0]["http_status"] == str(status)
    assert not cache.path_for(URL).exists()


def test_the_manifest_is_append_only_and_the_latest_row_counts(tmp_path: Path) -> None:
    cache = PageCache("newsite", tmp_path)
    cache.record(URL, 200, b"first")
    cache.record(URL, 200, b"second")  # a --refresh
    assert len(_rows(cache)) == 2
    page = cache.get(URL)
    assert page is not None and page.content_sha256 == hashlib.sha256(b"second").hexdigest()


@pytest.mark.parametrize("slug", ["", "../escape", ".hidden", "a/b"])
def test_a_bad_slug_is_refused(tmp_path: Path, slug: str) -> None:
    with pytest.raises(ValueError):
        PageCache(slug, tmp_path)


def test_raw_pages_are_gitignored() -> None:
    from src.config import REPO_ROOT

    assert "data/raw/" in (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
