"""Figure 6: province × ingredient heatmap, faceted by register (TIMELINE T1.20).

Specified in Bible v4 §12 and CLAUDE.md §6: fill = TF-IDF, the top ~60 ingredients by
variance, **both axes seriated by clustering, never alphabetical**, one panel per
register. 2D (rule 10), 300 dpi, one sequential hue.

How the specification is met, so each step can be checked or changed:

- **TF-IDF** is `src.analyze.rq1_registers`'s ``tfidf`` weighting: the share of a
  province's recipes containing an ingredient, times a smoothed inverse document frequency
  over every (register, province) vector. Figure and RQ1 use one definition.
- **Ingredients** are the `top_n` with the highest variance across every (register,
  province) row, with an absent ingredient counted as 0.
- **Seriation** is average-linkage hierarchical clustering on cosine distance, with
  optimal leaf ordering (`scipy.cluster.hierarchy`), so neighbouring rows and columns are
  the most similar ones. Provinces are clustered on their three register blocks side by
  side, so **one province order serves all three panels**, and ingredients on every row
  pooled, so **one ingredient order serves all three**. All-zero rows go last.
- **No data is not zero.** A province with no recipes from a register is a hatched grey
  row in that register's panel. A pale cell means the province has recipes but the
  ingredient is absent from them.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")  # no display needed to write a PNG
import matplotlib.pyplot as plt  # noqa: E402  - must follow the backend selection
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.patches import Patch, Rectangle  # noqa: E402
from scipy.cluster.hierarchy import leaves_list, linkage, optimal_leaf_ordering  # noqa: E402
from scipy.spatial.distance import pdist  # noqa: E402

from src.analyze.rq1_registers import Profile  # noqa: E402
from src.viz.thai_font import font_family  # noqa: E402

REGISTERS: tuple[str, ...] = ("official", "commercial", "domestic")
TOP_N = 60

SURFACE = "#ffffff"
RULE = "#3a403c"
TITLE_INK = "#16191a"
NO_DATA_FILL = "#f0efec"
NO_DATA_INK = "#8a8e8b"
# One hue, light to dark (sequential). Light end is off-white, so "absent" reads as
# empty paper rather than as a colour.
CMAP = LinearSegmentedColormap.from_list(
    "fig6", ["#f7fbff", "#c6dbef", "#6baed6", "#2171b5", "#08306b"]
)


@dataclass(frozen=True)
class Heatmap:
    provinces: list[str]          # province codes, seriated
    ingredients: list[str]        # canonical ids, seriated
    values: dict[str, np.ndarray]  # register -> provinces × ingredients (NaN = no data)
    n_recipes: dict[str, dict[str, int]]  # register -> province -> recipes


def seriate(matrix: np.ndarray) -> list[int]:
    """Row order from average-linkage clustering on cosine distance, with optimal leaf
    ordering. All-zero rows (no defined cosine) keep their relative order, last."""
    nonzero = [i for i in range(len(matrix)) if np.any(matrix[i])]
    zero = [i for i in range(len(matrix)) if i not in set(nonzero)]
    if len(nonzero) <= 2:
        return nonzero + zero
    sub = matrix[nonzero]
    dist = np.clip(pdist(sub, metric="cosine"), 0.0, None)
    tree = optimal_leaf_ordering(linkage(dist, method="average"), dist)
    return [nonzero[i] for i in leaves_list(tree)] + zero


def build(profiles: Sequence[Profile], top_n: int = TOP_N) -> Heatmap:
    """Select the ingredients, seriate both axes, and lay out one matrix per register."""
    by_reg: dict[str, dict[str, Profile]] = {r: {} for r in REGISTERS}
    for p in profiles:
        by_reg.setdefault(p.register, {})[p.unit] = p
    provinces = sorted({p.unit for p in profiles})
    every = sorted({k for p in profiles for k in p.vector})
    if not provinces or not every:
        return Heatmap([], [], {r: np.empty((0, 0)) for r in REGISTERS},
                       {r: {} for r in REGISTERS})

    rows = np.array([[p.vector.get(k, 0.0) for k in every] for p in profiles])
    variance = rows.var(axis=0)
    keep = sorted(range(len(every)), key=lambda j: (-variance[j], every[j]))[:top_n]
    ingredients = [every[j] for j in keep]

    def block(register: str) -> np.ndarray:
        out = np.full((len(provinces), len(ingredients)), np.nan)
        for i, prov in enumerate(provinces):
            if (p := by_reg.get(register, {}).get(prov)) is not None:
                out[i] = [p.vector.get(k, 0.0) for k in ingredients]
        return out

    raw = {r: block(r) for r in REGISTERS}
    side_by_side = np.hstack([np.nan_to_num(raw[r]) for r in REGISTERS])
    province_order = seriate(side_by_side)
    pooled = np.vstack([np.nan_to_num(raw[r]) for r in REGISTERS])
    ingredient_order = seriate(pooled.T)

    return Heatmap(
        provinces=[provinces[i] for i in province_order],
        ingredients=[ingredients[j] for j in ingredient_order],
        values={r: raw[r][np.ix_(province_order, ingredient_order)] for r in REGISTERS},
        n_recipes={r: {u: p.n_recipes for u, p in by_reg.get(r, {}).items()}
                   for r in REGISTERS},
    )


def render(
    heatmap: Heatmap,
    out: Path,
    *,
    province_label: dict[str, str],
    ingredient_label: dict[str, str],
    caption: str,
) -> Path:
    """Draw the three panels to `out`. With nothing to draw, write a figure that says
    so, so `make figures` always produces the file and never a misleading empty grid."""
    out.parent.mkdir(parents=True, exist_ok=True)
    with plt.rc_context({"font.family": font_family()}):
        if not heatmap.provinces:
            fig, ax = plt.subplots(figsize=(7.5, 2.2))
            ax.axis("off")
            ax.text(0.0, 0.75, "Figure 6 — province × ingredient (TF-IDF), by register",
                    fontsize=12, fontweight="bold", color=TITLE_INK, transform=ax.transAxes)
            ax.text(0.0, 0.35, "No data yet: no recipe in v_recipes_clean has mapped "
                    "ingredients.\nThe lexicon (HD-6) has to exist first.",
                    fontsize=9.5, color=RULE, transform=ax.transAxes, va="top")
            fig.savefig(out, dpi=300, bbox_inches="tight", facecolor=SURFACE)
            plt.close(fig)
            return out

        n_p, n_i = len(heatmap.provinces), len(heatmap.ingredients)
        finite = [v[np.isfinite(v)] for v in heatmap.values.values()]
        vmax = max((float(f.max()) for f in finite if f.size), default=1.0) or 1.0
        width = 3.2 + 3 * (0.16 * n_i + 0.6)
        height = 1.8 + 0.16 * n_p
        fig, axes = plt.subplots(1, 3, figsize=(width, height), sharey=True)
        fig.patch.set_facecolor(SURFACE)
        fig.subplots_adjust(wspace=0.06)
        image = None
        for ax, register in zip(axes, REGISTERS, strict=True):
            grid = heatmap.values[register]
            image = ax.imshow(np.ma.masked_invalid(grid), cmap=CMAP, vmin=0, vmax=vmax,
                              aspect="auto", interpolation="nearest")
            for i in range(n_p):
                if np.isnan(grid[i]).all():
                    ax.add_patch(Rectangle((-0.5, i - 0.5), n_i, 1, facecolor=NO_DATA_FILL,
                                           edgecolor=NO_DATA_INK, hatch="////",
                                           linewidth=0))
            covered = sum(1 for p in heatmap.provinces if p in heatmap.n_recipes[register])
            recipes = sum(heatmap.n_recipes[register].values())
            ax.set_title(f"{register}\n{covered} provinces · {recipes} recipes",
                         fontsize=9.5, color=TITLE_INK, loc="left")
            ax.set_xticks(range(n_i))
            ax.set_xticklabels([ingredient_label.get(k, k) for k in heatmap.ingredients],
                               rotation=90, fontsize=6.5, color=RULE)
            ax.tick_params(length=0)
            for spine in ax.spines.values():
                spine.set_visible(False)
        axes[0].set_yticks(range(n_p))
        axes[0].set_yticklabels([province_label.get(p, p) for p in heatmap.provinces],
                                fontsize=6.5, color=RULE)
        assert image is not None  # three panels were drawn
        fig.colorbar(image, ax=axes, fraction=0.015, pad=0.01, label="TF-IDF")
        fig.legend(handles=[Patch(facecolor=NO_DATA_FILL, edgecolor=NO_DATA_INK,
                                  hatch="////", label="no recipes from this register")],
                   loc="upper right", bbox_to_anchor=(0.99, 1.0), frameon=False, fontsize=8)
        fig.suptitle("Figure 6 — province × ingredient (TF-IDF), by register. "
                     "Both axes ordered by clustering.", x=0.01, ha="left",
                     fontsize=11, fontweight="bold", color=TITLE_INK)
        fig.text(0.01, -0.02, caption, fontsize=8, color=RULE, va="top")
        fig.savefig(out, dpi=300, bbox_inches="tight", facecolor=SURFACE)
        plt.close(fig)
    return out
