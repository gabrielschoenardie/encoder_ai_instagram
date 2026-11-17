from __future__ import annotations

import argparse
import os
import queue
import shutil
import sys
import threading
import time
import traceback
from dataclasses import dataclass, replace
from typing import Callable

from pydantic import ValidationError
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

import Reels_Encoder_v2_FINAL as RE
import reporter as R
from ui import tui_driver as D
from ui.config import EncodeConfig
from ui.theme import get_console
from ui.tui import forms as F
from ui.tui import state as S
from ui.tui import widgets as W
from ui.tui.keys import KeyReader
from ui.tui.screens import error_message, partial_wording, queue_summary, render
from ui.tui_capture import ConsoleCapture, _Sink

TICK_S = 0.1
READY_HOLD_S = 1.2
KEY_GAP_S = 0.3


@dataclass(frozen=True)
class _Arrived:
    key: S.Key
    ts: float


def _default_perf():
    try:
        import psutil

        vm = psutil.virtual_memory()
        return psutil.cpu_percent(interval=None), vm.percent, vm.used / 1e9
    except Exception:
        return None, None, None


def _default_tools(con) -> None:
    from ui.tui.tools import _flow_tools

    _flow_tools(con)


def _default_probe(path: str):
    from ui.probe import probe_source_dims

    return probe_source_dims(path)


def _spawn(fn: Callable[[], None]) -> None:
    threading.Thread(target=fn, daemon=True).start()


class App:
    def __init__(self, ns=None, *, console=None, run_single=None, run_batch=None, reader_factory=None, live_factory=None,
                 clock: Callable[[], float] = time.monotonic, sleep: Callable[[float], None] = time.sleep,
                 perf=None, size=None, output_path: str | None = None, terminate=None, tools=None, probe=None,
                 system=None, spawn=None):
        self._ns = ns
        self._console = console or get_console()
        self._run_single = run_single or D.run_single
        self._run_batch = run_batch or D.run_batch
        self._reader_factory = reader_factory or KeyReader
        self._live_factory = live_factory or (lambda c: Live(console=c, screen=True, auto_refresh=False,
                                                              redirect_stdout=False, redirect_stderr=False))
        self._clock = clock
        self._sleep = sleep
        self._perf = perf or _default_perf
        self._size = size or (lambda: (self._console.size.width, self._console.size.height))
        self._terminate = terminate or RE.terminate_active_ffmpeg
        self._tools = tools or _default_tools
        self._probe = probe or _default_probe
        self._spawn = spawn or _spawn
        self._probed: tuple | None = None
        self._ready_at: float | None = None
        self._last_key_at: float | None = None
        if ns is None:
            self.state = S.UIState(config={}, screen=S.HOME,
                                    system=system if system is not None else self._system_rows())
        else:
            out = output_path if output_path is not None else D._single_output_path(ns)
            self.state = S.UIState(config=dict(vars(ns)), output_path=out, output_preexisted=os.path.exists(out))
        self._queue: queue.Queue = queue.Queue()
        self._control = R.CancelControl(terminate=self._terminate)
        self._live = None
        self._reader = None
        self._capture = None
        self._orig_stderr = None
        self._orig_stdout = None
        self._lines: list = []
        self._last_code: int | None = None
        self._internal_seen: set = set()

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
        self._reader = self._reader_factory(self._emit)
        self._orig_stderr = sys.stderr
        self._orig_stdout = sys.stdout
        pinned = self._console._file is None
        if pinned:
            self._console.file = self._orig_stdout
        self._capture = ConsoleCapture(RE.console, self._queue.put)
        code = 1
        try:
            with self._live_factory(self._console) as live, self._capture:
                self._live = live
                sys.stderr = _Sink(self._queue.put)
                sys.stdout = _Sink(self._queue.put)
                try:
                    self._reader.start()
                    code = self._session()
                except KeyboardInterrupt:
                    code = self._interrupted_code()
                finally:
                    self._reader.stop()
                    sys.stderr = self._orig_stderr
                    sys.stdout = self._orig_stdout
        finally:
            sys.stderr = self._orig_stderr
            sys.stdout = self._orig_stdout
            if pinned:
                self._console.file = None
            self._reader.restore()
        self._summary(code)
        return code

    def _interrupted_code(self) -> int:
        s = self.state
        if s.screen == S.REPORT and s.exit_code is not None:
            return s.exit_code
        if s.is_batch and s.screen in (S.QUEUE, S.DETAILS, S.LOG):
            self.state = S.apply(s, S.Finished(130))
        return 130

    @staticmethod
    def _final_line(s: S.UIState, code: int) -> Text | None:
        if s.screen == S.REPORT:
            return queue_summary(s, code)
        if s.screen == S.COMPLETED:
            return Text(f"✓ entregue: {s.output_path}", style="ok")
        if s.screen == S.ERROR:
            return Text(f"✗ erro (código {code}): {error_message(s)}", style="err")
        if s.screen == S.CANCELLED:
            return Text(f"⚠ cancelado: {partial_wording(s)}", style="warn")
        return None

    def _summary(self, code: int) -> None:
        line = self._final_line(self.state, code)
        if line is None and not self._lines and code == 0 and self.state.screen == S.HOME:
            self._console.print("[warn]Cancelado pelo usuário.[/warn]")
            return
        for out in self._lines + ([line] if line is not None else []):
            self._console.print(out)

    def _session(self) -> int:
        while True:
            while True:
                self._until(lambda s: s.action in S.ACTIONS)
                act = self.state.action
                self.state = replace(self.state, action=None)
                if act == "exit":
                    return self._last_code if self._last_code is not None else 0
                if act == "tools":
                    self._run_tools()
                    continue
                if act == "arm":
                    self._arm()
                    continue
                if act == "check_source":
                    self._check_source()
                    continue
                blocked = self._start_blocked()
                if blocked:
                    self.state = S.apply(self.state, S.ReadyBlocked(blocked))
                    continue
                break
            ns = self._ns if self._ns is not None else argparse.Namespace(**self.state.config)
            if self.state.is_batch:
                code = self._start_batch(ns)
            else:
                code = self._run_single(ns, self._queue, self._control, self._tick)
            self._drain()
            self.state = S.apply(self.state, S.Finished(code))
            self._last_code = code
            self._until(lambda s: s.action in ("exit", "new"))
            if self.state.action == "exit":
                return code
            self._lines.append(self._final_line(self.state, code))
            while True:
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    break
            self._control = R.CancelControl(terminate=self._terminate)
            self._ready_at = self._last_key_at = None
            self.state = S.new_session(self.state)

    def _start_blocked(self) -> str | None:
        cfg = self.state.config
        if self.state.is_batch:
            folder = cfg.get("batch") or ""
            if not os.path.isdir(folder):
                return f"pasta não encontrada: {folder}"
            try:
                found = RE.find_video_files(folder)
            except OSError as exc:
                return f"não foi possível ler a pasta: {folder} ({exc})"
            if not found:
                return f"nenhum vídeo encontrado em: {folder}"
            return None
        inp = cfg.get("input") or ""
        if not os.path.isfile(inp):
            return f"arquivo de entrada não encontrado: {inp}"
        return None

    def _start_batch(self, ns) -> int:
        try:
            return self._run_batch(ns, self._queue, self._control, self._tick)
        except Exception as exc:
            self._queue.put(R.Error(type(exc).__name__, str(exc) or repr(exc), None, None, traceback.format_exc()))
            return 130 if self._control.cancelled else 1

    def _check_source(self) -> None:
        path = W.clean_path(self.state.source.text)
        if path.startswith("\\\\") and sum(path[2:].count(sep) for sep in "\\/") < 2:
            self.state = S.apply(self.state, S.SourceChecked(path, "NOT_FOUND"))
            return
        folder = F.is_folder(S.draft(self.state))
        self._spawn(lambda: self._source_worker(path, folder))

    def _source_worker(self, path: str, folder: bool) -> None:
        try:
            if folder:
                ev = self._check_folder(path)
            else:
                ev = S.SourceChecked(path, "INVALID" if not path or os.path.isdir(path)
                                     else "VALID" if os.path.isfile(path) else "NOT_FOUND")
        except Exception:
            ev = S.SourceChecked(path, "NOT_FOUND")
        ev = replace(ev, folder=folder)
        if folder or ev.status != "VALID":
            self._queue.put(ev)
            return
        if path != W.clean_path(self.state.source.text):
            return
        cached = self._probed
        if cached is None or cached[0] != path:
            self._queue.put(S.SourceChecked(path, "PROBING", folder=False))
            try:
                cached = (path, self._probe(path))
            except Exception:
                cached = (path, None)
            self._probed = cached
        self._queue.put(S.SourceChecked(path, "VALID", cached[1], folder=False))

    @staticmethod
    def _check_folder(path: str) -> S.SourceChecked:
        if not path or os.path.isfile(path):
            return S.SourceChecked(path, "INVALID")
        if not os.path.isdir(path):
            return S.SourceChecked(path, "NOT_FOUND")
        try:
            count = len(RE.find_video_files(path))
        except OSError:
            return S.SourceChecked(path, "NOT_FOUND")
        return S.SourceChecked(path, "VALID" if count else "EMPTY", None, count)

    def _arm(self) -> None:
        try:
            cfg = EncodeConfig.model_validate(F.to_config(S.draft(self.state)))
            ns = cfg.to_namespace()
            err = RE._validate_args_consistency(ns)
            if ns.batch:
                armed = S.Armed(vars(ns), "", False, err)
            else:
                out = D._single_output_path(ns)
                armed = S.Armed(vars(ns), out, os.path.exists(out), err)
        except (ValidationError, ValueError, TypeError) as e:
            armed = S.Armed({}, "", False, str(e))
        if not armed.error:
            self._drop_queued_keys()
        self.state = S.apply(self.state, armed)
        if self.state.screen == S.READY:
            self._ready_at = self._clock()

    def _drop_queued_keys(self) -> None:
        kept = []
        while True:
            try:
                ev = self._queue.get_nowait()
            except queue.Empty:
                break
            if not isinstance(ev, (S.Key, _Arrived)):
                kept.append(ev)
        for ev in kept:
            self._queue.put(ev)

    def _run_tools(self) -> None:
        self._reader.stop()
        self._reader.restore()
        sys.stderr = self._orig_stderr
        sys.stdout = self._orig_stdout
        self._capture.__exit__(None, None, None)
        self._live.stop()
        try:
            self._tools(self._console)
        finally:
            self._live.start()
            self._capture.__enter__()
            sys.stderr = _Sink(self._queue.put)
            sys.stdout = _Sink(self._queue.put)
            self._reader = self._reader_factory(self._emit)
            self._reader.start()

    def _until(self, done: Callable[[S.UIState], bool]) -> None:
        while not done(self.state):
            self._tick()
            if not done(self.state):
                self._sleep(TICK_S)

    def _tick(self) -> None:
        try:
            cpu, ram, used = self._perf()
            self.state = S.apply(self.state, S.Tick(self._clock(), tuple(self._size()), cpu, ram, used))
        except Exception as exc:
            self._internal_error(exc)
        try:
            self._drain()
        except Exception as exc:
            self._internal_error(exc)
        try:
            frame = render(self.state)
        except Exception as exc:
            frame = Panel(Text(f"erro ao desenhar a tela: {exc!r}\no encode continua", style="err"))
        try:
            self._live.update(frame, refresh=True)
        except Exception:
            pass

    def _internal_error(self, exc: Exception) -> None:
        try:
            key = repr(exc)
            if key in self._internal_seen:
                return
            self._internal_seen.add(key)
            self.state = S.internal_warning(self.state, f"erro interno na TUI: {type(exc).__name__}: {exc}")
        except Exception:
            pass

    def _emit(self, ev) -> None:
        self._queue.put(_Arrived(ev, self._clock()) if isinstance(ev, S.Key) else ev)

    def _key_accepted(self, ev: S.Key, now: float) -> bool:
        last, self._last_key_at = self._last_key_at, now
        if ev.name != "ENTER" or self.state.screen != S.READY or not self.state.preset:
            return True
        if self._ready_at is None or now - self._ready_at < READY_HOLD_S:
            return False
        return last is None or now - last >= KEY_GAP_S

    def _drain(self) -> None:
        while True:
            try:
                ev = self._queue.get_nowait()
            except queue.Empty:
                break
            if isinstance(ev, _Arrived):
                ev, ts = ev.key, ev.ts
            elif isinstance(ev, S.Key):
                ts = self._clock()
            if isinstance(ev, S.Key) and not self._key_accepted(ev, ts):
                continue
            self.state = S.apply(self.state, ev)
            if self.state.action == "cancel":
                self.state = replace(self.state, action=None)
                if self._control.request_cancel():
                    self._queue.put(R.Cancel("requested"))
                elif self.state.is_batch:
                    self.state = S.cancel_unavailable(self.state)
            elif self.state.action in S.ACTIONS:
                break
