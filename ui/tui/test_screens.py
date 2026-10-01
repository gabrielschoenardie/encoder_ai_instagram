import re
import unicodedata

from ui.theme import get_console
from ui.tui import screens as V
from ui.tui import state as S

CFG = {"input": "C:/v/clip_final.mov", "mode": "crf", "cineon_pipeline": "off", "fps": 30, "fit": "contain",
       "scale": "auto", "lut": "on", "hdr": "auto", "tonemap": "mobius", "loudnorm": "on", "enhance": "on",
       "enhance_ai": "off", "mctf": "off", "dither": "auto", "performance": "balanced", "threads": 0,
       "report": "on", "ebu_meter": "on"}


def text_of(state, width=120, height=40):
    con = get_console(record=True, width=width, height=height, force_terminal=True, color_system="truecolor")
    con.print(V.render(state))
    return con.export_text()


def assert_fits(out):
    for line in out.splitlines():
        assert len(line.rstrip()) <= 120, line


def assert_no_emoji(out):
    allowed = set("✓⚠✗●▸★█░▎▓○⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏─│╭╮╰╯═║╔╗╚╝┌┐└┘├┤┬┴┼━┃")
    for ch in out:
        if unicodedata.category(ch) == "So" and ch not in allowed:
            raise AssertionError(f"símbolo não permitido: {ch!r}")


def st(**kw):
    return S.UIState(config=dict(CFG), output_path="C:/v/clip_final_Hollywood_CRF18.mp4", **kw)


def test_ready_screen():
    out = text_of(st())
    assert "REELS ENCODER" in out and "READY TO ENCODE" in out
    assert "clip_final.mov" in out and "clip_final_Hollywood_CRF18.mp4" in out
    for region in ("KEY SETTINGS", "PIPELINE PLAN", "QC / DELIVERY", "START ENCODE"):
        assert region in out
    assert "passe único CRF" in out and "loudness" in out
    assert re.search(r"\[ENTER\].*\[ESC\]", out)
    assert_fits(out)
    assert_no_emoji(out)


def test_ready_plan_two_pass_and_cineon():
    two = text_of(S.UIState(config={**CFG, "mode": "2pass"}, output_path="o.mp4"))
    assert "PASS 1 / 2 + PASS 2 / 2" in two
    cin = text_of(S.UIState(config={**CFG, "cineon_pipeline": "on"}, output_path="o.mp4"))
    assert "FILM RENDER" in cin and "Cineon Film" in cin


def test_ready_report_off_says_certificate_disabled():
    out = text_of(S.UIState(config={**CFG, "report": "off"}, output_path="o.mp4"))
    assert "certificado desativado" in out


def test_small_terminal_notice():
    out = text_of(st(size=(100, 30)), width=100, height=30)
    assert "terminal pequeno" in out and "120×40" in out and "100×30" in out
    assert "READY TO ENCODE" not in out
