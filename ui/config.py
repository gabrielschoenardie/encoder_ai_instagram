"""
ui.config
=========
Typed configuration model that mirrors the encoder's ``argparse`` surface.

``EncodeConfig`` is the single typed source of truth for a job collected by the
interactive launcher. ``to_namespace()`` emits the *exact* ``argparse.Namespace``
the engine already consumes (identical attribute names and ``"on"/"off"`` string
values), so ``_encode_single_file`` / ``run_ffmpeg`` cannot tell whether the
config came from the CLI or the wizard.

Validation (ranges, choices) gives the wizard readable errors before a long
encode starts. Pydantic v2 is imported lazily by the package, but this module
imports it at top level because it *is* the model layer.
"""

from __future__ import annotations

import argparse
import os
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

# Literals kept as plain str with explicit choice validation so the model stays
# permissive to load from a Namespace while still validating user input.
OnOff = str
_CHOICES = {
    "mode": {"crf", "2pass"},
    "lut": {"on", "off"},
    "loudnorm": {"on", "off"},
    "ebu_meter": {"on", "off"},
    "hdr": {"auto", "off"},
    "tonemap": {"mobius", "reinhard", "hable", "bt2390"},
    "fps": {"auto", "24", "25", "30", "60"},
    "scale": {"auto", "off"},
    "fit": {"contain", "cover"},
    "show_hardware": {"on", "off"},
    "performance": {"quality", "balanced", "speed"},
    "cineon_pipeline": {"on", "off"},
    "enhance": {"on", "off"},
    "mctf": {"on", "off"},
    "dither": {"on", "off", "auto"},
    "enhance_ai": {"on", "off"},
}

DEFAULT_CINEON_LUT = "FilmLook_Portra400_SkinPriority_D65.cube"


class EncodeConfig(BaseModel):
    """All encoder options, mirroring ``argparse`` dest names 1:1."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    # I/O
    input: Optional[str] = None
    batch: Optional[str] = None
    output_dir: Optional[str] = None

    # Core encode
    mode: str = "crf"
    fps: str = "30"
    scale: str = "auto"
    fit: str = "contain"
    performance: str = "balanced"
    threads: int = Field(default=0, ge=0)

    # Color / LUT / HDR
    lut: str = "on"
    hdr: str = "auto"
    tonemap: str = "mobius"

    # Audio
    loudnorm: str = "on"
    ebu_meter: str = "on"

    # Cineon
    cineon_pipeline: str = "off"
    cineon_lut: str = DEFAULT_CINEON_LUT
    exposure_offset: float = Field(default=0.0, ge=-2.0, le=2.0)
    saturation: float = Field(default=1.0, ge=0.0, le=2.0)

    # Enhance / AI
    enhance: str = "on"
    enhance_ai: str = "on"
    mctf: str = "on"
    dither: str = "auto"

    # Misc / engine flags
    show_hardware: str = "on"
    hardware_info: bool = False
    ui: bool = False

    # ── validation ────────────────────────────────────────────────────────────
    def model_post_init(self, _ctx) -> None:
        for field, allowed in _CHOICES.items():
            val = getattr(self, field)
            if val not in allowed:
                raise ValueError(
                    f"{field}={val!r} inválido; escolha um de {sorted(allowed)}"
                )

    # ── conversions ───────────────────────────────────────────────────────────
    def to_namespace(self) -> argparse.Namespace:
        """Produce the exact argparse.Namespace the engine expects."""
        return argparse.Namespace(**self.model_dump())

    @classmethod
    def from_namespace(cls, ns: argparse.Namespace) -> "EncodeConfig":
        """Build a config from an argparse Namespace, ignoring unknown attrs."""
        known = set(cls.model_fields.keys())
        data = {k: v for k, v in vars(ns).items() if k in known}
        return cls(**data)

    # ── output naming (mirrors the engine's filename logic) ─────────────────────
    def output_path(self, input_file: Optional[str] = None) -> Optional[str]:
        """Default output filename for a single file, matching main()'s logic."""
        src = input_file or self.input
        if not src:
            return None
        base, _ = os.path.splitext(src)
        if self.cineon_pipeline == "on":
            return f"{base}_Cineon_Film.mp4"
        if self.mode == "crf":
            return f"{base}_Hollywood_CRF18.mp4"
        return f"{base}_Hollywood_2Pass.mp4"

    # ── presets ─────────────────────────────────────────────────────────────────
    @classmethod
    def preset_quick_ffmpeg(cls, input_file: Optional[str] = None) -> "EncodeConfig":
        """Fast FFmpeg native encode with LUT (the default product experience)."""
        return cls(input=input_file, cineon_pipeline="off", mode="crf", lut="on")

    @classmethod
    def preset_film_cineon(cls, input_file: Optional[str] = None) -> "EncodeConfig":
        """Film emulation via the Cineon pipeline."""
        return cls(input=input_file, cineon_pipeline="on", mode="crf")

    @classmethod
    def preset_batch(cls, folder: Optional[str] = None) -> "EncodeConfig":
        """Batch a folder with FFmpeg native (meter auto-suppressed by engine)."""
        return cls(batch=folder, cineon_pipeline="off", mode="crf", lut="on")
