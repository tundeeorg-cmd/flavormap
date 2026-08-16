"""Enumerate and fetch the DCP provincial food documents (source_id='dcp_food').

    uv run python -m scripts.fetch_dcp_food [--limit N] [--probe-only] [--region R]

The 2568 programme publishes one PDF per shortlisted menu at::

    https://food.culture.go.th/food68/{region}/{province_index}/{menu_index}.pdf

`province_index` is 1-based in Thai alphabetical order *within* the region, and
`menu_index` runs 1–3. Four regions — north 17, northeast 20, central 26, south 14 —
give a maximum of 231 documents.

**The URL index is a discovery convenience and nothing more.** The province label for a
record comes from parsing §1.1 of the document itself. If a parsed province ever
disagrees with the index, both are logged and the record is flagged; neither is silently
preferred. Nothing in this module writes a province anywhere.

404s are expected — not every slot is filled. The log of empty triples is itself a
coverage artifact and is written to ``data/raw/dcp_food/_enumeration_log.csv``.

Conduct (rule 7): 1 request/second minimum, identifying User-Agent carrying
SCRAPER_CONTACT_EMAIL, robots.txt re-checked at run time rather than trusted from the
audit. See ETHICS.md for the content-signal question and docs/decisions.md HD-3 for why
this source is currently used under option C — reference layer only, excluded from any
public release.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import time
import urllib.robotparser
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from src.config import get_settings

BASE = "https://food.culture.go.th"
ROBOTS = f"{BASE}/robots.txt"
OUT_DIR = Path("data/raw/dcp_food")
LOG_PATH = OUT_DIR / "_enumeration_log.csv"

RATE_LIMIT_SEC = 1.0
TIMEOUT_SEC = 60.0

# Province counts per region path, established empirically on 2026-08-16 by probing
# until the indices 404.
#
# The site uses a FIVE-region scheme with a separate `east/` path — not the four-region
# scheme (north/northeast/central/south) this project's `region4` column uses. Probing
# with four-region counts left the alphabetical tails of `north` and `central` 404ing,
# which looked like ten provinces missing from the programme and was in fact ten
# provinces filed under `east/`.
#
#   16 + 20 + 17 + 10 + 14 = 77 provinces x 3 menus = 231 documents
#
# These counts describe the SITE's directory layout. They are not a regional model and
# nothing downstream should treat them as one — `region4` in provinces.csv is unaffected.
REGIONS: dict[str, int] = {
    "north": 16,
    "northeast": 20,
    "central": 17,
    "east": 10,
    "south": 14,
}
MENUS_PER_PROVINCE = 3


def user_agent() -> str:
    email = get_settings().scraper_contact_email
    if not email or "example.com" in email:
        raise SystemExit(
            "SCRAPER_CONTACT_EMAIL is unset or still a placeholder. Rule 7 requires a "
            "genuinely reachable address in the User-Agent before any fetch."
        )
    return f"FlavorMapResearchBot/0.1 (+mailto:{email}; academic research, non-commercial)"


@dataclass
class Result:
    fetched: list[tuple[str, int, int, str, int]] = field(default_factory=list)
    missing: list[tuple[str, int, int, int]] = field(default_factory=list)
    errors: list[tuple[str, str]] = field(default_factory=list)


class Fetcher:
    """Polite sequential fetcher. One request per second, no concurrency."""

    def __init__(self, client: httpx.Client, robots: urllib.robotparser.RobotFileParser):
        self.client = client
        self.robots = robots
        self.ua = user_agent()
        self._last = 0.0

    def _wait(self) -> None:
        elapsed = time.monotonic() - self._last
        if elapsed < RATE_LIMIT_SEC:
            time.sleep(RATE_LIMIT_SEC - elapsed)
        self._last = time.monotonic()

    def allowed(self, url: str) -> bool:
        return self.robots.can_fetch(self.ua, url)

    def get(self, url: str) -> httpx.Response | None:
        if not self.allowed(url):
            # Never fetch a disallowed URL — report it and move on (rule 7).
            print(f"  DISALLOWED by robots.txt: {url}")
            return None
        self._wait()
        return self.client.get(url)

    def head(self, url: str) -> httpx.Response | None:
        if not self.allowed(url):
            print(f"  DISALLOWED by robots.txt: {url}")
            return None
        self._wait()
        return self.client.head(url)


def is_pdf(body: bytes) -> bool:
    return body[:5] == b"%PDF-"


def enumerate_food68(f: Fetcher, limit: int | None, only_region: str | None) -> Result:
    result = Result()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    n = 0

    for region, n_provinces in REGIONS.items():
        if only_region and region != only_region:
            continue
        for p in range(1, n_provinces + 1):
            for m in range(1, MENUS_PER_PROVINCE + 1):
                if limit is not None and n >= limit:
                    print(f"\n--limit {limit} reached")
                    return result

                dest = OUT_DIR / f"{region}_{p}_{m}.pdf"
                if dest.exists():
                    # Resumable: an existing file is never re-fetched.
                    body = dest.read_bytes()
                    result.fetched.append(
                        (region, p, m, hashlib.sha256(body).hexdigest(), len(body))
                    )
                    continue

                url = f"{BASE}/food68/{region}/{p}/{m}.pdf"
                n += 1
                try:
                    resp = f.get(url)
                except httpx.HTTPError as e:
                    result.errors.append((url, type(e).__name__))
                    print(f"  ERROR {type(e).__name__}: {url}")
                    continue
                if resp is None:
                    continue

                if resp.status_code == 200 and is_pdf(resp.content):
                    dest.write_bytes(resp.content)
                    digest = hashlib.sha256(resp.content).hexdigest()
                    result.fetched.append((region, p, m, digest, len(resp.content)))
                    print(f"  ok   {region}/{p}/{m}  {len(resp.content):>8,}B  {digest[:12]}")
                elif resp.status_code == 404:
                    result.missing.append((region, p, m, 404))
                elif resp.status_code == 200:
                    # 200 but not a PDF — usually a soft-404 HTML page.
                    result.missing.append((region, p, m, 200))
                    print(f"  soft-404 (200, not PDF) {region}/{p}/{m}")
                else:
                    result.missing.append((region, p, m, resp.status_code))
                    print(f"  {resp.status_code} {region}/{p}/{m}")

    return result


def probe_extensions(f: Fetcher) -> None:
    """Report only. No parsers, no bulk fetching — Task 3b explicitly defers these."""
    print("\n" + "=" * 62)
    print("EXTENSION PROBES — reporting only, nothing parsed")
    print("=" * 62)

    print("\n[1] food69/ — the 2569 round")
    for region in REGIONS:
        url = f"{BASE}/food69/{region}/1/1.pdf"
        try:
            r = f.head(url)
        except httpx.HTTPError as e:
            print(f"  {region:<10} ERROR {type(e).__name__}")
            continue
        if r is None:
            continue
        ct = r.headers.get("content-type", "?")
        print(f"  {region:<10} HTTP {r.status_code}  {ct}")

    print("\n[2] flat-numbered /{n}/{n}.pdf — an earlier round")
    hits = []
    for n in range(1, 78):
        url = f"{BASE}/{n}/{n}.pdf"
        try:
            r = f.head(url)
        except httpx.HTTPError:
            continue
        if r is None:
            continue
        if r.status_code == 200:
            hits.append((n, r.headers.get("content-length", "?")))
    print(f"  {len(hits)}/77 resolve")
    if hits:
        preview = ", ".join(str(n) for n, _ in hits[:20])
        print(f"  n = {preview}{' …' if len(hits) > 20 else ''}")

    print("\n[3] bookfood67/ — the 2567 FlipBuilder volume")
    for path in ("/bookfood67/", "/bookfood67/index.html", "/bookfood67/mobile/index.html"):
        try:
            r = f.head(BASE + path)
        except httpx.HTTPError as e:
            print(f"  {path:<32} ERROR {type(e).__name__}")
            continue
        if r is None:
            continue
        print(f"  {path:<32} HTTP {r.status_code}  {r.headers.get('content-type','?')}")


def write_log(result: Result) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["region", "province_index", "menu_index", "outcome",
                    "http_status", "sha256", "bytes"])
        for region, p, m, digest, size in result.fetched:
            w.writerow([region, p, m, "fetched", 200, digest, size])
        for region, p, m, status in result.missing:
            w.writerow([region, p, m, "missing", status, "", ""])
    print(f"\nenumeration log -> {LOG_PATH}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, help="stop after N network fetches")
    ap.add_argument("--region", choices=sorted(REGIONS), help="restrict to one region")
    ap.add_argument("--probe-only", action="store_true", help="run the extension probes only")
    args = ap.parse_args()

    robots = urllib.robotparser.RobotFileParser()
    robots.set_url(ROBOTS)
    robots.read()
    print(f"robots.txt re-checked at run time: {ROBOTS}")

    headers = {"User-Agent": user_agent()}
    with httpx.Client(headers=headers, timeout=TIMEOUT_SEC, follow_redirects=True) as client:
        f = Fetcher(client, robots)

        if not args.probe_only:
            print(f"\nenumerating food68/ — max {sum(REGIONS.values()) * MENUS_PER_PROVINCE} documents")
            result = enumerate_food68(f, args.limit, args.region)
            write_log(result)
            print(f"\nfetched {len(result.fetched)}  missing {len(result.missing)}  errors {len(result.errors)}")
            by_region: dict[str, int] = {}
            for region, *_ in result.fetched:
                by_region[region] = by_region.get(region, 0) + 1
            for region in REGIONS:
                print(f"  {region:<10} {by_region.get(region, 0):>3} documents")

        if args.limit is None:
            probe_extensions(f)

    print("\nProvince labels are NOT taken from these URLs. Parsing (Task 3d) reads §1.1.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
