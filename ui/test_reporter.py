import dataclasses
import queue
import threading

import pytest

import reporter as R


def _drain(q):
    out = []
    while not q.empty():
        out.append(q.get_nowait())
    return out


def test_events_are_frozen():
    ev = R.Stage(R.PASS, "1")
    with pytest.raises(dataclasses.FrozenInstanceError):
        ev.name = "X"


def test_emit_stamps_job_id_and_ts():
    q = queue.Queue()
    R.QueueReporter(q, job_id=3).emit(R.Info("oi"))
    (ev,) = _drain(q)
    assert ev.job_id == 3 and ev.ts > 0 and ev.text == "oi"


def test_progress_throttled_but_last_frame_passes(monkeypatch):
    now = [100.0]
    monkeypatch.setattr(R.time, "monotonic", lambda: now[0])
    q = queue.Queue()
    rep = R.QueueReporter(q, progress_interval=0.1)
    rep.emit(R.Progress(1, 10, 1.0, 1.0, "x", 0.0))
    now[0] += 0.05
    rep.emit(R.Progress(2, 10, 1.0, 1.0, "x", 0.0))
    now[0] += 0.01
    rep.emit(R.Progress(10, 10, 1.0, 1.0, "x", 0.0))
    assert [e.frame for e in _drain(q)] == [1, 10]


def test_stage_updates_control_and_blocks_cancel():
    calls = []
    ctl = R.CancelControl(terminate=lambda: calls.append(1) or True)
    rep = R.QueueReporter(queue.Queue(), control=ctl)
    rep.emit(R.Stage(R.ANALYZING, "mctf_mask"))
    assert ctl.request_cancel() is False and calls == []
    rep.emit(R.Stage(R.QC))
    assert ctl.request_cancel() is False
    rep.emit(R.Stage(R.PASS, "1"))
    assert ctl.request_cancel() is True and calls == [1] and ctl.cancelled


def test_cancel_raises_on_next_stage_pass_progress():
    ctl = R.CancelControl(terminate=lambda: False)
    q = queue.Queue()
    rep = R.QueueReporter(q, control=ctl)
    rep.emit(R.Stage(R.ANALYZING, "preflight"))
    assert ctl.request_cancel() is True
    with pytest.raises(R.CancelRequested):
        rep.emit(R.Stage(R.PROBING))
    assert isinstance(_drain(q)[-1], R.Stage)


def test_ffmpeg_line_never_raises_when_cancelled():
    ctl = R.CancelControl(terminate=lambda: False)
    ctl.force_cancel()
    rep = R.QueueReporter(queue.Queue(), control=ctl)
    rep.emit(R.FfmpegLine("frame=1"))
    rep.emit(R.Info("x"))


def test_force_cancel_ignores_blocked_stage_and_does_not_terminate():
    calls = []
    ctl = R.CancelControl(terminate=lambda: calls.append(1) or True)
    ctl.stage = (R.QC, None)
    ctl.force_cancel()
    assert ctl.cancelled and calls == []


def test_request_cancel_checks_stage_under_lock():
    ctl = R.CancelControl(terminate=lambda: True)
    ctl.stage = (R.PASS, "1")
    result = []
    with ctl._lock:
        t = threading.Thread(target=lambda: result.append(ctl.request_cancel()))
        t.start()
        t.join(0.2)
        ctl.stage = (R.QC, None)
    t.join(5)
    assert result == [False] and not ctl.cancelled


def test_stage_qc_emit_waits_for_inflight_cancel():
    ctl = R.CancelControl(terminate=lambda: True)
    rep = R.QueueReporter(queue.Queue(), control=ctl)
    rep.emit(R.Stage(R.PASS, "1"))
    outcome = []
    threads = []

    def enter_qc():
        try:
            rep.emit(R.Stage(R.QC))
            outcome.append("qc")
        except R.CancelRequested:
            outcome.append("cancelled")

    real_set = ctl._flag.set

    def racing_set():
        t = threading.Thread(target=enter_qc)
        threads.append(t)
        t.start()
        t.join(0.2)
        real_set()

    ctl._flag.set = racing_set
    assert ctl.request_cancel() is True
    threads[0].join(5)
    assert outcome == ["cancelled"]
