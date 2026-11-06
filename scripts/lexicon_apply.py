"""Turn the researcher's filled worksheet into lexicon rows (HD-6).

    uv run python -m scripts.lexicon_apply [--sheet data/interim/lexicon_groups.csv] [--write]
    (or: make lexicon-apply, then make lexicon)

Reads the ``group_decision`` and ``decision`` columns the researcher filled in
`scripts/lexicon_groups.py`'s worksheet and appends the matching rows to
``data/reference/lexicon/ingredient_aliases.csv`` (one entry) or
``ingredient_splits.csv`` (two or more entries, HD-6 Q5), or ``ingredient_exclusions.csv``
(``exclude``: not a flavour ingredient). **It only copies decisions.**
A blank decision is no decision: the string stays unmapped. Nothing is inferred from the
suggested group, the string or anything else.

How a row's decision is read:

- ``decision`` filled → that, for this string only. ``skip`` means leave it unmapped.
- ``decision`` blank and the group's first row has ``group_decision`` → that.
- ``exclude`` lists the string as not an ingredient (water, ice, equipment …); it maps
  to nothing and the coverage report leaves it out of the share.
- ``ING_0001`` maps; ``ING_0001|ING_0002`` splits. Ids must already be entries in
  ``canonical_ingredients.csv``; the entries themselves (name, gloss, category) are
  written by the researcher by hand.

Without ``--write`` it prints what it would add and changes nothing. With ``--write`` it
appends, then validates the whole lexicon with `src.clean.lexicon.read_lexicon`; if the
result does not validate, both files are restored and nothing changes.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from scripts.lexicon_groups import OUT as SHEET
from src.clean.lexicon import (
    ALIASES_FILE,
    CANONICAL_ID,
    EXCLUSION_COLUMNS,
    EXCLUSIONS_FILE,
    SPLITS_FILE,
    LexiconError,
    key,
    read_lexicon,
)
from src.config import REFERENCE_DIR

LEXICON_DIR = REFERENCE_DIR / "lexicon"
SKIP = "skip"
EXCLUDE = "exclude"
_SEP = re.compile(r"\s*[|;/]\s*")


@dataclass(frozen=True)
class Planned:
    aliases: list[tuple[str, str]]             # (alias, canonical_id)
    splits: list[tuple[str, tuple[str, ...]]]  # (alias, canonical_ids)
    exclusions: list[str]                       # aliases
    already: int                                # decided strings already in the lexicon
    errors: list[str]


def decisions(sheet: list[dict[str, str]]) -> list[tuple[int, str, str]]:
    """``(line, raw string, decision)`` for every row with a decision, ``skip``
    excluded. Line numbers are the CSV's, header = 1."""
    group_default: dict[str, str] = {}
    for row in sheet:
        g = row["group_rank"]
        if g not in group_default and row.get("group_decision", "").strip():
            group_default[g] = row["group_decision"].strip()
    out = []
    for line, row in enumerate(sheet, 2):
        own = row.get("decision", "").strip()
        chosen = own or group_default.get(row["group_rank"], "")
        if chosen and chosen.lower() != SKIP:
            out.append((line, row["name_th"], chosen))
    return out


def plan(sheet: list[dict[str, str]], directory: Path) -> Planned:
    lexicon = read_lexicon(directory)
    ids = {c.canonical_id for c in lexicon.canonicals}
    aliases: list[tuple[str, str]] = []
    splits: list[tuple[str, tuple[str, ...]]] = []
    exclusions: list[str] = []
    errors: list[str] = []
    already = 0
    seen: dict[str, tuple[str, ...]] = {}
    for line, raw, chosen in decisions(sheet):
        if chosen.lower() == EXCLUDE:
            k = key(raw)
            if k in seen and seen[k] != (EXCLUDE,):
                errors.append(f"line {line}: {raw}: decided twice, differently")
                continue
            seen[k] = (EXCLUDE,)
            if lexicon.is_excluded(raw):
                already += 1
            elif current := lexicon.entries_for(raw):
                errors.append(f"line {line}: {raw}: already maps to "
                              f"{'|'.join(current)}; change it in the lexicon files by hand")
            elif raw not in exclusions:
                exclusions.append(raw)
            continue
        parts = tuple(p for p in _SEP.split(chosen) if p)
        bad = [p for p in parts if not CANONICAL_ID.fullmatch(p)]
        if bad:
            errors.append(f"line {line}: {raw}: {', '.join(bad)} is not an entry id "
                          "(ING_ and 4 digits), 'skip' or 'exclude'")
            continue
        missing = [p for p in parts if p not in ids]
        if missing:
            errors.append(f"line {line}: {raw}: {', '.join(missing)} not in "
                          "canonical_ingredients.csv yet; add the entry first")
            continue
        if len(set(parts)) != len(parts):
            errors.append(f"line {line}: {raw}: an id is repeated")
            continue
        k = key(raw)
        if k in seen and seen[k] != parts:
            errors.append(f"line {line}: {raw}: decided twice, differently")
            continue
        seen[k] = parts
        if lexicon.is_excluded(raw):
            errors.append(f"line {line}: {raw}: is excluded; change it in the lexicon "
                          "files by hand")
            continue
        current = lexicon.entries_for(raw)
        if current:
            if tuple(sorted(current)) == tuple(sorted(parts)):
                already += 1
            else:
                errors.append(f"line {line}: {raw}: already maps to "
                              f"{'|'.join(current)}; change it in the lexicon files by hand")
            continue
        if len(parts) == 1:
            aliases.append((raw, parts[0]))
        else:
            splits.append((raw, parts))
    return Planned(aliases, splits, exclusions, already, errors)


def append(directory: Path, planned: Planned) -> None:
    files = [directory / ALIASES_FILE, directory / SPLITS_FILE, directory / EXCLUSIONS_FILE]
    backups = {f: f.read_bytes() if f.exists() else None for f in files}
    try:
        with (directory / ALIASES_FILE).open("a", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            for alias, cid in planned.aliases:
                w.writerow([alias, cid])
        split_path = directory / SPLITS_FILE
        new = not split_path.exists()
        with split_path.open("a", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["alias", "canonical_id"])
            for alias, parts in planned.splits:
                for cid in parts:
                    w.writerow([alias, cid])
        excl_path = directory / EXCLUSIONS_FILE
        new = not excl_path.exists()
        with excl_path.open("a", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(EXCLUSION_COLUMNS)
            for alias in planned.exclusions:
                w.writerow([alias, ""])
        read_lexicon(directory)
    except (LexiconError, OSError):
        for f, content in backups.items():
            if content is None:
                f.unlink(missing_ok=True)
            else:
                f.write_bytes(content)
        raise


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sheet", type=Path, default=SHEET)
    ap.add_argument("--dir", type=Path, default=LEXICON_DIR)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    with args.sheet.open(encoding="utf-8", newline="") as f:
        sheet = list(csv.DictReader(f))
    try:
        planned = plan(sheet, args.dir)
    except LexiconError as e:
        print(f"the lexicon files do not validate; fix them first:\n{e}", file=sys.stderr)
        return 1
    for e in planned.errors:
        print(f"refused  {e}", file=sys.stderr)
    print(f"{len(planned.aliases)} aliases, {len(planned.splits)} splits and "
          f"{len(planned.exclusions)} exclusions to add; "
          f"{planned.already} decided strings already in the lexicon; "
          f"{len(planned.errors)} refused")
    if planned.errors:
        print("nothing written: fix the refused rows first", file=sys.stderr)
        return 1
    if not args.write:
        print("dry run: add --write to append them")
        return 0
    try:
        append(args.dir, planned)
    except LexiconError as e:
        print(f"refused, files restored:\n{e}", file=sys.stderr)
        return 1
    print(f"appended to {args.dir}; now run `make lexicon`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
