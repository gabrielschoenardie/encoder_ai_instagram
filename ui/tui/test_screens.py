import re
import unicodedata

import reporter as R
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


def encoding_state():
    s = S.UIState(config={**CFG, "mode": "2pass"}, output_path="C:/v/clip_final_Hollywood_2Pass.mp4",
                  screen=S.ENCODING, now=200.0)
    for ev in (R.Stage(R.PREPARING, ts=100.0), R.Hardware({"tier": "high", "cpu_threads": 16}, ts=100.1),
               R.Stage(R.PROBING, ts=100.2), R.Probe(60.0, 1800, 30, 1080, 1920, False, ts=100.3),
               R.EncodeParams("long", 7500, 8500, 11475, 0.9, "slow", "2pass", ts=100.4),
               R.Stage(R.PASS, "1", ts=101.0), R.Pass(1, 2, "Pass 1", "start", ts=101.0),
               R.Pass(1, 2, "Pass 1", "end", ts=173.0), R.Stage(R.PASS, "2", ts=173.5),
               R.Pass(2, 2, "Pass 2", "start", ts=173.5),
               R.Progress(1152, 1800, 28.4, 0.95, "00:00:41", 125.0, ts=199.0),
               R.Info("Aviso: ffprobe falhou, usando duração padrão 30s", ts=199.1),
               R.FfmpegLine("frame= 1152 fps= 28 q=24.0", ts=199.2)):
        s = S.apply(s, ev)
    return S.apply(s, S.Tick(200.0, (120, 40), cpu=71.0, ram=48.0, ram_used_gb=7.8))


def test_encoding_dashboard():
    out = text_of(encoding_state())
    for txt in ("ENCODING", "PASS 1 / 2", "ANÁLISE", "PASS 2 / 2", "ENCODE FINAL", "100.0%", "ETA 00:00:41",
                "PROGRAM", "TIMELINE", "PERFORMANCE", "LOG", "1152 / 1800", "0.95x", "tier", "high",
                "⚠ 1", "[D] Details", "[C] Cancel"):
        assert txt in out, txt
    assert "✓ 00:01:12" in out
    assert_fits(out)
    assert_no_emoji(out)


def test_encoding_blocked_c_shows_disabled():
    s = S.apply(encoding_state(), R.Stage(R.ANALYZING, "mctf_mask", ts=201.0))
    assert "░[C]" in text_of(s)


def test_cancel_modal_over_dashboard():
    s = S.apply(encoding_state(), S.Key("C"))
    out = text_of(s)
    assert "CANCELAR ENCODE?" in out and "CONTINUAR ENCODE" in out and "CANCELAR ENCODE ]" in out
    assert "⚠ CANCEL?" in out and "PASS 2 / 2" in out and "LOG" in out
    assert_fits(out)


def test_details_screen():
    out = text_of(S.apply(encoding_state(), S.Key("D")))
    for txt in ("SOURCE", "HARDWARE", "ENCODING", "CONFIG", "OUTPUT", "PROGRESS",
                "1080", "1920", "long", "7500", "8500", "11475", "DET", "CALC", "CFG", "LIVE"):
        assert txt in out, txt
    assert_fits(out)


def test_details_without_events_shows_dash():
    s = S.UIState(config=dict(CFG), output_path="o.mp4", screen=S.DETAILS)
    out = text_of(s)
    assert "—" in out


def test_log_screen_filters():
    s = S.apply(encoding_state(), S.Key("L"))
    out = text_of(s)
    for tab in S.LOG_FILTERS:
        assert tab in out
    assert "ffprobe falhou" in out and "frame= 1152" in out
    s = S.apply(s, S.Key("RIGHT"))
    s = S.apply(s, S.Key("RIGHT"))
    s = S.apply(s, S.Key("RIGHT"))
    out = text_of(s)
    assert "ffprobe falhou" in out and "frame= 1152" not in out
    assert_fits(out)
