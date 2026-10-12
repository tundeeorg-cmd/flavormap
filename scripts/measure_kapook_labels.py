"""T1.13: how many of the loaded kapook recipes could carry a province or region label?

    uv run python -m scripts.measure_kapook_labels

**A measurement, not a labelling.** Nothing here writes to the database. Which rules (if
any) become labels is HD-Kapook (TIMELINE T1.14), the researcher's decision, and T1.15
applies it. So every rule family is reported in each of its variants, side by side, and
none is picked.

The unit is the commercial register as loaded: one row per kapook recipe in `recipes`
(1,360 on 2026-10-12). The text examined is the recipe's title and the site's category
path (`title_th`, `category_source`), not the article body.

Three rule families (TIMELINE T1.13):

**(a) Explicit province names**, with the three strictness levels of
`scripts.measure_labelled_fraction` (its AMBIGUOUS homograph list and ALIASES apply):
``a_permissive`` (any name, as a substring), ``a_strict`` (ambiguous names need a
จังหวัด/จ. marker) and ``a_marker`` (every name needs the marker).

**(b) Explicit regional claims**: ``b_compound`` uses that script's REGION_TERMS, where
only compounded forms count (ภาคใต้, อาหารเหนือ, อีสาน and so on). ``b_bare`` adds bare
เหนือ and ใต้, as TIMELINE's wording lists them, although they also mean "above" and
"below".

**(c) Dish-name match against the official register's dish names**: ``c_exact`` (the
title equals an official name) and ``c_substring`` (an official name appears in the
title). One official name can belong to several provinces, so a match can be ambiguous.

For each province-level rule a recipe is **unambiguous** (exactly one province) or
**conflicting** (more than one). Per-recipe results go to
``data/coverage/kapook_label_yield.csv``, which is gitignored: it lists official dish
names, which are DCP-derived (HD-3). The printed tables are aggregates only.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from dataclasses import dataclass, field

from scripts.measure_labelled_fraction import (
    REGION_TERMS,
    Province,
    load_provinces,
    province_hits,
)
from src.clean.normalize_th import normalize_thai
from src.config import DATA_DIR
from src.db import get_connection

BARE_REGION_TERMS = {**REGION_TERMS, "เหนือ": "North", "ใต้": "South"}
PROVINCE_RULES = ("a_permissive", "a_strict", "a_marker", "c_exact", "c_substring")
REGION_RULES = ("b_compound", "b_bare")
OUT = DATA_DIR / "coverage" / "kapook_label_yield.csv"


@dataclass
class Recipe:
    recipe_id: int
    title: str
    category: str
    hits: dict[str, set[str]] = field(default_factory=dict)


def _norm(text: str) -> str:
    return " ".join(normalize_thai(text)[0].split())


def region_claims(text: str, terms: dict[str, str]) -> set[str]:
    return {region for term, region in terms.items() if term in text}


def dish_matches(
    title: str, official: dict[str, set[str]], *, exact: bool
) -> tuple[set[str], set[str]]:
    """(province codes, official names) matched by `title`. `official` maps a normalised
    official dish name to the province codes it was recorded for."""
    t = _norm(title)
    names = {n for n in official if (t == n if exact else n in t)}
    codes = set().union(*(official[n] for n in names)) if names else set()
    return codes, names


def classify(
    recipe: Recipe, provinces: list[Province], official: dict[str, set[str]]
) -> dict[str, set[str]]:
    """Every rule's hits for one recipe: province codes, or region names for (b)."""
    text = f"{recipe.title}\n{recipe.category}"
    hits = {
        "a_permissive": province_hits(text, provinces, "permissive"),
        "a_strict": province_hits(text, provinces, "strict"),
        "a_marker": province_hits(text, provinces, "marker"),
        "b_compound": region_claims(text, REGION_TERMS),
        "b_bare": region_claims(text, BARE_REGION_TERMS),
    }
    hits["c_exact"], hits["c_exact_names"] = dish_matches(recipe.title, official, exact=True)
    hits["c_substring"], hits["c_substring_names"] = dish_matches(
        recipe.title, official, exact=False
    )
    return hits


def load(conn) -> tuple[list[Recipe], dict[str, set[str]]]:  # type: ignore[no-untyped-def]
    rows = conn.execute(
        """SELECT r.recipe_id, rr.parsed_json->>'title_th',
                  coalesce(rr.parsed_json->>'category_source', '')
             FROM recipes r JOIN raw_recipes rr USING (raw_id)
            WHERE r.register = 'commercial' ORDER BY r.recipe_id"""
    ).fetchall()
    recipes = [Recipe(rid, title or "", cat) for rid, title, cat in rows]
    official: dict[str, set[str]] = {}
    for name, code in conn.execute(
        """SELECT r.name_th, pa.province_code FROM recipes r
             JOIN province_attribution pa USING (recipe_id)
            WHERE r.register = 'official' AND r.name_th IS NOT NULL
              AND pa.province_code IS NOT NULL"""
    ).fetchall():
        official.setdefault(_norm(name), set()).add(code)
    return recipes, official


def summarise(recipes: list[Recipe], provinces: list[Province]) -> str:
    region_of = {p.code: p.region4 for p in provinces}
    name_of = {p.code: p.name_th for p in provinces}
    order = [p.code for p in provinces]
    n = len(recipes)
    out: list[str] = []

    out.append(f"**Recipes examined:** {n} (`register = 'commercial'`).\n")
    out.append("| Rule | Any hit | Unambiguous (one province / region) | Conflicting |")
    out.append("|---|---:|---:|---:|")
    for rule in (*PROVINCE_RULES, *REGION_RULES):
        sizes = [len(r.hits[rule]) for r in recipes]
        anyhit = sum(s > 0 for s in sizes)
        one = sum(s == 1 for s in sizes)
        out.append(f"| `{rule}` | {anyhit} ({anyhit / n:.1%}) | {one} ({one / n:.1%}) "
                   f"| {anyhit - one} |")

    out.append("\n**Unambiguous hits per province** (provinces with at least one hit; "
               "ordered as `data/reference/provinces.csv`):\n")
    cols = ("a_strict", "a_marker", "c_exact", "c_substring")
    out.append("| Province | Region | " + " | ".join(f"`{c}`" for c in cols) + " |")
    out.append("|---|---|" + "---:|" * len(cols))
    per = {c: Counter(next(iter(r.hits[c])) for r in recipes if len(r.hits[c]) == 1)
           for c in cols}
    for code in order:
        if any(per[c][code] for c in cols):
            out.append(f"| {name_of[code]} | {region_of[code]} | "
                       + " | ".join(str(per[c][code]) for c in cols) + " |")
    out.append("| **Provinces with ≥1** | | "
               + " | ".join(str(len(per[c])) for c in cols) + " |")

    out.append("\n**Unambiguous hits per region.** The (b) rules count region claims "
               "directly; the (a) and (c) columns roll unambiguous province hits up to "
               "`region4`:\n")
    regions = ("North", "Northeast", "Central", "South")
    rcols = ("b_compound", "b_bare", "a_strict", "c_substring")
    out.append("| Region | " + " | ".join(f"`{c}`" for c in rcols) + " |")
    out.append("|---|" + "---:|" * len(rcols))
    rcount = {c: Counter(next(iter(r.hits[c])) for r in recipes if len(r.hits[c]) == 1)
              for c in REGION_RULES}
    for reg in regions:
        cells = [rcount["b_compound"][reg], rcount["b_bare"][reg],
                 sum(v for k, v in per["a_strict"].items() if region_of[k] == reg),
                 sum(v for k, v in per["c_substring"].items() if region_of[k] == reg)]
        out.append(f"| {reg} | " + " | ".join(map(str, cells)) + " |")

    def agree(x: str, y: str) -> tuple[int, int]:
        both = [r for r in recipes if len(r.hits[x]) == 1 and len(r.hits[y]) == 1]
        return len(both), sum(r.hits[x] == r.hits[y] for r in both)

    out.append("\n**Where two families both give one province, do they agree?**\n")
    out.append("| Pair | Recipes with one province under both | Same province |")
    out.append("|---|---:|---:|")
    for x, y in (("a_strict", "c_exact"), ("a_strict", "c_substring"),
                 ("a_marker", "c_substring")):
        both, same = agree(x, y)
        out.append(f"| `{x}` and `{y}` | {both} | {same} |")
    used = Counter(nm for r in recipes for nm in r.hits["c_substring_names"])
    short = sum(1 for nm in used if len(nm) <= 4)
    out.append(f"\n`c_substring` matched {len(used)} distinct official dish names; "
               f"{short} of them are 4 characters or fewer, where a substring match is "
               "most likely to be generic. The names and per-recipe hits are in "
               f"`{OUT.relative_to(DATA_DIR.parent)}` (gitignored, DCP-derived).")
    return "\n".join(out)


def write_csv(recipes: list[Recipe]) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    keys = (*PROVINCE_RULES, *REGION_RULES, "c_exact_names", "c_substring_names")
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        w = csv.writer(handle)
        w.writerow(("recipe_id", "title_th", "category_source", *keys))
        for r in recipes:
            w.writerow((r.recipe_id, r.title, r.category,
                        *("|".join(sorted(r.hits[k])) for k in keys)))


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    provinces = load_provinces()
    with get_connection() as conn:
        conn.read_only = True
        recipes, official = load(conn)
    for r in recipes:
        r.hits = classify(r, provinces, official)
    write_csv(recipes)
    print(summarise(recipes, provinces))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
