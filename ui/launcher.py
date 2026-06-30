"""
ui.launcher
===========
The interactive Premiere-styled launcher (wizard).

Flow:  banner → preset menu → source pick → (preset-specific or full tabbed
config) → settings PREVIEW card → confirm → return an ``argparse.Namespace``.

The returned Namespace is *exactly* what the engine's ``main()`` consumes, so
the engine can dispatch it through its existing single/batch code paths. Returns
``None`` if the user cancels.

All prompting happens here, before any ``Live`` dashboard starts (no nesting of
interactive prompts inside ``Live``).
"""

from __future__ import annotations

import argparse
import os
from typing import Optional

from rich.prompt import Confirm

from . import components as C
from .config import EncodeConfig
from .probe import probe_source_dims
from .prompts import (
    ask_choice,
    ask_folder,
    ask_number,
    ask_path,
    ask_select,
    ask_toggle,
)
from .theme import get_console

SECTIONS = ["Source", "Color/LUT", "Audio", "Enhance", "Export"]

PRESETS = [
    "Encode rápido (FFmpeg)",
    "Film look (Cineon)",
    "Batch de pasta",
    "Configurar avançado…",
]


def run_launcher(console=None) -> Optional[argparse.Namespace]:
    """Drive the wizard. Returns a Namespace or None (cancelled).

    Ctrl-C and a closed stdin (EOF, e.g. piped input running out) cancel the
    wizard cleanly instead of crashing with a traceback.
    """
    con = console or get_console()
    try:
        return _run_launcher(con)
    except (EOFError, KeyboardInterrupt):
        con.print("\n[warn]Cancelado pelo usuário.[/warn]")
        return None


def _run_launcher(con) -> Optional[argparse.Namespace]:
    con.print(C.banner("REELS ENCODER", "Premiere Workspace · UI interativa"))

    preset = ask_choice(con, "Selecione um fluxo", PRESETS, default=1)

    if preset == 1:
        cfg = _flow_quick(con)
    elif preset == 2:
        cfg = _flow_cineon(con)
    elif preset == 3:
        cfg = _flow_batch(con)
    else:
        cfg = _flow_advanced(con)

    if cfg is None:
        return None

    # Preview → confirm loop
    while True:
        # Best-effort source-aspect probe (None for batch or any failure) so the
        # Program viewer can reflect the real source orientation.
        src_dims = probe_source_dims(cfg.input) if cfg.input else None
        con.print(C.settings_preview(cfg, src_dims=src_dims, console=con))
        if Confirm.ask("[primary]Iniciar encode com estas configurações?[/primary]",
                       default=True, console=con):
            return cfg.to_namespace()
        if not Confirm.ask("[primary]Revisar configurações?[/primary]",
                           default=True, console=con):
            con.print("[warn]Cancelado pelo usuário.[/warn]")
            return None
        cfg = _flow_advanced(con, base=cfg)
        if cfg is None:
            return None


# ──────────────────────────────────────────────────────────────────────────────
# Preset flows
# ──────────────────────────────────────────────────────────────────────────────
def _flow_quick(con) -> Optional[EncodeConfig]:
    path = ask_path(con, "Arquivo de vídeo de entrada")
    cfg = EncodeConfig.preset_quick_ffmpeg(path)
    cfg.fit = ask_select(con, "Enquadramento", ["contain", "cover"], cfg.fit)
    cfg.fps = ask_select(con, "FPS", ["auto", "24", "25", "30", "60"], cfg.fps)
    cfg.mode = ask_select(con, "Modo", ["crf", "2pass"], cfg.mode)
    return cfg


def _flow_cineon(con) -> Optional[EncodeConfig]:
    path = ask_path(con, "Arquivo de vídeo de entrada")
    cfg = EncodeConfig.preset_film_cineon(path)
    cfg.exposure_offset = ask_number(con, "Exposure offset (EV, -2..+2)",
                                     cfg.exposure_offset, lo=-2.0, hi=2.0)
    cfg.saturation = ask_number(con, "Saturação (0..2)", cfg.saturation, lo=0.0, hi=2.0)
    cfg.fit = ask_select(con, "Enquadramento", ["contain", "cover"], cfg.fit)
    return cfg


def _flow_batch(con) -> Optional[EncodeConfig]:
    folder = ask_folder(con, "Pasta com os vídeos")
    cfg = EncodeConfig.preset_batch(folder)
    if Confirm.ask("[primary]Definir pasta de saída separada?[/primary]",
                   default=False, console=con):
        cfg.output_dir = ask_folder(con, "Pasta de saída", must_exist=False)
    cfg.cineon_pipeline = ask_toggle(con, "Usar film look (Cineon)?", default_on=False)
    return cfg


# ──────────────────────────────────────────────────────────────────────────────
# Advanced (full tabbed) flow
# ──────────────────────────────────────────────────────────────────────────────
def _flow_advanced(con, base: Optional[EncodeConfig] = None) -> Optional[EncodeConfig]:
    cfg = base.model_copy(deep=True) if base else None

    # SOURCE
    con.print(C.tab_bar(SECTIONS, active=0, console=con))
    if cfg is None or not (cfg.input or cfg.batch):
        is_batch = ask_toggle(con, "É um batch de pasta?", default_on=False) == "on"
        if is_batch:
            folder = ask_folder(con, "Pasta com os vídeos")
            cfg = EncodeConfig.preset_batch(folder)
            if Confirm.ask("[primary]Pasta de saída separada?[/primary]",
                           default=False, console=con):
                cfg.output_dir = ask_folder(con, "Pasta de saída", must_exist=False)
        else:
            path = ask_path(con, "Arquivo de vídeo de entrada")
            cfg = cfg or EncodeConfig()
            cfg.input = path
    cfg.cineon_pipeline = ask_toggle(con, "Pipeline Cineon (film look)?",
                                     default_on=cfg.cineon_pipeline == "on")
    cfg.fit = ask_select(con, "Enquadramento", ["contain", "cover"], cfg.fit)
    cfg.fps = ask_select(con, "FPS", ["auto", "24", "25", "30", "60"], cfg.fps)
    cfg.scale = ask_select(con, "Downscale 4K→1080p", ["auto", "off"], cfg.scale)
    cfg.mode = ask_select(con, "Modo de encode", ["crf", "2pass"], cfg.mode)
    cfg.performance = ask_select(con, "Performance",
                                 ["quality", "balanced", "speed"], cfg.performance)

    # COLOR / LUT
    con.print(C.tab_bar(SECTIONS, active=1, console=con))
    if cfg.cineon_pipeline == "on":
        cfg.exposure_offset = ask_number(con, "Exposure offset (EV)",
                                         cfg.exposure_offset, lo=-2.0, hi=2.0)
        cfg.saturation = ask_number(con, "Saturação", cfg.saturation, lo=0.0, hi=2.0)
    else:
        cfg.lut = ask_toggle(con, "Aplicar Hollywood LUT?", default_on=cfg.lut == "on")
    cfg.hdr = ask_select(con, "HDR→SDR", ["auto", "off"], cfg.hdr)
    cfg.tonemap = ask_select(con, "Tonemap",
                             ["mobius", "reinhard", "hable", "bt2390"], cfg.tonemap)

    # AUDIO
    con.print(C.tab_bar(SECTIONS, active=2, console=con))
    cfg.loudnorm = ask_toggle(con, "Loudnorm EBU R128 (-14 LUFS)?",
                              default_on=cfg.loudnorm == "on")
    cfg.ebu_meter = ask_toggle(con, "Monitor EBU R128 pós-encode (FFplay)?",
                               default_on=cfg.ebu_meter == "on")

    # ENHANCE
    con.print(C.tab_bar(SECTIONS, active=3, console=con))
    cfg.enhance = ask_toggle(con, "Enhancement engine (denoise/sharpen/deband)?",
                             default_on=cfg.enhance == "on")
    if cfg.enhance == "on":
        cfg.enhance_ai = ask_toggle(con, "Decisões via AI (mock CNN)?",
                                    default_on=cfg.enhance_ai == "on")
        cfg.mctf = ask_toggle(con, "MCTF mask video (anti-flicker)?",
                              default_on=cfg.mctf == "on")
    cfg.dither = ask_select(con, "Blue-noise dither", ["auto", "on", "off"], cfg.dither)

    # EXPORT
    con.print(C.tab_bar(SECTIONS, active=4, console=con))
    cfg.show_hardware = ask_toggle(con, "Exibir perfil de hardware?",
                                   default_on=cfg.show_hardware == "on")
    cfg.threads = int(ask_number(con, "Threads (0 = auto)", cfg.threads, lo=0, integer=True))

    return cfg
