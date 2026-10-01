import argparse
import sys

import pytest

import Reels_Encoder_v2_FINAL as RE
import reporter as R
from ui.theme import get_console
from ui.tui import app as A
from ui.tui import screens as V
from ui.tui import state as S


class FakeLive:
    def __init__(self):
        self.frames = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def update(self, renderable, refresh=True):
        self.frames.append(renderable)


class FakeReader:
    def __init__(self, keys):
        self.keys = list(keys)
        self.stopped = self.restored = False

    def __call__(self, emit):
        self.emit = emit
        return self

    def start(self):
        for k in self.keys:
            self.emit(S.Key(k))

    def stop(self):
        self.stopped = True

    def restore(self):
        self.restored = True


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        self.t += 0.5
        return self.t


def ns(tmp_path):
    src = tmp_path / "in.mov"
    src.write_bytes(b"x")
    return argparse.Namespace(input=str(src), mode="crf", cineon_pipeline="off", output_dir=None,
                              report="on", ebu_meter="off", fit="contain", threads=0, performance="balanced")


def make(tmp_path, keys, run_single, **kw):
    live = FakeLive()
    reader = FakeReader(keys)
    holder = []

    def sleep(_):
        if holder and holder[0].state.screen in S.FINAL_SCREENS:
            holder[0]._queue.put(S.Key("ENTER"))

    app = A.App(ns(tmp_path), run_single=run_single, reader_factory=reader, live_factory=lambda c: live,
                clock=Clock(), sleep=sleep, perf=lambda: (10.0, 20.0, 1.0),
                size=lambda: (120, 40), output_path=str(tmp_path / "out.mp4"), **kw)
    holder.append(app)
    return app, live, reader


def fake_success(events_to_emit, code=0):
    def run(ns_, q, control, on_tick):
        for ev in events_to_emit:
            q.put(ev)
            on_tick()
        return code
    return run


def test_ready_esc_returns_zero_without_encoding(tmp_path):
    called = []
    app, live, reader = make(tmp_path, ["ESC"], lambda *a: called.append(1) or 0)
    assert app.run() == 0
    assert called == [] and reader.stopped and reader.restored


def test_ready_keys_after_enter_stay_queued(tmp_path):
    seen = []

    def run(ns_, q, control, on_tick):
        seen.append(q.qsize())
        return 0

    app, _, _ = make(tmp_path, ["ENTER", "D"], run)
    assert app.run() == 0
    assert seen == [1]


def test_success_flow_reaches_completed_then_exit(tmp_path):
    evs = [R.Stage(R.PREPARING, ts=1.0), R.Stage(R.PASS, "1", ts=2.0), R.Pass(1, 1, "Encode", "start", ts=2.0),
           R.Pass(1, 1, "Encode", "end", ts=3.0), R.Stage(R.DONE, ts=4.0), R.Done("out.mp4", 3.0, ts=4.0)]
    app, live, _ = make(tmp_path, ["ENTER"], fake_success(evs))
    assert app.run() == 0
    assert app.state.screen == S.COMPLETED and live.frames


def test_error_flow_returns_1(tmp_path):
    app, _, _ = make(tmp_path, ["ENTER"],
                     fake_success([R.Error("RuntimeError", "boom", None, None, "tb", ts=1.0)], code=1))
    assert app.run() == 1
    assert app.state.screen == S.ERROR


def test_c_confirm_calls_request_cancel(tmp_path):
    calls = []

    def run(ns_, q, control, on_tick):
        q.put(R.Stage(R.PASS, "1", ts=1.0))
        on_tick()
        q.put(S.Key("C"))
        q.put(S.Key("RIGHT"))
        q.put(S.Key("ENTER"))
        on_tick()
        calls.append(control.cancelled)
        return 130

    app, _, _ = make(tmp_path, ["ENTER"], run, terminate=lambda: True)
    assert app.run() == 130
    assert calls == [True] and app.state.screen == S.CANCELLED


def test_ctrl_c_in_ready_returns_130_and_restores(tmp_path, monkeypatch):
    orig = sys.stderr
    app, _, reader = make(tmp_path, [], lambda *a: 0)
    monkeypatch.setattr(app, "_tick", lambda *a, **k: (_ for _ in ()).throw(KeyboardInterrupt()))
    assert app.run() == 130
    assert sys.stderr is orig and reader.restored
    assert RE.console.file is not None


def test_stderr_and_console_restored_on_unexpected_exception(tmp_path):
    orig_err, orig_file = sys.stderr, RE.console.file

    def boom(*a):
        raise ValueError("bug")

    app, _, reader = make(tmp_path, ["ENTER"], boom)
    with pytest.raises(ValueError):
        app.run()
    assert sys.stderr is orig_err and RE.console.file is orig_file and reader.restored


def test_render_exception_does_not_escape_on_tick(tmp_path, monkeypatch):
    seen = []

    def run(ns_, q, control, on_tick):
        on_tick()
        seen.append("still-running")
        return 0

    app, live, _ = make(tmp_path, ["ENTER"], run)
    monkeypatch.setattr(A, "render", lambda s: (_ for _ in ()).throw(RuntimeError("render bug")))
    assert app.run() == 0
    assert seen == ["still-running"]


def test_resize_mid_encode_keeps_running(tmp_path):
    sizes = iter([(120, 40), (90, 30), (90, 30), (120, 40)] + [(120, 40)] * 50)
    evs = [R.Stage(R.PASS, "1", ts=1.0), R.Stage(R.DONE, ts=2.0)]
    app, live, _ = make(tmp_path, ["ENTER"], fake_success(evs))
    app._size = lambda: next(sizes)
    assert app.run() == 0


def test_stderr_writes_become_log_rows(tmp_path):
    def run(ns_, q, control, on_tick):
        sys.stderr.write("Traceback (most recent call last):\n  oops\n")
        on_tick()
        return 1

    app, _, _ = make(tmp_path, ["ENTER"], run)
    app.run()
    assert any("Traceback" in r.text for r in app.state.log)


def test_perf_and_live_update_exceptions_do_not_escape_on_tick(tmp_path):
    seen = []

    def run(ns_, q, control, on_tick):
        on_tick()
        seen.append("still-running")
        return 0

    def bad_perf():
        raise OSError("perf bug")

    app, live, _ = make(tmp_path, ["ENTER"], run)
    app._perf = bad_perf
    live.update = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("live bug"))
    assert app.run() == 0
    assert seen == ["still-running"]


def screen_text(state):
    con = get_console(record=True, width=120, height=40, force_terminal=True, color_system="truecolor")
    con.print(V.render(state))
    return con.export_text()


def test_output_preexisted_detected_at_start(tmp_path):
    app, _, _ = make(tmp_path, ["ESC"], lambda *a: 0)
    assert app.state.output_preexisted is False
    (tmp_path / "out.mp4").write_bytes(b"old")
    app, _, _ = make(tmp_path, ["ESC"], lambda *a: 0)
    assert app.state.output_preexisted is True


def test_confirmed_cancel_draws_cancel_requested_and_c_does_not_reopen(tmp_path):
    seen = {}

    def run(ns_, q, control, on_tick):
        q.put(R.Stage(R.PASS, "1", ts=1.0))
        q.put(R.Pass(1, 1, "Encode", "start", ts=1.0))
        on_tick()
        for k in ("C", "RIGHT", "ENTER"):
            q.put(S.Key(k))
        on_tick()
        seen["phase"] = app.state.cancel_phase
        seen["text"] = screen_text(app.state)
        q.put(S.Key("C"))
        on_tick()
        seen["modal"] = app.state.modal
        return 130

    app, _, _ = make(tmp_path, ["ENTER"], run, terminate=lambda: True)
    assert app.run() == 130
    assert seen["phase"] == "requested" and "CANCELAMENTO SOLICITADO" in seen["text"]
    assert seen["modal"] is None


def test_events_queued_before_return_apply_before_finished(tmp_path):
    payload = {"summary": {"ready": True}, "checks": []}

    def run(ns_, q, control, on_tick):
        q.put(R.Stage(R.QC, ts=1.0))
        q.put(R.Qc(payload, ts=1.1))
        return 0

    app, _, _ = make(tmp_path, ["ENTER"], run)
    screens = []
    inner = app._sleep
    app._sleep = lambda t: (screens.append(app.state.screen), inner(t))
    assert app.run() == 0
    assert app.state.screen == S.COMPLETED and app.state.seal_reveal_start is not None
    assert S.QC in screens and screens.index(S.QC) < screens.index(S.COMPLETED)


def recording():
    return get_console(record=True, width=400, force_terminal=False)


def test_summary_line_completed(tmp_path):
    con = recording()
    app, _, _ = make(tmp_path, ["ENTER"], fake_success([R.Stage(R.PASS, "1", ts=1.0)]), console=con)
    assert app.run() == 0
    lines = [ln for ln in con.export_text().splitlines() if ln.strip()]
    assert lines == [f"✓ entregue: {tmp_path / 'out.mp4'}"]


def test_summary_line_error(tmp_path):
    con = recording()
    err = R.Error("CalledProcessError", "Command '['ffmpeg', '-y']' returned 1", None, 1, None, ts=1.0)
    app, _, _ = make(tmp_path, ["ENTER"], fake_success([err], code=1), console=con)
    assert app.run() == 1
    lines = [ln for ln in con.export_text().splitlines() if ln.strip()]
    assert lines == ["✗ erro (código 1): CalledProcessError: ffmpeg saiu com código 1"]


def test_summary_line_cancelled(tmp_path):
    con = recording()
    evs = [R.Stage(R.PASS, "1", ts=1.0), R.Cancel("requested", ts=2.0), R.Cancel("cleaned", True, ts=3.0)]
    app, _, _ = make(tmp_path, ["ENTER"], fake_success(evs, code=130), console=con)
    assert app.run() == 130
    lines = [ln for ln in con.export_text().splitlines() if ln.strip()]
    assert lines == ["⚠ cancelado: output parcial removido: out.mp4"]


def test_summary_line_absent_on_ready_esc(tmp_path):
    con = recording()
    app, _, _ = make(tmp_path, ["ESC"], lambda *a: 0, console=con)
    assert app.run() == 0
    assert con.export_text().strip() == ""
