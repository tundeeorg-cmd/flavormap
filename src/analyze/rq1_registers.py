"""RQ1, preliminary: how far apart are the official and commercial registers? (T1.19)

Per unit (province or region), each register's recipes become one ingredient vector, and
the official↔commercial cosine distance is reported **with the recipe count of each side
beside it**. A distance resting on 2 recipes and one resting on 200 are not the same
claim, and the table never lets them look alike.

**Two choices are inputs, never defaults** (TIMELINE §0 rule 2: no analysis code
hard-codes an undecided choice):

- ``unit``: ``"province"`` or ``"region"``. Which one the commercial register can support
  is HD-Kapook (TIMELINE T1.14, `docs/decisions.md` HD-37).
- ``weighting``: how a set of recipes becomes a vector (HD-38). ``"prevalence"``: the
  share of the unit's recipes that contain each ingredient. ``"tfidf"``: that
  prevalence, times a smoothed inverse document frequency computed over every
  (register, unit) vector together, which down-weights ingredients common everywhere
  (fish sauce, salt). Under cosine distance, prevalence is equivalent to summing binary
  presence, since cosine ignores scale.

Ingredients are canonical ids from ``recipe_ingredients`` (the lexicon, HD-6). Recipes are
the rows of ``v_recipes_clean``, as every analysis reads them (CLAUDE.md §3.2): high or
medium confidence, 3–25 mapped ingredients. A recipe's region is its province's
``region4`` when it has a province, otherwise the attribution's own region label. Both
present and disagreeing is an error, never resolved silently.

**Per-source robustness** (TIMELINE v3 T1.19). `per_source_distances` repeats the
comparison with the commercial side split by ``source_id`` (Kapook only, MThai only, …)
beside the pooled result, so a finding that is one site's house style shows up as one.
Under ``tfidf`` the inverse document frequency is computed over the vectors in that
comparison, so the split table's idf includes one vector per source.

Inputs are the Parquet files `make parquet` writes (T1.18). This module writes nothing.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pandas as pd

from src.config import DATA_DIR

Unit = Literal["province", "region"]
Weighting = Literal["prevalence", "tfidf"]
UNITS: tuple[Unit, ...] = ("province", "region")
WEIGHTINGS: tuple[Weighting, ...] = ("prevalence", "tfidf")
PROCESSED = DATA_DIR / "processed"
COLUMN: dict[str, str] = {"province": "province_code", "region": "region"}


class InputError(ValueError):
    """The inputs cannot support the requested comparison."""


@dataclass(frozen=True)
class Profile:
    """One register's ingredient vector for one unit, and how many recipes built it."""

    register: str
    unit: str
    n_recipes: int
    vector: dict[str, float]


def load_inputs(processed: Path = PROCESSED) -> pd.DataFrame:
    """One row per (recipe, canonical ingredient), with register, province and region.
    Reads ``v_recipes_clean``, ``recipe_ingredients`` and ``provinces`` from Parquet."""
    needed = ("v_recipes_clean", "recipe_ingredients", "provinces")
    missing = [n for n in needed if not (processed / f"{n}.parquet").exists()]
    if missing:
        raise InputError(f"missing {', '.join(missing)} in {processed}; run `make parquet`")
    clean = pd.read_parquet(processed / "v_recipes_clean.parquet")
    ingredients = pd.read_parquet(processed / "recipe_ingredients.parquet")
    provinces = pd.read_parquet(processed / "provinces.parquet")
    return assemble(clean, ingredients, provinces)


def assemble(
    clean: pd.DataFrame, ingredients: pd.DataFrame, provinces: pd.DataFrame
) -> pd.DataFrame:
    """Join the three tables; resolve each recipe's region (see the module docstring)."""
    region4 = dict(zip(provinces["province_code"], provinces["region4"], strict=True))
    keep = ["recipe_id", "register", "province_code", "region"]
    keep += ["source_id"] if "source_id" in clean.columns else []
    rows = clean[keep].copy()
    derived = rows["province_code"].map(region4)
    clash = rows["region"].notna() & derived.notna() & (rows["region"] != derived)
    if clash.any():
        ids = rows.loc[clash, "recipe_id"].tolist()[:10]
        raise InputError(f"attribution region disagrees with the province's region4: {ids}")
    rows["region"] = derived.fillna(rows["region"])
    mapped = ingredients.dropna(subset=["canonical_id"])[["recipe_id", "canonical_id"]]
    return rows.merge(mapped.drop_duplicates(), on="recipe_id", how="inner")


def profiles(data: pd.DataFrame, unit: Unit, weighting: Weighting) -> list[Profile]:
    """Every (register, unit) ingredient vector, weighted as asked."""
    if unit not in UNITS:
        raise InputError(f"unit must be one of {UNITS}, got {unit!r}")
    if weighting not in WEIGHTINGS:
        raise InputError(f"weighting must be one of {WEIGHTINGS}, got {weighting!r}")
    column = COLUMN[unit]
    data = data.dropna(subset=[column])
    built: list[Profile] = []
    for (register, value), group in data.groupby(["register", column], sort=True):
        n = group["recipe_id"].nunique()
        counts = Counter(group.drop_duplicates(["recipe_id", "canonical_id"])["canonical_id"])
        built.append(Profile(str(register), str(value), n,
                             {k: c / n for k, c in counts.items()}))
    if weighting == "tfidf":
        docs = len(built)
        df = Counter(k for p in built for k in p.vector)
        idf = {k: math.log((1 + docs) / (1 + d)) + 1 for k, d in df.items()}
        built = [Profile(p.register, p.unit, p.n_recipes,
                         {k: v * idf[k] for k, v in p.vector.items()}) for p in built]
    return built


def cosine_distance(a: dict[str, float], b: dict[str, float]) -> float:
    dot = sum(v * b.get(k, 0.0) for k, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return math.nan
    return 1.0 - dot / (na * nb)


def register_distances(
    data: pd.DataFrame,
    unit: Unit,
    weighting: Weighting,
    pair: tuple[str, str] = ("official", "commercial"),
) -> pd.DataFrame:
    """One row per unit that either register covers: the two recipe counts and the
    cosine distance (NaN when a side has no recipes). Ordered by unit."""
    by_key = {(p.register, p.unit): p for p in profiles(data, unit, weighting)}
    units = sorted({u for (_, u) in by_key})
    a, b = pair
    rows = []
    for u in units:
        pa, pb = by_key.get((a, u)), by_key.get((b, u))
        rows.append({
            unit: u,
            f"n_{a}": pa.n_recipes if pa else 0,
            f"n_{b}": pb.n_recipes if pb else 0,
            "distance": cosine_distance(pa.vector, pb.vector) if pa and pb else math.nan,
        })
    return pd.DataFrame(rows, columns=[unit, f"n_{a}", f"n_{b}", "distance"])


def split_by_source(data: pd.DataFrame, register: str = "commercial") -> pd.DataFrame:
    """Relabel `register`'s rows as ``"<register>:<source_id>"``, one pseudo-register per
    source, leaving every other register as it is."""
    if "source_id" not in data.columns:
        raise InputError("no source_id column: rebuild the inputs with `make parquet`")
    out = data.copy()
    mask = out["register"] == register
    out.loc[mask, "register"] = register + ":" + out.loc[mask, "source_id"].astype(str)
    return out


def per_source_distances(
    data: pd.DataFrame, unit: Unit, weighting: Weighting
) -> pd.DataFrame:
    """Official↔commercial distances pooled, then per commercial source, in one long
    table with a ``commercial_source`` column (``"pooled"`` first, then source ids)."""
    tables = []
    pooled = register_distances(data, unit, weighting)
    tables.append(pooled.rename(columns={"n_commercial": "n_commercial_side"})
                  .assign(commercial_source="pooled"))
    split = split_by_source(data)
    labels = split.loc[split["register"].str.startswith("commercial:"), "register"]
    for source in sorted(labels.str.removeprefix("commercial:").unique()):
        table = register_distances(split, unit, weighting,
                                   pair=("official", f"commercial:{source}"))
        tables.append(table.rename(columns={f"n_commercial:{source}": "n_commercial_side"})
                      .assign(commercial_source=source))
    columns = ["commercial_source", unit, "n_official", "n_commercial_side", "distance"]
    return pd.concat(tables, ignore_index=True)[columns]
