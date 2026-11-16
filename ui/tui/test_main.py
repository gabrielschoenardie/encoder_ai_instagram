import types

import pytest

import Reels_Encoder_v2_FINAL as RE
from ui.config import EncodeConfig
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
    assert M.terminal_ok(console(100, 30), Tty(True), Tty(True))
    assert M.terminal_ok(console(80, 24), Tty(True), Tty(True))
    assert not M.terminal_ok(console(79, 24), Tty(True), Tty(True))
    assert not M.terminal_ok(console(80, 23), Tty(True), Tty(True))
    assert not M.terminal_ok(console(), Tty(False), Tty(True))
    assert not M.terminal_ok(console(), Tty(True), Tty(False))
    assert not M.terminal_ok(console(legacy=True), Tty(True), Tty(True))
    assert not M.terminal_ok(console(terminal=False), Tty(True), Tty(True))


def _refused(monkeypatch, **console_kwargs):
    printed = []
    con = console(**console_kwargs)
    con.print = lambda *a, **k: printed.append(" ".join(str(x) for x in a))
    monkeypatch.setattr(M, "get_console", lambda: con)
    monkeypatch.setattr(M, "terminal_ok", lambda *a, **k: False)

    def no_classic():
        raise AssertionError("RE.main chamado")

    monkeypatch.setattr(RE, "main", no_classic)
    return M.main(), "\n".join(printed)


def test_terminal_refused_prints_error_and_returns_1_without_classic_mode(monkeypatch):
    code, out = _refused(monkeypatch, w=70, h=20)
    assert code == 1
    assert "80×24" in out and "clássico" not in out


def test_terminal_refused_mentions_windows_terminal_on_legacy_console(monkeypatch):
    assert "Windows Terminal" in _refused(monkeypatch, legacy=True)[1]


def test_terminal_refused_omits_windows_terminal_hint_when_not_legacy(monkeypatch):
    assert "Windows Terminal" not in _refused(monkeypatch, w=80, h=24, legacy=False)[1]


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


def test_engine_main_without_job_opens_tui_and_exits_with_its_code(monkeypatch):
    calls = []
    monkeypatch.setattr(RE, "parse_cli", lambda: EncodeConfig().to_namespace())
    monkeypatch.setattr("ui.preflight.missing_ffmpeg_binaries", lambda *a, **k: [])
    monkeypatch.setattr(M, "main", lambda: calls.append("tui") or 7)
    with pytest.raises(SystemExit) as exc:
        RE.main()
    assert calls == ["tui"] and exc.value.code == 7


def test_engine_cli_no_longer_accepts_ui_flag():
    with pytest.raises(SystemExit) as exc:
        RE.parse_cli(["--ui"])
    assert exc.value.code == 2


def test_main_does_not_use_line_wizard(monkeypatch):
    monkeypatch.setattr(M, "get_console", lambda: console())
    monkeypatch.setattr(M, "terminal_ok", lambda *a, **k: True)
    monkeypatch.setattr(M, "_missing_binaries", lambda: [])
    monkeypatch.setattr(M, "App", lambda console=None: types.SimpleNamespace(run=lambda: 0))
    assert not hasattr(M, "run_launcher")
    assert M.main() == 0
