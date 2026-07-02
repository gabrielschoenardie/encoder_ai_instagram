"""Best-effort, silent, rotation-aware ffprobe helper for the UI.

Mirrors the rotation logic of the engine's ``get_input_resolution`` but never
raises and never prints: any failure (missing ffprobe, bad path, parse error)
returns ``None`` so the UI can fall back to the canonical Reels target.
"""
from __future__ import annotations

import json
import subprocess
from typing import Optional, Tuple

try:
    from .binaries import FFPROBE
except Exception:
    FFPROBE = "ffprobe"


def probe_source_dims(path: str) -> Optional[Tuple[int, int]]:
    """Effective (rotation-corrected) (width, height) of a video, or None.

    Best-effort and silent: returns None if ffprobe is missing/fails so the UI
    can fall back to the canonical target. Mirrors the engine's rotation swap so
    an iPhone vertical clip reports portrait effective dims.
    """
    try:
        out = subprocess.check_output(
            [
                FFPROBE,
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height:stream_tags=rotate:side_data:format_tags=rotate",
                "-of",
                "json",
                path,
            ],
            stderr=subprocess.PIPE,
        )

        data = json.loads(out.decode())

        width = 0
        height = 0
        rotation = 0

        streams = data.get("streams", [])
        if streams:
            stream = streams[0]
            width = int(stream.get("width", 0))
            height = int(stream.get("height", 0))

            tags = stream.get("tags", {})
            if "rotate" in tags:
                rotation = int(tags["rotate"])

            for sd in stream.get("side_data_list", []):
                if sd.get("side_data_type") == "Display Matrix":
                    rot = sd.get("rotation", 0)
                    if rot != 0:
                        rotation = int(rot)

        if rotation == 0:
            fmt_tags = data.get("format", {}).get("tags", {})
            if "rotate" in fmt_tags:
                rotation = int(fmt_tags["rotate"])

        if rotation in (90, -90, 270, -270):
            width, height = height, width

        if width > 0 and height > 0:
            return width, height
        return None

    except Exception:
        return None
