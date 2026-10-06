from __future__ import annotations

import os
from typing import Callable

from rich.align import Align
from rich.console import Group, RenderableType
from rich.layout import Layout
from rich.markup import escape
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

import reporter as R
from ui import components as C
from ui.theme import HEAVY_BOX, PANEL_BOX, glyphs
from ui.tui import forms as F
from ui.tui import state as S
from ui.tui import widgets as W

try:
    from version import __version__
except Exception:
    __version__ = "2.1.0"

SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
RAIL = ("HOME", "SOURCE", "CONFIG", "PREVIEW", "READY", "ENCODE", "QC", "DELIVERY")
BATCH_RAIL = ("HOME", "SOURCE", "CONFIG", "PREVIEW", "READY", "QUEUE", "REPORT")
QUEUE_ROWS = 9
JOB_LABEL = {
    "aguardando": ("· QUEUED", "muted"), "ok": ("✓ COMPLETED", "ok"), "pulado": ("○ SKIPPED", "muted"),
    "falha": ("✗ FAILED", "err"), "interrompido": ("⚠ CANCELLED", "warn"),
}
REPORT_TITLE = {0: ("✓ FILA CONCLUÍDA", "ok"), 1: ("✗ FILA CONCLUÍDA COM FALHAS", "err"),
                130: ("⚠ FILA INTERROMPIDA", "warn")}
STATUS = {
    S.HOME: "● HOME", S.SOURCE: "● SOURCE", S.CONFIGURATION: "● CONFIG", S.ADVANCED: "● ADVANCED",
    S.PREVIEW: "● PREVIEW",
    S.READY: "● READY", S.ENCODING: "ENCODING", S.DETAILS: "DETAILS", S.LOG: "LOG", S.QC: "QC",
    S.COMPLETED: "✓ COMPLETED", S.ERROR: "✗ ERROR", S.CANCELLED: "⚠ CANCELLED",
    S.QUEUE: "QUEUE", S.REPORT: "● REPORT",
}
FOOTER_KEYS = {
    S.HOME: "[↑↓] Navegar   [1-5] Abrir   [ENTER] Abrir   [ESC] Sair",
    S.SOURCE: "[digite] Caminho   [←→] Cursor   [ENTER] Continuar   [ESC] Voltar   [Ctrl+C] Sair",
    S.CONFIGURATION: "[↑↓] Campo   [←→] Valor   [0-9] Digitar   [ENTER] Próximo   [ESC] Voltar   [Ctrl+C] Sair",
    S.ADVANCED: "[↑↓] Campo   [←→] Valor/Aba   [SPACE] On/Off   [ENTER] Próximo   [ESC] Voltar   [Ctrl+C] Sair",
    S.PREVIEW: "[←→] Escolher   [ENTER] Confirmar   [ESC] Voltar   [Ctrl+C] Sair",
    S.READY: "[←→] Choose   [ENTER] Start encode   [ESC] Sair",
    S.ENCODING: "[D] Details   [L] Log   [C] Cancel   [Ctrl+C] Interrupt",
    S.DETAILS: "[D] Voltar   [L] Log   [ESC] Voltar   [Ctrl+C] Interrupt",
    S.LOG: "[←→] Filtro   [D] Details   [ESC] Voltar   [Ctrl+C] Interrupt",
    S.QC: "[D] Details   [L] Log   ░[C] Cancel   [Ctrl+C] Interrupt",
    S.COMPLETED: "[←→] Choose   [ENTER] Confirmar   [ESC] Sair",
    S.ERROR: "[↑↓] Rolar   [←→] Choose   [ENTER] Confirmar   [ESC] Sair",
    S.CANCELLED: "[←→] Choose   [ENTER] Confirmar   [ESC] Sair",
    S.QUEUE: "[D] Details   [L] Log   [C] Cancelar fila   [Ctrl+C] Interrupt",
    S.REPORT: "[↑↓] Rolar   [ENTER] Sair   [ESC] Sair",
}
MODAL_KEYS = "[←→] Choose   [ENTER] Confirm   [ESC] Keep encoding   [Ctrl+C] Interrupt"
SOURCE_TIPO_KEYS = "[←→] Tipo   [↓] Caminho   [ENTER] Continuar   [ESC] Voltar   [Ctrl+C] Sair"
CONFIG_BATCH_KEYS = "[↑↓] Campo   [←→] On/Off   [digite] Pasta   [ENTER] Próximo   [ESC] Voltar   [Ctrl+C] Sair"
SCREEN_RENDERERS: dict[str, Callable[[S.UIState], RenderableType]] = {}


def basename(path: str | None) -> str:
    return os.path.basename(path) if path else "—"


def fmt_secs(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    seconds = max(0, int(seconds))
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def elide(text, width: int) -> str:
    text = str(text) if text else "—"
    return text if len(text) <= width else "…" + text[-(width - 1):]


def folder_name(path) -> str:
    raw = str(path or "")
    return os.path.basename(raw.rstrip("/\\")) or raw or "—"


def videos(n: int | None) -> str:
    if n is None:
        return "— vídeos"
    return f"{n} vídeo{'' if n == 1 else 's'}"


def output_dir_text(cfg: dict) -> str:
    out = cfg.get("output_dir")
    return elide(out, 50) if out else "mesma pasta"


def source_text(cfg: dict, count: int | None) -> str:
    if cfg.get("batch"):
        return f"pasta {elide(folder_name(cfg['batch']), 40)} · {videos(count)}"
    return basename(cfg.get("input"))


def cineon_crf(cfg: dict) -> bool:
    return cfg.get("cineon_pipeline") == "on" and cfg.get("mode") != "2pass"


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
    if s.cancel_phase is not None and s.screen not in S.FINAL_SCREENS and s.screen != S.READY:
        return "⚠ CANCELANDO"
    if s.screen in (S.ENCODING, S.QC, S.QUEUE) and s.exit_code is None:
        spin = SPINNER[int(s.now * 10) % len(SPINNER)]
        track = S.active_pass(s)
        if s.screen == S.QUEUE:
            suffix = f" · JOB {s.active_job + 1}/{len(s.queue)}" if s.active_job is not None else ""
        else:
            suffix = f" · PASS {track.index}/{track.total}" if s.screen == S.ENCODING and track else ""
        return f"{spin} {base}{suffix}"
    return base


def _rail_active(s: S.UIState) -> str:
    if s.screen == S.REPORT:
        return "REPORT"
    if s.screen == S.QUEUE:
        return "QUEUE"
    if s.screen == S.HOME:
        return "HOME"
    if s.screen == S.SOURCE:
        return "SOURCE"
    if s.screen in (S.CONFIGURATION, S.ADVANCED):
        return "CONFIG"
    if s.screen == S.PREVIEW:
        return "PREVIEW"
    if s.screen == S.READY:
        return "READY"
    if s.screen in (S.COMPLETED,):
        return "DELIVERY"
    if s.screen == S.QC:
        return "QC"
    return "ENCODE"


def batch_view(s: S.UIState) -> bool:
    if s.screen in S.CONFIG_SCREENS:
        return s.screen != S.HOME and bool(s.preset) and F.is_folder(S.draft(s))
    return s.is_batch


def header(s: S.UIState) -> RenderableType:
    g = glyphs()
    top = Table.grid(expand=True)
    top.add_column(justify="left")
    top.add_column(justify="right")
    top.add_row(Text(f" REELS ENCODER  v{__version__}", style="title"), Text(_status(s) + " ", style="accent"))
    names = BATCH_RAIL if batch_view(s) else RAIL
    active = _rail_active(s)
    if active not in names:
        active = "QUEUE"
    idx = names.index(active)
    rail = Text(" ")
    for i, name in enumerate(names):
        if i < idx or (s.screen == S.COMPLETED and name != "DELIVERY"):
            rail.append(f"{g['ok']} {name}   ", style="ok")
        elif name == active:
            rail.append(f"{g['tab_l']}{name}   ", style="tab.active")
        else:
            rail.append(f"  {name}   ", style="tab.inactive")
    return Group(top, rail, Rule(characters="─", style="muted"))


def footer(s: S.UIState) -> RenderableType:
    keys = FOOTER_KEYS.get(s.screen, "")
    if s.modal == "CANCEL":
        keys = MODAL_KEYS
    elif s.screen in (S.QC, S.DETAILS) and s.back in S.FINAL_SCREENS:
        keys = "[ESC] Voltar"
    elif s.screen == S.LOG and s.back in S.FINAL_SCREENS:
        keys = "[←→] Filtro   [ESC] Voltar"
    elif s.screen in (S.ENCODING, S.QUEUE) and (S.cancel_blocked(s) or s.cancel_phase is not None):
        keys = keys.replace("[C] Cancel", "░[C] Cancel")
    elif s.screen == S.SOURCE and s.preset == 5:
        keys = SOURCE_TIPO_KEYS if s.tab_focus else "[↑] Tipo   " + keys
    elif s.screen == S.CONFIGURATION and s.preset == 3:
        keys = CONFIG_BATCH_KEYS
    elif s.screen == S.READY and s.preset:
        keys = keys.replace("[ESC] Sair", "[ESC] Voltar")
    return Group(Rule(characters="─", style="muted"), Text(" " + keys, style="muted"))


def _ready(s: S.UIState) -> RenderableType:
    cfg = s.config
    g = glyphs()
    batch = bool(cfg.get("batch"))
    src = source_text(cfg, s.source_count)
    out = f"saída: {output_dir_text(cfg)}" if batch else basename(s.output_path)
    if batch:
        banner_src = f"pasta {elide(folder_name(cfg['batch']), 30)} · {videos(s.source_count)}"
        banner_out = "saída: " + (elide(cfg["output_dir"], 45) if cfg.get("output_dir") else "mesma pasta")
    else:
        banner_src, banner_out = src, out
    top = hero([
        Text(""),
        Text("   READY TO ENCODE", style="title"),
        Text(""),
        Text(f"   {banner_src}   {g['arrow']}   {banner_out}"),
        Text(f"   {pipeline_label(cfg)}", style="muted"),
    ], height=7)
    two = cfg.get("mode") == "2pass"
    cineon = cfg.get("cineon_pipeline") == "on"
    key = panel(kv_table([
        ("SOURCE", src),
        ("OUTPUT", out),
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
    if batch:
        cert = "<vídeo>.qc.html · .qc.json por vídeo" if report_on else "certificado desativado (--report off)"
        meter = "suprimido em batch (motor)"
    else:
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
    esc = "Voltar" if s.preset else "Sair"
    start = "START QUEUE" if batch else "START ENCODE"
    actions.add_row(Text(f"   [ ESC  {esc} ]", style="muted"),
                    Text(f"{g['tab_l']}{g['arrow']}   {start}   ", style="tab.active"))
    parts = [top, mid, qc]
    if s.ready_error:
        parts.append(Text(f"   {s.ready_error}", style="err"))
    parts.append(actions)
    return Group(*parts)


SCREEN_RENDERERS[S.READY] = _ready


STAGE_ORDER = (R.PREPARING, R.PROBING, R.ANALYZING)
KIND_STYLE = {"SYSTEM": "info", "INFO": "value", "WARNING": "warn", "FFMPEG": "muted"}


def pass_label(track: S.PassTrack, cfg: dict) -> str:
    if track.label == "Pass 1":
        return "ANÁLISE"
    if track.label == "Pass 2":
        return "ENCODE FINAL"
    return "FILM RENDER" if cfg.get("cineon_pipeline") == "on" else "ENCODE"


def stage_rail(s: S.UIState) -> Text:
    g = glyphs()
    total = 2 if s.config.get("mode") == "2pass" else 1
    names = list(STAGE_ORDER) + [f"PASS {i}" for i in range(1, total + 1)] + [R.QC, "COMPLETED"]
    current = f"PASS {s.substep}" if s.stage == R.PASS else s.stage
    finished = s.exit_code == 0 and s.screen in (S.COMPLETED,)
    cur = names.index(current) if current in names else (len(names) - 1 if s.stage == R.DONE else -1)
    out = Text(" ")
    for i, name in enumerate(names):
        label = "FILM RENDER" if name == "PASS 1" and cineon_crf(s.config) else name
        if name == current and not finished:
            out.append(f"{g['tab_l']}{g['bullet']} {label}    ", style="tab.active")
        elif finished or i < cur:
            out.append(f"{g['ok']} {label}    ", style="ok")
        else:
            out.append(f"○ {label}    ", style="muted")
    return out


def pass_lines(s: S.UIState) -> list:
    if not s.passes:
        return [Text(" aguardando o primeiro passe…", style="muted")]
    lines = []
    for t in s.passes:
        line = Text(f" PASS {t.index} / {t.total}   {pass_label(t, s.config):<14}")
        line.append_text(bar(t.pct))
        tail = f"   {t.pct:6.1f}%   "
        tail += f"{glyphs()['ok']} {fmt_secs(t.seconds)}" if t.done else f"ETA {t.eta or '—'}"
        line.append(tail, style="ok" if t.done else "value")
        lines.append(line)
    return lines


def log_rows(rows, limit: int) -> Table:
    t = Table.grid(padding=(0, 2))
    t.add_column(no_wrap=True, width=8)
    t.add_column(overflow="ellipsis", no_wrap=True, max_width=104)
    for r in rows[-limit:]:
        t.add_row(Text(r.kind, style=KIND_STYLE.get(r.kind, "value")), Text(r.text))
    return t


def _log_panel(s: S.UIState, rows: int = 9, height: int = 11) -> Panel:
    title = "LOG" + (f" [warn]⚠ {s.warnings}[/]" if s.warnings else "")
    return panel(log_rows(s.log, rows), title, height=height)


def _src_dims(s: S.UIState):
    return (s.probe.width, s.probe.height) if s.probe else None


def _job_strip(s: S.UIState) -> RenderableType:
    g = glyphs()
    line = Text(" ")
    line.append(basename(s.config.get("input")), style="value")
    line.append(f"  {g['arrow']}  ", style="accent")
    line.append(basename(s.output_path), style="info")
    dims = _src_dims(s)
    if dims:
        line.append(f"   ·  {C.classify_aspect(*dims)} {dims[0]}×{dims[1]}", style="info.dim")
    return line


def _progress_header(s: S.UIState) -> Panel:
    track = S.active_pass(s)
    title = f"ENCODING · PASS {track.index} / {track.total}" if track else "ENCODING"
    if cineon_crf(s.config):
        title = "ENCODING · FILM LOOK (CINEON)"
    warn = [Text(" ⚠ CANCELAMENTO SOLICITADO · encerrando FFmpeg…", style="warn")] if s.cancel_phase else []
    return panel(Group(stage_rail(s), Text(""), *warn, *pass_lines(s)), title, height=7)


def _timeline(s: S.UIState) -> Panel:
    p = s.progress
    track = S.active_pass(s)
    job = (s.now - s.job_started) if s.job_started is not None else None
    return panel(kv_table([
        ("pass", f"{track.index} / {track.total} · {pass_label(track, s.config)}" if track else "—"),
        ("frame", f"{p.frame} / {p.total}" if p else "—"),
        ("fps", f"{p.fps:.1f}" if p else "—"),
        ("speed", f"{p.speed:.2f}x" if p else "—"),
        ("eta", p.eta if p else "—"),
        ("elapsed", fmt_secs(p.elapsed) if p else "—"),
        ("job elapsed", fmt_secs(job)),
    ]), "TIMELINE", height=13)


def _gauge(pct):
    return C.gauge_bar(pct) if pct is not None else Text("—")


def _performance(s: S.UIState) -> Panel:
    hw = s.hardware or {}
    threads = s.config.get("threads")
    return panel(kv_table([
        ("cpu", _gauge(s.cpu)),
        ("ram", _gauge(s.ram)),
        ("ram used", f"{s.ram_used_gb:.1f} GB" if s.ram_used_gb is not None else "—"),
        ("", ""),
        ("threads", f"{threads} (auto)" if threads in (0, None) else str(threads)),
        ("performance", s.config.get("performance", "—")),
        ("tier", hw.get("tier", "—")),
    ]), "PERFORMANCE", height=13)


def _middle(s: S.UIState) -> RenderableType:
    row = Table.grid(expand=True)
    row.add_column(width=30)
    row.add_column(ratio=1)
    row.add_column(ratio=1)
    viewer = C.viewer_frame(fit=s.config.get("fit", "contain"), src_dims=_src_dims(s), title="PROGRAM")
    row.add_row(Panel(viewer, height=13, box=PANEL_BOX, border_style="panel.border"), _timeline(s), _performance(s))
    return row


def cancel_modal(s: S.UIState) -> RenderableType:
    g = glyphs()
    track = S.active_pass(s)
    where = f"{s.stage or '—'}{' · ' + s.substep if s.substep else ''}"
    pct = f" · {track.pct:.0f}%" if track else ""
    noun = "FILA" if s.is_batch else "ENCODE"
    buttons = Text("   ")
    for i, label in enumerate((f"CONTINUAR {noun}", f"CANCELAR {noun}")):
        focused = s.modal_focus == i
        buttons.append(f"{g['arrow'] if focused else ' '}[ {label} ]   ", style="tab.active" if focused else "muted")
    lines = [
        Text(""),
        Text(f"  etapa ativa: {where}{pct}"),
        Text("  usa o caminho de interrupção existente (o mesmo do Ctrl+C)", style="muted"),
        Text(f"  parcial: {basename(s.output_path)}", style="muted"),
    ]
    if s.is_batch:
        lines.append(Text("  cancela a fila inteira; os jobs restantes não rodam", style="muted"))
    body = Group(*lines, Text(""), buttons)
    box = Panel(body, title=f"[warn]CANCELAR {noun}?[/]", box=PANEL_BOX, border_style="warn", width=64, height=12)
    return Align.center(box, vertical="middle", height=13)


def dashboard(s: S.UIState, middle: RenderableType) -> RenderableType:
    return Group(_job_strip(s), _progress_header(s), Text(""), middle, Text(""), _log_panel(s))


def _encoding(s: S.UIState) -> RenderableType:
    return dashboard(s, cancel_modal(s) if s.modal == "CANCEL" else _middle(s))


def _prov(value, tag: str) -> Text:
    out = Text(str(value) if value not in (None, "") else "—")
    out.append(f"  {tag}", style="muted")
    return out


def _mini(s: S.UIState) -> Text:
    track = S.active_pass(s)
    return Text(f" {s.stage or '—'}{' · ' + s.substep if s.substep else ''}"
                f"{f'   PASS {track.index}/{track.total} {track.pct:.1f}%' if track else ''}", style="muted")


def _details(s: S.UIState) -> RenderableType:
    p, hw, ep, pr, cfg = s.probe, s.hardware or {}, s.encode_params, s.progress, s.config
    track = S.active_pass(s)
    src = panel(kv_table([
        ("resolução", _prov(f"{p.width} × {p.height}" if p else None, "DET")),
        ("duração", _prov(fmt_secs(p.duration) if p else None, "DET")),
        ("frames", _prov(p.total_frames if p else None, "DET")),
        ("fps", _prov(p.fps if p else None, "DET")),
        ("HDR", _prov(("sim" if p.is_hdr else "não") if p else None, "DET")),
    ]), "SOURCE", height=15)
    hwp = panel(kv_table([
        ("cpu", _prov(hw.get("cpu_name"), "DET")),
        ("cores/threads", _prov(f"{hw['cpu_cores']} / {hw['cpu_threads']}" if "cpu_cores" in hw and "cpu_threads" in hw else None, "DET")),
        ("ram", _prov(f"{hw['ram_total_gb']:.1f} GB" if "ram_total_gb" in hw else None, "DET")),
        ("tier", _prov(hw.get("tier"), "DER")),
        ("preset rec.", _prov(hw.get("recommended_preset"), "DER")),
    ]), "HARDWARE", height=15)
    enc = panel(kv_table([
        ("modo", _prov(cfg.get("mode"), "CFG")),
        ("pass", _prov(f"{track.index} / {track.total}" if track else None, "LIVE")),
        ("VBV", _prov(ep.vbv_key if ep else None, "CALC")),
        ("target", _prov(ep.target if ep else None, "CALC")),
        ("maxrate", _prov(ep.maxrate if ep else None, "CALC")),
        ("bufsize", _prov(ep.bufsize if ep else None, "CALC")),
        ("vbv_init", _prov(ep.vbv_init if ep else None, "CALC")),
        ("x264 preset", _prov(ep.x264_preset if ep else None, "CALC")),
    ]), "ENCODING", height=15)
    con = panel(kv_table([
        ("pipeline", _prov(pipeline_label(cfg), "CFG")),
        ("LUT", _prov(cfg.get("lut"), "CFG")),
        ("loudnorm", _prov(cfg.get("loudnorm"), "CFG")),
        ("enhance", _prov(cfg.get("enhance"), "CFG")),
        ("AI", _prov(cfg.get("enhance_ai"), "CFG")),
        ("MCTF", _prov(cfg.get("mctf"), "CFG")),
        ("dither", _prov(cfg.get("dither"), "CFG")),
    ]), "CONFIG", height=15)
    out = panel(kv_table([
        ("output", _prov(basename(s.output_path), "CFG")),
        ("report", _prov(cfg.get("report"), "CFG")),
        ("ebu meter", _prov(cfg.get("ebu_meter"), "CFG")),
    ]), "OUTPUT", height=15)
    prog = panel(kv_table([
        ("frame", _prov(f"{pr.frame} / {pr.total}" if pr else None, "LIVE")),
        ("fps", _prov(f"{pr.fps:.1f}" if pr else None, "LIVE")),
        ("speed", _prov(f"{pr.speed:.2f}x" if pr else None, "LIVE")),
        ("eta", _prov(pr.eta if pr else None, "LIVE")),
        ("elapsed", _prov(fmt_secs(pr.elapsed) if pr else None, "LIVE")),
    ]), "PROGRESS", height=15)
    grid = Table.grid(expand=True)
    for _ in range(3):
        grid.add_column(ratio=1)
    grid.add_row(src, hwp, enc)
    grid.add_row(con, out, prog)
    return Group(_mini(s), grid)


def _log_screen(s: S.UIState) -> RenderableType:
    tabs = Text(" ")
    for i, name in enumerate(S.LOG_FILTERS):
        tabs.append(f" {name} ", style="tab.active" if i == s.log_filter else "tab.inactive")
        tabs.append("  ")
    rows = S.filtered_log(s)
    status = Text(f" {len(rows)} linhas · filtro {S.LOG_FILTERS[s.log_filter]}", style="muted")
    return Group(_mini(s), tabs, Rule(style="muted"), log_rows(rows, 28),
                 Rule(style="muted"), status)


SCREEN_RENDERERS[S.ENCODING] = _encoding
SCREEN_RENDERERS[S.DETAILS] = _details
SCREEN_RENDERERS[S.LOG] = _log_screen


def mmss(seconds: float) -> str:
    total = max(0, int(round(seconds)))
    return f"{total // 60:02d}:{total % 60:02d}"


def job_status(s: S.UIState, job: S.Job) -> Text:
    if job.status == "processando":
        return Text(f"{SPINNER[int(s.now * 10) % len(SPINNER)]} ENCODING", style="accent")
    label, style = JOB_LABEL.get(job.status, (job.status, "value"))
    return Text(label, style=style)


def job_time(job: S.Job) -> str:
    if job.status == "processando":
        return "…"
    if job.started is not None and job.finished is not None:
        return mmss(job.finished - job.started)
    return "—"


def queue_start(total: int, active: int | None, rows: int, scroll: int | None = None) -> int:
    if total <= rows:
        return 0
    if scroll is not None:
        return min(max(0, scroll), total - rows)
    if active is None:
        return 0
    return max(0, min(active - rows // 2, total - rows))


def queue_table(s: S.UIState, start: int, rows: int) -> Table:
    t = Table(box=None, expand=True, padding=(0, 1), header_style="label")
    t.add_column("JOB", width=4, justify="right", no_wrap=True)
    t.add_column("ARQUIVO", width=40, no_wrap=True, overflow="ellipsis")
    t.add_column("STATUS", width=13, no_wrap=True)
    t.add_column("ETA/DURAÇÃO", width=11, no_wrap=True)
    t.add_column("RESULTADO", ratio=1, no_wrap=True, overflow="ellipsis")
    for i, job in enumerate(s.queue[start:start + rows], start=start):
        style = "err" if job.status == "falha" else "muted"
        t.add_row(Text(str(i + 1)), Text(elide(os.path.basename(job.input), 40)), job_status(s, job),
                  Text(job_time(job)), Text(job.reason or "—", style=style))
    return t


def _queue_strip(s: S.UIState) -> Text:
    g = glyphs()
    cfg = s.config
    out = cfg.get("output_dir")
    line = Text(" BATCH ", style="accent")
    line.append(elide(cfg.get("batch"), 36), style="value")
    line.append(f" · {_count(len(s.queue), 'arquivo', 'arquivos')} ", style="muted")
    line.append(f"{g['arrow']} saída: {elide(out, 40) if out else 'mesma pasta'}", style="info")
    return line


def _queue(s: S.UIState) -> RenderableType:
    counts = S.queue_counts(s.queue)
    eta = S.queue_eta(s)
    title = (f"RENDER QUEUE · Job {counts['total'] - counts['aguardando']} de {counts['total']}"
             f" · ETA {mmss(eta) if eta is not None else '—'}")
    start = queue_start(len(s.queue), s.active_job, QUEUE_ROWS)
    table = panel(queue_table(s, start, QUEUE_ROWS), title, height=QUEUE_ROWS + 3)
    lower = [cancel_modal(s)] if s.modal == "CANCEL" else [_progress_header(s), _log_panel(s, 12, 14)]
    return Group(_queue_strip(s), table, *lower)


def _count(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def queue_summary(s: S.UIState, code: int) -> Text:
    c = S.queue_counts(s.queue)
    body = f"{c['ok']} ok · {_count(c['pulado'], 'pulado', 'pulados')} · {_count(c['falha'], 'falha', 'falhas')}"
    if code == 130:
        tail = _count(c["interrompido"], "interrompido", "interrompidos")
        return Text(f"⚠ fila interrompida: {body} · {tail} (código 130)", style="warn")
    if code == 0:
        return Text(f"✓ fila: {body} (código 0)", style="ok")
    return Text(f"✗ fila: {body} (código {code})", style="err")


def _report(s: S.UIState) -> RenderableType:
    g = glyphs()
    c = S.queue_counts(s.queue)
    code = s.exit_code
    title, style = REPORT_TITLE.get(code, (f"✗ FILA ENCERRADA (código {code})", "err"))
    total = s.queue_finished - s.queue_started \
        if s.queue_finished is not None and s.queue_started is not None else None
    top = hero([
        Text(f"   {title}", style=style),
        Text(f"   Sucesso {c['ok']}/{c['total']}   ·   Pulados {c['pulado']}   ·   Falhas {c['falha']}"
             f"   ·   Interrompidos {c['interrompido']}"),
        Text(f"   Tempo total {fmt_secs(total)}   ·   Código de saída {code if code is not None else '—'}",
             style="muted"),
        Text(""),
    ], height=6)
    start = queue_start(len(s.queue), None, S.REPORT_ROWS, s.queue_scroll)
    table = panel(queue_table(s, start, S.REPORT_ROWS), f"FILA · {_count(len(s.queue), 'arquivo', 'arquivos')}", height=S.REPORT_ROWS + 3)
    parts = [top, table]
    if s.removal_failed:
        parts.append(Text(f"   ⚠ NÃO foi possível remover {basename(s.output_path)} — apague à mão antes de "
                          "rodar a fila de novo", style="warn"))
    parts.append(Text(f"   {g['arrow']}[ SAIR ]", style="tab.active"))
    return Group(*parts)


SCREEN_RENDERERS[S.QUEUE] = _queue
SCREEN_RENDERERS[S.REPORT] = _report


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


def stderr_lines(err, log) -> list:
    raw = getattr(err, "stderr_tail", None) if err is not None else None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", "replace")
    if raw:
        return [ln for ln in raw.replace("\r", "\n").split("\n") if ln.strip()]
    return [r.text for r in log if r.kind == "FFMPEG"][-40:]


def action_row(s: S.UIState) -> Text:
    g = glyphs()
    out = Text("   ")
    for i, name in enumerate(S.final_actions(s)):
        focused = i == s.action_focus
        out.append(f"{g['arrow'] if focused else ' '}[ {name} ]   ", style="tab.active" if focused else "muted")
    return out


def _fmt(v, unit=""):
    return f"{v:.1f}{unit}" if isinstance(v, (int, float)) else "—"


def _ebu_table(qc) -> Table:
    audio = (qc or {}).get("audio", {})
    before, after = audio.get("before") or {}, audio.get("after") or {}
    targets = (qc or {}).get("targets") or {}
    t = Table(box=None, expand=True, padding=(0, 2))
    for col in ("", "ANTES", "DEPOIS", "Alvo"):
        t.add_column(col, style="label" if not col else "value")
    for key, unit in (("I", " LUFS"), ("TP", " dBTP"), ("LRA", " LU")):
        t.add_row(key, _fmt(before.get(key), unit), _fmt(after.get(key), unit), _fmt(targets.get(key), unit))
    return t


def _seal_checks(qc: dict) -> list:
    return [(c.get("label", ""), c.get("value", ""), c.get("passed")) for c in qc.get("checks", [])]


def _seal(s: S.UIState) -> RenderableType:
    qc = s.qc or {}
    if not S.seal_revealed(s):
        chips = [C.quality_chip(c.get("label", ""), c.get("passed")) for c in qc.get("checks", [])]
        return Panel(Group(Text(" verificando…", style="muted"), *chips), title="[panel.title]MASTER QC[/]",
                     title_align="left", box=HEAVY_BOX, border_style="panel.border", height=14)
    return C.delivery_seal(_seal_checks(qc), ready=qc.get("summary", {}).get("ready"))


def _delivery(s: S.UIState) -> Panel:
    cfg = s.config
    base = os.path.splitext(basename(s.output_path))[0]
    cert = f"{base}.qc.html · .qc.json" if cfg.get("report", "on") == "on" else "certificado desativado (--report off)"
    meter = "FFplay ANTES / DEPOIS" if cfg.get("ebu_meter", "on") == "on" else "desligado"
    return panel(kv_table([("certificado", cert), ("monitor EBU", meter)]), "DELIVERY", height=5)


def _qc(s: S.UIState) -> RenderableType:
    spin = SPINNER[int(s.now * 10) % len(SPINNER)]
    sub = Text(f" {spin} medindo loudness · checks do master" if s.qc is None else " checks concluídos",
               style="muted")
    return Group(_job_strip(s), panel(Group(stage_rail(s), sub), "QC", height=5),
                 panel(_ebu_table(s.qc), "EBU R128 — AUDITORIA PÓS-ENCODE", height=9),
                 _seal(s),
                 _delivery(s))


def _verdict(qc) -> Text:
    if qc is None:
        return Text("   QC indisponível", style="muted")
    ready = qc.get("summary", {}).get("ready")
    if ready:
        return Text("   ★ DELIVERY READY ★", style="seal")
    return Text("   ⚠ REVISAR ENTREGA ⚠", style="warn")


def _completed(s: S.UIState) -> RenderableType:
    g = glyphs()
    qc = s.qc or {}
    out_info, enc, video = qc.get("output", {}), qc.get("encode", {}), qc.get("video", {})
    summary, after = qc.get("summary", {}), (qc.get("audio", {}) or {}).get("after") or {}
    top = hero([Text(""), Text(f"   {g['ok']} ENCODE COMPLETE", style="ok"), Text(""), _verdict(s.qc),
                Text(f"   {basename(s.output_path)}", style="muted")], height=8)
    res = f"{video.get('width')} × {video.get('height')}" if video.get("width") else "—"
    left = panel(kv_table([
        ("arquivo", basename(s.output_path)),
        ("tamanho", out_info.get("size_human") or "—"),
        ("duração", enc.get("duration_human") or fmt_secs(s.done.seconds if s.done else None)),
        ("vídeo", f"{video.get('codec') or '—'} · {res} · {_fmt(video.get('fps'))} fps"),
    ]), "OUTPUT", height=14)
    right = panel(kv_table([
        ("passed", summary.get("passed", "—")),
        ("warnings", summary.get("warnings", "—")),
        ("failed", summary.get("failed", "—")),
        ("I depois", _fmt(after.get("I"), " LUFS")),
        ("TP depois", _fmt(after.get("TP"), " dBTP")),
        ("LRA depois", _fmt(after.get("LRA"), " LU")),
    ]), "MASTER QC · RESUMO", height=14)
    mid = Table.grid(expand=True)
    mid.add_column(ratio=1)
    mid.add_column(ratio=1)
    mid.add_row(left, right)
    return Group(top, mid, _delivery(s), action_row(s))


def error_message(s: S.UIState) -> str:
    err = s.error
    if err is None:
        return f"Encode terminou com erro (código {s.exit_code})"
    if err.returncode is not None:
        return f"{err.kind}: ffmpeg saiu com código {err.returncode}"
    first = next(iter((err.message or "").splitlines()), "")
    return f"{err.kind}: {first[:200] + '…' if len(first) > 200 else first}"


def _error(s: S.UIState) -> RenderableType:
    err = s.error
    card = C.error_card(error_message(s))
    card.height, card.padding = 5, (0, 2)
    lines = stderr_lines(err, s.log)
    start = min(s.error_scroll, max(0, len(lines) - 17))
    body = Group(*[Text(ln, overflow="ellipsis", no_wrap=True) for ln in lines[start:start + 17]]) if lines \
        else Text("—", style="muted")
    p = s.progress
    state = panel(kv_table([
        ("etapa", f"{s.stage or '—'}{' · ' + s.substep if s.substep else ''}"),
        ("último frame", f"{p.frame} / {p.total}" if p else "—"),
        ("output", f"o output parcial pode existir: {basename(s.output_path)}"),
    ]), "ESTADO", height=5)
    return Group(card, panel(body, "FFMPEG STDERR", height=19), state, action_row(s))


def partial_wording(s: S.UIState) -> str:
    name = basename(s.output_path)
    if s.partial_removed is True:
        return f"output parcial removido: {name}"
    if s.removal_failed:
        return f"NÃO foi possível remover {name} — apague à mão antes de rodar de novo"
    if s.output_preexisted:
        return f"o arquivo existente foi mantido: {name} (pode ter sido sobrescrito em parte)"
    return "nenhum output parcial"


def _cancelled(s: S.UIState) -> RenderableType:
    partial = partial_wording(s)
    card = Panel(Group(Text(""), Text("   ⚠ Encode interrompido pelo usuário", style="warn"), Text(""),
                       Text(f"   {partial}")), box=HEAVY_BOX, border_style="warn", height=8)
    return Group(card, _log_panel(s), action_row(s))


SCREEN_RENDERERS[S.QC] = _qc
SCREEN_RENDERERS[S.COMPLETED] = _completed
SCREEN_RENDERERS[S.ERROR] = _error
SCREEN_RENDERERS[S.CANCELLED] = _cancelled


def path_field(buf: W.TextBuf, width: int) -> Text:
    text, cur = buf.text, buf.cursor
    start = max(0, min(cur - width // 2, len(text) + 1 - width))
    view = text[start:start + width]
    pos = cur - start
    out = Text()
    out.append(view[:pos], style="value")
    out.append(view[pos:pos + 1] or " ", style="reverse")
    out.append(view[pos + 1:], style="value")
    return out


def _home(s: S.UIState) -> RenderableType:
    g = glyphs()
    top = hero([Text(""), Text("   REELS ENCODER", style="title"),
                Text("   Premiere Workspace · escolha um fluxo", style="muted")], height=7)
    menu = Text()
    for i, label in enumerate(F.PRESET_LABELS):
        n = i + 1
        enabled = n in F.ENABLED_PRESETS
        focused = i == s.home_focus
        prefix = f"{g['tab_l']}{g['arrow']} " if focused else "   "
        line = f"{prefix}{n}  {label}" + ("" if enabled else "   — chega no P3D")
        menu.append(line + "\n\n", style="tab.active" if focused else ("value" if enabled else "muted"))
    help_txt = Text(F.PRESET_HELP[s.home_focus + 1], style="value")
    mid = Table.grid(expand=True)
    mid.add_column(ratio=1)
    mid.add_column(ratio=1)
    mid.add_row(panel(menu, "FLUXOS", height=17), panel(help_txt, "O QUE FAZ", height=17))
    half = (len(s.system) + 1) // 2
    sysrow = Table.grid(expand=True)
    sysrow.add_column(ratio=1)
    sysrow.add_column(ratio=1)
    sysrow.add_row(kv_table(s.system[:half]), kv_table(s.system[half:]))
    return Group(top, mid, panel(sysrow, "SYSTEM", height=5))


_SOURCE_STATUS = {
    "VALID": ("✓ arquivo encontrado", "ok"),
    "NOT_FOUND": ("✗ arquivo não encontrado", "err"),
    "INVALID": ("⚠ informe um arquivo de vídeo", "warn"),
    "CHECKING": ("verificando…", "muted"),
}


_FOLDER_STATUS = {
    "VALID": ("✓ pasta encontrada · {videos}", "ok"),
    "EMPTY": ("⚠ nenhum vídeo encontrado", "warn"),
    "NOT_FOUND": ("✗ pasta não encontrada", "err"),
    "INVALID": ("⚠ informe uma pasta de vídeos", "warn"),
    "CHECKING": ("verificando…", "muted"),
}


def _program(s: S.UIState, d: dict, folder: bool) -> RenderableType:
    fit = d.get("fit", "contain")
    if folder:
        return Group(Text(f" pasta · {videos(s.source_count)}", style="muted"),
                     C.viewer_frame(fit=fit, src_dims=None, title="PROGRAM"))
    return C.viewer_frame(fit=fit, src_dims=s.source_dims, title="PROGRAM")


def _tipo_row(s: S.UIState, folder: bool) -> Text:
    g = glyphs()
    style = "tab.active" if s.tab_focus else "value"
    out = Text(f"{g['tab_l']}{g['arrow']} " if s.tab_focus else "", style=style)
    out.append(f"{'○' if folder else '●'} Arquivo único   {'●' if folder else '○'} Pasta (batch)", style=style)
    return out


def _source(s: S.UIState) -> RenderableType:
    dd = S.draft(s)
    folder = F.is_folder(dd)
    path = W.clean_path(s.source.text) or None
    d = {**dd, ("batch" if folder else "input"): path}
    rows = []
    if s.preset == 5:
        rows.append(("TIPO", _tipo_row(s, folder)))
    if folder:
        msg, style = _FOLDER_STATUS.get(s.source_status, ("—", "muted"))
        rows += [
            ("PASTA", path_field(s.source, 60)),
            ("STATUS", Text(msg.format(videos=videos(s.source_count)), style=style)),
            ("VÍDEOS", videos(s.source_count) if s.source_count is not None else "—"),
            ("SAÍDA", output_dir_text(F.to_config(d))),
        ]
    else:
        msg, style = _SOURCE_STATUS.get(s.source_status, ("—", "muted"))
        rows += [
            ("ARQUIVO", path_field(s.source, 60)),
            ("STATUS", Text(msg, style=style)),
            ("DIMENSÕES", f"{s.source_dims[0]} × {s.source_dims[1]}" if s.source_dims else "—"),
            ("SAÍDA", F.output_name(d)),
        ]
    left = panel(kv_table(rows), "SOURCE", height=26)
    right = Panel(_program(s, d, folder), height=26, box=PANEL_BOX, border_style="panel.border")
    mid = Table.grid(expand=True)
    mid.add_column(ratio=76)
    mid.add_column(ratio=40)
    mid.add_row(left, right)
    nxt = "ENTER → ADVANCED" if s.preset == 5 else "ENTER → CONFIGURATION"
    return Group(mid, panel(Text(f" {nxt}", style="accent"), "PRÓXIMO", height=4))


SCREEN_RENDERERS[S.HOME] = _home
SCREEN_RENDERERS[S.SOURCE] = _source


def _value_text(s: S.UIState, field, d: dict, focused: bool) -> Text:
    if field is F.CONTINUE:
        return Text("[ CONTINUAR ▸ ]", style="tab.active" if focused else "accent")
    if focused and s.edit is not None and field.kind in ("number", "path"):
        return path_field(s.edit, 20)
    v = d.get(field.name)
    if field.kind == "choice":
        return Text(f"◂ {v} ▸")
    if field.kind == "toggle":
        return Text(f"[{v}]", style="ok" if v == "on" else "muted")
    if field.kind == "number":
        return Text(W._fmt(v))
    if field.kind == "path":
        return Text(elide(v, 20) if v else "—", style="value" if v else "muted")
    return Text(str(v))


def field_rows(s: S.UIState) -> Table:
    g = glyphs()
    d = S.draft(s)
    items = S.form_items(s)
    cur = min(S.focus_of(s, S.focus_key(s)), len(items) - 1)
    in_fields = not (s.screen == S.ADVANCED and s.tab_focus)
    t = Table.grid(padding=(0, 1))
    t.add_column(width=3, no_wrap=True)
    t.add_column(width=44, no_wrap=True, overflow="ellipsis")
    t.add_column(no_wrap=True, overflow="ellipsis")
    for i, field in enumerate(items):
        focused = in_fields and i == cur
        style = "tab.active" if focused else "value"
        mark = f"{g['tab_l']}{g['arrow']}" if focused else ""
        label = "" if field is F.CONTINUE else field.label
        t.add_row(Text(mark, style=style), Text(label, style=style), _value_text(s, field, d, focused))
        if focused and s.field_error:
            t.add_row(Text(""), Text(s.field_error, style="err"), Text(""))
    return t


def preview_rows(cfg: dict) -> list:
    rows = [
        ("Pipeline", "Cineon Film" if cfg.get("cineon_pipeline") == "on" else "FFmpeg Native"),
        ("Mode", str(cfg.get("mode", "")).upper()),
        ("FPS", str(cfg.get("fps"))),
        ("Scale / Fit", f"{cfg.get('scale')} · {cfg.get('fit')}"),
        ("LUT", "Hollywood" if cfg.get("lut") == "on" else "off"),
        ("HDR", str(cfg.get("hdr"))),
        ("Tonemap", str(cfg.get("tonemap"))),
        ("Audio", f"loudnorm {cfg.get('loudnorm')} · −14 LUFS"),
        ("Performance", str(cfg.get("performance"))),
    ]
    if cfg.get("cineon_pipeline") == "on":
        exposure, sat = float(cfg.get("exposure_offset", 0)), float(cfg.get("saturation", 1))
        rows.append(("Exposure / Sat", f"{exposure:+.1f} EV · {sat:.2f}"))
    return rows


def preview_chips(cfg: dict) -> list:
    enh = cfg.get("enhance") == "on"
    ai = enh and cfg.get("enhance_ai") == "on"
    return [
        ("LUT", cfg.get("lut") == "on"),
        ("Loudnorm", cfg.get("loudnorm") == "on"),
        ("Enhance", enh),
        ("AI", ai),
        ("MCTF", ai and cfg.get("mctf") == "on"),
        ("Dither", cfg.get("dither") != "off"),
        ("EBU Meter", cfg.get("ebu_meter") == "on"),
    ]


def _chips_line(cfg: dict) -> Text:
    out = Text(" ")
    for label, ok in preview_chips(cfg):
        out.append_text(C.quality_chip(label, ok))
        out.append("   ")
    return out


_DEFAULTS_SHOWN = ("lut", "hdr", "tonemap", "loudnorm", "ebu_meter", "enhance", "dither", "performance", "scale")


def _configuration(s: S.UIState) -> RenderableType:
    d = S.draft(s)
    if F.is_folder(d):
        cfg = F.to_config(d)
        where = ("PASTA", f"{elide(cfg.get('batch'), 50)} · {videos(s.source_count)} · saída: {output_dir_text(cfg)}")
    else:
        where = ("ENTRADA", basename(d.get("input")))
    strip = panel(kv_table([("PIPELINE", pipeline_label(d)), where]), "RESUMO", height=4)
    asked = {f.name for f in F.form_for(s.preset)}
    defaults = kv_table([(n, str(d.get(n))) for n in _DEFAULTS_SHOWN if n not in asked])
    row = Table.grid(expand=True)
    row.add_column(ratio=72)
    row.add_column(ratio=44)
    row.add_row(panel(field_rows(s), "CONFIGURATION", height=29), panel(defaults, "PADRÕES", height=29))
    return Group(strip, row)


def _tab_bar(s: S.UIState) -> Text:
    g = glyphs()
    out = Text(" ")
    for i, name in enumerate(F.TABS):
        if i == s.tab:
            mark = f"{g['tab_l']}{g['arrow']}" if s.tab_focus else g["tab_l"]
            out.append(f"{mark}{name}   ", style="tab.active")
        else:
            out.append(f" {name}   ", style="tab.inactive")
    return out


def _advanced(s: S.UIState) -> RenderableType:
    d = S.draft(s)
    row = Table.grid(expand=True)
    row.add_column(ratio=74)
    row.add_column(ratio=42)
    row.add_row(panel(field_rows(s), F.TABS[s.tab].upper(), height=29),
                panel(kv_table(preview_rows(d)), "SETTINGS", height=29))
    return Group(_tab_bar(s), Rule(characters="─", style="muted"), row)


def _preview(s: S.UIState) -> RenderableType:
    g = glyphs()
    d = S.draft(s)
    folder = F.is_folder(d)
    if folder:
        cfg = F.to_config(d)
        title = f"PREVIEW · {source_text(cfg, s.source_count)} {g['arrow']} saída: {output_dir_text(cfg)}"
    else:
        title = f"PREVIEW · {basename(d.get('input'))} {g['arrow']} {F.output_name(d)}"
    inner = Table.grid(expand=True)
    inner.add_column(ratio=34)
    inner.add_column(ratio=78)
    inner.add_row(Panel(_program(s, d, folder), height=20, box=PANEL_BOX, border_style="panel.border"),
                  panel(kv_table(preview_rows(d)), "EXPORT SETTINGS", height=20))
    card = Panel(Group(inner, _chips_line(d)), title=f"[panel.title]{escape(title)}[/]", title_align="left",
                 box=PANEL_BOX, border_style="accent", height=28)
    actions = Text("   ")
    for i, label in enumerate(("CONTINUAR ▸ READY", "REVISAR")):
        focused = s.action_focus == i
        actions.append(f"{g['arrow'] if focused else ' '}[ {label} ]   ", style="tab.active" if focused else "muted")
    parts = [card]
    if s.field_error:
        parts.append(Text(f"   {s.field_error}", style="err"))
    parts.append(actions)
    return Group(*parts)


SCREEN_RENDERERS[S.CONFIGURATION] = _configuration
SCREEN_RENDERERS[S.ADVANCED] = _advanced
SCREEN_RENDERERS[S.PREVIEW] = _preview
