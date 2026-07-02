"""Startup preflight — verify the required FFmpeg binaries are reachable
(bundled in ``bin/`` or on PATH) before an encode begins."""
from __future__ import annotations

from typing import List, Sequence

from .binaries import find_missing_binaries


def missing_ffmpeg_binaries(
    required: Sequence[str] = ("ffmpeg", "ffprobe"), **kw
) -> List[str]:
    """Return the required binaries that are missing (bundled or PATH)."""
    return find_missing_binaries(required, **kw)
