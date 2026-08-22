"""Fetch recipe pages from cooking.kapook.com.

    uv run python -m scripts.fetch_kapook [--limit N] [--sitemap-only]

Conduct, per ETHICS.md rule 7 and the 2026-08-22 re-audit:

* robots.txt is re-fetched and honoured **at run time**, not trusted from the audit
* one request per second, sequential, no concurrency
* identifying User-Agent carrying SCRAPER_CONTACT_EMAIL
* every response recorded in a manifest with URL, timestamp, status and sha256

Raw HTML is cached to ``data/raw/kapook_cooking/`` — gitignored, never published, kept
so that parsing is reproducible and auditable. Nothing here writes to the database:
what may be *stored* is a narrower question than what may be fetched, and the page's
JSON-LD carries an ``articleBody`` field holding the full prose, which never leaves disk.

The sitemap lists 3,770 URLs but only 2,743 are recipes; 956 are ``/comment/`` pages and
43 are category listings. The 2026-08-09 audit's "3,908 recipes" was counting all of them.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import time
import urllib.robotparser
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from src.config import RAW_DIR, get_settings

BASE = "https://cooking.kapook.com"
ROBOTS = f"{BASE}/robots.txt"
SITEMAP = f"{BASE}/sitemap.xml"
OUT_DIR = RAW_DIR / "kapook_cooking"
MANIFEST = OUT_DIR / "_manifest.csv"

RATE_LIMIT_SEC = 1.0
TIMEOUT_SEC = 30.0
RECIPE_URL = re.compile(r"^https://cooking\.kapook\.com/view(\d+)\.html$")


def user_agent() -> str:
    email = get_settings().scraper_contact_email
    return f"FlavorMapResearchBot/0.1 (+mailto:{email}; academic research, non-commercial)"


@dataclass
class Fetcher:
    """Polite sequential fetcher. One request per second, no concurrency."""

    client: httpx.Client
    robots: urllib.robotparser.RobotFileParser
    ua: str
    _last: float = 0.0

    def _wait(self) -> None:
        elapsed = time.monotonic() - self._last
        if elapsed < RATE_LIMIT_SEC:
            time.sleep(RATE_LIMIT_SEC - elapsed)
        self._last = time.monotonic()

    def get(self, url: str) -> httpx.Response | None:
        if not self.robots.can_fetch(self.ua, url):
            print(f"  DISALLOWED by robots.txt: {url}")
            return None
        self._wait()
        return self.client.get(url)


def load_robots(client: httpx.Client, ua: str) -> urllib.robotparser.RobotFileParser:
    parser = urllib.robotparser.RobotFileParser()
    response = client.get(ROBOTS)
    response.raise_for_status()
    parser.parse(response.text.splitlines())
    if not parser.can_fetch(ua, BASE + "/"):
        raise SystemExit("robots.txt disallows our User-Agent at the root — stopping (rule 7).")
    print(f"robots.txt: fetched, root allowed for {ua}")
    return parser


def recipe_urls(fetcher: Fetcher) -> list[str]:
    response = fetcher.get(SITEMAP)
    if response is None or response.status_code != 200:
        raise SystemExit(f"sitemap unavailable: {response.status_code if response else 'blocked'}")
    locs = re.findall(r"<loc>([^<]+)</loc>", response.text)
    def recipe_id(url: str) -> int:
        match = RECIPE_URL.match(url)
        return int(match.group(1)) if match else 0

    urls = sorted({u for u in locs if RECIPE_URL.match(u)}, key=recipe_id)
    print(f"sitemap: {len(locs)} <loc> entries, {len(urls)} of them recipe pages")
    return urls


def already_fetched() -> set[str]:
    if not MANIFEST.exists():
        return set()
    with MANIFEST.open(encoding="utf-8") as handle:
        return {row["url"] for row in csv.DictReader(handle) if row["outcome"] == "fetched"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, help="stop after N new pages")
    ap.add_argument("--sitemap-only", action="store_true", help="enumerate, fetch nothing")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ua = user_agent()
    headers = {"User-Agent": ua, "Accept-Language": "th,en;q=0.8"}

    with httpx.Client(headers=headers, timeout=TIMEOUT_SEC, follow_redirects=True) as client:
        robots = load_robots(client, ua)
        fetcher = Fetcher(client=client, robots=robots, ua=ua)
        urls = recipe_urls(fetcher)
        if args.sitemap_only:
            return 0

        done = already_fetched()
        todo = [u for u in urls if u not in done][: args.limit]
        print(f"already fetched: {len(done)} | fetching now: {len(todo)}")

        new = MANIFEST.exists()
        with MANIFEST.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            if not new:
                writer.writerow(["url", "recipe_id", "outcome", "http_status", "sha256",
                                 "bytes", "fetched_at"])
            counts = {"fetched": 0, "missing": 0, "error": 0}
            for index, url in enumerate(todo, 1):
                match = RECIPE_URL.match(url)
                assert match is not None  # urls were filtered by this pattern
                page_id = match.group(1)
                try:
                    response = fetcher.get(url)
                except httpx.HTTPError as exc:
                    counts["error"] += 1
                    writer.writerow([url, page_id, "error", type(exc).__name__, "", 0,
                                     datetime.now(UTC).isoformat()])
                    continue
                if response is None:
                    counts["error"] += 1
                    continue
                if response.status_code != 200:
                    counts["missing"] += 1
                    writer.writerow([url, page_id, "missing", response.status_code, "", 0,
                                     datetime.now(UTC).isoformat()])
                    continue

                payload = response.content
                digest = hashlib.sha256(payload).hexdigest()
                (OUT_DIR / f"view{page_id}.html").write_bytes(payload)
                counts["fetched"] += 1
                writer.writerow([url, page_id, "fetched", 200, digest, len(payload),
                                 datetime.now(UTC).isoformat()])
                if index % 50 == 0:
                    handle.flush()
                    print(f"  {index}/{len(todo)}  fetched={counts['fetched']} "
                          f"missing={counts['missing']} errors={counts['error']}")

    print("\n" + "\n".join(f"{k:>9}: {v}" for k, v in counts.items()))
    print(f"manifest: {MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
