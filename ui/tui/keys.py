from __future__ import annotations

import os
import sys
import threading
import time
from typing import Callable

from ui.tui.state import Key

_CHARS = {"\r": "ENTER", "\n": "ENTER", "\x1b": "ESC", " ": "SPACE", "\x08": "BACKSPACE", "\x7f": "BACKSPACE"}
_HOTKEYS = {"d": "D", "l": "L", "c": "C"}
_WIN_EXT = {"H": "UP", "P": "DOWN", "K": "LEFT", "M": "RIGHT", "S": "DELETE"}
_ANSI = {"[A": "UP", "[B": "DOWN", "[C": "RIGHT", "[D": "LEFT"}
_WITH_CHAR = frozenset({"CHAR", "SPACE", "D", "L", "C"})


def _plain(ch: str) -> str | None:
    if not ch:
        return None
    if ch in _CHARS:
        return _CHARS[ch]
    if ch.lower() in _HOTKEYS:
        return _HOTKEYS[ch.lower()]
    if len(ch) == 1 and ch.isprintable():
        return "CHAR"
    return None


def decode_windows(ch: str, nxt: str | None = None) -> str | None:
    if ch in ("\x00", "\xe0"):
        return _WIN_EXT.get(nxt or "")
    return _plain(ch)


def decode_posix(seq: str) -> str | None:
    if seq.startswith("\x1b") and len(seq) > 1:
        return _ANSI.get(seq[1:3])
    return _plain(seq)


class KeyReader:
    def __init__(self, emit: Callable[[Key], None]):
        self._emit = emit
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._restore: Callable[[], None] | None = None

    def start(self) -> None:
        if os.name != "nt" and sys.stdin.isatty():
            import termios
            import tty

            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            tty.setcbreak(fd)
            self._restore = lambda: termios.tcsetattr(fd, termios.TCSADRAIN, old)
        try:
            import msvcrt

            while msvcrt.kbhit():
                msvcrt.getwch()
        except Exception:
            pass
        self._thread = threading.Thread(target=_reader_loop, args=(self,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)

    def restore(self) -> None:
        if self._restore is not None:
            self._restore()
            self._restore = None

    def _put(self, name: str | None, raw: str | None = None) -> None:
        if name is not None:
            self._emit(Key(name, raw if name in _WITH_CHAR else None))


def _reader_loop(reader: KeyReader) -> None:
    try:
        if os.name == "nt":
            _windows_loop(reader)
        else:
            _posix_loop(reader)
    except Exception:
        return


def _windows_loop(reader: KeyReader) -> None:
    import msvcrt

    while not reader._stop.is_set():
        if msvcrt.kbhit():
            ch = msvcrt.getwch()
            nxt = msvcrt.getwch() if ch in ("\x00", "\xe0") else None
            reader._put(decode_windows(ch, nxt), ch)
        else:
            time.sleep(0.05)


def _posix_loop(reader: KeyReader) -> None:
    import select

    fd = sys.stdin.fileno()
    while not reader._stop.is_set():
        ready, _, _ = select.select([fd], [], [], 0.05)
        if not ready:
            continue
        seq = os.read(fd, 1).decode("utf-8", "ignore")
        if seq == "\x1b":
            more, _, _ = select.select([fd], [], [], 0.03)
            if more:
                seq += os.read(fd, 2).decode("utf-8", "ignore")
        reader._put(decode_posix(seq), seq if len(seq) == 1 else None)
