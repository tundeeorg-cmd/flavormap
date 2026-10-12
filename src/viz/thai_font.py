"""The font family for figures that print Thai text.

The first installed family on `THAI_FONTS` wins. DejaVu Sans is matplotlib's bundled
fallback and has no Thai glyphs, so it is last on purpose.
"""

from __future__ import annotations

from matplotlib import font_manager

THAI_FONTS = ("Sarabun", "Thonburi", "Noto Sans Thai", "Leelawadee UI", "Tahoma")


def font_family() -> list[str]:
    installed = {f.name for f in font_manager.fontManager.ttflist}
    return [f for f in THAI_FONTS if f in installed] + ["DejaVu Sans"]
