"""Pure aspect-ratio classification — no I/O, no rich.

Shared by the UI and, via a guarded import, by the encoder engine so source
aspect reads the same everywhere. Callers pass ROTATION-CORRECTED (effective)
dimensions, so an iPhone vertical clip (physically landscape + rotate=90)
classifies as '9:16', not '16:9'.
"""
from __future__ import annotations

from math import gcd

_KNOWN = (
    ("9:16", 9 / 16),
    ("3:4", 3 / 4),
    ("1:1", 1.0),
    ("4:3", 4 / 3),
    ("16:9", 16 / 9),
)


def classify_aspect(width: int, height: int, tol: float = 0.04) -> str:
    """Label the aspect ratio of effective dims; '?' when unusable."""
    if width <= 0 or height <= 0:
        return "?"
    ratio = width / height
    for label, target in _KNOWN:
        if abs(ratio - target) <= target * tol:
            return label
    g = gcd(int(width), int(height)) or 1
    return f"{int(width) // g}:{int(height) // g}"


def orientation_of(width: int, height: int) -> str:
    """'portrait' | 'landscape' | 'square' | '?' from effective dims."""
    if width <= 0 or height <= 0:
        return "?"
    if height > width:
        return "portrait"
    if width > height:
        return "landscape"
    return "square"


def describe_aspect(width: int, height: int, rotation: int = 0) -> str:
    """Human-readable: aspect + orientation + iPhone auto-rotate note."""
    aspect = classify_aspect(width, height)
    orient = {
        "portrait": "vertical",
        "landscape": "horizontal",
        "square": "quadrado",
    }.get(orientation_of(width, height), "")
    note = " · iPhone auto-rotate" if rotation in (90, -90, 270, -270) else ""
    return f"{aspect} {orient}".strip() + note
