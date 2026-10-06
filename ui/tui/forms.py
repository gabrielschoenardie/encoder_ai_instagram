from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable

from pydantic import ValidationError

from ui.config import EncodeConfig
from ui.launcher import PRESETS

FIT = ("contain", "cover")
FPS = ("auto", "24", "25", "30", "60")
MODE = ("crf", "2pass")
SOURCE_KIND = "source_kind"
FILE = "file"
FOLDER = "folder"
OUTDIR_ON = "output_dir_on"
FORM_ONLY = frozenset({SOURCE_KIND, OUTDIR_ON})
OUTDIR_EMPTY = "Informe a pasta de saída."


@dataclass(frozen=True)
class Field:
    name: str
    kind: str
    label: str
    options: tuple = ()
    lo: float | None = None
    hi: float | None = None
    step: float = 1.0
    integer: bool = False
    visible_if: Callable[[dict], bool] | None = None


CONTINUE = Field("__continue__", "action", "CONTINUAR")


def _cineon_on(d: dict) -> bool:
    return d.get("cineon_pipeline") == "on"


def _cineon_off(d: dict) -> bool:
    return d.get("cineon_pipeline") != "on"


def _enhance_on(d: dict) -> bool:
    return d.get("enhance") == "on"


def _ai_on(d: dict) -> bool:
    return d.get("enhance") == "on" and d.get("enhance_ai") == "on"


def is_folder(d: dict) -> bool:
    return d.get(SOURCE_KIND) == FOLDER


def _outdir_on(d: dict) -> bool:
    return is_folder(d) and d.get(OUTDIR_ON) == "on"


QUICK = (
    Field("fit", "choice", "Enquadramento", FIT),
    Field("fps", "choice", "FPS", FPS),
    Field("mode", "choice", "Modo", MODE),
)
CINEON = (
    Field("exposure_offset", "number", "Exposure offset (EV, -2..+2)", lo=-2.0, hi=2.0, step=0.1,
          visible_if=_cineon_on),
    Field("saturation", "number", "Saturação (0..2)", lo=0.0, hi=2.0, step=0.05, visible_if=_cineon_on),
    Field("fit", "choice", "Enquadramento", FIT),
)
BATCH = (
    Field(OUTDIR_ON, "toggle", "Definir pasta de saída separada"),
    Field("output_dir", "path", "Pasta de saída", visible_if=_outdir_on),
    Field("cineon_pipeline", "toggle", "Usar film look (Cineon)"),
)
TABS = ("Source", "Color/LUT", "Audio", "Enhance", "Export")
ADVANCED = {
    "Source": (
        Field(OUTDIR_ON, "toggle", "Pasta de saída separada", visible_if=is_folder),
        Field("output_dir", "path", "Pasta de saída", visible_if=_outdir_on),
        Field("cineon_pipeline", "toggle", "Pipeline Cineon (film look)"),
        Field("fit", "choice", "Enquadramento", FIT),
        Field("fps", "choice", "FPS", FPS),
        Field("scale", "choice", "Downscale 4K→1080p", ("auto", "off")),
        Field("mode", "choice", "Modo de encode", MODE),
        Field("performance", "choice", "Performance", ("quality", "balanced", "speed")),
    ),
    "Color/LUT": (
        Field("exposure_offset", "number", "Exposure offset (EV)", lo=-2.0, hi=2.0, step=0.1, visible_if=_cineon_on),
        Field("saturation", "number", "Saturação", lo=0.0, hi=2.0, step=0.05, visible_if=_cineon_on),
        Field("lut", "toggle", "Aplicar Hollywood LUT", visible_if=_cineon_off),
        Field("hdr", "choice", "HDR→SDR", ("auto", "off")),
        Field("tonemap", "choice", "Tonemap", ("mobius", "reinhard", "hable")),
    ),
    "Audio": (
        Field("loudnorm", "toggle", "Loudnorm EBU R128 (-14 LUFS)"),
        Field("ebu_meter", "toggle", "Monitor EBU R128 pós-encode (FFplay)"),
    ),
    "Enhance": (
        Field("enhance", "toggle", "Enhancement engine (denoise/sharpen/deband)"),
        Field("enhance_ai", "toggle", "Decisões via AI (mock CNN)", visible_if=_enhance_on),
        Field("mctf", "toggle", "MCTF mask video (anti-flicker)", visible_if=_ai_on),
        Field("dither", "choice", "Dither (ruído anti-banding)", ("auto", "on", "off")),
    ),
    "Export": (
        Field("show_hardware", "toggle", "Exibir perfil de hardware"),
        Field("threads", "number", "Threads (0 = auto)", lo=0, hi=None, step=1, integer=True),
    ),
}
PRESET_LABELS = tuple(PRESETS)
ENABLED_PRESETS = (1, 2, 3, 4, 5)
PRESET_HELP = {
    1: "FFmpeg nativo com LUT Hollywood. Você escolhe enquadramento, FPS e modo (CRF ou 2-pass).",
    2: "Pipeline Cineon (film look). Você ajusta exposição, saturação e enquadramento.",
    3: "Todos os vídeos de uma pasta (sem subpastas), um por vez. Pasta de saída e film look opcionais.",
    4: "Ferramentas utilitárias: sai da tela cheia, roda a ferramenta e volta à HOME.",
    5: "Todas as opções em 5 abas: Source · Color/LUT · Audio · Enhance · Export.",
}


def new_draft(preset: int) -> dict:
    if preset == 1:
        return EncodeConfig.preset_quick_ffmpeg().model_dump()
    if preset == 2:
        return EncodeConfig.preset_film_cineon().model_dump()
    if preset == 3:
        return {**EncodeConfig.preset_batch().model_dump(), SOURCE_KIND: FOLDER, OUTDIR_ON: "off"}
    if preset == 5:
        return {**EncodeConfig().model_dump(), SOURCE_KIND: FILE, OUTDIR_ON: "off"}
    return EncodeConfig().model_dump()


def form_for(preset: int) -> tuple:
    return {1: QUICK, 3: BATCH}.get(preset, CINEON)


def to_config(draft: dict) -> dict:
    out = {k: v for k, v in draft.items() if k not in FORM_ONLY}
    if not draft.get("batch") or draft.get(OUTDIR_ON) != "on":
        out["output_dir"] = None
    return out


def outdir_missing(draft: dict) -> bool:
    return _outdir_on(draft) and not str(draft.get("output_dir") or "").strip()


def visible(fields, draft: dict) -> tuple:
    return tuple(f for f in fields if f.visible_if is None or f.visible_if(draft))


def derive(draft: dict) -> dict:
    if draft.get("enhance") == "on" and draft.get("enhance_ai") != "on":
        return {**draft, "mctf": "off"}
    return draft


def apply_change(draft: dict, name: str, value) -> tuple:
    new = derive({**draft, name: value})
    try:
        EncodeConfig.model_validate(to_config(new))
    except ValidationError as exc:
        return draft, exc.errors()[0]["msg"]
    return new, None


def output_name(draft: dict) -> str:
    if not draft.get("input"):
        return "—"
    out = EncodeConfig.model_validate(to_config(draft)).output_path()
    return os.path.basename(out) if out else "—"
