from __future__ import annotations

import shutil
import sys

import Reels_Encoder_v2_FINAL as RE
from ui import components as C
from ui.theme import get_console
from ui.tui.app import App
from ui.tui.state import MIN_SIZE


def terminal_ok(console, stdin=None, stdout=None) -> bool:
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    return (stdin.isatty() and stdout.isatty() and console.is_terminal and not console.legacy_windows
            and console.size.width >= MIN_SIZE[0] and console.size.height >= MIN_SIZE[1])


def _missing_binaries() -> list:
    try:
        from ui.preflight import missing_ffmpeg_binaries

        return list(missing_ffmpeg_binaries() or [])
    except Exception:
        return [name for name in ("ffmpeg", "ffprobe") if shutil.which(name) is None]


def _exit_code(exc: SystemExit) -> int:
    if exc.code is None:
        return 0
    return exc.code if isinstance(exc.code, int) else 1


def main() -> int:
    console = get_console()
    if not terminal_ok(console):
        console.print("[warn]A TUI precisa de um terminal interativo com VT e pelo menos 120×40 — "
                      "abrindo o modo clássico.[/warn]")
        try:
            RE.main()
        except SystemExit as exc:
            return _exit_code(exc)
        return 0
    missing = _missing_binaries()
    if missing:
        console.print(C.dependency_error_card(missing))
        return 1
    return App(console=console).run()


if __name__ == "__main__":
    sys.exit(main())
