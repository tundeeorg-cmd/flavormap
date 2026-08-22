"""Figure 4 — ingredient prevalence against distance from Bangkok, small multiples.

Bible §10 / §21 item 2. One panel per ingredient. X is great-circle km from Bangkok's
centroid, Y is the share of that province's recipes containing the ingredient, colour is
region, and point area is the number of recipes behind the point — a province resting on
one recipe must not read like a province resting on twenty.

The question it answers is whether pla ra and sticky rice separate from a flat control.
If every panel looks like the control, that is worth knowing in month one.

Output is a single self-contained HTML file with inline SVG: no JavaScript, no CDN, no
runtime dependency. It can be opened from disk or published as-is.

**This module computes; it does not decide.** Which ingredients to panel, and how an
ingredient is matched, are the caller's arguments — matching in particular is HD-6
territory (`canonical_ingredients` is empty and stays that way until the lexicon is
authored by hand), so every panel records the pattern it used and the figure prints it.
"""

from __future__ import annotations

import html
import math
from dataclasses import dataclass, field

# Region colours. Chosen to stay distinguishable in greyscale print as well as on screen.
REGION_COLOURS = {
    "Central": "#4C6EF5",
    "North": "#12B886",
    "Northeast": "#E8590C",
    "South": "#AE3EC9",
}
UNKNOWN_COLOUR = "#868E96"


@dataclass
class ProvincePoint:
    province_code: str
    name_en: str
    region: str | None
    km_from_bangkok: float
    n_recipes: int
    n_with_ingredient: int

    @property
    def prevalence(self) -> float:
        return self.n_with_ingredient / self.n_recipes if self.n_recipes else 0.0


@dataclass
class Panel:
    """One ingredient's panel."""

    label: str
    pattern: str
    points: list[ProvincePoint] = field(default_factory=list)
    is_control: bool = False
    note: str | None = None

    @property
    def n_provinces(self) -> int:
        return len(self.points)

    @property
    def n_recipes_with(self) -> int:
        return sum(p.n_with_ingredient for p in self.points)


def _scale(value: float, lo: float, hi: float, out_lo: float, out_hi: float) -> float:
    if hi <= lo:
        return out_lo
    return out_lo + (value - lo) / (hi - lo) * (out_hi - out_lo)


def _panel_svg(panel: Panel, max_km: float, width: int, height: int) -> str:
    """One small multiple, as an SVG group."""
    pad_l, pad_r, pad_t, pad_b = 38, 10, 26, 30
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b

    parts: list[str] = []
    title = html.escape(panel.label) + (" (control)" if panel.is_control else "")
    parts.append(
        f'<text x="{pad_l}" y="16" class="panel-title">{title}</text>'
        f'<text x="{width - pad_r}" y="16" class="panel-n" text-anchor="end">'
        f"n={panel.n_provinces} prov · {panel.n_recipes_with} rec</text>"
    )

    # Frame and gridlines at 0 / 50 / 100 %.
    for share in (0.0, 0.5, 1.0):
        y = pad_t + plot_h - _scale(share, 0, 1, 0, plot_h)
        parts.append(
            f'<line x1="{pad_l}" y1="{y:.1f}" x2="{pad_l + plot_w}" y2="{y:.1f}" class="grid"/>'
        )
        parts.append(
            f'<text x="{pad_l - 6}" y="{y + 3:.1f}" class="tick" text-anchor="end">'
            f"{int(share * 100)}%</text>"
        )

    for km in (0, max_km / 2, max_km):
        x = pad_l + _scale(km, 0, max_km, 0, plot_w)
        parts.append(
            f'<text x="{x:.1f}" y="{pad_t + plot_h + 16}" class="tick" '
            f'text-anchor="middle">{int(km)}</text>'
        )

    max_n = max((p.n_recipes for p in panel.points), default=1)
    for point in sorted(panel.points, key=lambda p: -p.n_recipes):
        x = pad_l + _scale(point.km_from_bangkok, 0, max_km, 0, plot_w)
        y = pad_t + plot_h - _scale(point.prevalence, 0, 1, 0, plot_h)
        # Area, not radius, encodes n — radius would exaggerate.
        radius = 2.0 + 4.0 * math.sqrt(point.n_recipes / max_n)
        colour = REGION_COLOURS.get(point.region or "", UNKNOWN_COLOUR)
        tip = (
            f"{point.name_en}: {point.n_with_ingredient}/{point.n_recipes} recipes, "
            f"{point.km_from_bangkok:.0f} km"
        )
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{colour}" '
            f'fill-opacity="0.7" stroke="{colour}" stroke-width="0.8">'
            f"<title>{html.escape(tip)}</title></circle>"
        )

    parts.append(
        f'<rect x="{pad_l}" y="{pad_t}" width="{plot_w}" height="{plot_h}" class="frame"/>'
    )
    return "".join(parts)


def render(
    panels: list[Panel],
    *,
    subtitle: str,
    caveats: list[str],
    columns: int = 3,
    panel_width: int = 250,
    panel_height: int = 170,
) -> str:
    """Assemble the small multiples into one self-contained HTML document."""
    max_km = max(
        (p.km_from_bangkok for panel in panels for p in panel.points), default=1000.0
    )
    max_km = math.ceil(max_km / 100) * 100

    cells: list[str] = []
    for index, panel in enumerate(panels):
        col, row = index % columns, index // columns
        x, y = col * panel_width, row * panel_height
        cells.append(
            f'<g transform="translate({x},{y})">'
            + _panel_svg(panel, max_km, panel_width, panel_height)
            + "</g>"
        )

    rows = math.ceil(len(panels) / columns) if panels else 0
    svg_w, svg_h = columns * panel_width, rows * panel_height

    legend = "".join(
        f'<span class="key"><i style="background:{colour}"></i>{html.escape(region)}</span>'
        for region, colour in REGION_COLOURS.items()
    )
    caveat_html = "".join(f"<li>{html.escape(c)}</li>" for c in caveats)
    patterns = "".join(
        f"<li><code>{html.escape(p.label)}</code> matched as "
        f"<code>{html.escape(p.pattern)}</code>"
        + (f" — {html.escape(p.note)}" if p.note else "")
        + "</li>"
        for p in panels
    )

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FlavorMap — Figure 4</title>
<style>
 :root {{ --fg:#1a1a1a; --muted:#666; --bg:#fff; --grid:#e5e5e5; --frame:#bbb; }}
 @media (prefers-color-scheme: dark) {{
   :root {{ --fg:#e8e8e8; --muted:#9a9a9a; --bg:#141414; --grid:#2c2c2c; --frame:#444; }}
 }}
 body {{ margin:0; padding:24px; background:var(--bg); color:var(--fg);
        font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
 h1 {{ font-size:19px; margin:0 0 2px; }}
 .sub {{ color:var(--muted); margin:0 0 14px; }}
 .wrap {{ overflow-x:auto; }}
 .panel-title {{ font-size:12px; font-weight:600; fill:var(--fg); }}
 .panel-n {{ font-size:10px; fill:var(--muted); }}
 .tick {{ font-size:9px; fill:var(--muted); }}
 .grid {{ stroke:var(--grid); stroke-width:1; }}
 .frame {{ fill:none; stroke:var(--frame); stroke-width:1; }}
 .key {{ margin-right:14px; font-size:12px; color:var(--muted); }}
 .key i {{ display:inline-block; width:10px; height:10px; border-radius:50%;
           margin-right:5px; vertical-align:-1px; }}
 .axis {{ color:var(--muted); font-size:12px; margin:6px 0 16px; }}
 .caveats {{ border-left:3px solid var(--frame); padding:2px 0 2px 14px;
             margin:20px 0; color:var(--muted); font-size:13px; }}
 code {{ font-size:12px; }}
</style></head><body>
<h1>Figure 4 — ingredient prevalence vs. distance from Bangkok</h1>
<p class="sub">{html.escape(subtitle)}</p>
<div>{legend}</div>
<div class="wrap"><svg width="{svg_w}" height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}"
 xmlns="http://www.w3.org/2000/svg" role="img"
 aria-label="Small multiples of ingredient prevalence against distance from Bangkok">
{"".join(cells)}
</svg></div>
<p class="axis">X: km from Bangkok · Y: share of that province's recipes containing the
ingredient · point area: recipes behind the point</p>
<div class="caveats"><strong>Read with:</strong><ul>{caveat_html}</ul>
<strong>Ingredient matching (provisional — HD-6 open):</strong><ul>{patterns}</ul></div>
</body></html>
"""
