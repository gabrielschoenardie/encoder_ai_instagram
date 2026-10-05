
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
