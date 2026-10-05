
from ui.tui import forms as F
from ui.tui import state as S


def home():
    return S.UIState(config={}, screen=S.HOME)


def key(name, char=None):
    return S.Key(name, char)


def type_text(s, text):
    for ch in text:
        name = "SPACE" if ch == " " else (ch.upper() if ch.lower() in "dlc" else "CHAR")
        s = S.apply(s, key(name, ch))
    return s


def test_home_navigation_skips_batch_and_wraps():
    s = home()
    assert s.home_focus == 0
    s = S.apply(s, key("DOWN"))
    assert s.home_focus == 1
    s = S.apply(s, key("DOWN"))
    assert s.home_focus == 3
    s = S.apply(s, key("UP"))
    assert s.home_focus == 1
    s = S.apply(home(), key("UP"))
    assert s.home_focus == 4


def test_home_digits_and_disabled_batch():
    assert S.apply(home(), key("CHAR", "3")) == home()
    s = S.apply(home(), key("CHAR", "4"))
    assert s.action == "tools" and s.screen == S.HOME
    s = S.apply(home(), key("CHAR", "2"))
    assert s.screen == S.SOURCE and s.preset == 2
    assert S.draft(s) == F.new_draft(2)
    s = S.apply(home(), key("ESC"))
    assert s.action == "exit" and s.exit_code == 0


def test_source_typing_hotkey_letters_inserts_chars():
    s = S.apply(home(), key("ENTER"))
    s = type_text(s, "C:\\dlc.mov")
    assert s.source.text == "C:\\dlc.mov"
    assert s.screen == S.SOURCE and s.modal is None
    assert s.action == "check_source" and s.source_status == "CHECKING"


def test_source_enter_requires_valid_then_routes_by_preset():
    s = type_text(S.apply(home(), key("ENTER")), "a.mov")
    assert S.apply(s, key("ENTER")).screen == S.SOURCE
    s = S.apply(s, S.SourceChecked("a.mov", "VALID", (1080, 1920)))
    assert s.source_dims == (1080, 1920)
    s = S.apply(s, key("ENTER"))
    assert s.screen == S.CONFIGURATION and S.draft(s)["input"] == "a.mov"
    s5 = type_text(S.apply(home(), key("CHAR", "5")), "b.mov")
    s5 = S.apply(S.apply(s5, S.SourceChecked("b.mov", "VALID")), key("ENTER"))
    assert s5.screen == S.ADVANCED and s5.adv_back == S.SOURCE


def test_stale_source_check_ignored():
    s = type_text(S.apply(home(), key("ENTER")), "a.mo")
    s = type_text(s, "v")
    s = S.apply(s, S.SourceChecked("a.mo", "VALID"))
    assert s.source_status == "CHECKING"
    s = S.apply(s, S.SourceChecked("a.mov", "NOT_FOUND"))
    assert s.source_status == "NOT_FOUND"


def test_source_quoted_path_matches_check():
    s = type_text(S.apply(home(), key("ENTER")), '"C:\\Meus Vídeos\\x.mov"')
    s = S.apply(s, S.SourceChecked("C:\\Meus Vídeos\\x.mov", "VALID"))
    assert s.source_status == "VALID"
    s = S.apply(s, key("ENTER"))
    assert S.draft(s)["input"] == "C:\\Meus Vídeos\\x.mov"


def test_source_esc_back_home_and_draft_remembered():
    s = type_text(S.apply(home(), key("ENTER")), "a.mov")
    s = S.apply(s, key("ESC"))
    assert s.screen == S.HOME and S.draft(s)["input"] == "a.mov"
    s = S.apply(s, key("ENTER"))
    assert s.source.text == "a.mov" and s.action == "check_source"


def test_armed_and_ready_blocked_and_ready_esc():
    s = S.UIState(config={}, screen=S.PREVIEW, preset=1)
    bad = S.apply(s, S.Armed({}, "", False, error="inválido"))
    assert bad.screen == S.PREVIEW and bad.field_error == "inválido"
    ok = S.apply(s, S.Armed({"input": "a.mov"}, "a_out.mp4", True))
    assert ok.screen == S.READY and ok.config == {"input": "a.mov"} and ok.output_preexisted
    blocked = S.apply(ok, S.ReadyBlocked("arquivo de entrada não encontrado: a.mov"))
    assert blocked.screen == S.READY and blocked.ready_error and blocked.action is None
    assert S.apply(ok, key("ESC")).screen == S.PREVIEW
    legacy = S.UIState(config={"input": "x"}, screen=S.READY)
    assert S.apply(legacy, key("ESC")).action == "exit"


def at_config(preset=1, path="a.mov"):
    s = S.apply(home(), key("CHAR", str(preset)))
    s = type_text(s, path)
    s = S.apply(s, S.SourceChecked(path, "VALID"))
    return S.apply(s, key("ENTER"))


def focused(s):
    return S.form_items(s)[min(S.focus_of(s, S.focus_key(s)), len(S.form_items(s)) - 1)]


def test_configuration_quick_choices_and_continue():
    s = at_config(1)
    assert [f.name for f in S.form_items(s)] == ["fit", "fps", "mode", "__continue__"]
    s = S.apply(s, key("RIGHT"))
    assert S.draft(s)["fit"] == "cover"
    s = S.apply(s, key("DOWN"))
    s = S.apply(s, key("LEFT"))
    assert S.draft(s)["fps"] == "25"
    s = S.apply(s, key("ENTER"))
    assert focused(s).name == "mode"
    s = S.apply(s, key("ENTER"))
    assert s.screen == S.PREVIEW and s.came_from == S.CONFIGURATION


def test_number_typing_commit_and_errors():
    s = at_config(2)
    s = S.apply(s, key("CHAR", "-"))
    s = type_text(s, "0.5")
    assert s.edit.text == "-0.5"
    s = S.apply(s, key("ENTER"))
    assert S.draft(s)["exposure_offset"] == -0.5 and s.edit is None
    assert focused(s).name == "saturation"


def test_number_out_of_range_keeps_value_and_shows_error():
    s = at_config(2)
    s = S.apply(s, key("CHAR", "5"))
    s = S.apply(s, key("ENTER"))
    assert S.draft(s)["exposure_offset"] == 0.0
    assert s.field_error == "Máximo é 2."
    s = S.apply(s, key("CHAR", "x"))
    assert s.edit is None
    s = S.apply(s, key("CHAR", "1"))
    s = S.apply(s, key("ESC"))
    assert s.edit is None and S.draft(s)["exposure_offset"] == 0.0 and s.screen == S.CONFIGURATION


def test_number_arrows_step():
    s = at_config(2)
    s = S.apply(s, key("RIGHT"))
    assert S.draft(s)["exposure_offset"] == 0.1


def test_esc_back_to_source_keeps_draft_and_focus_restored():
    s = at_config(1)
    s = S.apply(S.apply(s, key("DOWN")), key("RIGHT"))
    s = S.apply(s, key("ESC"))
    assert s.screen == S.SOURCE
    s = S.apply(s, key("ENTER"))
    assert s.screen == S.CONFIGURATION and focused(s).name == "fps" and S.draft(s)["fps"] == "60"


def test_advanced_tabs_two_level_focus():
    s = at_config(5)
    assert s.screen == S.ADVANCED and not s.tab_focus and focused(s).name == "cineon_pipeline"
    s = S.apply(s, key("UP"))
    assert s.tab_focus
    s = S.apply(s, key("RIGHT"))
    assert F.TABS[s.tab] == "Color/LUT"
    s = S.apply(s, key("DOWN"))
    assert not s.tab_focus and focused(s).name == "lut"
    s = S.apply(s, key("UP"))
    s = S.apply(s, key("LEFT"))
    assert F.TABS[s.tab] == "Source"


def test_focus_clamped_after_visibility_change():
    from dataclasses import replace
    s = at_config(5)
    s = S.apply(s, key("SPACE"))
    assert S.draft(s)["cineon_pipeline"] == "on"
    s = replace(s, tab=1, focus=s.focus + ((f"{S.ADVANCED}:1", 4),))
    assert focused(s) is F.CONTINUE
    s = replace(s, tab=0)
    s = S.apply(s, key("SPACE"))
    assert S.draft(s)["cineon_pipeline"] == "off"
    s = replace(s, tab=1)
    assert len(S.form_items(s)) == 4 and focused(s) is F.CONTINUE
    s = S.apply(s, key("ENTER"))
    assert s.screen == S.PREVIEW


def test_enhance_off_hides_ai_and_ai_off_forces_mctf_off():
    s = at_config(5)
    s = S.apply(s, key("UP"))
    for _ in range(3):
        s = S.apply(s, key("RIGHT"))
    assert F.TABS[s.tab] == "Enhance"
    s = S.apply(s, key("DOWN"))
    s = S.apply(s, key("DOWN"))
    s = S.apply(s, key("SPACE"))
    assert S.draft(s)["enhance_ai"] == "on"
    s = S.apply(s, key("DOWN"))
    s = S.apply(s, key("SPACE"))
    assert S.draft(s)["mctf"] == "on"
    s = S.apply(s, key("UP"))
    s = S.apply(s, key("SPACE"))
    assert S.draft(s)["enhance_ai"] == "off" and S.draft(s)["mctf"] == "off"


def test_preview_actions():
    s = at_config(1)
    s = S.apply(S.apply(S.apply(s, key("ENTER")), key("ENTER")), key("ENTER"))
    assert s.screen == S.PREVIEW
    assert S.apply(s, key("ENTER")).action == "arm"
    rev = S.apply(S.apply(s, key("RIGHT")), key("ENTER"))
    assert rev.screen == S.ADVANCED and rev.adv_back == S.PREVIEW and rev.tab == 0
    assert S.apply(rev, key("ESC")).screen == S.PREVIEW
    assert S.apply(s, key("ESC")).screen == S.CONFIGURATION
