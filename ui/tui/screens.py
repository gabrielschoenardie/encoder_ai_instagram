from __future__ import annotations

import os
from typing import Callable

from rich.align import Align
from rich.console import Group, RenderableType
from rich.layout import Layout
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

import reporter as R
from ui import components as C
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
    done_tracks = {f"PASS {t.index}" for t in s.passes if t.done}
    current = f"PASS {s.substep}" if s.stage == R.PASS else s.stage
    finished = s.exit_code == 0 and s.screen in (S.COMPLETED,)
    out = Text(" ")
    for name in names:
        is_done = finished or name in s.stages_done or name in done_tracks or (
            name in STAGE_ORDER and current not in STAGE_ORDER and current is not None)
        if name == current and not finished:
            out.append(f"{g['tab_l']}{g['bullet']} {name}    ", style="tab.active")
        elif is_done:
            out.append(f"{g['ok']} {name}    ", style="ok")
        else:
            out.append(f"○ {name}    ", style="muted")
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


def _log_panel(s: S.UIState) -> Panel:
    title = "LOG" + (f" [warn]⚠ {s.warnings}[/]" if s.warnings else "")
    return panel(log_rows(s.log, 9), title, height=11)


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
    return panel(Group(stage_rail(s), Text(""), *pass_lines(s)), title, height=7)


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
    buttons = Text("   ")
    for i, label in enumerate(("CONTINUAR ENCODE", "CANCELAR ENCODE")):
        focused = s.modal_focus == i
        buttons.append(f"{g['arrow'] if focused else ' '}[ {label} ]   ", style="tab.active" if focused else "muted")
    body = Group(
        Text(""),
        Text(f"  etapa ativa: {where}{pct}"),
        Text("  usa o caminho de interrupção existente (o mesmo do Ctrl+C)", style="muted"),
        Text(f"  parcial: {basename(s.output_path)}", style="muted"),
        Text(""),
        buttons,
    )
    box = Panel(body, title="[warn]CANCELAR ENCODE?[/]", box=PANEL_BOX, border_style="warn", width=64, height=12)
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
    revealed = s.seal_reveal_start is not None and s.now - s.seal_reveal_start >= S.SEAL_REVEAL_S - 1e-6
    if not revealed:
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


def _error(s: S.UIState) -> RenderableType:
    err = s.error
    msg = f"{err.kind}: {err.message}" if err is not None else f"Encode terminou com erro (código {s.exit_code})"
    card = C.error_card(msg)
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


def _cancelled(s: S.UIState) -> RenderableType:
    if s.partial_removed is True:
        partial = f"output parcial removido: {basename(s.output_path)}"
    elif s.partial_removed is False:
        partial = f"NÃO foi possível remover {basename(s.output_path)} — apague à mão antes de rodar de novo"
    else:
        partial = "nenhum output parcial"
    card = Panel(Group(Text(""), Text("   ⚠ Encode interrompido pelo usuário", style="warn"), Text(""),
                       Text(f"   {partial}")), box=HEAVY_BOX, border_style="warn", height=8)
    return Group(card, _log_panel(s), action_row(s))


SCREEN_RENDERERS[S.QC] = _qc
SCREEN_RENDERERS[S.COMPLETED] = _completed
SCREEN_RENDERERS[S.ERROR] = _error
SCREEN_RENDERERS[S.CANCELLED] = _cancelled
