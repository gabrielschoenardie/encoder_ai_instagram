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
_ANSI = {"[A": "UP", "[B": "DOWN", "[C": "RIGHT", "[D": "LEFT", "[3~": "DELETE"}
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
        return _ANSI.get(seq[1:])
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


_MODIFIER_VKS = frozenset({0x10, 0x11, 0x12, 0x14, 0x90, 0x91})


def _pending_is_extended() -> bool:
    try:
        import ctypes
        from ctypes import wintypes

        class _Key(ctypes.Structure):
            _fields_ = [
                ("down", wintypes.BOOL), ("repeat", wintypes.WORD), ("vk", wintypes.WORD),
                ("scan", wintypes.WORD), ("char", wintypes.WCHAR), ("ctrl", wintypes.DWORD),
            ]

        class _Rec(ctypes.Structure):
            _fields_ = [("type", wintypes.WORD), ("pad", wintypes.WORD), ("key", _Key)]

        k32 = ctypes.windll.kernel32
        k32.GetStdHandle.restype = wintypes.HANDLE
        handle = k32.GetStdHandle(-10)
        buf = (_Rec * 16)()
        n = wintypes.DWORD()
        if not k32.PeekConsoleInputW(handle, buf, 16, ctypes.byref(n)):
            return True
        for rec in buf[: n.value]:
            if rec.type == 1 and rec.key.down and rec.key.vk not in _MODIFIER_VKS:
                return rec.key.char == "\0"
    except Exception:
        pass
    return True


def _windows_loop(reader: KeyReader) -> None:
    import msvcrt

    while not reader._stop.is_set():
        if msvcrt.kbhit():
            extended = _pending_is_extended()
            ch = msvcrt.getwch()
            if ch == "\xe0" and not extended:
                reader._put(_plain(ch), ch)
                continue
            nxt = msvcrt.getwch() if ch in ("\x00", "\xe0") else None
            reader._put(decode_windows(ch, nxt), ch)
        else:
            time.sleep(0.05)


def _read_posix_seq(read: Callable[[int], bytes], ready: Callable[[float], bool]) -> str:
    first = read(1)
    if first == b"\x1b":
        data = first
        if ready(0.03):
            data += read(1)
            if data[-1:] in (b"[", b"O"):
                for _ in range(16):
                    if not ready(0.03):
                        break
                    byte = read(1)
                    data += byte
                    if not byte or 0x40 <= byte[0] <= 0x7E:
                        break
        return data.decode("utf-8", "ignore")
    if first and first[0] >= 0xC0:
        extra = 1 if first[0] < 0xE0 else 2 if first[0] < 0xF0 else 3
        first += read(extra)
    return first.decode("utf-8", "ignore")


def _posix_loop(reader: KeyReader) -> None:
    import select

    fd = sys.stdin.fileno()

    def ready(timeout: float) -> bool:
        return bool(select.select([fd], [], [], timeout)[0])

    while not reader._stop.is_set():
        if not ready(0.05):
            continue
        seq = _read_posix_seq(lambda n: os.read(fd, n), ready)
        reader._put(decode_posix(seq), seq if len(seq) == 1 else None)
