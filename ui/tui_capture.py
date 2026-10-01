from __future__ import annotations

import re
import threading
import unicodedata
from typing import Callable

import reporter as R

_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
_DROP = {"︎", "️", "‍"}


def strip_symbols(text: str) -> str:
    kept = "".join(
        ch for ch in _ANSI.sub("", text)
        if ch not in _DROP and unicodedata.category(ch) != "So"
    )
    return " ".join(kept.split())


class _Sink:
    def __init__(self, emit: Callable[[R.Info], None]):
        self._emit = emit
        self._buf = ""
        self._lock = threading.Lock()

    def write(self, text: str) -> int:
        with self._lock:
            self._buf += text
            *lines, self._buf = self._buf.split("\n")
        for line in lines:
            clean = strip_symbols(line)
            if clean:
                self._emit(R.Info(clean))
        return len(text)

    def flush(self) -> None:
        pass

    def isatty(self) -> bool:
        return False


class ConsoleCapture:
    def __init__(self, console, emit: Callable[[R.Info], None], width: int = 1000):
        self._console = console
        self._emit = emit
        self._width = width

    def __enter__(self) -> "ConsoleCapture":
        self._orig_file = self._console.file
        self._orig_width = self._console.width
        self._console.file = _Sink(self._emit)
        self._console.width = self._width
        return self

    def __exit__(self, *exc) -> None:
        self._console.file = self._orig_file
        self._console.width = self._orig_width
