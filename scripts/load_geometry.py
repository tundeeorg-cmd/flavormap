"""Load Thailand province geometry from GADM v4.1 into `provinces`.

    uv run python -m scripts.load_geometry [--gadm PATH] [--dry-run]

Reads the attribute table from ``data/reference/provinces.csv`` (77 rows: ISO code,
Thai and English names, region4, border_country) and joins it to GADM v4.1 Thailand
level-1 polygons, writing both ``geom`` and the derived centroids.

Why centroids are derived rather than typed. ``provinces.csv`` deliberately ships with
``centroid_lat`` / ``centroid_lon`` empty. Every distance in RQ1 is computed from these
numbers, and 154 coordinates transcribed by hand is 154 chances to introduce an error
that no test would catch and that would quietly bend the distance-decay curve. Deriving
them from the same geometry that draws the maps keeps them reproducible and consistent
with Figure 1.

Centroids use ST_PointOnSurface, not ST_Centroid. A true centroid can fall outside a
concave or multi-part polygon — Phang Nga and Krabi both have geometry where this
happens — and a "province centre" in the Andaman Sea would corrupt distance-decay
without ever looking obviously wrong.

GADM is CC-BY for non-commercial use; cite it in the dataset card.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import zipfile
from pathlib import Path

import httpx

from src.config import REFERENCE_DIR
from src.db import get_connection

GADM_URL = "https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_THA_1.json.zip"
GADM_CACHE = Path("data/raw/reference/gadm41_THA_1.json")

# GADM's NAME_1 spellings that differ from this project's name_en. GADM is the odd one
# out in each case; provinces.csv follows ISO 3166-2:TH.
GADM_NAME_FIXES = {
    "Bangkok Metropolis": "Bangkok",
    "Buriram": "Buri Ram",
    "Chachoengsao": "Chachoengsao",
    "Chainat": "Chai Nat",
    "Chaiyaphum": "Chaiyaphum",
    "Chon Buri": "Chon Buri",
    "Lop Buri": "Lop Buri",
    "Nakhon Si Thammarat": "Nakhon Si Thammarat",
    "Phangnga": "Phangnga",
    "Phatthalung": "Phatthalung",
    "Phra Nakhon Si Ayutthaya": "Phra Nakhon Si Ayutthaya",
    "Prachin Buri": "Prachin Buri",
    "Si Sa Ket": "Si Sa Ket",
    "Sing Buri": "Sing Buri",
    "Ubon Ratchathani": "Ubon Ratchathani",
    "Nong Bua Lam Phu": "Nong Bua Lam Phu",
    "Bueng Kan": "Bueng Kan",
}


def fetch_gadm(url: str = GADM_URL, cache: Path = GADM_CACHE) -> dict:
    """Download and cache the GADM level-1 GeoJSON. Cached forever — it never changes."""
    if cache.exists():
        print(f"using cached {cache}")
        return json.loads(cache.read_text(encoding="utf-8"))

    print(f"downloading {url} …")
    try:
        resp = httpx.get(url, timeout=120.0, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        raise SystemExit(
            f"could not reach GADM: {e}\n\n"
            "Geometry is not loadable without it. Download "
            f"{url}\nby hand, unzip, and place the .json at {cache}, then re-run with\n"
            "  uv run python -m scripts.load_geometry --gadm <path>\n"
            "Nothing is written to the database on this path — provinces.geom and the\n"
            "centroids stay NULL rather than being filled with anything invented."
        ) from e

    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        name = next(n for n in zf.namelist() if n.endswith(".json"))
        payload = zf.read(name).decode("utf-8")

    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(payload, encoding="utf-8")
    print(f"cached to {cache}")
    return json.loads(payload)


def read_reference() -> list[dict[str, str]]:
    path = REFERENCE_DIR / "provinces.csv"
    if not path.exists():
        raise SystemExit(f"{path} not found — build the province reference table first.")
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 77:
        raise SystemExit(f"expected 77 provinces in {path}, found {len(rows)}")
    return rows


def index_gadm(fc: dict) -> dict[str, dict]:
    """Map normalised English province name -> GADM feature."""
    out: dict[str, dict] = {}
    for feat in fc["features"]:
        raw = feat["properties"].get("NAME_1", "")
        out[GADM_NAME_FIXES.get(raw, raw)] = feat
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gadm", type=Path, help="path to a local gadm41_THA_1.json")
    ap.add_argument("--dry-run", action="store_true", help="match only; write nothing")
    args = ap.parse_args()

    reference = read_reference()
    fc = json.loads(args.gadm.read_text(encoding="utf-8")) if args.gadm else fetch_gadm()
    by_name = index_gadm(fc)

    matched, unmatched = [], []
    for row in reference:
        feat = by_name.get(row["name_en"])
        (matched if feat else unmatched).append((row, feat) if feat else row)

    print(f"matched {len(matched)}/77 provinces to GADM geometry")
    if unmatched:
        print("\nUNMATCHED — fix GADM_NAME_FIXES before loading:", file=sys.stderr)
        for row in unmatched:
            print(f"  {row['province_code']}  {row['name_en']}", file=sys.stderr)
        print(f"\nGADM names available:\n  {sorted(by_name)}", file=sys.stderr)
        # Partial loads produce a province table that looks complete and is not.
        raise SystemExit("refusing to load a partial province table")

    if args.dry_run:
        print("dry run — nothing written")
        return 0

    conn = get_connection()
    try:
        for row, feat in matched:
            conn.execute(
                """
                INSERT INTO provinces (province_code, name_th, name_en, region4,
                                       dialect_group, border_country,
                                       centroid_lat, centroid_lon, geom)
                VALUES (%s, %s, %s, %s,
                        NULLIF(%s,''), NULLIF(%s,''),
                        0, 0,
                        ST_Multi(ST_GeomFromGeoJSON(%s)))
                ON CONFLICT (province_code) DO UPDATE SET
                    name_th        = EXCLUDED.name_th,
                    name_en        = EXCLUDED.name_en,
                    region4        = EXCLUDED.region4,
                    dialect_group  = EXCLUDED.dialect_group,
                    border_country = EXCLUDED.border_country,
                    geom           = EXCLUDED.geom
                """,
                (row["province_code"], row["name_th"], row["name_en"], row["region4"],
                 row["dialect_group"], row["border_country"],
                 json.dumps(feat["geometry"])),
            )

        # Derive centroids from the geometry just loaded. ST_PointOnSurface guarantees
        # the point lies inside the polygon; ST_Centroid does not.
        conn.execute(
            """
            UPDATE provinces
               SET centroid_lat = ST_Y(ST_PointOnSurface(geom)),
                   centroid_lon = ST_X(ST_PointOnSurface(geom))
             WHERE geom IS NOT NULL
            """
        )
        conn.commit()

        n, bad = conn.execute(
            """
            SELECT count(*),
                   count(*) FILTER (WHERE NOT ST_Intersects(
                       geom, ST_SetSRID(ST_MakePoint(centroid_lon, centroid_lat), 4326)))
            FROM provinces
            """
        ).fetchone()
        print(f"loaded {n} provinces; {bad} centroid(s) outside their polygon")
    finally:
        conn.close()

    print(
        "\ndialect_group is intentionally NULL for all 77 rows — that is HD-1 and it is "
        "the researcher's to fill."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
