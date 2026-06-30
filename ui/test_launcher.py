"""Wiring tests for ui.launcher via monkeypatched prompts (no real stdin)."""

import argparse

import ui.launcher as L
from ui.theme import get_console


def _silent_console():
    return get_console(record=True, width=80)


def test_quick_flow_returns_valid_namespace(monkeypatch):
    monkeypatch.setattr(L, "ask_choice", lambda *a, **k: 1)  # preset 1 = quick
    monkeypatch.setattr(L, "ask_path", lambda *a, **k: "clip.mov")
    monkeypatch.setattr(L, "ask_select", lambda con, msg, opts, default: default)
    # Confirm.ask is imported into L's namespace
    monkeypatch.setattr(L, "Confirm", type("C", (), {"ask": staticmethod(lambda *a, **k: True)}))

    ns = L.run_launcher(console=_silent_console())
    assert isinstance(ns, argparse.Namespace)
    assert ns.input == "clip.mov"
    assert ns.cineon_pipeline == "off"
    assert ns.mode == "crf"
    # every engine attribute present
    for attr in ("lut", "loudnorm", "hdr", "tonemap", "fps", "fit", "ebu_meter",
                 "enhance", "enhance_ai", "dither", "show_hardware", "threads"):
        assert hasattr(ns, attr)


def test_cineon_flow(monkeypatch):
    monkeypatch.setattr(L, "ask_choice", lambda *a, **k: 2)  # preset 2 = cineon
    monkeypatch.setattr(L, "ask_path", lambda *a, **k: "clip.mov")
    monkeypatch.setattr(L, "ask_number", lambda con, msg, default, **k: default)
    monkeypatch.setattr(L, "ask_select", lambda con, msg, opts, default: default)
    monkeypatch.setattr(L, "Confirm", type("C", (), {"ask": staticmethod(lambda *a, **k: True)}))

    ns = L.run_launcher(console=_silent_console())
    assert ns.cineon_pipeline == "on"


def test_eof_during_prompt_returns_none(monkeypatch):
    # Closing stdin (Ctrl-D / piped EOF) must cancel cleanly, not crash.
    def boom(*a, **k):
        raise EOFError

    monkeypatch.setattr(L, "ask_choice", boom)
    ns = L.run_launcher(console=_silent_console())
    assert ns is None


def test_keyboardinterrupt_during_prompt_returns_none(monkeypatch):
    # Ctrl-C must cancel cleanly, not propagate a traceback.
    def boom(*a, **k):
        raise KeyboardInterrupt

    monkeypatch.setattr(L, "ask_choice", boom)
    ns = L.run_launcher(console=_silent_console())
    assert ns is None


def test_cancel_returns_none(monkeypatch):
    monkeypatch.setattr(L, "ask_choice", lambda *a, **k: 1)
    monkeypatch.setattr(L, "ask_path", lambda *a, **k: "clip.mov")
    monkeypatch.setattr(L, "ask_select", lambda con, msg, opts, default: default)
    # First Confirm (start?) = False, second (review?) = False -> cancel
    calls = {"n": 0}

    def fake_ask(*a, **k):
        calls["n"] += 1
        return False

    monkeypatch.setattr(L, "Confirm", type("C", (), {"ask": staticmethod(fake_ask)}))
    ns = L.run_launcher(console=_silent_console())
    assert ns is None
