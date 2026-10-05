from ui.tui import forms as F
from ui.tui import state as S
from ui.tui import widgets as W
from ui.tui.test_screens import assert_fits, text_of
from ui.tui.test_screens import assert_no_emoji as _assert_no_emoji


def assert_no_emoji(out):
    _assert_no_emoji(out.replace("◂", "").replace("▶", ""))


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


def cfg_state(preset=1, **kw):
    d = {**F.new_draft(preset), "input": "C:/v/clip.mov"}
    return S.UIState(config={}, screen=kw.pop("screen", S.CONFIGURATION), preset=preset, drafts=((preset, d),), **kw)


def test_configuration_quick():
    out = text_of(cfg_state(1))
    for txt in ("Enquadramento", "FPS", "Modo", "◂ contain ▸", "CONTINUAR", "PADRÕES", "loudnorm"):
        assert txt in out, txt
    assert_fits(out)
    assert_no_emoji(out)


def test_configuration_cineon_numbers_and_error():
    s = cfg_state(2, field_error="Máximo é 2.")
    out = text_of(s)
    assert "+0.0" in out and "1.00" in out and "Máximo é 2." in out


def test_configuration_number_edit_shows_buffer():
    s = cfg_state(2, edit=W.TextBuf("-0.7", 4))
    assert "-0.7" in text_of(s)


def test_advanced_each_tab():
    for i, tab in enumerate(F.TABS):
        s = cfg_state(5, screen=S.ADVANCED, tab=i)
        out = text_of(s)
        for t in F.TABS:
            assert t in out
        for f in F.visible(F.ADVANCED[tab], S.draft(s)):
            assert f.label.split(" (")[0] in out, f.label
        assert "SETTINGS" in out and "Pipeline" in out
        assert_fits(out)
        assert_no_emoji(out)
    focused_bar = text_of(cfg_state(5, screen=S.ADVANCED, tab_focus=True))
    assert "▎▸Source" in focused_bar


def test_preview_rows_and_chips():
    d = {**F.new_draft(5), "cineon_pipeline": "on", "exposure_offset": 0.5, "saturation": 0.8}
    rows = dict(__import__("ui.tui.screens", fromlist=["preview_rows"]).preview_rows(d))
    assert list(rows)[:9] == ["Pipeline", "Mode", "FPS", "Scale / Fit", "LUT", "HDR", "Tonemap", "Audio", "Performance"]
    assert rows["Exposure / Sat"] == "+0.5 EV · 0.80"
    chips = dict(__import__("ui.tui.screens", fromlist=["preview_chips"]).preview_chips(d))
    assert list(chips) == ["LUT", "Loudnorm", "Enhance", "AI", "MCTF", "Dither", "EBU Meter"]


def test_preview_screen_and_error():
    s = cfg_state(1, screen=S.PREVIEW, field_error="combinação inválida")
    out = text_of(s)
    for txt in ("PREVIEW", "EXPORT SETTINGS", "CONTINUAR", "REVISAR", "combinação inválida", "LUT", "EBU Meter"):
        assert txt in out, txt
    assert_fits(out)
    assert_no_emoji(out)


def test_ready_shows_ready_error():
    s = S.UIState(config={"input": "C:/v/clip.mov", "mode": "crf", "cineon_pipeline": "off"}, screen=S.READY,
                  preset=1, output_path="C:/v/o.mp4", ready_error="arquivo de entrada não encontrado: C:/v/clip.mov")
    assert "arquivo de entrada não encontrado" in text_of(s)
