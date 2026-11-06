"""HD-15 / T1.12: the researcher's ที่มา coding → ``recipe_ingredients.acquisition_modes``.

    uv run python -m scripts.acquisition --generate   (make acquisition-sheet)
    uv run python -m scripts.acquisition              (make acquisition; also make lexicon)

**HD-15, decided 2026-11-06: C.** The researcher hand-codes the DCP form's ที่มา strings.
Every mode the text names is stored (iii). Place-only text gets ``local``. Non-source
text (units, citations, ``[REDACTED]``) is coded ``none``. Uncoded strings stay NULL.
Nothing here infers a mode: the parser's keyword hints were removed under the same
decision, and the ``acquisition_mode`` keys still inside older ``parsed_json`` are never
read.

**The coding file** ``data/reference/acquisition_map.csv`` (gitignored: DCP-derived
strings, some with district detail; HD-3, HD-21). Columns:

``rank``, ``acquisition_raw``, ``n_rows``, ``n_recipes``
    Written by ``--generate``: strings ranked by how many official ingredient rows carry
    them, so coding top-down covers the most rows first.
``modes``
    **The researcher's.** Empty = not coded yet. Otherwise ``|``-separated values from
    ``grown | foraged | market | packaged | local``, or ``none``.
``note``
    The researcher's, free text. Never read by code.

``--generate`` is merge-safe. ``modes`` and ``note`` are kept for every string already in
the file. New strings are appended in rank order. A string no longer in the corpus is
kept with ``n_rows`` 0, never deleted. Ranks and counts are refreshed.

**Loading** (the default run):
1. The whole file replaces ``acquisition_map``. Coded rows only; ``none`` → modes NULL.
2. For each official ingredient line whose ที่มา text is coded, the line is mapped to
   entries with the same lexicon lookup ``canonicalise`` uses.
3. ``acquisition_modes`` is set on those ``recipe_ingredients`` rows to the union of the
   modes of every line that maps to the row. Every other row is NULL.

``make lexicon`` runs this after ``canonicalise``, whose rebuild clears the column.

**Coverage report**, printed on every run: lines with ที่มา text; coded strings and the
lines they cover; ``recipe_ingredients`` rows with modes, by mode, and multi-mode rows.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg

from scripts.canonicalise import lookup
from src.config import REFERENCE_DIR
from src.db import get_connection

MAP_FILE = REFERENCE_DIR / "acquisition_map.csv"
COLUMNS = ("rank", "acquisition_raw", "n_rows", "n_recipes", "modes", "note")
MODES = ("grown", "foraged", "market", "packaged", "local")
NONE = "none"

LINES_QUERY = """
SELECT r.recipe_id, i ->> 'name_th', i ->> 'acquisition_raw'
  FROM recipes r
  JOIN raw_recipes rr ON rr.raw_id = r.raw_id
  CROSS JOIN LATERAL jsonb_array_elements(
      COALESCE(rr.parsed_json -> 'ingredients', '[]'::jsonb)) AS i
 WHERE r.register = 'official'
"""


class CodingError(ValueError):
    """The coding file holds a value HD-15 does not allow."""


def norm(text: str | None) -> str:
    """The key a ที่มา string is coded under: whitespace collapsed."""
    return " ".join((text or "").split())


@dataclass(frozen=True)
class Line:
    recipe_id: int
    name_th: str
    acquisition_raw: str          # normalised; "" when the form gives none


def parse_modes(value: str, where: str) -> tuple[str, ...] | None:
    """``""`` → not coded (raises nothing; caller skips); ``none`` → (); else modes."""
    value = value.strip()
    if value.lower() == NONE:
        return ()
    modes = tuple(dict.fromkeys(m.strip() for m in value.split("|") if m.strip()))
    bad = [m for m in modes if m not in MODES]
    if bad or not modes:
        raise CodingError(f"{where}: modes {value!r}: allowed {' | '.join(MODES)} or {NONE}")
    return modes


def read_map(path: Path = MAP_FILE) -> dict[str, tuple[str, ...]]:
    """Coded strings only: key → modes (``()`` = coded none)."""
    if not path.exists():
        return {}
    out: dict[str, tuple[str, ...]] = {}
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise CodingError(f"{path.name}: header must be {','.join(COLUMNS)}")
        for n, row in enumerate(reader, 2):
            if not (row["modes"] or "").strip():
                continue
            modes = parse_modes(row["modes"], f"{path.name} line {n}")
            if modes is not None:
                out[norm(row["acquisition_raw"])] = modes
    return out


def ranked(lines: list[Line]) -> list[tuple[str, int, int]]:
    """(string, rows, recipes), most rows first, ties by string."""
    rows = Counter(ln.acquisition_raw for ln in lines if ln.acquisition_raw)
    recipes: dict[str, set[int]] = defaultdict(set)
    for ln in lines:
        if ln.acquisition_raw:
            recipes[ln.acquisition_raw].add(ln.recipe_id)
    return sorted(((s, n, len(recipes[s])) for s, n in rows.items()),
                  key=lambda t: (-t[1], t[0]))


def merge_sheet(lines: list[Line], existing: list[dict[str, str]]) -> list[dict[str, str]]:
    """The regenerated sheet: corpus strings in rank order, then strings the researcher
    already has that are gone from the corpus (n_rows 0). modes and note always kept."""
    kept = {norm(r["acquisition_raw"]): r for r in existing}
    out = []
    seen = set()
    for i, (s, n, n_rec) in enumerate(ranked(lines), 1):
        old = kept.get(s, {})
        out.append({"rank": str(i), "acquisition_raw": s, "n_rows": str(n),
                    "n_recipes": str(n_rec), "modes": old.get("modes", ""),
                    "note": old.get("note", "")})
        seen.add(s)
    for s, old in kept.items():
        if s not in seen:
            out.append({"rank": "", "acquisition_raw": s, "n_rows": "0", "n_recipes": "0",
                        "modes": old.get("modes", ""), "note": old.get("note", "")})
    return out


def write_sheet(rows: list[dict[str, str]], path: Path = MAP_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)


def modes_by_row(lines: list[Line], coding: dict[str, tuple[str, ...]],
                 entries_for: Any) -> dict[tuple[int, str], tuple[str, ...]]:
    """(recipe_id, canonical_id) → union of the coded modes of every line mapping to it,
    in HD-15's order. Lines coded ``none`` or uncoded add nothing."""
    acc: dict[tuple[int, str], set[str]] = defaultdict(set)
    for ln in lines:
        modes = coding.get(ln.acquisition_raw)
        if not modes:
            continue
        for cid in entries_for(ln.name_th):
            acc[(ln.recipe_id, cid)].update(modes)
    return {k: tuple(m for m in MODES if m in v) for k, v in acc.items()}


@dataclass
class Coverage:
    lines: int
    with_text: int
    strings: int
    coded_strings: int
    coded_none: int
    lines_coded: int
    rows_with_modes: int
    by_mode: dict[str, int]
    multi_mode_rows: int

    def report(self) -> str:
        pct = 100 * self.lines_coded / self.with_text if self.with_text else 0.0
        modes = ", ".join(f"{m} {self.by_mode.get(m, 0)}" for m in MODES)
        return (f"official ingredient lines {self.lines}; with ที่มา text {self.with_text} "
                f"in {self.strings} distinct strings\n"
                f"coded strings {self.coded_strings} (of which none: {self.coded_none}); "
                f"lines covered {self.lines_coded} of {self.with_text} ({pct:.1f}%)\n"
                f"recipe_ingredients rows with modes {self.rows_with_modes}: {modes}; "
                f"multi-mode {self.multi_mode_rows}")


def coverage(lines: list[Line], coding: dict[str, tuple[str, ...]],
             rows: dict[tuple[int, str], tuple[str, ...]]) -> Coverage:
    with_text = [ln for ln in lines if ln.acquisition_raw]
    by_mode: Counter[str] = Counter(m for modes in rows.values() for m in modes)
    present = {ln.acquisition_raw for ln in with_text}
    return Coverage(
        lines=len(lines), with_text=len(with_text), strings=len(present),
        coded_strings=sum(1 for s in coding if s in present),
        coded_none=sum(1 for s, m in coding.items() if s in present and not m),
        lines_coded=sum(1 for ln in with_text if ln.acquisition_raw in coding),
        rows_with_modes=len(rows), by_mode=dict(by_mode),
        multi_mode_rows=sum(1 for m in rows.values() if len(m) > 1),
    )


def read_lines(conn: psycopg.Connection[Any]) -> list[Line]:
    return [Line(rid, name or "", norm(raw))
            for rid, name, raw in conn.execute(LINES_QUERY).fetchall()]


def apply(conn: psycopg.Connection[Any], coding: dict[str, tuple[str, ...]],
          rows: dict[tuple[int, str], tuple[str, ...]]) -> int:
    """Replace acquisition_map and recipe_ingredients.acquisition_modes in one transaction.
    Returns the number of rows given modes, read back after commit."""
    conn.commit()          # end the implicit read transaction (see scripts/apply_labels.py)
    with conn.transaction():
        conn.execute("DELETE FROM acquisition_map")
        for s, modes in sorted(coding.items()):
            conn.execute("INSERT INTO acquisition_map (acquisition_raw, modes) VALUES (%s, %s)",
                         (s, list(modes) or None))
        conn.execute("UPDATE recipe_ingredients SET acquisition_modes = NULL "
                     "WHERE acquisition_modes IS NOT NULL")
        for (rid, cid), modes in rows.items():
            conn.execute("UPDATE recipe_ingredients SET acquisition_modes = %s "
                         "WHERE recipe_id = %s AND canonical_id = %s", (list(modes), rid, cid))
    (n,) = conn.execute("SELECT count(*) FROM recipe_ingredients "
                        "WHERE acquisition_modes IS NOT NULL").fetchone()  # type: ignore[misc]
    return int(n)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--generate", action="store_true",
                    help="write/refresh the ranked coding file (merge-safe), then report")
    ap.add_argument("--map", type=Path, default=MAP_FILE)
    ap.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    args = ap.parse_args(argv)
    conn = get_connection()
    try:
        lines = read_lines(conn)
        if args.generate:
            existing: list[dict[str, str]] = []
            if args.map.exists():
                with args.map.open(encoding="utf-8", newline="") as f:
                    existing = list(csv.DictReader(f))
            sheet = merge_sheet(lines, existing)
            if not args.dry_run:
                write_sheet(sheet, args.map)
                print(f"wrote {args.map} ({len(sheet)} strings; "
                      f"{sum(1 for r in sheet if r['modes'].strip())} already coded)")
        try:
            coding = read_map(args.map)
        except CodingError as e:
            print(f"acquisition: {e}")
            return 1
        rows = modes_by_row(lines, coding, lookup(conn))
        print(coverage(lines, coding, rows).report())
        if not args.map.exists():
            print(f"no coding file at {args.map}: run `make acquisition-sheet`")
        if args.dry_run or args.generate:
            return 0
        n = apply(conn, coding, rows)
        print(f"recipe_ingredients now holds {n} rows with acquisition modes "
              "(read back after commit)")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
