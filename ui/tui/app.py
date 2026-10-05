from __future__ import annotations

import argparse
import os
import queue
import shutil
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
from ui.config import EncodeConfig
from ui.theme import get_console
from ui.tui import state as S
from ui.tui import widgets as W
from ui.tui.keys import KeyReader
from ui.tui.screens import error_message, partial_wording, render
from ui.tui_capture import ConsoleCapture, _Sink

TICK_S = 0.1


def _default_perf():
    try:
        import psutil

        vm = psutil.virtual_memory()
        return psutil.cpu_percent(interval=None), vm.percent, vm.used / 1e9
    except Exception:
        return None, None, None


def _default_tools(con) -> None:
    from ui.launcher import _flow_tools

    _flow_tools(con)


def _default_probe(path: str):
    from ui.probe import probe_source_dims

    return probe_source_dims(path)


class App:
    def __init__(self, ns=None, *, console=None, run_single=None, reader_factory=None, live_factory=None,
                 clock: Callable[[], float] = time.monotonic, sleep: Callable[[float], None] = time.sleep,
                 perf=None, size=None, output_path: str | None = None, terminate=None, tools=None, probe=None,
                 system=None):
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
        self._tools = tools or _default_tools
        self._probe = probe or _default_probe
        self._probed: tuple | None = None
        if ns is None:
            self.state = S.UIState(config={}, screen=S.HOME, system=system or self._system_rows())
        else:
            out = output_path if output_path is not None else D._single_output_path(ns)
            self.state = S.UIState(config=dict(vars(ns)), output_path=out, output_preexisted=os.path.exists(out))
        self._queue: queue.Queue = queue.Queue()
        self._control = R.CancelControl(terminate=self._terminate)
        self._live = None
        self._reader = None
        self._capture = None
        self._orig_stderr = None

    @staticmethod
    def _system_rows() -> tuple:
        side = os.path.join(os.path.dirname(RE.FFMPEG), "ffplay")
        has_ffplay = bool(shutil.which("ffplay")) or os.path.exists(side) or os.path.exists(side + ".exe")
        return (
            ("FFmpeg", os.path.basename(RE.FFMPEG)),
            ("ffprobe", os.path.basename(RE.FFPROBE)),
            ("ffplay", "ok" if has_ffplay else "⚠ ausente — monitor EBU desligado"),
            ("hardware", "detectado no início do encode"),
        )

    def run(self) -> int:
        self._reader = self._reader_factory(self._queue.put)
        self._orig_stderr = sys.stderr
        self._capture = ConsoleCapture(RE.console, self._queue.put)
        code = 1
        try:
            with self._live_factory(self._console) as live, self._capture:
                self._live = live
                sys.stderr = _Sink(self._queue.put)
                try:
                    self._reader.start()
                    code = self._session()
                except KeyboardInterrupt:
                    code = 130
                finally:
                    self._reader.stop()
                    sys.stderr = self._orig_stderr
        finally:
            sys.stderr = self._orig_stderr
            self._reader.restore()
        self._summary(code)
        return code

    def _summary(self, code: int) -> None:
        s = self.state
        if s.screen == S.COMPLETED:
            line = Text(f"✓ entregue: {s.output_path}", style="ok")
        elif s.screen == S.ERROR:
            line = Text(f"✗ erro (código {code}): {error_message(s)}", style="err")
        elif s.screen == S.CANCELLED:
            line = Text(f"⚠ cancelado: {partial_wording(s)}", style="warn")
        elif code == 0 and s.screen == S.HOME:
            self._console.print("[warn]Cancelado pelo usuário.[/warn]")
            return
        else:
            return
        self._console.print(line)

    def _session(self) -> int:
        while True:
            self._until(lambda s: s.action in S.ACTIONS)
            act = self.state.action
            self.state = replace(self.state, action=None)
            if act == "exit":
                return 0
            if act == "tools":
                self._run_tools()
                continue
            if act == "arm":
                self._arm()
                continue
            if act == "check_source":
                self._check_source()
                continue
            inp = self.state.config.get("input") or ""
            if not os.path.isfile(inp):
                self.state = S.apply(self.state, S.ReadyBlocked(f"arquivo de entrada não encontrado: {inp}"))
                continue
            break
        ns = self._ns if self._ns is not None else argparse.Namespace(**self.state.config)
        code = self._run_single(ns, self._queue, self._control, self._tick)
        self._drain()
        self.state = S.apply(self.state, S.Finished(code))
        self._until(lambda s: s.action == "exit")
        return code

    def _check_source(self) -> None:
        path = W.clean_path(self.state.source.text)
        if not path or os.path.isdir(path):
            status = "INVALID"
        elif os.path.isfile(path):
            status = "VALID"
        else:
            status = "NOT_FOUND"
        dims = None
        if status == "VALID":
            if self._probed is None or self._probed[0] != path:
                self._probed = (path, self._probe(path))
            dims = self._probed[1]
        self.state = S.apply(self.state, S.SourceChecked(path, status, dims))

    def _arm(self) -> None:
        cfg = EncodeConfig.model_validate(S.draft(self.state))
        ns = cfg.to_namespace()
        err = RE._validate_args_consistency(ns)
        out = D._single_output_path(ns)
        self.state = S.apply(self.state, S.Armed(vars(ns), out, os.path.exists(out), err))

    def _run_tools(self) -> None:
        self._reader.stop()
        self._reader.restore()
        sys.stderr = self._orig_stderr
        self._capture.__exit__(None, None, None)
        self._live.stop()
        try:
            self._tools(self._console)
        finally:
            self._live.start()
            self._capture.__enter__()
            sys.stderr = _Sink(self._queue.put)
            self._reader = self._reader_factory(self._queue.put)
            self._reader.start()

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
                if self._control.request_cancel():
                    self._queue.put(R.Cancel("requested"))
            elif self.state.action in S.ACTIONS:
                break
