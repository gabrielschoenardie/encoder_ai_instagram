"""
ui.dashboard
============
Premiere-styled live encode dashboard.

``EncodeDashboard`` duck-types the engine's ``ResolveProgressHUD``: it exposes
``update_frame(frame)`` (called by ``ffmpeg_live_reader``) and ``render()``
(handed to a Rich ``Live``). The engine seam in ``_run_encoding`` builds it via
``make_dashboard(...)`` and falls back to ``ResolveProgressHUD`` if ``ui`` (or
its deps) is unavailable — so behavior without this package is unchanged.

The live log is read from the **shared stderr deque** the engine already keeps
(``stderr_tail``), so no change to ``ffmpeg_live_reader`` is needed.
"""

from __future__ import annotations

import time
from typing import Deque, Optional

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from . import components as C
from .theme import PANEL_BOX, glyphs

try:  # perf monitor is best-effort
    import psutil
    _PSUTIL = True
except Exception:  # pragma: no cover - psutil is a stated dependency
    _PSUTIL = False


class EncodeDashboard:
    """Live dashboard with the same update interface as ResolveProgressHUD."""

    def __init__(self, total_frames: int, source_fps: int = 30,
                 log_sink: Optional[Deque[str]] = None, console=None,
                 title: str = "ENCODING"):
        self.total_frames = max(int(total_frames), 1)
        self.source_fps = max(int(source_fps), 1)
        self.current_frame = 0
        self.start_time = time.time()
        self.last_time = self.start_time
        self.last_frame = 0
        self.fps = 0.0
        self.speed = 0.0
        self.eta = "--:--:--"
        self.log_sink = log_sink
        self.console = console
        self.title = title
        self._glyphs = glyphs(console)
        if _PSUTIL:
            try:
                psutil.cpu_percent(interval=None)  # prime non-blocking reading
            except Exception:
                pass

    # ── update (identical math to ResolveProgressHUD) ───────────────────────────
    def update_frame(self, frame) -> None:
        try:
            frame = int(frame)
        except (TypeError, ValueError):
            return
        self.current_frame = frame
        now = time.time()
        dt = now - self.last_time
        df = frame - self.last_frame
        if dt > 0:
            self.fps = max(df / dt, 0.1)
            self.speed = self.fps / self.source_fps
        else:
            self.fps = 0.0
            self.speed = 0.0
        self.last_frame = frame
        self.last_time = now
        remaining = max(self.total_frames - frame, 1)
        eta_seconds = remaining / max(self.fps, 0.01)
        self.eta = time.strftime("%H:%M:%S", time.gmtime(eta_seconds))

    # ── rendering ───────────────────────────────────────────────────────────────
    def _progress_bar(self, width: int = 44) -> Text:
        g = self._glyphs
        p = min(max(self.current_frame / self.total_frames, 0.0), 1.0)
        filled = int(p * width)
        bar = Text()
        bar.append(g["block_full"] * filled, style="bar.complete")
        bar.append(g["block_empty"] * (width - filled), style="bar.back")
        bar.append(f"  {p * 100:5.1f}%", style="value")
        return bar

    def _metrics_panel(self) -> RenderableType:
        grid = Table.grid(padding=(0, 2))
        grid.add_column(style="label", justify="right")
        grid.add_column(style="value")
        grid.add_row("frame", f"{self.current_frame}/{self.total_frames}")
        grid.add_row("fps", f"{self.fps:.1f}")
        grid.add_row("speed", f"{self.speed:.2f}x")
        grid.add_row("eta", self.eta)
        elapsed = time.strftime("%H:%M:%S", time.gmtime(time.time() - self.start_time))
        grid.add_row("elapsed", elapsed)
        return Panel(grid, title="TIMELINE", title_align="left",
                     border_style="panel.border", box=PANEL_BOX, padding=(1, 2))

    def _perf_panel(self) -> RenderableType:
        grid = Table.grid(padding=(0, 2))
        grid.add_column(style="label", justify="right")
        grid.add_column(style="value")
        if _PSUTIL:
            try:
                cpu = psutil.cpu_percent(interval=None)
                vm = psutil.virtual_memory()
                grid.add_row("cpu", f"{cpu:.0f}%")
                grid.add_row("ram", f"{vm.percent:.0f}%")
                grid.add_row("ram used", f"{vm.used / 1e9:.1f} GB")
            except Exception:
                grid.add_row("perf", "—")
        else:
            grid.add_row("perf", "psutil n/d")
        return Panel(grid, title="PERFORMANCE", title_align="left",
                     border_style="panel.border", box=PANEL_BOX, padding=(1, 2))

    def render(self) -> RenderableType:
        g = self._glyphs
        header = Panel(self._progress_bar(), title=f"{g['film']} {self.title}",
                       title_align="left", border_style="accent",
                       box=PANEL_BOX, padding=(0, 2))
        cols = Table.grid(expand=True)
        cols.add_column(ratio=1)
        cols.add_column(ratio=1)
        cols.add_row(self._metrics_panel(), self._perf_panel())
        log_lines = list(self.log_sink) if self.log_sink else []
        log = C.log_panel(log_lines, title="LOG", max_lines=5, console=self.console)
        return Group(header, cols, log)


def make_dashboard(total_frames: int, fps: int = 30,
                   log_sink: Optional[Deque[str]] = None, console=None,
                   title: str = "ENCODING") -> EncodeDashboard:
    """Factory used by the engine seam in _run_encoding."""
    return EncodeDashboard(total_frames, source_fps=fps, log_sink=log_sink,
                           console=console, title=title)
