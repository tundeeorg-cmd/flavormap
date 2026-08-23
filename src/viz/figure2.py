"""Figure 2 — regional separation against geographic distance.

Draws the specification in ``docs/figure2_spec_draft.md``. Two panels, both 2D (rule 10),
300 dpi, colourblind-safe.

**The absence of a fitted line is the argument.** RQ1 was specified as a distance-decay
curve over ~2,900 province pairs; this corpus supports six region pairs. A LOESS through
six points would reintroduce exactly the claim the analysis withdrew, so the panel shows
the points and the caption says why there is no line.

Panel B exists because a non-significant result has to be legible as *the observed value
sits inside its null* rather than as a gap on a chart — and because the small-n pairs have
visibly wider nulls, which is the honest way to show that a pair is undetermined rather
than measured at zero.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")  # no display on this machine, and none needed to write a PNG
import matplotlib.pyplot as plt  # noqa: E402  - must follow the backend selection

# Colourblind-safe: a dark teal against a neutral grey separates under deuteranopia,
# protanopia and tritanopia, and the fill/hollow distinction carries the same information
# again for anyone reading a greyscale print.
SIGNIFICANT = "#1F6F5C"
NOT_SIGNIFICANT = "#8A8F8A"
RULE = "#3A403C"
ALPHA = 0.05
#: half-width of the null band in data units on panel A's X axis (kilometres)
NULL_HALF_WIDTH_KM = 13.0


@dataclass
class PairPoint:
    """One region pair: its geography, its separation, and its permutation null."""

    label: str
    km: float
    separation: float
    p_holm: float
    n: int
    null: list[float]

    @property
    def significant(self) -> bool:
        return self.p_holm < ALPHA

    @property
    def colour(self) -> str:
        return SIGNIFICANT if self.significant else NOT_SIGNIFICANT


def render(points: list[PairPoint], out: Path, cohort_n: int, permutations: int) -> Path:
    points = sorted(points, key=lambda p: p.km)
    figure, (upper, lower) = plt.subplots(
        2, 1, figsize=(8.2, 9.0), height_ratios=[1.15, 1.0],
        gridspec_kw={"hspace": 0.32},
    )

    # ── Panel A ───────────────────────────────────────────────────────────────
    upper.axhline(0.0, color=RULE, linewidth=0.8, linestyle=(0, (4, 3)), zorder=1)

    # The bar is the pair's NULL, not an interval around the estimate. Drawn as a wide
    # translucent band with caps rather than a thin line, because a thin vertical line
    # through a point reads as an error bar, and an error bar is the opposite claim: it
    # would say the estimate is uncertain, where this says the null is centred on zero
    # and the observed value does or does not escape it.
    for point in points:
        low, high = np.percentile(point.null, [2.5, 97.5])
        upper.add_patch(plt.Rectangle(
            (point.km - NULL_HALF_WIDTH_KM, low), NULL_HALF_WIDTH_KM * 2, high - low,
            facecolor=point.colour, alpha=0.16, edgecolor=point.colour,
            linewidth=0.7, zorder=2,
        ))
    for point in points:
        upper.plot(
            point.km, point.separation, marker="o", markersize=9,
            markerfacecolor=point.colour if point.significant else "white",
            markeredgecolor=point.colour, markeredgewidth=1.8, zorder=4,
        )

    # Labels are staggered rather than placed at a fixed offset: C–N and C–S sit 45 km
    # apart with near-identical separations, and two labels at the same offset overlap.
    placed: list[tuple[float, float]] = []
    for point in sorted(points, key=lambda p: p.km):
        offset = 15.0
        while any(abs(point.km - x) < 90 and abs(offset - y) < 24 for x, y in placed):
            offset += 24.0
        placed.append((point.km, offset))
        upper.annotate(
            f"{point.label}\nn={point.n}",
            (point.km, point.separation), textcoords="offset points",
            xytext=(0, offset), ha="center", fontsize=8.5, color=RULE, linespacing=1.3,
        )

    upper.set_xlabel("great-circle distance between region centroids (km)", fontsize=9.5)
    upper.set_ylabel("compositional separation\n(between − within mean cosine distance)",
                     fontsize=9.5)
    upper.text(
        0.0, 1.20, "Regional separation does not track distance",
        transform=upper.transAxes, fontsize=13, color="#16191A", fontweight="bold",
        va="bottom",
    )
    upper.text(
        0.0, 1.035,
        "Six region pairs — every pair there is. Filled = Holm-adjusted p < 0.05; shaded "
        "band = the middle 95% of that\npair's permutation null, so a point outside its "
        "band is a separation the labels do not produce by chance.\nNo fitted line: six "
        "points cannot carry one, and RQ1's distance-decay curve was withdrawn.",
        transform=upper.transAxes, fontsize=8.5, color=RULE, va="bottom", linespacing=1.6,
    )
    upper.margins(x=0.13, y=0.34)

    # ── Panel B ───────────────────────────────────────────────────────────────
    by_separation = sorted(points, key=lambda p: p.separation)
    positions = range(len(by_separation))
    parts = lower.violinplot(
        [p.null for p in by_separation], positions=list(positions),
        orientation="horizontal", widths=0.85, showextrema=False, showmedians=False,
    )
    for body, point in zip(parts["bodies"], by_separation, strict=True):
        body.set_facecolor(point.colour)
        body.set_alpha(0.22)
        body.set_edgecolor(point.colour)
        body.set_linewidth(0.8)

    for y, point in zip(positions, by_separation, strict=True):
        lower.plot(
            point.separation, y, marker="|", markersize=22,
            markeredgecolor=point.colour, markeredgewidth=2.4, zorder=3,
        )
        lower.annotate(
            f"p = {point.p_holm:.4f}" if point.p_holm < 0.001 else f"p = {point.p_holm:.3f}",
            (point.separation, y), textcoords="offset points", xytext=(9, 7),
            fontsize=8, color=point.colour,
            fontweight="bold" if point.significant else "normal",
            # The zero rule passes behind the near-zero pairs' labels and reads as a
            # stray glyph inside the number.
            bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.2, "alpha": 0.85},
        )

    lower.axvline(0.0, color=RULE, linewidth=0.8, linestyle=(0, (4, 3)))
    lower.set_yticks(list(positions))
    lower.set_yticklabels([p.label for p in by_separation], fontsize=9)
    lower.set_xlabel("compositional separation", fontsize=9.5)
    lower.text(
        0.0, 1.105, "Where each observed separation falls in its own null",
        transform=lower.transAxes, fontsize=11.5, color="#16191A", fontweight="bold",
        va="bottom",
    )
    lower.text(
        0.0, 1.03,
        f"Shaded: {permutations:,} permuted separations per pair. A wider null is a pair "
        "with less power, not a pair with no effect.",
        transform=lower.transAxes, fontsize=8.5, color=RULE, va="bottom",
    )
    lower.margins(y=0.10)

    for axis in (upper, lower):
        axis.spines[["top", "right"]].set_visible(False)
        axis.tick_params(labelsize=8.5, colors=RULE)
        for spine in axis.spines.values():
            spine.set_color(RULE)
            spine.set_linewidth(0.8)

    figure.text(
        0.011, 0.012,
        f"RQ1 at region level · {cohort_n} single-dish recipes, kapook corpus · "
        "ingredient tokenisation provisional pending HD-6 · seed 42",
        fontsize=7.5, color=NOT_SIGNIFICANT,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(out, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    return out
