"""The pipeline-fidelity matrix (RQ4) — Bible v4 Figure 4, CLAUDE.md §6.

X axis: dish cooked. Y axis: information class, in §6's order (quantities, order,
technique, specificity, completeness). Each cell is survived / degraded / lost, read
from ``cook_along_log``. 2D (rule 10), 300 dpi.

**Named for what it is, not its number.** ``figures/figure4.html`` — v3's prevalence
view — still occupies the Figure 4 filename, and its disposition is an open researcher
decision (CLAUDE.md §6). This module does not take the slot from it.

**Dish order is HD-25** (``docs/decisions.md``): by information lost, most-damaged dish
first, scoring lost = 2, degraded = 1, survived = 0; ties broken by cook date. Never
alphabetical (§5's ordering trap). A cell that was not recorded scores 0 for ordering and
is drawn as *not recorded* — hatched and labelled — never as survived.

**Colour.** One hue, light → dark, because the three levels are ordered: darker means
more information lost. Steps 250 / 450 / 700 of the reference blue ramp, validated as an
ordinal ramp (monotone lightness, visible step gaps, light end ≥ 2:1 on the surface).
Every cell also carries its level as text, so the figure reads in greyscale print and
under any colour-vision deficiency without relying on the fill.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # no display needed to write a PNG
import matplotlib.pyplot as plt  # noqa: E402  - must follow the backend selection
from matplotlib import font_manager  # noqa: E402
from matplotlib.patches import Patch, Rectangle  # noqa: E402

# §6's order, verbatim. The Y axis follows it top to bottom.
CLASSES: tuple[str, ...] = ("quantities", "order", "technique", "specificity", "completeness")

LEVELS: tuple[str, ...] = ("survived", "degraded", "lost")
LOSS_SCORE = {"survived": 0, "degraded": 1, "lost": 2, None: 0}

FILL = {"survived": "#86b6ef", "degraded": "#2a78d6", "lost": "#0d366b"}
INK = {"survived": "#16191a", "degraded": "#ffffff", "lost": "#ffffff"}
NOT_RECORDED_FILL = "#f0efec"
NOT_RECORDED_INK = "#6b6f6c"
SURFACE = "#ffffff"
RULE = "#3a403c"
TITLE_INK = "#16191a"

# Dish names are Thai. The first installed family on this list wins; DejaVu Sans is
# matplotlib's bundled fallback and has no Thai glyphs, so it is last on purpose.
THAI_FONTS = ("Sarabun", "Thonburi", "Noto Sans Thai", "Leelawadee UI", "Tahoma")


@dataclass(frozen=True)
class DishRow:
    """One cook-along: one column of the matrix."""

    label: str
    cook_date: datetime.date
    cells: dict[str, str | None]  # class -> level, or None when not recorded
    classifier_gets_wrong: bool = False

    @property
    def loss(self) -> int:
        return sum(LOSS_SCORE[self.cells.get(c)] for c in CLASSES)


def order_dishes(rows: list[DishRow]) -> list[DishRow]:
    """HD-25: most information lost first; ties by cook date, earliest first."""
    return sorted(rows, key=lambda r: (-r.loss, r.cook_date))


def _font_family() -> list[str]:
    installed = {f.name for f in font_manager.fontManager.ttflist}
    return [f for f in THAI_FONTS if f in installed] + ["DejaVu Sans"]


def render(rows: list[DishRow], out: Path, planned: int = 8) -> Path:
    """Draw the matrix to `out`. `planned` is §7.4's dish count, used in the caption
    so a partial matrix states how far through the cook-alongs it is."""
    dishes = order_dishes(rows)
    n = len(dishes)
    width = max(4.8, 1.25 * max(n, 1) + 2.2)

    with plt.rc_context({"font.family": _font_family()}):
        fig, ax = plt.subplots(figsize=(width, 4.6))
        fig.patch.set_facecolor(SURFACE)
        ax.set_facecolor(SURFACE)

        gap = 0.04  # a thin surface gap between cells
        for x, dish in enumerate(dishes):
            for y, cls in enumerate(CLASSES):
                level = dish.cells.get(cls)
                if level is None:
                    fill, ink, hatch = NOT_RECORDED_FILL, NOT_RECORDED_INK, "////"
                    text = "not\nrecorded"
                    # Keep the hatch from running through the label.
                    bbox: dict[str, str] | None = {"boxstyle": "round,pad=0.25",
                                                   "facecolor": NOT_RECORDED_FILL,
                                                   "edgecolor": "none"}
                else:
                    fill, ink, text, hatch, bbox = FILL[level], INK[level], level, None, None
                ax.add_patch(Rectangle(
                    (x + gap / 2, y + gap / 2), 1 - gap, 1 - gap,
                    facecolor=fill, edgecolor=NOT_RECORDED_INK if hatch else "none",
                    hatch=hatch, linewidth=0,
                ))
                ax.text(x + 0.5, y + 0.5, text, ha="center", va="center", fontsize=7.5,
                        color=ink, linespacing=1.1, bbox=bbox)

        ax.set_xlim(0, max(n, 1))
        ax.set_ylim(len(CLASSES), 0)  # first class at the top
        ax.set_yticks([i + 0.5 for i in range(len(CLASSES))])
        ax.set_yticklabels(CLASSES, fontsize=9, color=RULE)
        ax.set_xticks([i + 0.5 for i in range(n)])
        ax.set_xticklabels(
            [f"{d.label}{' †' if d.classifier_gets_wrong else ''}\n{d.cook_date:%Y-%m-%d}"
             for d in dishes],
            fontsize=8.5, color=RULE,
        )
        ax.tick_params(length=0)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.set_xlabel("dish cooked — most information lost on the left", fontsize=9,
                      color=RULE, labelpad=8)
        ax.set_ylabel("information class", fontsize=9, color=RULE)

        if n == 0:
            ax.text(0.5, len(CLASSES) / 2, "no cook-alongs logged yet",
                    ha="center", va="center", fontsize=10, color=NOT_RECORDED_INK)

        # Fixed margins in inches, so the matrix sits directly under the caption at any
        # dish count (tight_layout left a large gap above the cells).
        height = fig.get_figheight()
        fig.subplots_adjust(left=1.25 / width, right=1 - 0.15 / width,
                            top=1 - 0.85 / height, bottom=1.15 / height)
        fig.suptitle("What survives normalisation: cooking from the cleaned dataset",
                     x=0.02, y=1 - 0.12 / height, ha="left", va="top",
                     fontsize=12, fontweight="bold", color=TITLE_INK)
        caption = (f"n = {n} of {planned} planned dishes. Each dish cooked from the cleaned "
                   "ingredient list, not the source page.")
        if any(d.classifier_gets_wrong for d in dishes):
            caption += " † = a dish the classifier gets wrong."
        fig.text(0.02, 1 - 0.45 / height, caption, ha="left", va="top", fontsize=8, color=RULE)

        handles = [Patch(facecolor=FILL[lv], label=lv) for lv in LEVELS]
        handles.append(Patch(facecolor=NOT_RECORDED_FILL, edgecolor=NOT_RECORDED_INK,
                             hatch="////", linewidth=0, label="not recorded"))
        fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.02, 0.0),
                   ncol=4, frameon=False, fontsize=8)

        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=300, bbox_inches="tight", facecolor=SURFACE)
        plt.close(fig)
    return out
