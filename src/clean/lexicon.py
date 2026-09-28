"""Read and validate the hand-authored ingredient lexicon (HD-6, HD-10).

Three CSV files in ``data/reference/lexicon/``, one per table in migration 004:

``canonical_ingredients.csv``
    ``canonical_id, name_th, name_en, category, is_fermented, regional_note,
    decision_note``
``ingredient_aliases.csv``
    ``alias, canonical_id``
``ingredient_conflations.csv``
    ``canonical_id_a, canonical_id_b, reason``

Every row is written by the researcher, so every row loads as ``approved_by_human =
true`` and every alias as ``match_method = 'manual'``. The file is the approval, which is
how rule 4 ("never merge canonical ingredients without [HD] approval") holds.

**IDs are assigned by the researcher** (``ING_0001`` …) and never derived from row order,
so sorting or reordering a file cannot renumber the lexicon under recipes already mapped
to it.

**Each canonical Thai name is also an alias of itself.** A raw string identical to an
entry's name maps to that entry without being listed twice. Listing it in the aliases
file anyway is harmless; pointing it at a *different* entry is refused.

**The conflation guard (CLAUDE.md §13, ``test_conflation_guard``).** A conflation pair
records two entries that look alike but must stay distinct. No alias may map across a
pair: a string that is one member's Thai name must map to that member, never to the
other. Within these files that is already guaranteed — each canonical name is locked to
its own entry above — so the guard runs against the *database*, where aliases can also
arrive by other routes (``CONFLATION_VIOLATIONS``). Pairs are stored with the lower ID
first, so (A, B) and (B, A) are one pair.

**Categories are HD-27's.** ``category`` must be one of ``CATEGORIES``, assigned by
culinary role rather than botany. ``is_fermented`` is a separate, required ``true`` /
``false``: fermentation is an axis, not a category. ``other`` may be at most
``OTHER_CEILING`` of the lexicon; past that the load stops, because HD-27 says the
taxonomy then needs revisiting and the fact belongs in ``docs/limitations.md``. The same
list is a CHECK constraint in migration 023; a test keeps the two in step.

**What this module does not decide.** Strings are compared after NFC normalisation and
whitespace collapsing only (``key()``), the same comparison
``scripts/lexicon_worklist.py`` uses for its ``mapped`` column.

Free-text fields are refused if they carry personal data, as for cook-along logs
(``personal_data_classes()``). These files are committed.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from src.ingest.pdpa import personal_data_classes

CANONICAL_FILE = "canonical_ingredients.csv"
ALIASES_FILE = "ingredient_aliases.csv"
CONFLATIONS_FILE = "ingredient_conflations.csv"

CANONICAL_COLUMNS = ("canonical_id", "name_th", "name_en", "category", "is_fermented",
                     "regional_note", "decision_note")
ALIAS_COLUMNS = ("alias", "canonical_id")
CONFLATION_COLUMNS = ("canonical_id_a", "canonical_id_b", "reason")

CANONICAL_ID = re.compile(r"ING_\d{4}")

# HD-27 (docs/decisions.md, 2026-09-28), in the decision's order. Mirrored by the CHECK
# constraint in db/migrations/023_ingredient_category_taxonomy.sql.
CATEGORIES: tuple[str, ...] = (
    "aromatic", "chilli", "herb", "spice", "vegetable", "fruit", "protein_meat",
    "protein_fish", "protein_other", "coconut", "acid", "fat", "starch", "sweetener",
    "other",
)

# HD-27: `other` stays under 5% of the lexicon.
OTHER_CEILING = 0.05

_WS = re.compile(r"\s+")


def key(text: str) -> str:
    """NFC plus whitespace collapsing, and nothing more. The one string comparison the
    lexicon, its loader and the authoring worklist all share."""
    return _WS.sub(" ", unicodedata.normalize("NFC", text)).strip()


# Aliases in the database that map across a conflation pair: the alias is (by key) the
# Thai name of one member but points at the other. Must return no rows.
CONFLATION_VIOLATIONS = """
SELECT a.alias, a.canonical_id AS maps_to, own.canonical_id AS is_name_of
  FROM ingredient_conflations c
  JOIN canonical_ingredients own ON own.canonical_id IN (c.canonical_id_a, c.canonical_id_b)
  JOIN ingredient_aliases a
    ON normalize(regexp_replace(btrim(a.alias), '\\s+', ' ', 'g'), NFC)
     = normalize(regexp_replace(btrim(own.name_th), '\\s+', ' ', 'g'), NFC)
 WHERE a.canonical_id IN (c.canonical_id_a, c.canonical_id_b)
   AND a.canonical_id <> own.canonical_id
"""


@dataclass(frozen=True)
class CategoryCheck:
    """HD-27's check over the lexicon's entries-per-category counts. The one definition
    shared by ``make status`` and the authoring worklist, so they cannot disagree."""

    total: int
    by_category: dict[str, int]  # every HD-27 category, in HD-27's order, zeros included
    unknown: list[str]           # categories present that are not on HD-27's list
    other: int

    @property
    def other_share(self) -> float:
        return self.other / self.total if self.total else 0.0

    @property
    def over_ceiling(self) -> bool:
        return self.other_share > OTHER_CEILING


def check_categories(entries_by_category: Mapping[str, int]) -> CategoryCheck:
    return CategoryCheck(
        total=sum(entries_by_category.values()),
        by_category={c: entries_by_category.get(c, 0) for c in CATEGORIES},
        unknown=sorted(set(entries_by_category) - set(CATEGORIES)),
        other=entries_by_category.get("other", 0),
    )


class LexiconError(ValueError):
    """The lexicon files cannot be loaded as written."""


@dataclass(frozen=True)
class Canonical:
    canonical_id: str
    name_th: str
    name_en: str
    category: str
    is_fermented: bool
    regional_note: str | None
    decision_note: str | None


@dataclass(frozen=True)
class Conflation:
    canonical_id_a: str
    canonical_id_b: str
    reason: str


@dataclass(frozen=True)
class Lexicon:
    canonicals: list[Canonical]
    aliases: dict[str, str]  # alias -> canonical_id, canonical names included
    conflations: list[Conflation]


def _read(path: Path, columns: tuple[str, ...]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if tuple(reader.fieldnames or ()) != columns:
            raise LexiconError(
                f"{path.name}: header must be exactly {','.join(columns)}"
            )
        return [{k: key(v or "") for k, v in row.items()} for row in reader]


def _optional(value: str) -> str | None:
    return value or None


def read_lexicon(directory: Path) -> Lexicon:
    """Read and validate all three files. Raises one ``LexiconError`` listing every
    problem found, so a single run shows everything that needs fixing."""
    errors: list[str] = []

    canonicals: list[Canonical] = []
    by_id: dict[str, Canonical] = {}
    by_name: dict[str, str] = {}
    for line, row in enumerate(_read(directory / CANONICAL_FILE, CANONICAL_COLUMNS), 2):
        where = f"{CANONICAL_FILE}:{line}"
        cid = row["canonical_id"]
        if not CANONICAL_ID.fullmatch(cid):
            errors.append(f"{where}: canonical_id {cid!r} is not ING_ followed by 4 digits")
        if cid in by_id:
            errors.append(f"{where}: canonical_id {cid} is used twice")
        for column in ("name_th", "name_en", "category"):
            if not row[column]:
                errors.append(f"{where}: {column} is required")
        if row["category"] and row["category"] not in CATEGORIES:
            errors.append(f"{where}: category {row['category']!r} is not in HD-27's list")
        if row["is_fermented"] not in ("true", "false"):
            errors.append(f"{where}: is_fermented must be true or false")
        if row["name_th"] and row["name_th"] in by_name:
            errors.append(
                f"{where}: name_th {row['name_th']} is already {by_name[row['name_th']]}"
            )
        for column in ("regional_note", "decision_note"):
            if classes := personal_data_classes(row[column]):
                errors.append(f"{where}: {column} contains personal data ({', '.join(classes)})")
        entry = Canonical(cid, row["name_th"], row["name_en"], row["category"],
                          row["is_fermented"] == "true",
                          _optional(row["regional_note"]), _optional(row["decision_note"]))
        canonicals.append(entry)
        by_id.setdefault(cid, entry)
        if row["name_th"]:
            by_name.setdefault(row["name_th"], cid)

    n_other = sum(c.category == "other" for c in canonicals)
    if canonicals and n_other / len(canonicals) > OTHER_CEILING:
        errors.append(
            f"{CANONICAL_FILE}: {n_other} of {len(canonicals)} entries "
            f"({n_other / len(canonicals):.1%}) are 'other', over HD-27's "
            f"{OTHER_CEILING:.0%} ceiling. Stop: the taxonomy needs revisiting, and that "
            "goes in docs/limitations.md."
        )

    aliases: dict[str, str] = dict(by_name)
    for line, row in enumerate(_read(directory / ALIASES_FILE, ALIAS_COLUMNS), 2):
        where = f"{ALIASES_FILE}:{line}"
        alias, cid = row["alias"], row["canonical_id"]
        if not alias:
            errors.append(f"{where}: alias is required")
            continue
        if cid not in by_id:
            errors.append(f"{where}: {alias} points at {cid!r}, which is not an entry")
            continue
        if alias in aliases and aliases[alias] != cid:
            if alias in by_name:
                errors.append(f"{where}: {alias} is the name of {by_name[alias]}, "
                              f"so it cannot map to {cid}")
            else:
                errors.append(f"{where}: {alias} maps to both {aliases[alias]} and {cid}")
            continue
        aliases[alias] = cid

    conflations: list[Conflation] = []
    seen_pairs: set[tuple[str, str]] = set()
    for line, row in enumerate(_read(directory / CONFLATIONS_FILE, CONFLATION_COLUMNS), 2):
        where = f"{CONFLATIONS_FILE}:{line}"
        a, b = sorted((row["canonical_id_a"], row["canonical_id_b"]))
        missing = [c for c in (a, b) if c not in by_id]
        if missing:
            errors.append(f"{where}: {', '.join(missing)} not an entry")
            continue
        if a == b:
            errors.append(f"{where}: an entry cannot be conflated with itself")
            continue
        if not row["reason"]:
            errors.append(f"{where}: reason is required")
        if (a, b) in seen_pairs:
            errors.append(f"{where}: pair {a}, {b} is listed twice")
        seen_pairs.add((a, b))
        conflations.append(Conflation(a, b, row["reason"]))

    if errors:
        raise LexiconError("\n".join(errors))
    return Lexicon(canonicals, aliases, conflations)
