import re
import unicodedata
from dataclasses import replace

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


PAYLOAD = {
    "checks": [{"label": "Container", "value": "mp4", "passed": True},
               {"label": "Loudness", "value": "-14.0 LUFS", "passed": True},
               {"label": "Resolution", "value": "1080x1920", "passed": None}],
    "summary": {"passed": 2, "warnings": 1, "failed": 0, "ready": True},
    "audio": {"before": {"I": -20.1, "TP": -3.0, "LRA": 7.0}, "after": {"I": -14.0, "TP": -1.6, "LRA": 6.0}},
    "targets": {"I": -14.0, "TP": -1.5, "LRA": None},
    "output": {"size_human": "38.2 MB"}, "encode": {"duration_human": "00:03:17"},
    "video": {"codec": "h264", "width": 1080, "height": 1920, "fps": 30.0},
}


def qc_state(reveal_done: bool, ready=True):
    payload = {**PAYLOAD, "summary": {**PAYLOAD["summary"], "ready": ready}}
    s = encoding_state()
    s = S.apply(s, R.Stage(R.QC, ts=300.0))
    s = S.apply(s, R.Qc(payload, ts=301.0))
    s = S.apply(s, S.Tick(301.0, (120, 40)))
    if reveal_done:
        s = S.apply(s, S.Tick(301.0 + S.SEAL_REVEAL_S, (120, 40)))
    return s


def test_qc_before_and_after_reveal():
    before = text_of(qc_state(False))
    assert "EBU R128" in before and "MASTER QC" in before and "verificando" in before
    assert "-14.0" in before and "-20.1" in before
    after = text_of(qc_state(True))
    assert "D E L I V E R Y   R E A D Y" in after
    assert "░[C]" in after
    assert_fits(after)
    assert_no_emoji(after)


def test_qc_review_seal():
    assert "R E V I S A R   E N T R E G A" in text_of(qc_state(True, ready=False))


def test_completed_screen():
    s = S.apply(qc_state(True), S.Finished(0))
    s = S.apply(s, S.Tick(400.0, (120, 40)))
    assert s.screen == S.COMPLETED
    out = text_of(s)
    for txt in ("ENCODE COMPLETE", "DELIVERY READY", "OUTPUT", "38.2 MB", "00:03:17", "SAIR", "VER QC", "VER LOG"):
        assert txt in out, txt
    assert_fits(out)
    assert_no_emoji(out)


def test_completed_report_off():
    s = S.UIState(config={**CFG, "report": "off"}, output_path="o.mp4", screen=S.COMPLETED, exit_code=0, qc=PAYLOAD)
    assert "certificado desativado" in text_of(s)


def test_error_screen_handles_bytes_and_none_stderr():
    base = S.apply(encoding_state(), R.Error("CalledProcessError", "ffmpeg saiu com 1",
                                             b"linha a\r\nlinha b\xff\n", 1, None, ts=250.0))
    out = text_of(S.apply(base, S.Finished(1)))
    assert "ffmpeg saiu com código 1" in out and "linha a" in out and "linha b" in out
    assert "FFMPEG STDERR" in out and "ESTADO" in out and "SAIR" in out
    none_err = S.apply(encoding_state(), R.Error("RuntimeError", "x", None, None, "tb", ts=250.0))
    out = text_of(S.apply(none_err, S.Finished(1)))
    assert "frame= 1152" in out
    assert_fits(out)


def test_error_without_error_event_uses_exit_code():
    out = text_of(S.apply(encoding_state(), S.Finished(2)))
    assert "código 2" in out


def test_cancelled_screen_partial_results():
    base = S.apply(encoding_state(), R.Cancel("requested", ts=250.0))
    removed = S.apply(S.apply(base, R.Cancel("cleaned", True, ts=251.0)), S.Finished(130))
    assert "Encode interrompido pelo usuário" in text_of(removed)
    assert "output parcial removido" in text_of(removed)
    kept = S.apply(S.apply(base, R.Cancel("cleaned", False, ts=251.0)), S.Finished(130))
    assert "NÃO foi possível remover" not in text_of(kept)
    none = S.apply(base, S.Finished(130))
    out = text_of(none)
    assert "nenhum output parcial" in out
    assert_fits(out)


def cancelled_state(*evs, preexisted=False):
    s = S.apply(encoding_state(), R.Cancel("requested", ts=250.0))
    s = replace(s, output_preexisted=preexisted)
    for ev in evs:
        s = S.apply(s, ev)
    return S.apply(s, S.Finished(130))


def test_cancelled_wording_partial_removed():
    out = text_of(cancelled_state(R.Cancel("cleaned", True, ts=251.0)))
    assert "output parcial removido: clip_final_Hollywood_2Pass.mp4" in out


def test_cancelled_wording_removal_failed():
    out = text_of(cancelled_state(R.Cancel("cleaned", False, ts=251.0),
                                  R.Info("NÃO foi possível remover clip_final_Hollywood_2Pass.mp4", ts=251.1)))
    assert "NÃO foi possível remover clip_final_Hollywood_2Pass.mp4" in out and "apague à mão" in out


def test_cancelled_wording_no_file_written_is_not_an_alarm():
    out = text_of(cancelled_state(R.Cancel("cleaned", False, ts=251.0)))
    assert "nenhum output parcial" in out and "apague à mão" not in out
    assert_fits(out)


def test_cancelled_wording_preexisting_output_kept():
    out = text_of(cancelled_state(R.Cancel("terminated", ts=251.0), preexisted=True))
    assert ("o arquivo existente foi mantido: clip_final_Hollywood_2Pass.mp4 "
            "(pode ter sido sobrescrito em parte)") in out
    assert "nenhum output parcial" not in out
    assert_fits(out)


def test_error_long_message_keeps_layout():
    argv = "Command '['ffmpeg', '-y', '-i', 'C:/v/clip_final.mov', " + "'-x264-params', 'a=b:c=d', " * 60
    msg = (argv + "]' returned non-zero exit status 1.\n") * 3
    msg = (msg + "\n" + "z" * 3000)[:3000]
    s = S.apply(encoding_state(), R.Error("CalledProcessError", msg, b"linha a\nlinha b\n", 1, None, ts=250.0))
    out = text_of(S.apply(s, S.Finished(1)))
    assert "CalledProcessError: ffmpeg saiu com código 1" in out
    for txt in ("FFMPEG STDERR", "ESTADO", "SAIR", "linha a"):
        assert txt in out, txt
    assert "-x264-params" not in out
    assert_fits(out)
    lines = out.splitlines()
    assert len(lines) == 40 and "[ESC] Sair" in "\n".join(lines[-3:])


def test_error_message_without_returncode_is_first_line_truncated():
    s = st(screen=S.ERROR, exit_code=1, error=R.Error("RuntimeError", "y" * 300 + "\nsegunda", None, None, None))
    assert V.error_message(s) == "RuntimeError: " + "y" * 200 + "…"
    short = st(screen=S.ERROR, exit_code=1, error=R.Error("validation", "modo inválido", None, None, None))
    assert V.error_message(short) == "validation: modo inválido"


def test_cancel_requested_header_status_and_footer():
    s = S.apply(encoding_state(), R.Cancel("requested", ts=250.0))
    out = text_of(s)
    assert "⚠ CANCELAMENTO SOLICITADO · encerrando FFmpeg…" in out
    assert "⚠ CANCELANDO" in out and "░[C] Cancel" in out
    assert_fits(out)
    assert_no_emoji(out)


def footer_of(out):
    return "\n".join(out.splitlines()[-3:])


def test_footer_modal_keys():
    foot = footer_of(text_of(S.apply(encoding_state(), S.Key("C"))))
    assert "[←→] Choose   [ENTER] Confirm   [ESC] Keep encoding   [Ctrl+C] Interrupt" in foot
    assert "[D] Details" not in foot


def test_footer_overlays_from_final_screen():
    done = S.apply(S.apply(qc_state(True), S.Finished(0)), S.Tick(400.0, (120, 40)))
    qc = S.apply(S.apply(done, S.Key("RIGHT")), S.Key("ENTER"))
    assert qc.screen == S.QC
    foot = footer_of(text_of(qc))
    assert "[ESC] Voltar" in foot and "[D]" not in foot and "[C]" not in foot and "Ctrl+C" not in foot
    log = S.apply(S.apply(S.apply(done, S.Key("RIGHT")), S.Key("RIGHT")), S.Key("ENTER"))
    assert log.screen == S.LOG
    foot = footer_of(text_of(log))
    assert "[←→] Filtro" in foot and "[ESC] Voltar" in foot and "[D]" not in foot and "Ctrl+C" not in foot
    det = S.apply(log, S.Key("D"))
    assert det.screen == S.DETAILS
    foot = footer_of(text_of(det))
    assert "[ESC] Voltar" in foot and "[L]" not in foot and "Ctrl+C" not in foot


def test_cineon_crf_film_render_rail_and_title():
    s = S.UIState(config={**CFG, "cineon_pipeline": "on"}, output_path="C:/v/clip_final_Cineon_Film.mp4",
                  screen=S.ENCODING, now=10.0)
    for ev in (R.Stage(R.PREPARING, ts=1.0), R.Stage(R.PROBING, ts=2.0), R.Stage(R.PASS, "1", ts=3.0),
               R.Pass(1, 1, "Cineon", "start", ts=3.0)):
        s = S.apply(s, ev)
    rail = V.stage_rail(s).plain
    assert "FILM RENDER" in rail and "PASS 1" not in rail
    assert "ENCODING · FILM LOOK (CINEON)" in text_of(s)


def test_stage_rail_done_by_order():
    s = S.UIState(config={**CFG, "cineon_pipeline": "on"}, output_path="o.mp4", screen=S.ENCODING)
    for ev in (R.Stage(R.PREPARING, ts=1.0), R.Stage(R.ANALYZING, "preflight", ts=2.0), R.Stage(R.PROBING, ts=3.0)):
        s = S.apply(s, ev)
    rail = V.stage_rail(s).plain
    assert "✓ PREPARING" in rail and "✓ ANALYZING" not in rail and "○ ANALYZING" in rail
