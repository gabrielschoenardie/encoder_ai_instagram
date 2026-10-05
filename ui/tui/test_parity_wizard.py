import io
from dataclasses import replace

import pytest
from rich.console import Console

import ui.launcher as L
from ui.config import EncodeConfig
from ui.theme import THEME
from ui.tui import forms as F
from ui.tui import state as S

SCENARIOS = [
    (1, {"Enquadramento": "cover", "FPS": "24", "Modo": "2pass"},
     {"fit": "cover", "fps": "24", "mode": "2pass"}),
    (2, {"Exposure": -0.5, "Satura": 1.2, "Enquadramento": "cover"},
     {"exposure_offset": -0.5, "saturation": 1.2, "fit": "cover"}),
    (5, {"Pipeline Cineon": "on", "Exposure": 0.5, "Satura": 0.8, "Tonemap": "hable"},
     {"cineon_pipeline": "on", "exposure_offset": 0.5, "saturation": 0.8, "tonemap": "hable"}),
    (5, {"Decisões via AI": "on", "MCTF": "on", "Dither": "on"},
     {"enhance_ai": "on", "mctf": "on", "dither": "on"}),
    (5, {"Enhancement engine": "off", "Threads": 4, "Performance": "speed"},
     {"performance": "speed", "enhance": "off", "threads": 4}),
]


def wizard_ns(monkeypatch, preset, path, answers, used):
    def pick(message, default):
        for k, v in answers.items():
            if k in message:
                used.add(k)
                return v
        return default

    monkeypatch.setattr(L, "ask_choice", lambda con, title, options, default=1: preset)
    monkeypatch.setattr(L, "ask_path", lambda con, message, must_exist=True: path)
    monkeypatch.setattr(L, "ask_select", lambda con, message, options, default: pick(message, default))
    monkeypatch.setattr(L, "ask_toggle", lambda con, message, default_on=True: pick(message, "on" if default_on else "off"))
    monkeypatch.setattr(L, "ask_number",
                        lambda con, message, default, lo=None, hi=None, integer=False: pick(message, default))
    monkeypatch.setattr(L, "probe_source_dims", lambda p: None, raising=False)
    monkeypatch.setattr(L.Confirm, "ask",
                        lambda message, *a, **k: True if "Iniciar" in message else k.get("default", False))
    return L.run_launcher(Console(file=io.StringIO(), width=120, theme=THEME))


def press(s, name, ch=None):
    s = S.apply(s, S.Key(name, ch))
    return replace(s, action=None) if s.action == "check_source" else s


def type_text(s, text):
    for ch in text:
        name = "SPACE" if ch == " " else (ch.upper() if ch.lower() in "dlc" else "CHAR")
        s = press(s, name, ch)
    return s


def current(s):
    items = S.form_items(s)
    return items[min(S.focus_of(s, S.focus_key(s)), len(items) - 1)]


def goto_field(s, name):
    if s.screen == S.ADVANCED:
        tab = next(i for i, t in enumerate(F.TABS) if any(f.name == name for f in F.ADVANCED[t]))
        s = replace(s, tab=tab, tab_focus=False)
    s = replace(s, focus=tuple((k, v) for k, v in s.focus if k != S.focus_key(s)))
    for _ in range(len(S.form_items(s))):
        if current(s).name == name:
            return s, current(s)
        s = press(s, "DOWN")
    raise AssertionError(f"campo não alcançado: {name}")


def set_field(s, name, value):
    s, field = goto_field(s, name)
    if field.kind == "number":
        for ch in str(value):
            s = press(s, "CHAR", ch)
        return press(s, "ENTER")
    for _ in range(len(field.options) + 2):
        if S.draft(s)[name] == value:
            return s
        s = press(s, "RIGHT")
    assert S.draft(s)[name] == value, (name, value)
    return s


def tui_ns(preset, path, values):
    s = S.UIState(config={}, screen=S.HOME)
    s = press(s, "CHAR", str(preset))
    s = type_text(s, path)
    s = S.apply(s, S.SourceChecked(path, "VALID"))
    s = press(s, "ENTER")
    for name, value in values.items():
        s = set_field(s, name, value)
    return EncodeConfig.model_validate(S.draft(s)).to_namespace()


@pytest.mark.parametrize("preset,answers,values", SCENARIOS)
def test_tui_form_matches_line_wizard(monkeypatch, tmp_path, preset, answers, values):
    src = tmp_path / "clip.mov"
    src.write_bytes(b"x")
    used = set()
    want = wizard_ns(monkeypatch, preset, str(src), answers, used)
    assert set(answers) == used
    got = tui_ns(preset, str(src), values)
    for k, v in values.items():
        assert getattr(got, k) == v, k
    assert vars(got) == vars(want)
