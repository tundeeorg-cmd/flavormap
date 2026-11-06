"""Mention coverage of the lexicon, after each authoring batch (TIMELINE T1.17).

    uv run python -m scripts.lexicon_coverage        (also run by: make lexicon)

What share of the corpus's ingredient mentions the researcher's lexicon maps so far,
measured against T1.16's targets: at least 150 canonical entries, and at least 80% of
ingredient mentions mapped.

**A mention** is one distinct ingredient string in one recipe: a (recipe, string) pair,
counted exactly as `scripts.lexicon_worklist` counts them (the same query, the same
`key()` comparison, the same mapping index). A mention is **mapped** when its string is a
lexicon Thai name or an approved alias, **excluded** when the researcher listed its
string in ``ingredient_exclusions.csv`` as not a flavour ingredient, and **conflicting**
when it maps to two entries, which the loader should have refused.

**The share leaves excluded mentions out of the denominator:** ``mapped / (mentions −
excluded)``. Water, ice and equipment are not gaps in the lexicon, so they neither help
nor hurt the T1.16 target. ``mentions`` and ``excluded`` are both reported, so the
unadjusted share can always be recomputed.

**Read the per-register rows, not only the total.** Kapook strings are whole lines with
quantities (``พริกแห้ง 5 เม็ด``), because stripping quantities is the unbuilt §7.2
cleaning step. An entry named ``พริกแห้ง`` maps the DCP mention and not the kapook line,
so the commercial share stays low until that step exists or the line is an alias. That is
a fact about the pipeline, not about the lexicon's progress.

**Re-run after each batch** (``make lexicon``: load, canonicalise, report). Each scope
shows its change since the newest earlier snapshot. A split string (HD-6 Q5) counts as
mapped.

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

from scripts.lexicon_worklist import CONFLICT, EXCLUDED, MAPPED_QUERY, QUERY, mapping_index
from src.clean.lexicon import key
from src.config import DATA_DIR
from src.db import get_connection

COVERAGE_DIR = DATA_DIR / "coverage"
TARGET_ENTRIES = 150
TARGET_SHARE = 0.80
COLUMNS = ("snapshot_date", "scope", "mentions", "mapped", "conflicting", "excluded",
           "mapped_share", "strings", "strings_mapped")


@dataclass(frozen=True)
class Coverage:
    scope: str
    mentions: int
    mapped: int
    conflicting: int
    strings: int
    strings_mapped: int
    excluded: int = 0

    @property
    def share(self) -> float:
        """Mapped share of the mentions that are ingredients (excluded ones left out)."""
        base = self.mentions - self.excluded
        return self.mapped / base if base else 0.0


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
            else "excluded" if hit and hit[0] == EXCLUDED
            else "mapped" if hit else "unmapped"
            for *_, k in subset
        )
        strings = {k for *_, k in subset}
        return Coverage(scope, len(subset), status["mapped"], status["conflict"],
                        len(strings),
                        sum(1 for k in strings if (h := index.get(k))
                            and h[0] not in (CONFLICT, EXCLUDED)),
                        status["excluded"])

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
                        c.excluded, f"{c.share:.4f}", c.strings, c.strings_mapped))
    return path


def previous_snapshot(out_dir: Path, before: datetime.date) -> dict[str, tuple[int, int]]:
    """``{scope: (mapped, mentions − excluded)}`` from the newest snapshot dated before
    `before`, so each batch's report shows what the batch moved. Empty when there is
    none. Snapshots written before exclusions existed have no ``excluded`` column (0)."""
    older = sorted(p for p in out_dir.glob("lexicon_*.csv")
                   if p.stem.removeprefix("lexicon_") < f"{before:%Y%m%d}")
    if not older:
        return {}
    with older[-1].open(encoding="utf-8", newline="") as handle:
        return {r["scope"]: (int(r["mapped"]),
                             int(r["mentions"]) - int(r.get("excluded") or 0))
                for r in csv.DictReader(handle)}


def _delta(c: Coverage, before: dict[str, tuple[int, int]]) -> str:
    if c.scope not in before:
        return ""
    mapped, mentions = before[c.scope]
    old = mapped / mentions if mentions else 0.0
    return f"  ({c.share - old:+.1%} since last snapshot)"


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
    today = datetime.date.today()
    before = previous_snapshot(args.out_dir, today)
    path = write_snapshot(results, today, args.out_dir)

    total = results[0]
    print(f"lexicon entries     {entries}  (T1.16 target ≥ {TARGET_ENTRIES})")
    print(f"mentions mapped     {total.mapped} of {total.mentions - total.excluded} = "
          f"{total.share:.1%}  (T1.16 target ≥ {TARGET_SHARE:.0%}){_delta(total, before)}")
    if total.excluded:
        print(f"excluded            {total.excluded} mentions (not ingredients; left out "
              "of the share)")
    if total.conflicting:
        print(f"CONFLICTING         {total.conflicting} mentions map to two entries")
    for c in results[1:]:
        print(f"  {c.scope:<28} {c.mapped:>6} / {c.mentions - c.excluded:<6} {c.share:6.1%}"
              f"{_delta(c, before)}")
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
