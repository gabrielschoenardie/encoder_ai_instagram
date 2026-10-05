from ui.tui import state as S
from ui.tui import widgets as W
from ui.tui.test_screens import assert_fits, assert_no_emoji, text_of


def home(**kw):
    return S.UIState(config={}, screen=S.HOME,
                     system=(("FFmpeg", "ffmpeg.exe"), ("ffprobe", "ffprobe.exe"), ("ffplay", "ok"),
                             ("hardware", "detectado no início do encode")), **kw)


def test_home_screen():
    out = text_of(home())
    for txt in ("REELS ENCODER", "Encode rápido (FFmpeg)", "Film look (Cineon)", "Batch de pasta",
                "chega no P3D", "Tools", "Configurar avançado", "O QUE FAZ", "SYSTEM", "ffprobe.exe",
                "detectado no início do encode", "[1-5]"):
        assert txt in out, txt
    assert "▸" in out
    assert_fits(out)
    assert_no_emoji(out)


def test_home_rail_has_no_checks_before_home():
    out = text_of(home())
    assert "✓ HOME" not in out and "✓ SOURCE" not in out


def test_source_screen_states():
    base = S.UIState(config={}, screen=S.SOURCE, preset=1, drafts=((1, {**S.draft(S.UIState(config={}, preset=1))}),),
                     source=W.TextBuf("C:/v/clip.mov", 13))
    for status, txt in (("VALID", "arquivo encontrado"), ("NOT_FOUND", "não encontrado"),
                        ("INVALID", "informe um arquivo"), ("CHECKING", "verificando")):
        out = text_of(S.UIState(**{**base.__dict__, "source_status": status}))
        assert txt in out, status
        assert "clip.mov" in out and "PROGRAM" in out and "ENTER → CONFIGURATION" in out
        assert_fits(out)
        assert_no_emoji(out)
    out = text_of(S.UIState(**{**base.__dict__, "source_status": "VALID", "source_dims": (1080, 1920)}))
    assert "1080 × 1920" in out and "clip_Hollywood" in out


def test_source_preset5_shows_disabled_batch():
    s = S.UIState(config={}, screen=S.SOURCE, preset=5)
    out = text_of(s)
    assert "É um batch de pasta?" in out and "chega no P3D" in out and "ENTER → ADVANCED" in out


def test_path_field_long_path_keeps_cursor_visible():
    buf = W.TextBuf("C:/" + "a" * 200 + "/z.mov", 206)
    txt = __import__("ui.tui.screens", fromlist=["path_field"]).path_field(buf, 60)
    assert len(txt.plain) <= 61 and "z.mov" in txt.plain
