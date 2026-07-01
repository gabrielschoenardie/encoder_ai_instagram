"""
ui.components
=============
Reusable Premiere-styled Rich renderables shared by the launcher and the
encode dashboard. Every function returns a Rich renderable (Panel/Table/Text/
Group) built from real data — no I/O, no engine imports — so they are trivially
unit-testable under ``Console(record=True)``.

The recurring Premiere frame is: a **tab bar** on top, a **Program** panel and a
**Properties** panel side by side, and a **Log** strip below.
"""

from __future__ import annotations

import os
from typing import Iterable, Optional, Sequence

from rich.align import Align
from rich.columns import Columns
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from . import theme
from .aspect import classify_aspect, orientation_of
from .theme import GRID_BOX, PANEL_BOX, glyphs


def _g(console=None) -> dict:
    return glyphs(console)


def _short_path(p: str, limit: int = 30) -> str:
    """Basename, middle-elided, so a deep path can't clip the panel title.

    Keeps the head and tail of the filename (the tail carries the extension
    and the engine's ``_Hollywood_CRF18`` / ``_Cineon_Film`` suffix) joined by
    an ASCII ellipsis so it stays safe on legacy consoles.
    """
    name = os.path.basename(p.rstrip("/\\")) or p
    if len(name) <= limit:
        return name
    keep = limit - 3
    head = keep // 2
    tail = keep - head
    return f"{name[:head]}...{name[-tail:]}"


# ──────────────────────────────────────────────────────────────────────────────
# Header / tabs
# ──────────────────────────────────────────────────────────────────────────────
def banner(title: str, subtitle: str = "", console=None) -> RenderableType:
    """Top brand banner."""
    g = _g(console)
    head = Text()
    head.append(f"{g['film']} ", style="accent")
    head.append(title, style="primary")
    if subtitle:
        head.append(f"   {subtitle}", style="muted")
    return Panel(head, box=PANEL_BOX, border_style="panel.border", padding=(0, 1))


def tab_bar(sections: Sequence[str], active: int, console=None) -> RenderableType:
    """Premiere-style tab strip; the active section is highlighted."""
    g = _g(console)
    line = Text()
    for i, name in enumerate(sections):
        if i == active:
            line.append(f" {g['tab_l']} {name} ", style="tab.active")
        else:
            line.append(f" {name} ", style="tab.inactive")
        if i != len(sections) - 1:
            line.append(" ", style="muted")
    return Panel(line, box=GRID_BOX, border_style="panel.border", padding=(0, 1))


# ──────────────────────────────────────────────────────────────────────────────
# Panels
# ──────────────────────────────────────────────────────────────────────────────
def _aspect_frame(fit: str = "contain", aspect: str = "9:16",
                  dims: str = "1080 x 1920", orientation: str = "portrait",
                  console=None) -> RenderableType:
    """A 'Program monitor' frame that visualises the source aspect + framing.

    The frame's char grid adapts to ``orientation`` so it *looks* the right
    shape despite ~2:1 terminal cells: portrait → a tall narrow frame, landscape
    → a wide short frame, square → medium. ``contain`` draws letterbox bars (the
    whole source fits, bars top/bottom); ``cover`` fills the frame edge-to-edge
    with corner crop markers. ``aspect``/``dims`` label the source. Glyphs
    downgrade to ASCII on legacy consoles.
    """
    g = _g(console)

    # Inner width (chars) + count of decorative bars/edge rows, picked so the
    # rendered panel reads as the right shape on a ~2:1 cell grid.
    if orientation == "landscape":
        w, bars = 28, 1
    elif orientation == "square":
        w, bars = 18, 1
    else:  # portrait (default)
        w, bars = 16, 2

    def line(text: str = "", style: str = "value") -> Text:
        return Text(text.center(w), style=style)

    labels = [
        ("", "value"),
        (aspect, "value"),
        (dims, "info"),
        ("", "value"),
        (fit, "accent"),
        ("preenche · crop" if fit == "cover" else "ajusta", "muted"),
        ("", "value"),
    ]

    if fit == "cover":
        edge = g["block_full"]
        mark = g["bullet"]

        def framed(inner_text: str = "", inner_style: str = "value") -> Text:
            t = Text()
            t.append(edge, style="accent")
            t.append(inner_text.center(w - 2), style=inner_style)
            t.append(edge, style="accent")
            return t

        crop = Text()
        crop.append(edge, style="accent")
        mid = (" " + mark).ljust(w - 3) + mark + " "
        crop.append(mid[: w - 2], style="warn")
        crop.append(edge, style="accent")
        rows = [crop] * bars
        rows += [framed(t, s) for (t, s) in labels]
        rows += [crop] * bars
    else:  # contain
        bar = Text(g["block_empty"] * w, style="muted")
        rows = [bar] * bars
        rows += [line(t, s) for (t, s) in labels]
        rows += [bar] * bars

    return Panel(Group(*rows), border_style="panel.border", box=PANEL_BOX,
                 padding=(0, 1), width=w + 4)


def program_panel(
    source: str,
    output: Optional[str],
    meta: Optional[Sequence[str]] = None,
    fit: str = "contain",
    src_dims: Optional[tuple] = None,
    console=None,
) -> RenderableType:
    """The 'Program' monitor: a framing preview plus source/output rows.

    When ``src_dims=(w, h)`` (rotation-corrected effective dims) is given, the
    framing preview reflects the *real* source aspect/orientation; otherwise it
    falls back to the canonical Reels target (9:16, 1080x1920, portrait).
    """
    if src_dims and len(src_dims) == 2:
        sw, sh = int(src_dims[0]), int(src_dims[1])
        frame = _aspect_frame(
            fit,
            aspect=classify_aspect(sw, sh),
            dims=f"{sw} x {sh}",
            orientation=orientation_of(sw, sh),
            console=console,
        )
    else:
        frame = _aspect_frame(fit, console=console)
    body = Table.grid(padding=(0, 1))
    body.add_column(style="label", justify="right")
    body.add_column(style="value")
    body.add_row("in", source or "—")
    body.add_row("out", output or "—")
    for ln in meta or []:
        body.add_row("", Text(ln, style="muted"))
    inner = Group(frame, body)
    return Panel(inner, title="PROGRAM", title_align="left",
                 border_style="panel.border", box=PANEL_BOX, padding=(1, 2))


def program_split(
    source: str,
    output: Optional[str],
    prop_rows: Sequence[tuple],
    fit: str = "contain",
    meta: Optional[Sequence[str]] = None,
    prop_title: str = "EXPORT SETTINGS",
    src_dims: Optional[tuple] = None,
    console=None,
) -> RenderableType:
    """Premiere-style split: the 9:16 Program monitor (left) + Properties (right).

    Mirrors the dashboard's two-column ``Table.grid(expand=True)`` pattern: the
    viewer takes its natural width on the left, the properties card stretches.
    """
    split = Table.grid(expand=True, padding=(0, 1))
    split.add_column(justify="left")
    split.add_column(ratio=1)
    split.add_row(
        program_panel(source, output, meta=meta, fit=fit, src_dims=src_dims,
                      console=console),
        properties_panel(prop_rows, title=prop_title, console=console),
    )
    return split


def properties_panel(rows: Sequence[tuple], title: str = "PROPERTIES",
                     console=None) -> RenderableType:
    """Right-side properties: a list of (label, value) pairs."""
    tbl = Table.grid(padding=(0, 2))
    tbl.add_column(style="label", justify="right")
    tbl.add_column(style="value")
    for label, value in rows:
        tbl.add_row(str(label), str(value))
    return Panel(tbl, title=title, title_align="left",
                 border_style="panel.border", box=PANEL_BOX, padding=(1, 2))


def info_card(title: str, body: RenderableType, style: str = "panel.border",
              console=None) -> RenderableType:
    """A titled card for arbitrary content."""
    return Panel(body, title=title, title_align="left",
                 border_style=style, box=PANEL_BOX, padding=(1, 2))


# ──────────────────────────────────────────────────────────────────────────────
# Quality indicators
# ──────────────────────────────────────────────────────────────────────────────
def quality_chip(label: str, status: Optional[bool], console=None) -> Text:
    """A ✓/⚠/✗ chip. status True->ok, False->warn, None->neutral."""
    g = _g(console)
    if status is True:
        return Text(f"{g['ok']} {label}", style="ok")
    if status is False:
        return Text(f"{g['warn']} {label}", style="warn")
    return Text(f"{g['bullet']} {label}", style="muted")


def quality_row(chips: Iterable[Text], console=None) -> RenderableType:
    """Lay chips out in columns."""
    return Columns(list(chips), padding=(0, 3), expand=False)


# ──────────────────────────────────────────────────────────────────────────────
# Log / notifications
# ──────────────────────────────────────────────────────────────────────────────
def log_panel(lines: Sequence[str], title: str = "LOG", max_lines: int = 6,
              console=None) -> RenderableType:
    """Bounded log strip showing the most recent lines."""
    g = _g(console)
    recent = list(lines)[-max_lines:]
    if not recent:
        body = Text("—", style="muted")
    else:
        body = Text()
        for i, ln in enumerate(recent):
            body.append(f"{g['arrow']} ", style="accent")
            body.append(ln.rstrip(), style="muted")
            if i != len(recent) - 1:
                body.append("\n")
    return Panel(body, title=title, title_align="left",
                 border_style="panel.border", box=PANEL_BOX, padding=(0, 1))


def job_strip(source: str, output: Optional[str] = None,
              src_dims: Optional[tuple] = None, console=None) -> RenderableType:
    """A thin one-line job-identity strip: source ▸ output (+ aspect tag).

    Shown atop the live dashboard so the encode never loses sight of *what* is
    being rendered. Paths are middle-elided; when ``src_dims=(w, h)`` (effective
    dims) is given, a small aspect tag (e.g. '9:16 1080×1920') is appended.
    """
    g = _g(console)
    line = Text()
    line.append(f"{g['film']} ", style="accent")
    line.append(_short_path(source) if source else "—", style="value")
    line.append(f"  {g['arrow']}  ", style="accent")
    line.append(_short_path(output) if output else "(saída)", style="info")
    if src_dims and len(src_dims) == 2:
        try:
            sw, sh = int(src_dims[0]), int(src_dims[1])
            if sw > 0 and sh > 0:
                line.append(f"   ·  {classify_aspect(sw, sh)} {sw}×{sh}", style="info.dim")
        except (TypeError, ValueError):
            pass
    return Panel(line, box=GRID_BOX, border_style="panel.border", padding=(0, 1))


def gauge_bar(pct: float, width: int = 12, console=None) -> RenderableType:
    """A small horizontal load gauge whose fill scales with ``pct`` (0–100) and
    whose colour steps green→amber→red by threshold. Used by the perf monitor."""
    g = _g(console)
    try:
        pct = float(pct)
    except (TypeError, ValueError):
        pct = 0.0
    pct = min(max(pct, 0.0), 100.0)
    filled = int(round(pct / 100.0 * width))
    filled = min(max(filled, 0), width)
    if pct >= 85:
        style = "err"
    elif pct >= 60:
        style = "warn"
    else:
        style = "ok"
    bar = Text()
    bar.append(g["block_full"] * filled, style=style)
    bar.append(g["block_empty"] * (width - filled), style="bar.back")
    return bar


def notification(message: str, level: str = "info", console=None) -> RenderableType:
    """A one-line toast-style notification."""
    g = _g(console)
    icon = {"ok": g["ok"], "warn": g["warn"], "err": g["err"]}.get(level, g["arrow"])
    style = {"ok": "ok", "warn": "warn", "err": "err"}.get(level, "info")
    return Panel(Text(f"{icon} {message}", style=style),
                 box=GRID_BOX, border_style=style, padding=(0, 1))


# ──────────────────────────────────────────────────────────────────────────────
# Settings preview (shown before encode)
# ──────────────────────────────────────────────────────────────────────────────
def settings_preview(config, src_dims=None, console=None) -> RenderableType:
    """Compose a full pre-encode preview from an EncodeConfig.

    Accepts the EncodeConfig (or anything with the same attributes). Builds a
    Premiere-style card: properties + a quality/feature chip row.
    """
    g = _g(console)
    pipeline = "Cineon Film" if config.cineon_pipeline == "on" else "FFmpeg Native"
    rows = [
        ("Pipeline", pipeline),
        ("Mode", config.mode.upper()),
        ("FPS", config.fps),
        ("Scale / Fit", f"{config.scale} · {config.fit}"),
        ("LUT", "Hollywood" if config.lut == "on" else "off"),
        ("HDR", config.hdr),
        ("Tonemap", config.tonemap),
        (f"{g['audio']} Audio", f"loudnorm {config.loudnorm} · −14 LUFS"),
        ("Performance", config.performance),
    ]
    if config.cineon_pipeline == "on":
        rows.append(("Exposure / Sat", f"{config.exposure_offset:+.1f} EV · {config.saturation:.2f}"))

    chips = [
        quality_chip("LUT", config.lut == "on", console),
        quality_chip(f"{g['audio']} Loudnorm", config.loudnorm == "on", console),
        quality_chip("Enhance", config.enhance == "on", console),
        quality_chip(f"{g['spark']} AI", config.enhance_ai == "on", console),
        quality_chip("Dither", config.dither != "off", console),
        quality_chip("EBU Meter", config.ebu_meter == "on", console),
    ]

    src_full = config.input or config.batch or "—"
    out_full = config.output_path() if hasattr(config, "output_path") else None
    src = _short_path(src_full)
    out = _short_path(out_full) if out_full else None

    inner = Group(
        program_split(src, out, rows, fit=config.fit, src_dims=src_dims,
                      console=console),
        Align.left(quality_row(chips, console=console)),
    )
    return info_card(f"PREVIEW · {src} → {out or '(batch)'}", inner,
                     style="accent", console=console)


# ──────────────────────────────────────────────────────────────────────────────
# Delivery seal (post-encode QC certificate)
# ──────────────────────────────────────────────────────────────────────────────
def delivery_seal(checks, *, ready=None, console=None) -> RenderableType:
    """Hollywood-style 'delivery seal' QC card certifying the final audio.

    Args:
        checks:  sequence of ``(label, value, passed)`` where ``passed`` is
                 ``True`` (✓/ok), ``False`` (⚠/warn) or ``None`` (•/muted unknown).
        ready:   force the seal state; when ``None`` it is derived from ``checks``
                 (ready iff no check failed — ``None`` counts as unknown, not fail).
        console: themed Rich Console (for glyph downgrade only).
    """
    g = _g(console)
    checks = list(checks)

    if ready is None:
        ready = not any(p is False for (_, _, p) in checks)

    grid = Table.grid(padding=(0, 3))
    grid.add_column()
    grid.add_column()

    cells = []
    for label, value, passed in checks:
        chip = quality_chip(label, passed, console=console)
        cell = Text()
        cell.append_text(chip)
        cell.append("  ")
        cell.append(str(value), style="value")
        cells.append(cell)

    for i in range(0, len(cells), 2):
        left = cells[i]
        right = cells[i + 1] if i + 1 < len(cells) else Text("")
        grid.add_row(left, right)

    rule_style = "seal" if ready else "warn"
    if ready:
        seal_line = Text(f"{g['star']}  D E L I V E R Y   R E A D Y  {g['star']}",
                         style="seal")
    else:
        seal_line = Text(f"{g['warn']}  R E V I S A R   E N T R E G A  {g['warn']}",
                         style="warn")

    inner = Group(
        grid,
        Rule(style=rule_style),
        Align.center(seal_line),
    )
    return Panel(inner, title="MASTER QC", title_align="left",
                 border_style="seal" if ready else "warn",
                 box=theme.HEAVY_BOX, padding=(1, 2))
