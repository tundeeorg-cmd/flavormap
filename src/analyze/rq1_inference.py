"""RQ1 inference: bootstrap confidence intervals and permutation p-values for the
official↔commercial distances `src.analyze.rq1_registers` computes (DH2027 outline v0.2,
Section 4, "Is the difference real?").

**Same distance, faster arithmetic.** Profiles, TF-IDF and cosine distance are exactly
`rq1_registers`' definitions (a test checks the observed distances agree to 1e-9), redone
on a recipes × ingredients 0/1 matrix so thousands of resamples are cheap. Every (register,
unit) group in the data is a document for the inverse document frequency, as in
`rq1_registers.profiles`; in a resample the idf is recomputed from the resampled vectors,
so the interval includes the idf's own sampling noise.

**Bootstrap** (outline: "resampling recipes within each province"; at HD-37's region unit,
within each region). Every (register, unit) group is resampled with replacement to its own
size, all groups at once, and the distance recomputed. The interval is the
**bias-corrected percentile** interval at ``1 - alpha`` (HD-44, 2026-11-06): resampling
small groups inflates a cosine distance, so the plain percentile interval sat at or above
the observed value; the correction shifts the percentiles by the bootstrap's own bias
(`bias_corrected_interval`). ``interval="percentile"`` gives the plain one. A side with
one recipe has no sampling variation to show; its interval collapses to the point, and the
recipe count beside it says why.

**Permutation: two nulls, both computed** (HD-44, revised 2026-11-06: **``register`` is
primary**, ``unit`` secondary; each is Holm-adjusted across the regions of a scope by
`holm`):

``unit`` (secondary)
    The outline v0.2 wording: "shuffle province labels" (here: region labels). Within each
    register, unit labels are permuted across that register's recipes, group sizes kept.
    The null is the distance between same-sized random official and commercial recipe
    sets, so a small p says *this unit's* gap is larger than the registers' gap in
    general.
``register`` (primary)
    Within the unit, the official / commercial labels are permuted across the unit's
    pooled recipes, sizes kept; every other group fixed. A small p says the two registers
    differ in this unit by more than chance allocation of its recipes would produce.

p is one-sided (distance at least as large as observed), ``(1 + #{null ≥ obs}) /
(1 + n)``, so it is never 0. `infer` returns raw p-values; the Holm adjustment is applied
per family by the caller (`scripts/run_rq1.py`), since only it knows the family.

Pure: takes the DataFrame `rq1_registers.assemble` returns, writes nothing.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
from scipy.stats import norm

from src.analyze.rq1_registers import COLUMN, UNITS, WEIGHTINGS, InputError, Unit, Weighting

Null = Literal["unit", "register"]
NULLS: tuple[Null, ...] = ("unit", "register")
CHUNK = 500  # resamples per vectorised batch; bounds memory at CHUNK × groups × ingredients


@dataclass(frozen=True)
class Design:
    """Recipes as rows of a 0/1 ingredient matrix, with each recipe's group."""

    units: list[str]
    groups: list[tuple[str, str]]   # (register, unit), sorted
    group_rows: list[np.ndarray]    # row indices of each group's recipes
    x: np.ndarray                   # recipes × ingredients, float64 0/1
    register_of: np.ndarray         # per recipe
    unit_of: np.ndarray             # per recipe

    def index(self, register: str, unit: str) -> int | None:
        try:
            return self.groups.index((register, unit))
        except ValueError:
            return None


def design(data: pd.DataFrame, unit: Unit) -> Design:
    if unit not in UNITS:
        raise InputError(f"unit must be one of {UNITS}, got {unit!r}")
    column = COLUMN[unit]
    data = data.dropna(subset=[column]).drop_duplicates(["recipe_id", "canonical_id"])
    recipes = (data[["recipe_id", "register", column]].drop_duplicates("recipe_id")
               .sort_values("recipe_id").reset_index(drop=True))
    if recipes.empty:
        raise InputError("no recipe has both a unit and a mapped ingredient")
    ingredients = sorted(data["canonical_id"].unique())
    row = {rid: i for i, rid in enumerate(recipes["recipe_id"])}
    col = {k: j for j, k in enumerate(ingredients)}
    x = np.zeros((len(recipes), len(ingredients)))
    x[[row[r] for r in data["recipe_id"]], [col[k] for k in data["canonical_id"]]] = 1.0
    register_of = recipes["register"].astype(str).to_numpy()
    unit_of = recipes[column].astype(str).to_numpy()
    groups = sorted(set(zip(register_of, unit_of, strict=True)))
    group_rows = [np.flatnonzero((register_of == r) & (unit_of == u)) for r, u in groups]
    return Design(sorted(set(unit_of)), groups, group_rows, x, register_of, unit_of)


def _weight(p: np.ndarray, weighting: Weighting) -> np.ndarray:
    """`p`: (..., groups, ingredients) prevalence. TF-IDF as `rq1_registers.profiles`:
    idf = ln((1 + docs) / (1 + df)) + 1 over the groups axis."""
    if weighting not in WEIGHTINGS:
        raise InputError(f"weighting must be one of {WEIGHTINGS}, got {weighting!r}")
    if weighting == "prevalence":
        return p
    docs = p.shape[-2]
    df = (p > 0).sum(axis=-2, keepdims=True)
    return p * (np.log((1 + docs) / (1 + df)) + 1)


def _cosine(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Row-wise cosine distance over the last axis; NaN where a side is all zero."""
    dot = (a * b).sum(-1)
    norm = np.sqrt((a * a).sum(-1)) * np.sqrt((b * b).sum(-1))
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(norm > 0, 1.0 - dot / np.where(norm > 0, norm, 1.0), np.nan)


def _prevalence(d: Design) -> np.ndarray:
    return np.stack([d.x[rows].mean(axis=0) for rows in d.group_rows])


@dataclass(frozen=True)
class UnitResult:
    unit: str
    n_a: int
    n_b: int
    distance: float
    ci_low: float
    ci_high: float
    p_unit: float
    p_register: float


def observed(d: Design, weighting: Weighting, pair: tuple[str, str]) -> dict[str, float]:
    w = _weight(_prevalence(d), weighting)
    out = {}
    for u in d.units:
        ia, ib = d.index(pair[0], u), d.index(pair[1], u)
        out[u] = float(_cosine(w[ia], w[ib])) if ia is not None and ib is not None else math.nan
    return out


def _chunks(n: int) -> list[int]:
    return [min(CHUNK, n - i) for i in range(0, n, CHUNK)]


def bootstrap(
    d: Design, weighting: Weighting, pair: tuple[str, str], n: int,
    rng: np.random.Generator,
) -> dict[str, np.ndarray]:
    """unit -> `n` bootstrap distances (only units both sides cover)."""
    targets = {u: (d.index(pair[0], u), d.index(pair[1], u)) for u in d.units}
    targets = {u: (a, b) for u, (a, b) in targets.items() if a is not None and b is not None}
    out: dict[str, list[np.ndarray]] = {u: [] for u in targets}
    for size in _chunks(n):
        p = np.empty((size, len(d.groups), d.x.shape[1]))
        for g, rows in enumerate(d.group_rows):
            m = len(rows)
            counts = rng.multinomial(m, np.full(m, 1.0 / m), size=size)
            p[:, g, :] = counts @ d.x[rows] / m
        w = _weight(p, weighting)
        for u, (a, b) in targets.items():
            out[u].append(_cosine(w[:, a, :], w[:, b, :]))
    return {u: np.concatenate(v) for u, v in out.items()}


def permute_register(
    d: Design, weighting: Weighting, pair: tuple[str, str], n: int,
    rng: np.random.Generator,
) -> dict[str, np.ndarray]:
    """unit -> `n` null distances with the pair's labels shuffled within the unit."""
    base = _prevalence(d)
    out: dict[str, np.ndarray] = {}
    for u in d.units:
        a, b = d.index(pair[0], u), d.index(pair[1], u)
        if a is None or b is None:
            continue
        rows_a, rows_b = d.group_rows[a], d.group_rows[b]
        pool = d.x[np.concatenate([rows_a, rows_b])]
        total = pool.sum(axis=0)
        na, nb = len(rows_a), len(rows_b)
        parts = []
        for size in _chunks(n):
            order = rng.permuted(np.tile(np.arange(na + nb), (size, 1)), axis=1)
            member = np.zeros((size, na + nb))
            np.put_along_axis(member, order[:, :na], 1.0, axis=1)
            sum_a = member @ pool
            p = np.broadcast_to(base, (size, *base.shape)).copy()
            p[:, a, :] = sum_a / na
            p[:, b, :] = (total - sum_a) / nb
            w = _weight(p, weighting)
            parts.append(_cosine(w[:, a, :], w[:, b, :]))
        out[u] = np.concatenate(parts)
    return out


def permute_unit(
    d: Design, weighting: Weighting, pair: tuple[str, str], n: int,
    rng: np.random.Generator,
) -> dict[str, np.ndarray]:
    """unit -> `n` null distances with unit labels shuffled within each register."""
    targets = {u: (d.index(pair[0], u), d.index(pair[1], u)) for u in d.units}
    targets = {u: (a, b) for u, (a, b) in targets.items() if a is not None and b is not None}
    by_register: dict[str, list[int]] = {}
    for g, (register, _) in enumerate(d.groups):
        by_register.setdefault(register, []).append(g)
    out: dict[str, list[float]] = {u: [] for u in targets}
    for _ in range(n):
        p = np.empty((len(d.groups), d.x.shape[1]))
        for gs in by_register.values():
            rows = np.concatenate([d.group_rows[g] for g in gs])
            shuffled = d.x[rng.permutation(rows)]
            start = 0
            for g in gs:
                m = len(d.group_rows[g])
                p[g] = shuffled[start:start + m].mean(axis=0)
                start += m
        w = _weight(p, weighting)
        for u, (a, b) in targets.items():
            out[u].append(float(_cosine(w[a], w[b])))
    return {u: np.asarray(v) for u, v in out.items()}


Interval = Literal["bias_corrected", "percentile"]


def bias_corrected_interval(boot: np.ndarray, obs: float, alpha: float) -> tuple[float, float]:
    """Bias-corrected percentile interval (Efron 1981). z0 = Φ⁻¹(share of bootstrap
    values below the observed one, ties counted half); the interval takes the
    Φ(2·z0 ± z_{1-α/2}) quantiles. z0 = 0 gives the plain percentile interval. The share
    is clamped to [1/(n+1), n/(n+1)] so z0 stays finite."""
    boot = boot[np.isfinite(boot)]
    n = boot.size
    if n == 0 or not math.isfinite(obs):
        return math.nan, math.nan
    share = (np.sum(boot < obs) + 0.5 * np.sum(boot == obs)) / n
    share = min(max(share, 1 / (n + 1)), n / (n + 1))
    z0 = float(norm.ppf(share))
    z = float(norm.ppf(1 - alpha / 2))
    lo, hi = norm.cdf(2 * z0 - z), norm.cdf(2 * z0 + z)
    return float(np.quantile(boot, lo)), float(np.quantile(boot, hi))


def holm(pvalues: list[float]) -> list[float]:
    """Holm–Bonferroni step-down adjustment over one family (HD-44: the regions of one
    scope). NaN entries are left NaN and do not count toward the family size."""
    idx = [i for i, p in enumerate(pvalues) if isinstance(p, float) and math.isfinite(p)]
    m = len(idx)
    out = [math.nan] * len(pvalues)
    running = 0.0
    for rank, i in enumerate(sorted(idx, key=lambda i: pvalues[i])):
        running = max(running, min(1.0, (m - rank) * pvalues[i]))
        out[i] = running
    return out


def p_value(null: np.ndarray, obs: float) -> float:
    null = null[np.isfinite(null)]
    if not math.isfinite(obs) or null.size == 0:
        return math.nan
    return float((1 + np.sum(null >= obs - 1e-12)) / (1 + null.size))


def infer(
    data: pd.DataFrame,
    unit: Unit,
    weighting: Weighting,
    pair: tuple[str, str] = ("official", "commercial"),
    *,
    n_boot: int,
    n_perm: int,
    seed: int,
    alpha: float = 0.05,
    interval: Interval = "bias_corrected",
) -> list[UnitResult]:
    """One row per unit either side of `pair` covers: counts, distance, percentile CI,
    and both permutation p-values. Units one side lacks get NaN, as in
    `rq1_registers.register_distances`."""
    d = design(data, unit)
    obs = observed(d, weighting, pair)
    rngs = [np.random.default_rng([seed, i]) for i in range(3)]
    boot = bootstrap(d, weighting, pair, n_boot, rngs[0]) if n_boot else {}
    null_u = permute_unit(d, weighting, pair, n_perm, rngs[1]) if n_perm else {}
    null_r = permute_register(d, weighting, pair, n_perm, rngs[2]) if n_perm else {}
    results = []
    for u in d.units:
        ia, ib = d.index(pair[0], u), d.index(pair[1], u)
        na = len(d.group_rows[ia]) if ia is not None else 0
        nb = len(d.group_rows[ib]) if ib is not None else 0
        if ia is None and ib is None:
            continue
        b = boot.get(u, np.array([]))
        b = b[np.isfinite(b)]
        if not b.size:
            lo, hi = math.nan, math.nan
        elif interval == "bias_corrected":
            lo, hi = bias_corrected_interval(b, obs[u], alpha)
        else:
            lo, hi = float(np.quantile(b, alpha / 2)), float(np.quantile(b, 1 - alpha / 2))
        results.append(UnitResult(
            u, na, nb, obs[u], lo, hi,
            p_value(null_u.get(u, np.array([])), obs[u]),
            p_value(null_r.get(u, np.array([])), obs[u]),
        ))
    return results
