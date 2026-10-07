
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


def test_home_navigation_visits_all_presets_and_wraps():
    s = home()
    assert s.home_focus == 0
    for want in (1, 2, 3, 4, 0):
        s = S.apply(s, key("DOWN"))
        assert s.home_focus == want
    s = S.apply(home(), key("UP"))
    assert s.home_focus == 4


def test_home_digits_open_presets():
    s = S.apply(home(), key("CHAR", "3"))
    assert s.screen == S.SOURCE and s.preset == 3 and S.draft(s) == F.new_draft(3)
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


def test_esc_from_preview_after_revisar_escapes_to_origin():
    s = at_config(1)
    s = S.apply(S.apply(S.apply(s, key("ENTER")), key("ENTER")), key("ENTER"))
    s = S.apply(S.apply(s, key("RIGHT")), key("ENTER"))
    assert s.screen == S.ADVANCED
    while focused(s) is not F.CONTINUE:
        s = S.apply(s, key("DOWN"))
    s = S.apply(s, key("ENTER"))
    assert s.screen == S.PREVIEW
    s = S.apply(s, key("ESC"))
    assert s.screen == S.CONFIGURATION
    s = S.apply(s, key("ESC"))
    assert s.screen == S.SOURCE
    s = S.apply(s, key("ESC"))
    assert s.screen == S.HOME


def test_advanced_enter_on_last_field_walks_tabs_then_preview():
    s = at_config(5)
    for tab in range(len(F.TABS)):
        assert s.screen == S.ADVANCED and s.tab == tab and not s.tab_focus
        assert S.focus_of(s, S.focus_key(s)) == 0
        while S.form_items(s)[S.focus_of(s, S.focus_key(s)) + 1] is not F.CONTINUE:
            s = S.apply(s, key("ENTER"))
        s = S.apply(s, key("ENTER"))
    assert s.screen == S.PREVIEW


def test_advanced_continue_action_on_first_tab_goes_to_preview():
    s = at_config(5)
    while focused(s) is not F.CONTINUE:
        s = S.apply(s, key("DOWN"))
    s = S.apply(s, key("ENTER"))
    assert s.screen == S.PREVIEW and s.tab == 0


def test_advanced_enter_on_cineon_color_tab_moves_to_audio():
    s = at_config(5)
    s = S.apply(s, key("SPACE"))
    s = S.apply(S.apply(S.apply(s, key("ENTER")), key("ENTER")), key("ENTER"))
    s = S.apply(S.apply(S.apply(s, key("ENTER")), key("ENTER")), key("ENTER"))
    assert s.tab == 1 and focused(s).name == "exposure_offset"
    s = S.apply(S.apply(s, key("CHAR", "1")), key("ENTER"))
    s = S.apply(S.apply(s, key("ENTER")), key("ENTER"))
    assert focused(s).name == "tonemap"
    s = S.apply(s, key("ENTER"))
    assert s.screen == S.ADVANCED and s.tab == 2 and focused(s).name == "loudnorm"


def test_advanced_threads_commit_on_last_tab_goes_to_preview():
    from dataclasses import replace
    s = replace(at_config(5), tab=4)
    s = S.apply(s, key("DOWN"))
    assert focused(s).name == "threads"
    s = S.apply(S.apply(s, key("CHAR", "4")), key("ENTER"))
    assert s.screen == S.PREVIEW and S.draft(s)["threads"] == 4


def test_up_down_clear_field_error():
    s = at_config(2)
    s = S.apply(S.apply(s, key("CHAR", "3")), key("ENTER"))
    assert s.field_error == "Máximo é 2."
    assert S.apply(s, key("DOWN")).field_error is None
    s = S.apply(S.apply(S.apply(s, key("DOWN")), key("CHAR", "3")), key("ENTER"))
    assert s.field_error == "Máximo é 2."
    assert S.apply(s, key("UP")).field_error is None


def test_down_from_tab_bar_lands_on_first_field():
    from dataclasses import replace
    s = replace(at_config(5), focus=((f"{S.ADVANCED}:0", 6),), tab_focus=True)
    s = S.apply(s, key("DOWN"))
    assert not s.tab_focus and focused(s).name == "cineon_pipeline"


def test_esc_preset5_after_revisar_escapes_to_source_and_home():
    s = at_config(5)
    assert s.screen == S.ADVANCED
    while focused(s) is not F.CONTINUE:
        s = S.apply(s, key("DOWN"))
    s = S.apply(s, key("ENTER"))
    assert s.screen == S.PREVIEW and s.came_from == S.ADVANCED
    s = S.apply(S.apply(s, key("RIGHT")), key("ENTER"))
    assert s.screen == S.ADVANCED and s.adv_back == S.PREVIEW
    s = S.apply(s, key("ESC"))
    assert s.screen == S.PREVIEW
    s = S.apply(s, key("ESC"))
    assert s.screen == S.ADVANCED
    s = S.apply(s, key("ESC"))
    assert s.screen == S.SOURCE
    s = S.apply(s, key("ESC"))
    assert s.screen == S.HOME


def at_folder(preset=3, path="C:/v/lote", count=3):
    from dataclasses import replace
    s = S.apply(home(), key("CHAR", str(preset)))
    if preset == 5:
        s = S.apply(S.apply(S.apply(s, key("UP")), key("RIGHT")), key("DOWN"))
    s = replace(type_text(s, path), action=None)
    s = S.apply(s, S.SourceChecked(path, "VALID", None, count))
    return S.apply(s, key("ENTER"))


def test_preset3_opens_folder_source_and_routes_to_configuration():
    s = S.apply(home(), key("CHAR", "3"))
    assert s.screen == S.SOURCE and F.is_folder(S.draft(s)) and not s.tab_focus
    s = type_text(s, "C:/v/lote")
    assert s.action == "check_source" and s.source_status == "CHECKING" and s.source_count is None
    s = S.apply(s, S.SourceChecked("C:/v/lote", "VALID", None, 3))
    assert s.source_status == "VALID" and s.source_count == 3
    s = S.apply(s, key("ENTER"))
    assert s.screen == S.CONFIGURATION
    assert S.draft(s)["batch"] == "C:/v/lote" and S.draft(s)["input"] is None


def test_empty_folder_blocks_enter():
    s = type_text(S.apply(home(), key("CHAR", "3")), "C:/v/vazia")
    s = S.apply(s, S.SourceChecked("C:/v/vazia", "EMPTY", None, 0))
    assert s.source_status == "EMPTY" and s.source_count == 0
    assert S.apply(s, key("ENTER")).screen == S.SOURCE


def test_preset5_tipo_switches_kind_and_keeps_other_edits():
    from dataclasses import replace
    s = S.apply(home(), key("CHAR", "5"))
    s = replace(s, drafts=((5, {**S.draft(s), "fps": "60"}),))
    s = replace(type_text(s, "C:/v/lote"), action=None)
    s = S.apply(s, key("UP"))
    assert s.tab_focus and s.screen == S.SOURCE
    assert S.apply(s, key("CHAR", "x")) == s
    s = S.apply(s, key("RIGHT"))
    d = S.draft(s)
    assert F.is_folder(d) and d["batch"] == "C:/v/lote" and d["input"] is None and d["fps"] == "60"
    assert s.source_status == "CHECKING" and s.action == "check_source"
    s = S.apply(replace(s, action=None), key("LEFT"))
    d = S.draft(s)
    assert not F.is_folder(d) and d["input"] == "C:/v/lote" and d["batch"] is None and d["fps"] == "60"
    s = S.apply(s, key("DOWN"))
    assert not s.tab_focus
    assert S.apply(s, key("CHAR", "x")).source.text == "C:/v/lotex"


def test_preset5_tipo_with_empty_path_is_invalid_without_check():
    s = S.apply(S.apply(S.apply(home(), key("CHAR", "5")), key("UP")), key("SPACE"))
    assert F.is_folder(S.draft(s)) and s.source_status == "INVALID" and s.action is None


def test_preset5_folder_advanced_source_tab_starts_with_outdir_toggle():
    s = at_folder(5)
    assert s.screen == S.ADVANCED and not s.tab_focus and s.adv_back == S.SOURCE
    assert [f.name for f in S.form_items(s)][:2] == [F.OUTDIR_ON, "cineon_pipeline"]
    assert S.draft(s)["batch"] == "C:/v/lote" and S.draft(s)["input"] is None


def test_source_esc_remembers_folder():
    s = type_text(S.apply(home(), key("CHAR", "3")), "C:/v/lote")
    s = S.apply(s, key("ESC"))
    assert s.screen == S.HOME and S.draft(s)["batch"] == "C:/v/lote"
    s = S.apply(s, key("CHAR", "3"))
    assert s.source.text == "C:/v/lote" and s.action == "check_source"


def test_batch_form_outdir_toggle_shows_path_field():
    s = at_folder(3)
    assert [f.name for f in S.form_items(s)] == [F.OUTDIR_ON, "cineon_pipeline", "__continue__"]
    s = S.apply(s, key("SPACE"))
    assert S.draft(s)[F.OUTDIR_ON] == "on"
    assert [f.name for f in S.form_items(s)] == [F.OUTDIR_ON, "output_dir", "cineon_pipeline", "__continue__"]


def test_outdir_empty_blocks_with_inline_error_cleared_on_focus_change():
    s = S.apply(S.apply(at_folder(3), key("SPACE")), key("DOWN"))
    assert focused(s).name == "output_dir"
    s = S.apply(s, key("ENTER"))
    assert s.screen == S.CONFIGURATION and s.field_error == F.OUTDIR_EMPTY and focused(s).name == "output_dir"
    s = S.apply(s, key("DOWN"))
    assert s.field_error is None and focused(s).name == "cineon_pipeline"
    s = S.apply(S.apply(s, key("DOWN")), key("ENTER"))
    assert s.screen == S.CONFIGURATION and s.field_error == F.OUTDIR_EMPTY and focused(s).name == "output_dir"
    assert S.apply(s, key("UP")).field_error is None


def test_outdir_typing_hotkey_letters_and_commit():
    s = S.apply(S.apply(at_folder(3), key("SPACE")), key("DOWN"))
    s = type_text(s, "D:/clips/lote")
    assert s.edit.text == "D:/clips/lote" and s.modal is None and s.screen == S.CONFIGURATION
    s = S.apply(s, key("ENTER"))
    assert S.draft(s)["output_dir"] == "D:/clips/lote" and s.edit is None and focused(s).name == "cineon_pipeline"
    assert F.to_config(S.draft(s))["output_dir"] == "D:/clips/lote"
    s = S.apply(S.apply(S.apply(s, key("UP")), key("UP")), key("SPACE"))
    assert S.draft(s)[F.OUTDIR_ON] == "off"
    assert F.to_config(S.draft(s))["output_dir"] is None and S.draft(s)["output_dir"] == "D:/clips/lote"


def test_outdir_edit_esc_cancels_and_quoted_empty_commit_errors():
    s = S.apply(S.apply(at_folder(3), key("SPACE")), key("DOWN"))
    s = S.apply(type_text(s, "X:/a"), key("ESC"))
    assert s.edit is None and S.draft(s)["output_dir"] is None and s.screen == S.CONFIGURATION
    s = S.apply(type_text(s, '""'), key("ENTER"))
    assert s.field_error == F.OUTDIR_EMPTY and S.draft(s)["output_dir"] is None and s.edit is None


def test_advanced_folder_enter_walks_tabs_with_outdir_then_preview():
    s = S.apply(at_folder(5), key("SPACE"))
    s = S.apply(type_text(S.apply(s, key("DOWN")), "D:/saida"), key("ENTER"))
    assert focused(s).name == "cineon_pipeline" and s.tab == 0
    tabs = []
    for _ in range(60):
        if s.screen != S.ADVANCED:
            break
        tabs.append(s.tab)
        s = S.apply(s, key("ENTER"))
    assert s.screen == S.PREVIEW and S.draft(s)["output_dir"] == "D:/saida"
    assert tabs == sorted(tabs) and set(tabs) == {0, 1, 2, 3, 4}


def test_advanced_continue_with_empty_outdir_jumps_back_to_source_tab():
    from dataclasses import replace
    s = replace(S.apply(at_folder(5), key("SPACE")), tab=4)
    while focused(s) is not F.CONTINUE:
        s = S.apply(s, key("DOWN"))
    s = S.apply(s, key("ENTER"))
    assert s.screen == S.ADVANCED and s.tab == 0 and not s.tab_focus
    assert focused(s).name == "output_dir" and s.field_error == F.OUTDIR_EMPTY


def test_esc_chain_preset3_after_revisar_never_loops():
    s = at_folder(3)
    while focused(s) is not F.CONTINUE:
        s = S.apply(s, key("DOWN"))
    s = S.apply(s, key("ENTER"))
    assert s.screen == S.PREVIEW and s.came_from == S.CONFIGURATION
    s = S.apply(S.apply(s, key("RIGHT")), key("ENTER"))
    assert s.screen == S.ADVANCED and s.adv_back == S.PREVIEW
    assert S.form_items(s)[0].name == F.OUTDIR_ON
    while focused(s) is not F.CONTINUE:
        s = S.apply(s, key("DOWN"))
    s = S.apply(s, key("ENTER"))
    assert s.screen == S.PREVIEW
    for want in (S.CONFIGURATION, S.SOURCE, S.HOME):
        s = S.apply(s, key("ESC"))
        assert s.screen == want
    assert S.draft(s)["batch"] == "C:/v/lote"


def test_esc_chain_preset5_folder_after_revisar_never_loops():
    s = at_folder(5)
    while focused(s) is not F.CONTINUE:
        s = S.apply(s, key("DOWN"))
    s = S.apply(s, key("ENTER"))
    assert s.screen == S.PREVIEW and s.came_from == S.ADVANCED
    s = S.apply(S.apply(s, key("RIGHT")), key("ENTER"))
    assert s.screen == S.ADVANCED and s.adv_back == S.PREVIEW
    for want in (S.PREVIEW, S.ADVANCED, S.SOURCE, S.HOME):
        s = S.apply(s, key("ESC"))
        assert s.screen == want
    assert F.is_folder(S.draft(s))
