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


def test_batch_flow_returns_valid_namespace(monkeypatch):
    monkeypatch.setattr(L, "ask_choice", lambda *a, **k: 3)  # preset 3 = batch
    monkeypatch.setattr(L, "ask_folder", lambda *a, **k: "clips")
    monkeypatch.setattr(L, "ask_toggle", lambda *a, **k: "off")
    calls = {"n": 0}

    def fake_confirm(*a, **k):
        calls["n"] += 1
        return calls["n"] > 1  # "pasta de saída separada?" = No, "Iniciar encode?" = Yes

    monkeypatch.setattr(L, "Confirm", type("C", (), {"ask": staticmethod(fake_confirm)}))

    ns = L.run_launcher(console=_silent_console())
    assert isinstance(ns, argparse.Namespace)
    assert ns.batch == "clips"
    assert ns.cineon_pipeline == "off"


def test_advanced_flow_returns_valid_namespace(monkeypatch):
    monkeypatch.setattr(L, "ask_choice", lambda *a, **k: 5)  # preset 5 = advanced (else branch)
    monkeypatch.setattr(L, "ask_toggle", lambda *a, **k: "off")
    monkeypatch.setattr(L, "ask_select", lambda con, msg, opts, default: default)
    monkeypatch.setattr(L, "ask_number", lambda con, msg, default, **k: default)
    monkeypatch.setattr(L, "ask_path", lambda *a, **k: "clip.mov")
    monkeypatch.setattr(L, "Confirm", type("C", (), {"ask": staticmethod(lambda *a, **k: True)}))

    ns = L.run_launcher(console=_silent_console())
    assert isinstance(ns, argparse.Namespace)
    assert ns.input == "clip.mov"
    assert ns.cineon_pipeline == "off"


def _seq(values):
    it = iter(values)
    return lambda *a, **k: next(it)


def test_advanced_flow_tonemap_options_match_tonemap_algorithms(monkeypatch):
    """BD6b: trava a lista literal do ask_select('Tonemap', ...) contra
    TONEMAP_ALGORITHMS — sem isso, bt2390 poderia voltar só no launcher e
    o CI ficaria verde (EncodeConfig não valida atribuição direta)."""
    import Reels_Encoder_v2_FINAL as R

    recorded = []

    def recording_ask_select(con, msg, opts, default):
        recorded.append((msg, opts))
        return default

    monkeypatch.setattr(L, "ask_choice", lambda *a, **k: 5)  # preset 5 = advanced
    monkeypatch.setattr(L, "ask_toggle", lambda *a, **k: "off")
    monkeypatch.setattr(L, "ask_select", recording_ask_select)
    monkeypatch.setattr(L, "ask_number", lambda con, msg, default, **k: default)
    monkeypatch.setattr(L, "ask_path", lambda *a, **k: "clip.mov")
    monkeypatch.setattr(L, "Confirm", type("C", (), {"ask": staticmethod(lambda *a, **k: True)}))

    ns = L.run_launcher(console=_silent_console())
    assert isinstance(ns, argparse.Namespace)

    tonemap_calls = [opts for msg, opts in recorded if msg == "Tonemap"]
    assert len(tonemap_calls) == 1
    assert set(tonemap_calls[0]) == set(R.TONEMAP_ALGORITHMS)


def _run_advanced_recording_toggles(monkeypatch, enhance_ai):
    prompts = []

    def recording_ask_toggle(con, msg, default_on=False, **k):
        prompts.append(msg)
        if msg.startswith("Enhancement engine"):
            return "on"
        if msg.startswith("Decisões via AI"):
            return enhance_ai
        if msg.startswith("MCTF mask video"):
            return "on"
        return "off"

    monkeypatch.setattr(L, "ask_choice", lambda *a, **k: 5)  # preset 5 = advanced
    monkeypatch.setattr(L, "ask_toggle", recording_ask_toggle)
    monkeypatch.setattr(L, "ask_select", lambda con, msg, opts, default: default)
    monkeypatch.setattr(L, "ask_number", lambda con, msg, default, **k: default)
    monkeypatch.setattr(L, "ask_path", lambda *a, **k: "clip.mov")
    monkeypatch.setattr(L, "Confirm", type("C", (), {"ask": staticmethod(lambda *a, **k: True)}))

    ns = L.run_launcher(console=_silent_console())
    assert isinstance(ns, argparse.Namespace)
    return ns, prompts


def test_advanced_flow_skips_mctf_prompt_when_enhance_ai_off(monkeypatch):
    ns, prompts = _run_advanced_recording_toggles(monkeypatch, "off")
    assert not any(p.startswith("MCTF mask video") for p in prompts)
    assert ns.mctf == "off"


def test_advanced_flow_asks_mctf_prompt_when_enhance_ai_on(monkeypatch):
    ns, prompts = _run_advanced_recording_toggles(monkeypatch, "on")
    assert any(p.startswith("MCTF mask video") for p in prompts)
    assert ns.mctf == "on"


def test_tools_flow_runs_tool_then_returns_to_menu(monkeypatch):
    # main menu -> Tools(4); tools menu -> tool #1; tools menu -> Voltar(5); main menu -> quick(1)
    monkeypatch.setattr(L, "ask_choice", _seq([4, 1, 5, 1]))
    ran = {"cmd": None}

    def fake_run(cmd, cwd=None):
        ran["cmd"] = cmd

    monkeypatch.setattr(L, "subprocess", type("S", (), {"run": staticmethod(fake_run)}))
    monkeypatch.setattr(L, "Prompt", type("P", (), {"ask": staticmethod(lambda *a, **k: "")}))
    monkeypatch.setattr(L, "ask_path", lambda *a, **k: "clip.mov")
    monkeypatch.setattr(L, "ask_select", lambda con, msg, opts, default: default)
    monkeypatch.setattr(L, "Confirm", type("C", (), {"ask": staticmethod(lambda *a, **k: True)}))

    ns = L.run_launcher(console=_silent_console())
    assert ran["cmd"] == L.TOOLS[0][1]
    assert isinstance(ns, argparse.Namespace)  # wizard reached the quick flow after "Voltar"
    assert ns.input == "clip.mov"


def test_tools_flow_subprocess_exception_does_not_crash(monkeypatch):
    monkeypatch.setattr(L, "ask_choice", _seq([4, 1, 5, 1]))

    def boom_run(cmd, cwd=None):
        raise FileNotFoundError("script missing")

    monkeypatch.setattr(L, "subprocess", type("S", (), {"run": staticmethod(boom_run)}))
    monkeypatch.setattr(L, "Prompt", type("P", (), {"ask": staticmethod(lambda *a, **k: "")}))
    monkeypatch.setattr(L, "ask_path", lambda *a, **k: "clip.mov")
    monkeypatch.setattr(L, "ask_select", lambda con, msg, opts, default: default)
    monkeypatch.setattr(L, "Confirm", type("C", (), {"ask": staticmethod(lambda *a, **k: True)}))

    ns = L.run_launcher(console=_silent_console())
    assert isinstance(ns, argparse.Namespace)  # exception was swallowed, wizard kept going
    assert ns.input == "clip.mov"


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
