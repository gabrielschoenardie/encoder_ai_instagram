from __future__ import annotations

import os
from typing import Callable

from rich.console import Group, RenderableType
from rich.layout import Layout
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from ui.theme import HEAVY_BOX, PANEL_BOX, glyphs
from ui.tui import state as S

try:
    from version import __version__
except Exception:
    __version__ = "2.1.0"

SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
RAIL = ("HOME", "SOURCE", "CONFIG", "PREVIEW", "READY", "ENCODE", "QC", "DELIVERY")
STATUS = {
    S.READY: "● READY", S.ENCODING: "ENCODING", S.DETAILS: "DETAILS", S.LOG: "LOG", S.QC: "QC",
    S.COMPLETED: "✓ COMPLETED", S.ERROR: "✗ ERROR", S.CANCELLED: "⚠ CANCELLED",
}
FOOTER_KEYS = {
    S.READY: "[←→] Choose   [ENTER] Start encode   [ESC] Sair",
    S.ENCODING: "[D] Details   [L] Log   [C] Cancel   [Ctrl+C] Interrupt",
    S.DETAILS: "[D] Voltar   [L] Log   [ESC] Voltar   [Ctrl+C] Interrupt",
    S.LOG: "[←→] Filtro   [D] Details   [ESC] Voltar   [Ctrl+C] Interrupt",
    S.QC: "[D] Details   [L] Log   ░[C] Cancel   [Ctrl+C] Interrupt",
    S.COMPLETED: "[←→] Choose   [ENTER] Confirmar   [ESC] Sair",
    S.ERROR: "[↑↓] Rolar   [←→] Choose   [ENTER] Confirmar   [ESC] Sair",
    S.CANCELLED: "[←→] Choose   [ENTER] Confirmar   [ESC] Sair",
}
SCREEN_RENDERERS: dict[str, Callable[[S.UIState], RenderableType]] = {}


def basename(path: str | None) -> str:
    return os.path.basename(path) if path else "—"


def fmt_secs(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    seconds = max(0, int(seconds))
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def pipeline_label(cfg: dict) -> str:
    pipe = "Cineon Film" if cfg.get("cineon_pipeline") == "on" else "FFmpeg native"
    return f"{pipe} · {cfg.get('mode', '—')}"


def bar(pct: float, width: int = 48) -> Text:
    g = glyphs()
    filled = int(round(width * max(0.0, min(pct, 100.0)) / 100.0))
    out = Text()
    out.append(g["block_full"] * filled, style="bar.complete")
    out.append(g["block_empty"] * (width - filled), style="bar.back")
    return out


def kv_table(rows) -> Table:
    t = Table.grid(padding=(0, 2))
    t.add_column(style="label", no_wrap=True)
    t.add_column(style="value", overflow="ellipsis", no_wrap=True)
    for label, value in rows:
        t.add_row(label, value if isinstance(value, Text) else Text(str(value)))
    return t


def panel(body: RenderableType, title: str, height: int | None = None, style: str = "panel.border") -> Panel:
    return Panel(body, title=f"[panel.title]{title}[/]", title_align="left", box=PANEL_BOX,
                 border_style=style, height=height)


def hero(lines, height: int, style: str = "panel.border") -> Panel:
    return Panel(Group(*lines), box=HEAVY_BOX, border_style=style, height=height)


def _status(s: S.UIState) -> str:
    base = STATUS.get(s.screen, s.screen)
    if s.modal == "CANCEL":
        return "⚠ CANCEL?"
    if s.screen in (S.ENCODING, S.QC) and s.exit_code is None:
        spin = SPINNER[int(s.now * 10) % len(SPINNER)]
        track = S.active_pass(s)
        suffix = f" · PASS {track.index}/{track.total}" if s.screen == S.ENCODING and track else ""
        return f"{spin} {base}{suffix}"
    return base


def _rail_active(s: S.UIState) -> str:
    if s.screen == S.READY:
        return "READY"
    if s.screen in (S.COMPLETED,):
        return "DELIVERY"
    if s.screen == S.QC:
        return "QC"
    return "ENCODE"


def header(s: S.UIState) -> RenderableType:
    g = glyphs()
    top = Table.grid(expand=True)
    top.add_column(justify="left")
    top.add_column(justify="right")
    top.add_row(Text(f" REELS ENCODER  v{__version__}", style="title"), Text(_status(s) + " ", style="accent"))
    active = _rail_active(s)
    idx = RAIL.index(active)
    rail = Text(" ")
    for i, name in enumerate(RAIL):
        if i < 4 or i < idx or (s.screen == S.COMPLETED and name != "DELIVERY"):
            rail.append(f"{g['ok']} {name}   ", style="ok")
        elif name == active:
            rail.append(f"{g['tab_l']}{name}   ", style="tab.active")
        else:
            rail.append(f"  {name}   ", style="tab.inactive")
    return Group(top, rail, Rule(characters="─", style="muted"))


def footer(s: S.UIState) -> RenderableType:
    keys = FOOTER_KEYS.get(s.screen, "")
    if s.screen == S.ENCODING and S.cancel_blocked(s):
        keys = keys.replace("[C] Cancel", "░[C] Cancel")
    return Group(Rule(characters="─", style="muted"), Text(" " + keys, style="muted"))


def _ready(s: S.UIState) -> RenderableType:
    cfg = s.config
    g = glyphs()
    top = hero([
        Text(""),
        Text("   READY TO ENCODE", style="title"),
        Text(""),
        Text(f"   {basename(cfg.get('input'))}   {g['arrow']}   {basename(s.output_path)}"),
        Text(f"   {pipeline_label(cfg)}", style="muted"),
    ], height=7)
    two = cfg.get("mode") == "2pass"
    cineon = cfg.get("cineon_pipeline") == "on"
    key = panel(kv_table([
        ("SOURCE", basename(cfg.get("input"))),
        ("OUTPUT", basename(s.output_path)),
        ("PIPELINE", pipeline_label(cfg)),
        ("", ""),
        ("MODO", f"{cfg.get('mode')} · {'2 passes' if two else '1 passe'}"),
        ("FPS", f"{cfg.get('fps')} · {cfg.get('fit')} · scale {cfg.get('scale')}"),
        ("COR", f"LUT {cfg.get('lut')} · HDR {cfg.get('hdr')} · {cfg.get('tonemap')}"),
        ("ÁUDIO", f"loudnorm {cfg.get('loudnorm')} · alvo instagram"),
        ("ENHANCE", f"{cfg.get('enhance')} · AI {cfg.get('enhance_ai')} · MCTF {cfg.get('mctf')} · dither {cfg.get('dither')}"),
        ("PERF", f"{cfg.get('performance')} · threads {cfg.get('threads')}"),
    ]), "KEY SETTINGS", height=15)
    analyzing = [n for n, on in (("enhance", cfg.get("enhance") == "on"),
                                 ("MCTF máscara", cfg.get("mctf") == "on" and cfg.get("enhance_ai") == "on"),
                                 ("loudness da fonte", cfg.get("loudnorm") == "on")) if on]
    if cineon:
        encoding = f"FILM RENDER · {'PASS 1 / 2 + PASS 2 / 2' if two else 'passe único'}"
    else:
        encoding = "PASS 1 / 2 + PASS 2 / 2" if two else "passe único CRF"
    report_on = cfg.get("report", "on") == "on"
    plan = panel(kv_table([
        ("○ PREPARING", "hardware · validação"),
        ("○ PROBING", "duração · frames · fps · HDR"),
        ("○ ANALYZING", " · ".join(analyzing) if analyzing else "—"),
        ("○ ENCODING", encoding),
        ("○ QC", "EBU R128 · checks do master"),
        ("○ COMPLETED", "MASTER QC · certificado" if report_on else "MASTER QC · certificado desativado"),
    ]), "PIPELINE PLAN", height=15)
    mid = Table.grid(expand=True)
    mid.add_column(ratio=1)
    mid.add_column(ratio=1)
    mid.add_row(key, plan)
    base = os.path.splitext(basename(s.output_path))[0]
    cert = f"{base}.qc.html · .qc.json" if report_on else "certificado desativado (--report off)"
    meter = "FFplay ANTES / DEPOIS" if cfg.get("ebu_meter", "on") == "on" else "desligado"
    qc = panel(kv_table([
        ("10 checks no master", "Container · Video · Resolution · Bit Depth · Color · FPS"),
        ("", "Loudness · True Peak · Codec · Sample Rate"),
        ("certificado", cert),
        ("monitor EBU", meter),
    ]), "QC / DELIVERY", height=6)
    actions = Table.grid(expand=True)
    actions.add_column(justify="left")
    actions.add_column(justify="right")
    actions.add_row(Text("   [ ESC  Sair ]", style="muted"), Text(f"{g['tab_l']}{g['arrow']}   START ENCODE   ", style="tab.active"))
    return Group(top, mid, qc, actions)


SCREEN_RENDERERS[S.READY] = _ready


def _small(s: S.UIState) -> RenderableType:
    w, h = s.size
    return Panel(Text(f"terminal pequeno — amplie para 120×40 (atual {w}×{h})\n"
                      "o encode continua rodando", style="warn"), box=PANEL_BOX, border_style="warn")


def render(s: S.UIState) -> RenderableType:
    w, h = s.size
    if w < S.MIN_SIZE[0] or h < S.MIN_SIZE[1]:
        return _small(s)
    body_fn = SCREEN_RENDERERS.get(s.screen)
    body = body_fn(s) if body_fn else Text(s.screen)
    root = Layout()
    root.split_column(Layout(header(s), name="header", size=3), Layout(body, name="body", size=34),
                      Layout(footer(s), name="footer", size=3))
    return root
