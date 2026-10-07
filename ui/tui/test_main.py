import types

import Reels_Encoder_v2_FINAL as RE
from ui.tui import __main__ as M


class Tty:
    def __init__(self, tty):
        self._tty = tty

    def isatty(self):
        return self._tty


def console(w=120, h=40, terminal=True, legacy=False):
    return types.SimpleNamespace(is_terminal=terminal, legacy_windows=legacy,
                                 size=types.SimpleNamespace(width=w, height=h), print=lambda *a, **k: None)


def test_terminal_ok_rules():
    assert M.terminal_ok(console(), Tty(True), Tty(True))
    assert not M.terminal_ok(console(), Tty(False), Tty(True))
    assert not M.terminal_ok(console(119, 40), Tty(True), Tty(True))
    assert not M.terminal_ok(console(120, 39), Tty(True), Tty(True))
    assert not M.terminal_ok(console(legacy=True), Tty(True), Tty(True))
    assert not M.terminal_ok(console(terminal=False), Tty(True), Tty(True))


def test_fallback_runs_classic_main(monkeypatch):
    called = []
    monkeypatch.setattr(M, "get_console", lambda: console(80, 24))
    monkeypatch.setattr(M, "terminal_ok", lambda *a, **k: False)
    monkeypatch.setattr(RE, "main", lambda: called.append(1))
    assert M.main() == 0 and called == [1]


def _fallback_output(monkeypatch, **console_kwargs):
    printed = []
    con = console(**console_kwargs)
    con.print = lambda *a, **k: printed.append(" ".join(str(x) for x in a))
    monkeypatch.setattr(M, "get_console", lambda: con)
    monkeypatch.setattr(M, "terminal_ok", lambda *a, **k: False)
    monkeypatch.setattr(RE, "main", lambda: None)
    M.main()
    return "\n".join(printed)


def test_fallback_mentions_windows_terminal_on_legacy_console(monkeypatch):
    assert "Windows Terminal" in _fallback_output(monkeypatch, legacy=True)


def test_fallback_omits_windows_terminal_hint_when_not_legacy(monkeypatch):
    assert "Windows Terminal" not in _fallback_output(monkeypatch, w=80, h=24, legacy=False)


def test_fallback_propagates_classic_exit_code(monkeypatch):
    monkeypatch.setattr(M, "get_console", lambda: console())
    monkeypatch.setattr(M, "terminal_ok", lambda *a, **k: False)

    def boom():
        raise SystemExit(2)

    monkeypatch.setattr(RE, "main", boom)
    assert M.main() == 2


def test_missing_binaries_returns_1(monkeypatch):
    monkeypatch.setattr(M, "get_console", lambda: console())
    monkeypatch.setattr(M, "terminal_ok", lambda *a, **k: True)
    monkeypatch.setattr(M, "_missing_binaries", lambda: ["ffmpeg"])
    assert M.main() == 1


def test_runs_app_and_returns_its_code(monkeypatch):
    monkeypatch.setattr(M, "get_console", lambda: console())
    monkeypatch.setattr(M, "terminal_ok", lambda *a, **k: True)
    monkeypatch.setattr(M, "_missing_binaries", lambda: [])
    monkeypatch.setattr(M, "App", lambda console=None: types.SimpleNamespace(run=lambda: 130))
    assert M.main() == 130


def test_main_does_not_use_line_wizard(monkeypatch):
    monkeypatch.setattr(M, "get_console", lambda: console())
    monkeypatch.setattr(M, "terminal_ok", lambda *a, **k: True)
    monkeypatch.setattr(M, "_missing_binaries", lambda: [])
    monkeypatch.setattr(M, "App", lambda console=None: types.SimpleNamespace(run=lambda: 0))
    assert not hasattr(M, "run_launcher")
    assert M.main() == 0
