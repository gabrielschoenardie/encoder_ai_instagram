"""Resolve FFmpeg CLI binaries (ffmpeg / ffprobe / ffplay).

Portability: end users don't need a system FFmpeg. Bundled builds dropped into
the project-root ``bin/`` folder win; otherwise we fall back to whatever is on
the system PATH. Pure stdlib, PyInstaller-aware (``sys.frozen``).
"""
from __future__ import annotations

import os
import shutil
import sys
from typing import Callable, List, Optional, Sequence


def _proj_dir() -> str:
    """Directory holding the bundled ``bin/`` folder (frozen → next to the exe;
    else the repo root, i.e. the parent of this ``ui/`` package)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _exe_name(name: str) -> str:
    """Platform-correct filename (``ffmpeg`` -> ``ffmpeg.exe`` on Windows)."""
    if os.name == "nt" and not name.lower().endswith(".exe"):
        return name + ".exe"
    return name


def bundled_path(name: str, proj_dir: Optional[str] = None) -> Optional[str]:
    """Path to ``bin/<name>`` if it exists on disk, else None."""
    base = proj_dir if proj_dir is not None else _proj_dir()
    candidate = os.path.join(base, "bin", _exe_name(name))
    return candidate if os.path.isfile(candidate) else None


def resolve_binary(
    name: str,
    which: Callable[[str], Optional[str]] = shutil.which,
    proj_dir: Optional[str] = None,
) -> str:
    """Resolve a binary name to an invocable path.

    Order: bundled ``bin/`` -> system PATH -> bare name (last resort, so error
    messages still read sensibly)."""
    b = bundled_path(name, proj_dir=proj_dir)
    if b:
        return b
    on_path = which(name) or which(_exe_name(name))
    if on_path:
        return on_path
    return _exe_name(name) if os.name == "nt" else name


def available(
    name: str,
    which: Callable[[str], Optional[str]] = shutil.which,
    proj_dir: Optional[str] = None,
) -> bool:
    """True if ``name`` is bundled in ``bin/`` or found on PATH."""
    if bundled_path(name, proj_dir=proj_dir):
        return True
    return bool(which(name) or which(_exe_name(name)))


def find_missing_binaries(
    required: Sequence[str] = ("ffmpeg", "ffprobe"),
    which: Callable[[str], Optional[str]] = shutil.which,
    proj_dir: Optional[str] = None,
) -> List[str]:
    """Subset of ``required`` that is neither bundled nor on PATH."""
    return [n for n in required if not available(n, which=which, proj_dir=proj_dir)]


# Resolved once at import; the engine threads these into every subprocess call.
# ffplay is OPTIONAL (visual QC only) and never part of the required set.
FFMPEG = resolve_binary("ffmpeg")
FFPROBE = resolve_binary("ffprobe")
FFPLAY = resolve_binary("ffplay")
