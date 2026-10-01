from __future__ import annotations

import queue
import sys
import time
from dataclasses import replace
from typing import Callable

from rich.live import Live
from rich.panel import Panel
from rich.text import Text

import Reels_Encoder_v2_FINAL as RE
import reporter as R
from ui import tui_driver as D
from ui.theme import get_console
from ui.tui import state as S
from ui.tui.keys import KeyReader
from ui.tui.screens import render
from ui.tui_capture import ConsoleCapture, _Sink

TICK_S = 0.1


def _default_perf():
    try:
        import psutil

        vm = psutil.virtual_memory()
        return psutil.cpu_percent(interval=None), vm.percent, vm.used / 1e9
    except Exception:
        return None, None, None


class App:
    def __init__(self, ns, *, console=None, run_single=None, reader_factory=None, live_factory=None,
                 clock: Callable[[], float] = time.monotonic, sleep: Callable[[float], None] = time.sleep,
                 perf=None, size=None, output_path: str | None = None, terminate=None):
        self._ns = ns
        self._console = console or get_console()
        self._run_single = run_single or D.run_single
        self._reader_factory = reader_factory or KeyReader
        self._live_factory = live_factory or (lambda c: Live(console=c, screen=True, auto_refresh=False))
        self._clock = clock
        self._sleep = sleep
        self._perf = perf or _default_perf
        self._size = size or (lambda: (self._console.size.width, self._console.size.height))
        self._terminate = terminate or RE.terminate_active_ffmpeg
        out = output_path if output_path is not None else D._single_output_path(ns)
        self.state = S.UIState(config=dict(vars(ns)), output_path=out)
        self._queue: queue.Queue = queue.Queue()
        self._control = R.CancelControl(terminate=self._terminate)
        self._live = None

    def run(self) -> int:
        reader = self._reader_factory(self._queue.put)
        orig_stderr = sys.stderr
        code = 1
        try:
            with self._live_factory(self._console) as live, ConsoleCapture(RE.console, self._queue.put):
                self._live = live
                sys.stderr = _Sink(self._queue.put)
                try:
                    reader.start()
                    code = self._session()
                except KeyboardInterrupt:
                    code = 130
                finally:
                    reader.stop()
                    sys.stderr = orig_stderr
        finally:
            sys.stderr = orig_stderr
            reader.restore()
        return code

    def _session(self) -> int:
        self._until(lambda s: s.action in ("start", "exit"))
        if self.state.action == "exit":
            return 0
        self.state = replace(self.state, action=None)
        code = self._run_single(self._ns, self._queue, self._control, self._tick)
        self.state = S.apply(self.state, S.Finished(code))
        self._until(lambda s: s.action == "exit")
        return code

    def _until(self, done: Callable[[S.UIState], bool]) -> None:
        while not done(self.state):
            self._tick()
            if not done(self.state):
                self._sleep(TICK_S)

    def _tick(self) -> None:
        try:
            self._drain()
            cpu, ram, used = self._perf()
            self.state = S.apply(self.state, S.Tick(self._clock(), tuple(self._size()), cpu, ram, used))
        except Exception:
            pass
        try:
            frame = render(self.state)
        except Exception as exc:
            frame = Panel(Text(f"erro ao desenhar a tela: {exc!r}\no encode continua", style="err"))
        try:
            self._live.update(frame, refresh=True)
        except Exception:
            pass

    def _drain(self) -> None:
        while True:
            try:
                ev = self._queue.get_nowait()
            except queue.Empty:
                break
            self.state = S.apply(self.state, ev)
            if self.state.action == "cancel":
                self.state = replace(self.state, action=None)
                self._control.request_cancel()
            elif self.state.action in ("start", "exit"):
                break
