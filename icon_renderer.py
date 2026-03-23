"""Pillow-based tray icon for OpenAI Usage Tray — Windows.

Renders a 64×64 RGBA image showing today's spend in dollars.
Background tint reflects cost level against thresholds.

Render pipeline: draw at 128×128 → LANCZOS downsample to 64×64.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

_RENDER = 128
_OUT = 64

_FONT_CANDIDATES = [
    "C:/Windows/Fonts/consolab.ttf",   # Consolas Bold
    "C:/Windows/Fonts/consola.ttf",    # Consolas Regular
    "C:/Windows/Fonts/courbd.ttf",     # Courier New Bold
    "C:/Windows/Fonts/cour.ttf",       # Courier New
    "C:/Windows/Fonts/lucon.ttf",      # Lucida Console
    "C:/Windows/Fonts/arialbd.ttf",    # Arial Bold (last resort)
]

# Background colours (RGBA) — dark base with cost-level tint
_BG_NORMAL = (26, 26, 26, 235)   # neutral dark
_BG_WARN   = (60, 38, 0, 235)    # amber tint
_BG_CRIT   = (60, 0, 0, 235)     # red tint
_TEXT_COLOR = "#DDDDDD"


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in _FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _draw_centered(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    text: str,
    fill: str,
    font: ImageFont.FreeTypeFont,
) -> None:
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        draw.text((cx - w // 2 - bbox[0], cy - h // 2 - bbox[1]), text, fill=fill, font=font)
    except AttributeError:
        # Pillow < 9.2 fallback
        draw.text((cx - 16, cy - 8), text, fill=fill, font=font)


def render_icon(today_cost: float, *, warning: float, critical: float) -> Image.Image:
    """Return a 64×64 RGBA PIL.Image for the system tray.

    Args:
        today_cost: Today's spend in USD.
        warning:    Monthly warning threshold in USD (for background tint).
        critical:   Monthly critical threshold in USD (for background tint).

    Note: tint thresholds are compared against today_cost for a live
    per-day indicator. The title bar uses month totals; the icon uses today.
    """
    if today_cost >= critical:
        bg = _BG_CRIT
    elif today_cost >= warning:
        bg = _BG_WARN
    else:
        bg = _BG_NORMAL

    sz = _RENDER
    img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, sz - 1, sz - 1], fill=bg)

    # Format: "$4.20" for < $10, "$14.2" for < $100, "$142" for >= $100
    if today_cost >= 100:
        text = f"${int(today_cost)}"
        font_size = 36
    elif today_cost >= 10:
        text = f"${today_cost:.1f}"
        font_size = 32
    else:
        text = f"${today_cost:.2f}"
        font_size = 28

    font = _load_font(font_size)
    _draw_centered(draw, sz // 2, sz // 2, text, _TEXT_COLOR, font)

    return img.resize((_OUT, _OUT), Image.LANCZOS)
