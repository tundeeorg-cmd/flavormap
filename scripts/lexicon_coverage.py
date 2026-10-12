"""Mention coverage of the lexicon, after each authoring batch (TIMELINE T1.17).

    uv run python -m scripts.lexicon_coverage        (also run by: make lexicon)

What share of the corpus's ingredient mentions the researcher's lexicon maps so far,
measured against T1.16's targets: at least 150 canonical entries, and at least 80% of
ingredient mentions mapped.

**A mention** is one distinct ingredient string in one recipe: a (recipe, string) pair,
counted exactly as `scripts.lexicon_worklist` counts them (the same query, the same
`key()` comparison, the same mapping index). A mention is **mapped** when its string is a
lexicon Thai name or an approved alias, and **conflicting** when it maps to two entries,
which the loader should have refused.

**Read the per-register rows, not only the total.** Kapook strings are whole lines with
quantities (``พริกแห้ง 5 เม็ด``), because stripping quantities is the unbuilt §7.2
cleaning step. An entry named ``พริกแห้ง`` maps the DCP mention and not the kapook line,
so the commercial share stays low until that step exists or the line is an alias. That is
a fact about the pipeline, not about the lexicon's progress.

**What is committed.** ``data/coverage/lexicon_YYYYMMDD.csv`` holds counts only: no
ingredient string, nothing DCP-derived. It is committed under the same rule as HD-28's
status snapshots (`.gitignore`). This script never writes to the database and never
suggests a mapping (the HD-6 boundary).
"""

from __future__ import annotations

import argparse
import csv
import datetime
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from scripts.lexicon_worklist import CONFLICT, MAPPED_QUERY, QUERY, mapping_index
from src.clean.lexicon import key
from src.config import DATA_DIR
from src.db import get_connection

COVERAGE_DIR = DATA_DIR / "coverage"
TARGET_ENTRIES = 150
TARGET_SHARE = 0.80
COLUMNS = ("snapshot_date", "scope", "mentions", "mapped", "conflicting", "mapped_share",
           "strings", "strings_mapped")


@dataclass(frozen=True)
class Coverage:
    scope: str
    mentions: int
    mapped: int
    conflicting: int
    strings: int
    strings_mapped: int

    @property
    def share(self) -> float:
        return self.mapped / self.mentions if self.mentions else 0.0


def coverage(
    rows: Iterable[tuple[str, str, int, str | None]],
    index: dict[str, tuple[str, str]],
) -> list[Coverage]:
    """Coverage overall, per register and per source, from worklist-shaped rows
    ``(source_id, register, recipe_id, raw string)``."""
    mentions = {(src, reg, rid, key(s)) for src, reg, rid, s in rows if s and key(s)}

    def measure(scope: str, subset: set[tuple[str, str, int, str]]) -> Coverage:
        status = Counter(
            "conflict" if (hit := index.get(k)) and hit[0] == CONFLICT
            else "mapped" if hit else "unmapped"
            for *_, k in subset
        )
        strings = {k for *_, k in subset}
        return Coverage(scope, len(subset), status["mapped"], status["conflict"],
                        len(strings), sum(1 for k in strings
                                          if (h := index.get(k)) and h[0] != CONFLICT))

    out = [measure("all", mentions)]
    for register in sorted({m[1] for m in mentions}):
        out.append(measure(f"register:{register}", {m for m in mentions if m[1] == register}))
    for source in sorted({m[0] for m in mentions}):
        out.append(measure(f"source:{source}", {m for m in mentions if m[0] == source}))
    return out


def write_snapshot(results: list[Coverage], day: datetime.date, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"lexicon_{day:%Y%m%d}.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        w = csv.writer(handle)
        w.writerow(COLUMNS)
        for c in results:
            w.writerow((day.isoformat(), c.scope, c.mentions, c.mapped, c.conflicting,
                        f"{c.share:.4f}", c.strings, c.strings_mapped))
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=COVERAGE_DIR)
    args = ap.parse_args()
    with get_connection() as conn:
        conn.read_only = True
        rows = conn.execute(QUERY).fetchall()
        index = mapping_index(conn.execute(MAPPED_QUERY).fetchall())
        entries = conn.execute("SELECT count(*) FROM canonical_ingredients").fetchone()[0]
    results = coverage(rows, index)
    path = write_snapshot(results, datetime.date.today(), args.out_dir)

    total = results[0]
    print(f"lexicon entries     {entries}  (T1.16 target ≥ {TARGET_ENTRIES})")
    print(f"mentions mapped     {total.mapped} of {total.mentions} = {total.share:.1%}  "
          f"(T1.16 target ≥ {TARGET_SHARE:.0%})")
    if total.conflicting:
        print(f"CONFLICTING         {total.conflicting} mentions map to two entries")
    for c in results[1:]:
        print(f"  {c.scope:<28} {c.mapped:>6} / {c.mentions:<6} {c.share:6.1%}")
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
