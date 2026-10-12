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
coverage artifact and is written to ``data/raw/dcp_food/_enumeration_log.csv``, with each
document's URL and, for a document fetched in that run, its UTC fetch time. A document
already on disk is not re-fetched, so its fetch time is left blank, never guessed.

The original 2026-08-16 log has no URL or time columns. ``--reconstruct-log`` rebuilds
the URLs from its (region, province, menu) triples, with no network, into
``data/interim/dcp_enumeration_log_reconstructed.csv``; ``data/raw/`` is not touched.
The timestamp gap is recorded in ETHICS.md.

Conduct (rule 7): 1 request/second minimum, identifying User-Agent carrying
SCRAPER_CONTACT_EMAIL, robots.txt re-checked at run time rather than trusted from the
audit. See ETHICS.md for the content-signal question and docs/decisions.md HD-3 for why
this source is currently used under option C — reference layer only, excluded from any
public release.
"""

from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from src.config import DATA_DIR, RAW_DIR
from src.scrape.conduct import PoliteFetcher, load_robots, make_client, user_agent
from src.scrape.ethics import require_go

BASE = "https://food.culture.go.th"
ROBOTS = f"{BASE}/robots.txt"
OUT_DIR = RAW_DIR / "dcp_food"
LOG_PATH = OUT_DIR / "_enumeration_log.csv"
RECONSTRUCTED_LOG = DATA_DIR / "interim" / "dcp_enumeration_log_reconstructed.csv"
LOG_COLUMNS = ["region", "province_index", "menu_index", "url", "fetched_at", "outcome",
               "http_status", "sha256", "bytes"]
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


def doc_url(region: str, province_index: int, menu_index: int) -> str:
    """The one place a document URL is built."""
    return f"{BASE}/food68/{region}/{province_index}/{menu_index}.pdf"


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")


@dataclass
class Result:
    # (region, province, menu, sha256, bytes, fetched_at or None when already on disk)
    fetched: list[tuple[str, int, int, str, int, str | None]] = field(default_factory=list)
    # (region, province, menu, http_status, fetched_at)
    missing: list[tuple[str, int, int, int, str]] = field(default_factory=list)
    errors: list[tuple[str, str]] = field(default_factory=list)


def is_pdf(body: bytes) -> bool:
    return body[:5] == b"%PDF-"


def enumerate_food68(f: PoliteFetcher, limit: int | None, only_region: str | None) -> Result:
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
                        (region, p, m, hashlib.sha256(body).hexdigest(), len(body), None)
                    )
                    continue

                url = doc_url(region, p, m)
                n += 1
                try:
                    at = _now()
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
                    result.fetched.append((region, p, m, digest, len(resp.content), at))
                    print(f"  ok   {region}/{p}/{m}  {len(resp.content):>8,}B  {digest[:12]}")
                elif resp.status_code == 404:
                    result.missing.append((region, p, m, 404, at))
                elif resp.status_code == 200:
                    # 200 but not a PDF — usually a soft-404 HTML page.
                    result.missing.append((region, p, m, 200, at))
                    print(f"  soft-404 (200, not PDF) {region}/{p}/{m}")
                else:
                    result.missing.append((region, p, m, resp.status_code, at))
                    print(f"  {resp.status_code} {region}/{p}/{m}")

    return result


def probe_extensions(f: PoliteFetcher) -> None:
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


def write_log(result: Result, path: Path = LOG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(LOG_COLUMNS)
        for region, p, m, digest, size, at in result.fetched:
            w.writerow([region, p, m, doc_url(region, p, m), at or "", "fetched", 200,
                        digest, size])
        for region, p, m, status, at in result.missing:
            w.writerow([region, p, m, doc_url(region, p, m), at, "missing", status, "", ""])
    print(f"\nenumeration log -> {path}")


def reconstruct_log(source: Path = LOG_PATH, out: Path = RECONSTRUCTED_LOG) -> int:
    """Copy an original (URL-less) log with each row's URL rebuilt from its triple and a
    blank ``fetched_at``. Reads `source`, writes `out`; returns the row count."""
    with source.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=LOG_COLUMNS)
        w.writeheader()
        for row in rows:
            url = doc_url(row["region"], int(row["province_index"]), int(row["menu_index"]))
            w.writerow({**row, "url": url, "fetched_at": row.get("fetched_at", "")})
    return len(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, help="stop after N network fetches")
    ap.add_argument("--region", choices=sorted(REGIONS), help="restrict to one region")
    ap.add_argument("--probe-only", action="store_true", help="run the extension probes only")
    ap.add_argument("--reconstruct-log", action="store_true",
                    help="rebuild URLs for the existing log into data/interim/; no network")
    args = ap.parse_args()

    if args.reconstruct_log:
        n = reconstruct_log()
        print(f"{n} rows -> {RECONSTRUCTED_LOG} (fetched_at blank: not recorded in 2026-08)")
        return 0

    ua = user_agent()
    require_go("dcp_food")  # docs/scraping_rules.md §1: no crawl without a recorded go
    with make_client(ua, timeout=TIMEOUT_SEC) as client:
        robots = load_robots(client, BASE, ua)
        print(f"robots.txt re-checked at run time: {ROBOTS}")
        f = PoliteFetcher(client, robots, ua)

        if not args.probe_only:
            max_docs = sum(REGIONS.values()) * MENUS_PER_PROVINCE
            print(f"\nenumerating food68/ — max {max_docs} documents")
            result = enumerate_food68(f, args.limit, args.region)
            write_log(result)
            print(
                f"\nfetched {len(result.fetched)}  missing {len(result.missing)}  "
                f"errors {len(result.errors)}"
            )
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
