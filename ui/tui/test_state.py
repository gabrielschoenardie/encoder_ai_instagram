import dataclasses
from dataclasses import replace

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


def test_stage_qc_switches_screen():
    s = _s(screen=S.ENCODING)
    s = S.apply(s, R.Stage(R.QC, ts=5.0))
    assert s.screen == S.QC


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


@pytest.mark.parametrize("screen", [S.ENCODING, S.QUEUE])
def test_c_in_encoding_and_queue_changes_nothing(screen):
    s = _run(_s(screen=screen, is_batch=screen == S.QUEUE), R.Stage(R.PASS, "1", ts=1.0))
    for ch in ("C", "c"):
        s2 = S.apply(s, S.Key("CHAR", ch))
        assert s2 == s and s2.action is None
    s2 = S.apply(s, S.Key("C"))
    assert s2 == s and s2.action is None


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


def test_master_kept_only_from_driver_info():
    s = _run(_s(screen=S.ENCODING), R.Cancel("requested", ts=1.0), R.Cancel("cleaned", False, ts=2.0))
    assert s.master_kept is False
    s = S.apply(s, R.Info("Master mantido — QC não concluído.", ts=3.0))
    assert s.master_kept is True


def test_kept_unvalidated_from_driver_infos():
    from ui import tui_driver as D
    base = _run(_s(screen=S.ENCODING), R.Cancel("requested", ts=1.0), R.Cancel("terminated", ts=2.0))
    assert base.kept_unvalidated is False
    s = S.apply(base, R.Info(D.TEMP_PRESENT_MSG.format(name="out.mp4", temp="out_temp.mp4"), ts=3.0))
    assert s.kept_unvalidated is True
    s = S.apply(base, R.Info(D.WORKER_STUCK_MSG.format(n=D.WORKER_WAIT_S, name="out.mp4"), ts=3.0))
    assert s.kept_unvalidated is True


def test_seal_reveal_tolerates_float_error():
    payload = {"summary": {"ready": True}, "checks": []}
    s = _run(_s(screen=S.ENCODING), R.Stage(R.QC, ts=300.0), R.Qc(payload, ts=301.0),
             S.Tick(301.0, (120, 40)), S.Finished(0))
    s = S.apply(s, S.Tick(301.0 + S.SEAL_REVEAL_S, (120, 40)))
    assert s.screen == S.COMPLETED
    assert S.seal_revealed(s)
    assert not S.seal_revealed(dataclasses.replace(s, now=301.5))


SMALL = (79, 24)


@pytest.mark.parametrize("screen", [S.HOME, S.SOURCE, S.CONFIGURATION, S.ADVANCED, S.PREVIEW, S.READY])
def test_keys_ignored_below_min_size_without_running_encode(screen):
    s = _s(screen=screen, preset=1, size=SMALL)
    for name, ch in (("DOWN", None), ("ENTER", None), ("ESC", None), ("CHAR", "1"), ("C", None)):
        assert S.apply(s, S.Key(name, ch)) == s


@pytest.mark.parametrize("screen", [S.COMPLETED, S.ERROR, S.CANCELLED, S.REPORT])
def test_keys_ignored_below_min_size_on_final_screens(screen):
    s = _s(screen=screen, exit_code=0, size=SMALL)
    for name in ("ENTER", "ESC", "RIGHT", "DOWN"):
        assert S.apply(s, S.Key(name)) == s


def test_keys_on_home_work_again_at_min_size():
    s = _s(screen=S.HOME, size=SMALL)
    s = S.apply(s, S.Tick(1.0, S.MIN_SIZE))
    assert S.apply(s, S.Key("ESC")).action == "exit"


def test_overlay_over_running_encode_still_answers_keys_below_min_size():
    s = _s(screen=S.ENCODING, size=SMALL)
    s = S.apply(s, S.Key("L"))
    assert s.screen == S.LOG
    assert S.apply(s, S.Key("ESC")).screen == S.ENCODING


def test_encode_running_predicate():
    assert S.encode_running(_s(screen=S.ENCODING))
    assert S.encode_running(_s(screen=S.QUEUE, is_batch=True))
    assert S.encode_running(_s(screen=S.QC))
    assert S.encode_running(_s(screen=S.LOG, back=S.QC))
    assert not S.encode_running(_s(screen=S.QC, exit_code=0))
    assert not S.encode_running(_s(screen=S.LOG, back=S.COMPLETED, exit_code=0))
    assert not S.encode_running(_s(screen=S.QC, back=S.COMPLETED))
    for screen in (S.HOME, S.SOURCE, S.CONFIGURATION, S.ADVANCED, S.PREVIEW, S.READY, S.COMPLETED, S.REPORT):
        assert not S.encode_running(_s(screen=screen))


def test_source_checked_of_old_kind_is_discarded_after_toggle(tmp_path):
    s = S.apply(S.UIState(config={}, screen=S.HOME), S.Key("CHAR", "5"))
    path = str(tmp_path)
    s = dataclasses.replace(s, source=S.W.TextBuf(path, len(path)), source_status="CHECKING")
    s = S._toggle_kind(s)
    assert s.source_status == "CHECKING"
    s = S.apply(s, S.SourceChecked(path, "INVALID", folder=False))
    assert s.source_status == "CHECKING"
    s = S.apply(s, S.SourceChecked(path, "EMPTY", None, 0, folder=True))
    assert (s.source_status, s.source_count) == ("EMPTY", 0)
    s = S.apply(s, S.SourceChecked(path, "NOT_FOUND"))
    assert s.source_status == "NOT_FOUND"


def _final(screen, preset=1, **kw):
    return _s(screen=screen, preset=preset, exit_code={S.COMPLETED: 0, S.CANCELLED: 130}.get(screen, 1), **kw)


def test_final_actions_offer_new_encode_last_only_for_home_session():
    assert S.final_actions(_final(S.COMPLETED)) == ("SAIR", "VER LOG", "NOVO ENCODE")
    assert S.final_actions(_final(S.COMPLETED, qc={})) == ("SAIR", "VER QC", "VER LOG", "NOVO ENCODE")
    assert S.final_actions(_final(S.ERROR)) == ("SAIR", "VER LOG", "NOVO ENCODE")
    assert S.final_actions(_final(S.CANCELLED, preset=0)) == ("SAIR", "VER LOG")
    assert S.final_actions(_final(S.CANCELLED, worker_stuck=True)) == ("SAIR", "VER LOG")


def test_worker_stuck_set_by_driver_info_only():
    from ui import tui_driver as D
    base = _run(_s(screen=S.ENCODING, preset=1), R.Cancel("requested", ts=1.0))
    assert S.apply(base, R.Info("Master mantido — QC não concluído.")).worker_stuck is False
    s = S.apply(base, R.Info(D.WORKER_STUCK_MSG.format(n=D.WORKER_WAIT_S, name="out.mp4"), ts=3.0))
    assert s.worker_stuck is True
    s = S.apply(s, S.Finished(130))
    assert "NOVO ENCODE" not in S.final_actions(s)
    assert S.apply(s, S.Key("CHAR", "n")).action is None


def test_enter_on_new_encode_requests_new_session():
    s = _final(S.CANCELLED)
    s = _run(s, S.Key("RIGHT"), S.Key("RIGHT"), S.Key("RIGHT"))
    assert s.action_focus == 2
    assert S.apply(s, S.Key("ENTER")).action == "new"


def test_stuck_info_reclamps_focus_and_enter_executes_focused_action():
    from ui import tui_driver as D
    s = _final(S.COMPLETED, qc={})
    s = _run(s, S.Key("RIGHT"), S.Key("RIGHT"), S.Key("RIGHT"))
    assert S.final_actions(s)[s.action_focus] == "NOVO ENCODE"
    s = S.apply(s, R.Info(D.WORKER_STUCK_MSG.format(n=D.WORKER_WAIT_S, name="out.mp4"), ts=3.0))
    assert s.worker_stuck is True
    assert 0 <= s.action_focus < len(S.final_actions(s))
    assert S.apply(s, S.Key("ENTER")).screen == S.LOG


def test_enter_clamps_stale_action_focus():
    s = replace(_final(S.COMPLETED, qc={}, worker_stuck=True), action_focus=3)
    assert S.apply(s, S.Key("ENTER")).screen == S.LOG
    assert S.apply(replace(_final(S.ERROR, worker_stuck=True), action_focus=2), S.Key("ENTER")).screen == S.LOG


@pytest.mark.parametrize("screen", [S.QC, S.LOG])
@pytest.mark.parametrize("ch", ["n", "N"])
def test_n_ignored_in_qc_and_log_opened_from_final(screen, ch):
    s = replace(_final(S.COMPLETED, qc={}), screen=screen, back=S.COMPLETED)
    out = S.apply(s, S.Key("CHAR", ch))
    assert out.action is None and out == s


@pytest.mark.parametrize("screen", [S.COMPLETED, S.ERROR, S.CANCELLED, S.REPORT])
@pytest.mark.parametrize("ch", ["n", "N"])
def test_n_shortcut_requests_new_session(screen, ch):
    assert S.apply(_final(screen), S.Key("CHAR", ch)).action == "new"
    assert S.apply(_final(screen, preset=0), S.Key("CHAR", ch)).action is None
    assert S.apply(_final(screen, worker_stuck=True), S.Key("CHAR", ch)).action is None


def test_new_encode_is_a_known_action():
    assert "new" in S.ACTIONS


def test_new_session_carries_only_navigation_fields():
    dirty = _s(screen=S.CANCELLED, preset=3, drafts=((1, {"input": "a.mov"}),), focus=(("CONFIGURATION", 2),),
               home_focus=2, system=(("FFmpeg", "x"),), size=(130, 45), now=50.0, cpu=1.0, ram=2.0,
               ram_used_gb=3.0, cancel_phase="cleaned", exit_code=0, is_batch=True, back=S.QC,
               seal_reveal_start=4.0, stage=R.PASS, passes=(S.PassTrack(1, 1, "x"),), action="new",
               log=(S.LogRow("INFO", "x"),), queue=(S.Job("a", "b"),), worker_stuck=False)
    fresh = S.new_session(dirty)
    want = S.UIState(config={}, screen=S.HOME, drafts=dirty.drafts, focus=dirty.focus, home_focus=2,
                     system=dirty.system, size=(130, 45), now=50.0, cpu=1.0, ram=2.0, ram_used_gb=3.0)
    for f in dataclasses.fields(S.UIState):
        assert getattr(fresh, f.name) == getattr(want, f.name), f.name
    assert fresh.drafts == ((1, {"input": "a.mov"}),)
