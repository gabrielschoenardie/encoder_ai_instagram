"""
ui
==
Premiere-Pro-styled interactive terminal UI for the Reels encoder.

Additive layer: the engine imports this package behind guarded ``try/except
ImportError`` so the classic CLI keeps working if ``ui`` (or its deps) is absent.

Public API:
    get_console()      -> themed Rich Console
    THEME              -> the Rich Theme
    make_dashboard(...) -> Live encode dashboard (duck-types ResolveProgressHUD)
    EncodeConfig       -> typed config model (argparse round-trip)

``make_dashboard`` is imported lazily to keep import cost low and avoid
pulling optional deps until actually needed.
"""

from __future__ import annotations

from .theme import THEME, get_console, glyphs  # noqa: F401

__all__ = ["THEME", "get_console", "glyphs", "EncodeConfig", "make_dashboard"]


def __getattr__(name):  # PEP 562 lazy attributes
    if name == "EncodeConfig":
        from .config import EncodeConfig
        return EncodeConfig
    if name == "make_dashboard":
        from .dashboard import make_dashboard
        return make_dashboard
    raise AttributeError(f"module 'ui' has no attribute {name!r}")
