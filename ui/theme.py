"""
ui.theme
========
Premiere-Pro-styled visual identity for the encoder's terminal UI.

Single source of truth for colors, named Rich styles, box choices and glyph
sets (with ASCII fallbacks for legacy Windows consoles). Everything visual in
the ``ui`` package pulls from here so the look stays cohesive and a palette
tweak is a one-line change.

The module is import-safe with nothing but ``rich`` installed; it never touches
the encoder engine.
"""

from __future__ import annotations

import sys

from rich import box
from rich.console import Console
from rich.theme import Theme

# ──────────────────────────────────────────────────────────────────────────────
# Palette (Adobe Premiere Pro inspired: indigo/violet on ink, cyan/amber accents)
# ──────────────────────────────────────────────────────────────────────────────
PALETTE = {
    "ink":      "#13141a",   # background reference (not painted, just documented)
    "indigo":   "#5b6cff",   # primary brand accent
    "violet":   "#a06bff",   # secondary brand accent
    "cyan":     "#33d6e0",   # informational highlight
    "amber":    "#ffb454",   # warnings / attention
    "green":    "#3ddc84",   # success / pass
    "red":      "#ff5c7a",   # error / fail
    "gold":     "#d4af37",   # "delivery ready" seal accent
    "text":     "#e6e8ef",   # primary text
    "muted":    "#8a8fa3",   # secondary / dim text
}

# ──────────────────────────────────────────────────────────────────────────────
# Named styles — referenced as "[label]" / "[value]" etc. throughout the UI
# ──────────────────────────────────────────────────────────────────────────────
THEME = Theme(
    {
        "primary":       f"bold {PALETTE['indigo']}",
        "accent":        PALETTE["violet"],
        "info":          PALETTE["cyan"],
        "ok":            f"bold {PALETTE['green']}",
        "warn":          f"bold {PALETTE['amber']}",
        "err":           f"bold {PALETTE['red']}",
        "muted":         PALETTE["muted"],
        "title":         f"bold {PALETTE['violet']}",
        "label":         PALETTE["muted"],
        "value":         f"bold {PALETTE['text']}",
        "seal":          f"bold {PALETTE['gold']}",
        # dim colour-accent variants for secondary coloured text
        "accent.dim":    f"dim {PALETTE['violet']}",
        "info.dim":      f"dim {PALETTE['cyan']}",
        "value.dim":     f"dim {PALETTE['text']}",
        # tab bar
        "tab.active":    f"bold {PALETTE['ink']} on {PALETTE['indigo']}",
        "tab.inactive":  PALETTE["muted"],
        # structural
        "panel.border":  PALETTE["indigo"],
        "panel.title":   f"bold {PALETTE['violet']}",
        "bar.complete":  PALETTE["indigo"],
        "bar.pulse":     PALETTE["violet"],
        "bar.back":      PALETTE["muted"],
    }
)

# Box styles used across panels (kept here so the look is consistent)
PANEL_BOX = box.ROUNDED
HEAVY_BOX = box.DOUBLE
GRID_BOX = box.SIMPLE

# ──────────────────────────────────────────────────────────────────────────────
# Glyphs — Unicode set + ASCII fallback for legacy consoles
# ──────────────────────────────────────────────────────────────────────────────
_GLYPHS_UNICODE = {
    "ok": "✓",
    "warn": "⚠",
    "err": "✗",
    "bullet": "●",
    "arrow": "▸",
    "star": "★",
    "block_full": "█",
    "block_empty": "░",
    "tab_l": "▎",
    "film": "🎞",
    "audio": "🎧",
    "spark": "✨",
}
_GLYPHS_ASCII = {
    "ok": "OK",
    "warn": "!",
    "err": "x",
    "bullet": "*",
    "arrow": ">",
    "star": "*",
    "block_full": "#",
    "block_empty": "-",
    "tab_l": "|",
    "film": "[F]",
    "audio": "[A]",
    "spark": "*",
}


def glyphs(console: Console | None = None) -> dict:
    """Return the glyph table, downgrading to ASCII on non-Unicode consoles."""
    if console is not None and getattr(console, "legacy_windows", False):
        return dict(_GLYPHS_ASCII)
    enc = (getattr(console, "encoding", None) or "utf-8").lower() if console else "utf-8"
    if "utf" not in enc:
        return dict(_GLYPHS_ASCII)
    return dict(_GLYPHS_UNICODE)


# ──────────────────────────────────────────────────────────────────────────────
# Console factory
# ──────────────────────────────────────────────────────────────────────────────
def _ensure_utf8_streams() -> None:
    """Best-effort: switch stdout/stderr to UTF-8 so emoji/box glyphs don't crash
    on legacy Windows consoles (cp1252). Guarded and idempotent; a no-op where
    reconfigure is unavailable or the stream is already UTF-8.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            enc = (getattr(stream, "encoding", "") or "").lower()
            if "utf" not in enc:
                stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:
            pass


def get_console(**kwargs) -> Console:
    """Themed Rich Console factory. The single entry point for a styled console.

    Falls back gracefully on any terminal: stdout/stderr are nudged to UTF-8,
    Rich auto-detects color/Unicode support, and our glyph table downgrades to
    ASCII when needed.
    """
    _ensure_utf8_streams()
    return Console(theme=THEME, **kwargs)
