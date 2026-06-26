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

from typing import Iterable, Optional, Sequence

from rich.align import Align
from rich.columns import Columns
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from . import theme
from .theme import GRID_BOX, PANEL_BOX, glyphs


def _g(console=None) -> dict:
    return glyphs(console)


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
            line.append(f" {name} ", style="tab.active")
        else:
            line.append(f" {name} ", style="tab.inactive")
        if i != len(sections) - 1:
            line.append(" ", style="muted")
    return Panel(line, box=GRID_BOX, border_style="panel.border", padding=(0, 1))


# ──────────────────────────────────────────────────────────────────────────────
# Panels
# ──────────────────────────────────────────────────────────────────────────────
def program_panel(
    source: str,
    output: Optional[str],
    meta: Optional[Sequence[str]] = None,
    console=None,
) -> RenderableType:
    """The 'Program' monitor: source/output and a 9:16 target placeholder."""
    body = Table.grid(padding=(0, 1))
    body.add_column(style="label", justify="right")
    body.add_column(style="value")
    body.add_row("in", source or "—")
    body.add_row("out", output or "—")
    for line in meta or []:
        body.add_row("", Text(line, style="muted"))
    return Panel(body, title="PROGRAM", title_align="left",
                 border_style="panel.border", box=PANEL_BOX, padding=(1, 2))


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
def settings_preview(config, console=None) -> RenderableType:
    """Compose a full pre-encode preview from an EncodeConfig.

    Accepts the EncodeConfig (or anything with the same attributes). Builds a
    Premiere-style card: properties + a quality/feature chip row.
    """
    pipeline = "Cineon Film" if config.cineon_pipeline == "on" else "FFmpeg Native"
    rows = [
        ("Pipeline", pipeline),
        ("Mode", config.mode.upper()),
        ("FPS", config.fps),
        ("Scale / Fit", f"{config.scale} · {config.fit}"),
        ("LUT", "Hollywood" if config.lut == "on" else "off"),
        ("HDR", config.hdr),
        ("Tonemap", config.tonemap),
        ("Audio", f"loudnorm {config.loudnorm} · −14 LUFS"),
        ("Performance", config.performance),
    ]
    if config.cineon_pipeline == "on":
        rows.append(("Exposure / Sat", f"{config.exposure_offset:+.1f} EV · {config.saturation:.2f}"))

    chips = [
        quality_chip("LUT", config.lut == "on", console),
        quality_chip("Loudnorm", config.loudnorm == "on", console),
        quality_chip("Enhance", config.enhance == "on", console),
        quality_chip("AI", config.enhance_ai == "on", console),
        quality_chip("Dither", config.dither != "off", console),
        quality_chip("EBU Meter", config.ebu_meter == "on", console),
    ]

    src = config.input or config.batch or "—"
    out = config.output_path() if hasattr(config, "output_path") else None

    inner = Group(
        properties_panel(rows, title="EXPORT SETTINGS", console=console),
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
