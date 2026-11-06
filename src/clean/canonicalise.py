"""Raw ingredient strings → ``recipe_ingredients`` rows, through the researcher's lexicon.

The one step between the hand-authored lexicon (HD-6, HD-10) and every analysis that
reads ``v_recipes_clean``. It maps; it never decides. A string becomes rows only when the
researcher has listed it:

- an entry's Thai name or an ``ingredient_aliases`` alias → one row;
- an ``ingredient_splits`` string (HD-6 Q5, "split all") → one row per entry it names;
- anything else → no row. Unmapped strings stay unmapped and show up in the coverage
  report; nothing is guessed, fuzzy-matched or defaulted (rule 4).

Strings are compared with `src.clean.lexicon.key()`, the same comparison the worklist,
the coverage report and the loader use, so "mapped" means one thing everywhere.

``recipe_ingredients`` keys on ``(recipe_id, canonical_id)``. When two lines of one recipe
map to the same entry (``เกลือ`` and ``เกลือป่น 1 ช้อนชา``, both → เกลือ under HD-6 Q2),
the recipe gets one row and ``raw_text`` keeps every source line, joined by
``RAW_JOIN`` in source order, so nothing the source said is lost.

``extraction_method`` follows the register the line came from: official rows were read
from the DCP forms (``institutional_pdf``), domestic rows from interviews
(``interview``), commercial rows by the web parsers (``rule``). Quantities and
acquisition mode are left NULL: quantity conversion is rule 3's separate step, and
acquisition mode is HD-15 (deferred until after 20 Nov).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

RAW_JOIN = " ‖ "

EXTRACTION_METHOD: dict[str, str] = {
    "official": "institutional_pdf",
    "domestic": "interview",
    "commercial": "rule",
}


@dataclass(frozen=True)
class IngredientRow:
    recipe_id: int
    canonical_id: str
    raw_text: str
    extraction_method: str


@dataclass(frozen=True)
class Outcome:
    rows: list[IngredientRow]
    mentions: int          # (recipe, raw line) pairs seen
    mapped_mentions: int   # of which mapped to at least one entry
    split_mentions: int    # of which mapped through a split


def canonicalise(
    lines: Iterable[tuple[str, str, int, str | None]],
    entries_for: Callable[[str], tuple[str, ...]],
) -> Outcome:
    """Rows for ``recipe_ingredients`` from worklist-shaped lines
    ``(source_id, register, recipe_id, raw string)``. ``entries_for`` is
    `Lexicon.entries_for` (or the database equivalent): the entries a string maps to,
    empty when unmapped."""
    merged: dict[tuple[int, str], list[str]] = {}
    method: dict[int, str] = {}
    mentions = mapped = split = 0
    for _source, register, recipe_id, raw in lines:
        if not raw or not raw.strip():
            continue
        mentions += 1
        entries = entries_for(raw)
        if not entries:
            continue
        mapped += 1
        split += len(entries) > 1
        if register not in EXTRACTION_METHOD:
            raise ValueError(f"recipe {recipe_id}: unknown register {register!r}")
        method[recipe_id] = EXTRACTION_METHOD[register]
        for cid in entries:
            texts = merged.setdefault((recipe_id, cid), [])
            if raw.strip() not in texts:
                texts.append(raw.strip())
    rows = [IngredientRow(rid, cid, RAW_JOIN.join(texts), method[rid])
            for (rid, cid), texts in sorted(merged.items())]
    return Outcome(rows, mentions, mapped, split)
