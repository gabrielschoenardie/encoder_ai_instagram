import dataclasses

import pytest

import reporter as R
from ui.tui import state as S


def _s(**kw):
    cfg = {"input": "in.mov", "mode": "2pass", "cineon_pipeline": "off"}
    return S.UIState(config=cfg, output_path="out.mp4", **kw)


def _run(s, *evs):
    for ev in evs:
        s = S.apply(s, ev)
    return s


def test_state_is_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        _s().screen = "X"


def test_ready_enter_starts_and_esc_exits_zero():
    s = S.apply(_s(), S.Key("ENTER"))
    assert s.screen == S.ENCODING and s.action == "start"
    s = S.apply(_s(), S.Key("ESC"))
    assert s.action == "exit" and s.exit_code == 0


def test_unmapped_keys_ignored():
    s = _s(screen=S.ENCODING)
    assert S.apply(s, S.Key("X")) == s
    assert S.apply(_s(), S.Key("D")) == _s()


def test_stage_flow_marks_done_and_logs_system():
    s = _run(_s(screen=S.ENCODING),
             R.Stage(R.PREPARING, ts=1.0), R.Stage(R.PROBING, ts=2.0), R.Stage(R.PASS, "1", ts=3.0))
    assert (s.stage, s.substep) == (R.PASS, "1")
    assert s.stages_done == (R.PREPARING, R.PROBING)
    assert s.job_started == 1.0
    assert [r.kind for r in s.log] == ["SYSTEM"] * 3


def test_stage_qc_switches_screen_and_closes_modal():
    s = _s(screen=S.ENCODING, modal="CANCEL")
    s = S.apply(s, R.Stage(R.QC, ts=5.0))
    assert s.screen == S.QC and s.modal is None


def test_pass_tracks_keep_pass1_and_end_is_100():
    s = _run(_s(screen=S.ENCODING),
             R.Pass(1, 2, "Pass 1", "start", ts=10.0),
             R.Progress(50, 100, 25.0, 1.0, "00:00:02", 2.0, ts=11.0),
             R.Pass(1, 2, "Pass 1", "end", ts=14.0),
             R.Pass(2, 2, "Pass 2", "start", ts=14.5),
             R.Progress(10, 100, 25.0, 1.0, "00:00:04", 0.4, ts=15.0))
    p1, p2 = s.passes
    assert p1.done and p1.pct == 100.0 and p1.seconds == pytest.approx(4.0)
    assert not p2.done and p2.pct == pytest.approx(10.0) and p2.eta == "00:00:04"
    assert S.active_pass(s) is p2


def test_c_opens_modal_and_confirm_requests_cancel_once():
    s = _run(_s(screen=S.ENCODING), R.Stage(R.PASS, "1", ts=1.0), S.Key("C"))
    assert s.modal == "CANCEL" and s.modal_focus == 0
    s = S.apply(s, S.Key("ENTER"))
    assert s.modal is None and s.action is None
    s = _run(s, S.Key("C"), S.Key("RIGHT"), S.Key("ENTER"))
    assert s.action == "cancel" and s.modal is None


def test_double_enter_in_modal_single_cancel():
    s = _run(_s(screen=S.ENCODING), R.Stage(R.PASS, "1", ts=1.0),
             S.Key("C"), S.Key("RIGHT"), S.Key("ENTER"))
    s2 = S.apply(s, S.Key("ENTER"))
    assert s.action == "cancel"
    assert s2.modal is None and s2.action == "cancel"


def test_esc_closes_modal_without_cancel():
    s = _run(_s(screen=S.ENCODING), R.Stage(R.PASS, "1", ts=1.0), S.Key("C"), S.Key("ESC"))
    assert s.modal is None and s.action is None


@pytest.mark.parametrize("stage", [R.Stage(R.ANALYZING, "mctf_mask", ts=1.0), R.Stage(R.QC, ts=1.0)])
def test_c_ignored_when_blocked(stage):
    s = _run(_s(screen=S.ENCODING), stage)
    assert S.cancel_blocked(s)
    assert S.apply(s, S.Key("C")).modal is None


def test_events_after_cancel_ignored():
    s = _run(_s(screen=S.ENCODING), R.Stage(R.PASS, "1", ts=1.0), R.Cancel("requested", ts=2.0))
    s2 = _run(s, R.Stage(R.QC, ts=3.0), R.Progress(5, 10, 1.0, 1.0, "x", 1.0, ts=3.1))
    assert s2.stage == R.PASS and s2.screen == S.ENCODING and s2.cancel_phase == "requested"


def test_cancel_cleaned_records_partial_removed():
    s = _run(_s(screen=S.ENCODING), R.Cancel("requested", ts=1.0), R.Cancel("cleaned", True, ts=2.0))
    assert s.cancel_phase == "cleaned" and s.partial_removed is True


def test_info_warning_classification_and_ffmpeg_cr():
    s = _run(_s(screen=S.ENCODING),
             R.Info("Aviso: ffprobe falhou, usando duração padrão 30s", ts=1.0),
             R.Info("LUT Portra 400 carregada", ts=1.1),
             R.Info("MCTF falhou: [Errno 22]", ts=1.2),
             R.FfmpegLine("frame=1 fps=1\rframe=2 fps=2\r", ts=1.3))
    assert [r.kind for r in s.log] == ["WARNING", "INFO", "WARNING", "FFMPEG"]
    assert s.warnings == 2
    assert s.log[-1].text == "frame=2 fps=2"


def test_log_filter_cycles_with_left_right():
    s = _run(_s(screen=S.ENCODING), R.Info("a", ts=1.0), R.FfmpegLine("f", ts=1.1), S.Key("L"))
    assert s.screen == S.LOG and s.back == S.ENCODING
    s = _run(s, S.Key("RIGHT"))
    assert S.LOG_FILTERS[s.log_filter] == "SYSTEM"
    s = _run(s, S.Key("RIGHT"), S.Key("RIGHT"), S.Key("RIGHT"))
    assert [r.text for r in S.filtered_log(s)] == ["f"]
    assert S.apply(s, S.Key("ESC")).screen == S.ENCODING


def test_details_toggle_and_payload_events():
    s = _run(_s(screen=S.ENCODING),
             R.Hardware({"tier": "high"}, ts=1.0),
             R.Probe(30.0, 900, 30, 1080, 1920, False, ts=1.1),
             R.EncodeParams("short", 9800, 11000, 14850, 0.9, "slow", "2pass", ts=1.2),
             S.Key("D"))
    assert s.screen == S.DETAILS and s.hardware == {"tier": "high"}
    assert s.probe.width == 1080 and s.encode_params.vbv_key == "short"
    assert S.apply(s, S.Key("D")).screen == S.ENCODING


def test_finished_paths():
    base = _s(screen=S.ENCODING)
    assert S.apply(base, S.Finished(0)).screen == S.COMPLETED
    assert S.apply(base, S.Finished(130)).screen == S.CANCELLED
    assert S.apply(base, S.Finished(1)).screen == S.ERROR
    assert S.apply(base, S.Finished(2)).screen == S.ERROR
    s = _run(base, S.Key("D"), S.Finished(1))
    assert s.screen == S.ERROR


def test_seal_reveal_then_completed():
    payload = {"summary": {"ready": True}, "checks": []}
    s = _run(_s(screen=S.ENCODING), R.Stage(R.QC, ts=1.0), R.Qc(payload, ts=2.0),
             S.Tick(2.1, (120, 40)), S.Finished(0))
    assert s.screen == S.QC and s.seal_reveal_start == 2.1
    s = S.apply(s, S.Tick(2.5, (120, 40)))
    assert s.screen == S.QC
    s = S.apply(s, S.Tick(2.2 + S.SEAL_REVEAL_S, (120, 40)))
    assert s.screen == S.COMPLETED


def test_final_actions_and_exit():
    s = S.apply(_s(screen=S.ENCODING, qc={"summary": {}}), S.Finished(0))
    s = S.apply(s, S.Tick(9.0, (120, 40)))
    s = S.apply(s, S.Tick(99.0, (120, 40)))
    assert s.screen == S.COMPLETED
    assert S.final_actions(s) == ("SAIR", "VER QC", "VER LOG")
    v = _run(s, S.Key("RIGHT"), S.Key("ENTER"))
    assert v.screen == S.QC and v.back == S.COMPLETED
    assert S.apply(v, S.Key("ESC")).screen == S.COMPLETED
    e = S.apply(s, S.Key("ENTER"))
    assert e.action == "exit"
    assert S.final_actions(S.apply(_s(screen=S.ENCODING), S.Finished(1))) == ("SAIR", "VER LOG")


def _error_state(n_lines):
    tail = "\n".join(f"linha {i}" for i in range(n_lines))
    s = _run(_s(screen=S.ENCODING), R.Error("FFmpegError", "boom", tail, 1, None))
    return S.apply(s, S.Finished(1))


def test_error_scroll_bounds():
    s = _error_state(25)
    s = _run(s, S.Key("UP"))
    assert s.error_scroll == 0
    s = _run(s, S.Key("DOWN"), S.Key("DOWN"))
    assert s.error_scroll == 2


def test_error_scroll_has_upper_limit():
    s = _error_state(30)
    s = _run(s, *[S.Key("DOWN")] * 100)
    assert s.error_scroll == 30 - S.ERROR_ROWS
    assert _run(s, S.Key("UP")).error_scroll == 30 - S.ERROR_ROWS - 1


def test_error_scroll_stays_zero_when_stderr_fits():
    s = _run(_error_state(5), S.Key("DOWN"), S.Key("DOWN"))
    assert s.error_scroll == 0


def test_cancel_requested_logged_once():
    s = _run(_s(screen=S.ENCODING), R.Cancel("requested", ts=1.0), R.Cancel("requested", ts=1.5))
    assert [r.text for r in s.log].count("CANCEL · requested") == 1


def test_tick_records_size_and_perf():
    s = S.apply(_s(), S.Tick(3.0, (100, 30), cpu=12.0, ram=40.0, ram_used_gb=6.5))
    assert s.size == (100, 30) and s.now == 3.0 and s.cpu == 12.0 and s.ram_used_gb == 6.5


def test_removal_failed_only_from_driver_warning():
    s = _run(_s(screen=S.ENCODING), R.Cancel("requested", ts=1.0), R.Cancel("cleaned", False, ts=2.0))
    assert s.removal_failed is False and s.output_preexisted is False
    s = S.apply(s, R.Info("NÃO foi possível remover out.mp4", ts=3.0))
    assert s.removal_failed is True


def test_seal_reveal_tolerates_float_error():
    payload = {"summary": {"ready": True}, "checks": []}
    s = _run(_s(screen=S.ENCODING), R.Stage(R.QC, ts=300.0), R.Qc(payload, ts=301.0),
             S.Tick(301.0, (120, 40)), S.Finished(0))
    s = S.apply(s, S.Tick(301.0 + S.SEAL_REVEAL_S, (120, 40)))
    assert s.screen == S.COMPLETED
    assert S.seal_revealed(s)
    assert not S.seal_revealed(dataclasses.replace(s, now=301.5))
