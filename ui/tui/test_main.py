import argparse
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


def test_fallback_propagates_classic_exit_code(monkeypatch):
    monkeypatch.setattr(M, "get_console", lambda: console())
    monkeypatch.setattr(M, "terminal_ok", lambda *a, **k: False)

    def boom():
        raise SystemExit(2)

    monkeypatch.setattr(RE, "main", boom)
    assert M.main() == 2


def test_launcher_cancel_returns_zero(monkeypatch):
    monkeypatch.setattr(M, "get_console", lambda: console())
    monkeypatch.setattr(M, "terminal_ok", lambda *a, **k: True)
    monkeypatch.setattr(M, "run_launcher", lambda c: None)
    assert M.main() == 0


def test_validation_error_returns_2(monkeypatch):
    monkeypatch.setattr(M, "get_console", lambda: console())
    monkeypatch.setattr(M, "terminal_ok", lambda *a, **k: True)
    monkeypatch.setattr(M, "run_launcher", lambda c: argparse.Namespace(input="x"))
    monkeypatch.setattr(M, "_missing_binaries", lambda: [])
    monkeypatch.setattr(RE, "_validate_args_consistency", lambda ns: "inválido")
    assert M.main() == 2


def test_missing_binaries_returns_1(monkeypatch):
    monkeypatch.setattr(M, "get_console", lambda: console())
    monkeypatch.setattr(M, "terminal_ok", lambda *a, **k: True)
    monkeypatch.setattr(M, "run_launcher", lambda c: argparse.Namespace(input="x"))
    monkeypatch.setattr(M, "_missing_binaries", lambda: ["ffmpeg"])
    assert M.main() == 1


def test_runs_app_and_returns_its_code(monkeypatch):
    monkeypatch.setattr(M, "get_console", lambda: console())
    monkeypatch.setattr(M, "terminal_ok", lambda *a, **k: True)
    monkeypatch.setattr(M, "run_launcher", lambda c: argparse.Namespace(input="x"))
    monkeypatch.setattr(M, "_missing_binaries", lambda: [])
    monkeypatch.setattr(RE, "_validate_args_consistency", lambda ns: None)
    monkeypatch.setattr(M, "App", lambda ns, console=None: types.SimpleNamespace(run=lambda: 130))
    assert M.main() == 130
