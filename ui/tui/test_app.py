import argparse
import os
import sys
from dataclasses import replace

import pytest

import Reels_Encoder_v2_FINAL as RE
import reporter as R
from ui.theme import get_console
from ui.tui import app as A
from ui.tui import forms as F
from ui.tui import screens as V
from ui.tui import state as S
from ui.tui import widgets as W


class FakeLive:
    def __init__(self):
        self.frames = []
        self.starts = self.stops = 0

    def start(self):
        self.starts += 1

    def stop(self):
        self.stops += 1

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


def make_home(tmp_path, keys, run_single=None, **kw):
    live = FakeLive()
    reader = CharReader(keys)
    holder = []

    def sleep(_):
        if holder and holder[0].state.screen in S.FINAL_SCREENS:
            holder[0]._queue.put(S.Key("ENTER"))

    app = A.App(run_single=run_single or (lambda *a: 0), reader_factory=reader, live_factory=lambda c: live,
                clock=Clock(), sleep=sleep, perf=lambda: (10.0, 20.0, 1.0), size=lambda: (120, 40),
                system=(("FFmpeg", "x"),), probe=lambda p: (1080, 1920), **kw)
    holder.append(app)
    return app, live, reader


def keys_for(text):
    return [("SPACE" if ch == " " else (ch.upper() if ch.lower() in "dlc" else "CHAR"), ch) for ch in text]


class CharReader(FakeReader):
    def start(self):
        for k in self.keys:
            name, ch = k if isinstance(k, tuple) else (k, None)
            self.emit(S.Key(name, ch))


def test_home_esc_exits_zero_and_prints_cancel(tmp_path):
    import io

    from rich.console import Console
    buf = io.StringIO()
    app, _, _ = make_home(tmp_path, ["ESC"], console=Console(file=buf, width=120))
    assert app.run() == 0
    assert "Cancelado pelo usuário." in buf.getvalue()


@pytest.mark.timeout(30)
def test_full_flow_home_to_completed(tmp_path):
    src = tmp_path / "clip.mov"
    src.write_bytes(b"x")
    seen = []
    holder = []

    def run(ns_, q, control, on_tick):
        seen.append(ns_)
        return 0

    def sleep(_):
        if holder and holder[0].state.screen in S.FINAL_SCREENS | {S.READY}:
            holder[0]._queue.put(S.Key("ENTER"))

    keys = [("CHAR", "1")] + keys_for(str(src)) + ["ENTER"] * 6
    live = FakeLive()
    app = A.App(run_single=run, reader_factory=CharReader(keys), live_factory=lambda c: live, clock=Clock(),
                sleep=sleep, perf=lambda: (None, None, None), size=lambda: (120, 40),
                system=(), probe=lambda p: None)
    holder.append(app)
    assert app.run() == 0
    assert seen and seen[0].input == str(src) and seen[0].cineon_pipeline == "off"


@pytest.mark.timeout(30)
def test_enters_queued_after_arm_do_not_start_encode(tmp_path):
    src = tmp_path / "clip.mov"
    src.write_bytes(b"x")
    ran = []
    first_pause = []
    holder = []

    def sleep(_):
        app = holder[0]
        if not first_pause:
            first_pause.append(app.state.screen)
        app._queue.put(S.Key("ESC"))

    keys = [("CHAR", "1")] + keys_for(str(src)) + ["ENTER"] * 5 + ["ENTER", "ENTER", ("CHAR", "x")]
    app = A.App(run_single=lambda *a: ran.append(1) or 0, reader_factory=CharReader(keys),
                live_factory=lambda c: FakeLive(), clock=Clock(), sleep=sleep, perf=lambda: (None, None, None),
                size=lambda: (120, 40), system=(), probe=lambda p: None)
    holder.append(app)
    assert app.run() == 0
    assert ran == [] and first_pause == [S.READY]


class StillClock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


def preview_app(tmp_path, script, ran):
    src = tmp_path / "clip.mov"
    src.write_bytes(b"x")
    clock = StillClock()
    seen = {"ready": None, "loops": 0}

    def sleep(_):
        seen["loops"] += 1
        if seen["loops"] > 2000:
            raise KeyboardInterrupt
        if app.state.screen in S.FINAL_SCREENS:
            app._queue.put(S.Key("ENTER"))
        elif app.state.screen == S.READY:
            if seen["ready"] is None:
                seen["ready"] = clock.t
            script(app, clock, clock.t - seen["ready"])

    app = A.App(run_single=lambda *a: ran.append(clock.t) or 0, reader_factory=CharReader(["ENTER"]),
                live_factory=lambda c: FakeLive(), clock=clock, sleep=sleep, perf=lambda: (None, None, None),
                size=lambda: (120, 40), system=(), probe=lambda p: None)
    app.state = S.UIState(config={}, screen=S.PREVIEW, preset=1,
                          drafts=((1, {**S.draft(S.UIState(config={}, preset=1)), "input": str(src)}),))
    return app, seen


@pytest.mark.timeout(30)
def test_held_enter_after_arm_never_starts_encode(tmp_path):
    ran = []

    def script(app, clock, elapsed):
        if elapsed > 6.0:
            raise KeyboardInterrupt
        clock.t += 0.03
        app._queue.put(S.Key("ENTER"))

    app, _ = preview_app(tmp_path, script, ran)
    assert app.run() == 130
    assert ran == [] and app.state.screen == S.READY


@pytest.mark.timeout(30)
def test_enter_before_ready_hold_is_ignored_then_isolated_enter_starts(tmp_path):
    ran = []
    pressed = []

    def script(app, clock, elapsed):
        for at in (0.5, 1.3):
            if at not in pressed and elapsed >= at - 1e-9:
                pressed.append(at)
                app._queue.put(S.Key("ENTER"))
                return
        clock.t += 0.1

    app, seen = preview_app(tmp_path, script, ran)
    assert app.run() == 0
    assert pressed == [0.5, 1.3] and len(ran) == 1
    assert abs(ran[0] - seen["ready"] - 1.3) < 1e-6


@pytest.mark.timeout(30)
def test_released_enter_after_burst_starts_encode(tmp_path):
    ran = []
    pressed = []

    def script(app, clock, elapsed):
        if elapsed < 2.0:
            clock.t += 0.03
            app._queue.put(S.Key("ENTER"))
        elif not pressed:
            clock.t += 0.5
            pressed.append(1)
            app._queue.put(S.Key("ENTER"))

    app, seen = preview_app(tmp_path, script, ran)
    assert app.run() == 0
    assert len(ran) == 1 and ran[0] - seen["ready"] >= 2.5 - 1e-6


def test_esc_in_ready_works_right_after_arm(tmp_path):
    app, _ = preview_app(tmp_path, lambda *a: None, [])
    app._arm()
    assert app.state.screen == S.READY
    app._queue.put(S.Key("ENTER"))
    app._queue.put(S.Key("ESC"))
    app._drain()
    assert app.state.screen == S.PREVIEW and app.state.action is None


def test_held_enter_dequeued_after_stall_is_still_rejected(tmp_path):
    app, _ = preview_app(tmp_path, lambda *a: None, [])
    app._arm()
    clock = app._clock
    for i in range(50):
        clock.t += 0.03
        app._emit(S.Key("ENTER"))
        if i % 3 == 2:
            app._drain()
    for _ in range(17):
        clock.t += 0.03
        app._emit(S.Key("ENTER"))
    app._drain()
    assert app.state.screen == S.READY and app.state.action is None


def test_p3b_ready_enter_starts_without_hold(tmp_path):
    ran = []
    clock = StillClock()
    app = A.App(ns(tmp_path), run_single=lambda *a: ran.append(clock.t) or 0, reader_factory=FakeReader(["ENTER"]),
                live_factory=lambda c: FakeLive(), clock=clock,
                sleep=lambda _: app._queue.put(S.Key("ENTER")), perf=lambda: (None, None, None),
                size=lambda: (120, 40), output_path=str(tmp_path / "out.mp4"))
    assert app.run() == 0
    assert ran == [100.0]


def test_arm_drops_only_key_events(tmp_path):
    src = tmp_path / "clip.mov"
    src.write_bytes(b"x")
    app, _, _ = make_home(tmp_path, [])
    app.state = S.UIState(config={}, screen=S.PREVIEW, preset=1,
                          drafts=((1, {**S.draft(S.UIState(config={}, preset=1)), "input": str(src)}),))
    tick = S.Tick(1.0, (120, 40))
    for ev in (S.Key("ENTER"), tick, S.Key("ESC")):
        app._queue.put(ev)
    app._arm()
    assert app.state.screen == S.READY
    left = []
    while not app._queue.empty():
        left.append(app._queue.get_nowait())
    assert left == [tick]


def test_arm_error_keeps_preview_and_queued_keys(tmp_path):
    app, _, _ = make_home(tmp_path, [])
    app.state = S.UIState(config={}, screen=S.PREVIEW, preset=1,
                          drafts=((1, {**S.draft(S.UIState(config={}, preset=1)), "threads": "muitas"}),))
    app._queue.put(S.Key("ESC"))
    app._arm()
    assert app.state.screen == S.PREVIEW and app.state.field_error
    assert app._queue.qsize() == 1


@pytest.mark.parametrize("exc", [ValueError("ruim"), TypeError("tipo")])
def test_arm_exceptions_become_field_error(tmp_path, monkeypatch, exc):
    src = tmp_path / "clip.mov"
    src.write_bytes(b"x")
    app, _, _ = make_home(tmp_path, [])
    app.state = S.UIState(config={}, screen=S.PREVIEW, preset=1,
                          drafts=((1, {**S.draft(S.UIState(config={}, preset=1)), "input": str(src)}),))

    def boom(ns_):
        raise exc

    monkeypatch.setattr(A.RE, "_validate_args_consistency", boom)
    app._arm()
    assert app.state.screen == S.PREVIEW and app.state.field_error == str(exc)


def test_empty_system_rows_are_kept(tmp_path):
    app = A.App(reader_factory=CharReader([]), live_factory=lambda c: FakeLive(), system=())
    assert app.state.system == ()


def test_tools_exception_restores_terminal_and_propagates(tmp_path):
    class ExitLive(FakeLive):
        exited = False

        def __exit__(self, *exc):
            self.exited = True
            return False

    orig_err, orig_file = sys.stderr, RE.console.file
    first, second = CharReader([("CHAR", "4")]), CharReader([])
    readers = iter([first, second])
    live = ExitLive()
    app = A.App(reader_factory=lambda emit: next(readers)(emit), live_factory=lambda c: live, clock=Clock(),
                sleep=lambda _: None, perf=lambda: (None, None, None), size=lambda: (120, 40), system=(),
                probe=lambda p: None, tools=lambda c: 1 / 0)
    with pytest.raises(ZeroDivisionError):
        app.run()
    assert first.restored and second.restored and second.stopped
    assert live.exited and live.stops == 1
    assert sys.stderr is orig_err and RE.console.file is orig_file


def test_check_source_quoted_path_with_spaces_is_valid(tmp_path):
    d = tmp_path / "Meus Vídeos"
    d.mkdir()
    f = d / "x.mov"
    f.write_bytes(b"x")
    app, _, _ = make_home(tmp_path, [])
    app.state = S.apply(app.state, S.Key("CHAR", "1"))
    for name, ch in keys_for(f'"{f}"'):
        app.state = S.apply(app.state, S.Key(name, ch))
    app._check_source()
    assert app.state.source_status == "VALID" and app.state.source_dims == (1080, 1920)


def test_ready_revalidates_missing_input(tmp_path, monkeypatch):
    ran = []
    seen_errors = []
    app, _, _ = make_home(tmp_path, ["ENTER", "ESC", "ESC", "ESC", "ESC", "ESC"],
                          run_single=lambda *a: ran.append(1) or 0)
    app.state = S.UIState(config={"input": str(tmp_path / "missing.mov")}, screen=S.READY, preset=1)
    app._ready_at = 0.0
    orig_apply = S.apply

    def spy(s, ev):
        out = orig_apply(s, ev)
        if out.ready_error:
            seen_errors.append(out.ready_error)
        return out

    monkeypatch.setattr(S, "apply", spy)
    assert app.run() == 0
    assert ran == [] and seen_errors and "missing.mov" in seen_errors[0]


def test_tools_suspends_and_resumes(tmp_path):
    calls = []
    readers = iter([CharReader([("CHAR", "4")]), CharReader(["ESC"])])
    live = FakeLive()
    app = A.App(reader_factory=lambda emit: next(readers)(emit), live_factory=lambda c: live, clock=Clock(),
                sleep=lambda _: None, perf=lambda: (None, None, None), size=lambda: (120, 40), system=(),
                probe=lambda p: None, tools=lambda con: calls.append("tools"))
    assert app.run() == 0
    assert calls == ["tools"] and live.stops == 1 and live.starts == 1


@pytest.mark.timeout(30)
def test_ctrl_c_in_configuration_returns_130(tmp_path):
    app, _, reader = make_home(tmp_path, [("CHAR", "1")])
    orig = app._tick

    def tick():
        orig()
        if app.state.screen == S.SOURCE:
            raise KeyboardInterrupt

    app._tick = tick
    assert app.run() == 130 and reader.restored


def test_arm_strips_form_state_keys(tmp_path):
    src = tmp_path / "clip.mov"
    src.write_bytes(b"x")
    app, _, _ = make_home(tmp_path, [])
    app.state = S.UIState(config={}, screen=S.PREVIEW, preset=5,
                          drafts=((5, {**F.new_draft(5), "input": str(src)}),))
    app._arm()
    assert app.state.screen == S.READY and app.state.field_error is None
    assert F.OUTDIR_ON not in app.state.config and F.SOURCE_KIND not in app.state.config


def batch_folder(tmp_path, names=("a.mov", "b.mov")):
    folder = tmp_path / "lote"
    folder.mkdir()
    for n in names:
        (folder / n).write_bytes(b"x")
    return folder


def fake_batch(events, code, record):
    def run(ns_, q, control, on_tick):
        record.append(ns_)
        jobs = tuple((p, os.path.splitext(p)[0] + "_Hollywood_CRF18.mp4") for p in RE.find_video_files(ns_.batch))
        for ev in (R.QueueInit(jobs), *events, R.QueueDone(code)):
            q.put(ev)
            on_tick()
        record.append(control.cancelled)
        return code
    return run


def batch_app(folder, run_batch, **kw):
    holder = []

    def sleep(_):
        if holder and holder[0].state.screen in S.FINAL_SCREENS | {S.READY}:
            holder[0]._queue.put(S.Key("ENTER"))

    def no_single(*a):
        raise AssertionError("run_single chamado em batch")

    def no_probe(p):
        raise AssertionError("probe chamado para pasta")

    keys = [("CHAR", "3")] + keys_for(str(folder)) + ["ENTER"] * 6
    app = A.App(run_single=no_single, run_batch=run_batch, reader_factory=CharReader(keys),
                live_factory=lambda c: FakeLive(), clock=Clock(), sleep=sleep, perf=lambda: (None, None, None),
                size=lambda: (120, 40), system=(), probe=no_probe, **kw)
    holder.append(app)
    return app


def summary_lines(con):
    return [ln for ln in con.export_text().splitlines() if ln.strip()]


@pytest.mark.timeout(30)
def test_batch_flow_home_to_report_code_0(tmp_path):
    folder = batch_folder(tmp_path)
    rec = []
    con = recording()
    evs = [R.JobStart(0), R.JobDone(0, "ok", None), R.JobStart(1), R.JobDone(1, "ok", None)]
    app = batch_app(folder, fake_batch(evs, 0, rec), console=con)
    assert app.run() == 0
    ns_ = rec[0]
    assert ns_.batch == str(folder) and ns_.input is None and ns_.output_dir is None
    assert ns_.cineon_pipeline == "off" and not hasattr(ns_, F.OUTDIR_ON)
    assert app.state.screen == S.REPORT and [j.status for j in app.state.queue] == ["ok", "ok"]
    assert summary_lines(con) == ["✓ fila: 2 ok · 0 pulados · 0 falhas (código 0)"]


@pytest.mark.timeout(30)
def test_batch_flow_failure_code_1(tmp_path):
    folder = batch_folder(tmp_path)
    rec = []
    con = recording()
    evs = [R.JobStart(0), R.Error("CalledProcessError", "ffmpeg falhou", None, 1, "tb", job_id=0),
           R.JobDone(0, "falha", "ffmpeg falhou\ndetalhe"), R.JobSkip(1, "output existe")]
    app = batch_app(folder, fake_batch(evs, 1, rec), console=con)
    assert app.run() == 1
    assert [(j.status, j.reason) for j in app.state.queue] == [("falha", "ffmpeg falhou"), ("pulado", "saída já existe")]
    assert app.state.screen == S.REPORT and app.state.error is None
    assert summary_lines(con) == ["✗ fila: 0 ok · 1 pulado · 1 falha (código 1)"]


@pytest.mark.timeout(30)
def test_batch_cancel_from_queue_code_130(tmp_path):
    folder = batch_folder(tmp_path)
    rec = []
    con = recording()
    evs = [R.JobStart(0), R.Stage(R.PASS, "1", job_id=0), S.Key("C"), S.Key("RIGHT"), S.Key("ENTER"),
           R.JobDone(0, "falha", "cancelado pelo usuário"), R.Cancel("terminated"), R.Cancel("cleaned", True)]
    app = batch_app(folder, fake_batch(evs, 130, rec), console=con, terminate=lambda: True)
    assert app.run() == 130
    assert rec[-1] is True
    assert [j.status for j in app.state.queue] == ["interrompido", "aguardando"]
    assert summary_lines(con) == ["⚠ fila interrompida: 0 ok · 0 pulados · 0 falhas · 1 interrompido (código 130)"]


@pytest.mark.timeout(30)
def test_batch_error_before_queue_goes_to_error_screen(tmp_path):
    folder = batch_folder(tmp_path)
    con = recording()

    def run(ns_, q, control, on_tick):
        q.put(R.Error("batch_folder", f"Pasta não encontrada: {ns_.batch}", None, None, None))
        on_tick()
        return 1

    app = batch_app(folder, run, console=con)
    assert app.run() == 1 and app.state.screen == S.ERROR
    assert summary_lines(con) == [f"✗ erro (código 1): batch_folder: Pasta não encontrada: {folder}"]


def test_check_source_folder_counts_videos_like_engine(tmp_path):
    lote = batch_folder(tmp_path, names=("a.mov", "B.MP4", "a_Hollywood_CRF18.mp4", "notas.txt"))
    (lote / "sub").mkdir()
    (lote / "sub" / "c.mov").write_bytes(b"x")
    vazia = tmp_path / "vazia"
    vazia.mkdir()
    app, _, _ = make_home(tmp_path, [])

    def no_probe(p):
        raise AssertionError("probe chamado para pasta")

    app._probe = no_probe
    app.state = S.apply(app.state, S.Key("CHAR", "3"))
    cases = ((lote, "VALID", 2), (vazia, "EMPTY", 0), (tmp_path / "nada", "NOT_FOUND", None),
             (lote / "a.mov", "INVALID", None), ("", "INVALID", None))
    for path, status, count in cases:
        text = str(path)
        app.state = replace(app.state, source=W.TextBuf(text, len(text)))
        app._check_source()
        assert (app.state.source_status, app.state.source_count) == (status, count), path


def test_arm_batch_has_no_single_output(tmp_path):
    folder = batch_folder(tmp_path)
    app, _, _ = make_home(tmp_path, [])
    d = {**F.new_draft(3), "batch": str(folder), F.OUTDIR_ON: "on", "output_dir": str(tmp_path / "saida")}
    app.state = S.UIState(config={}, screen=S.PREVIEW, preset=3, drafts=((3, d),), source_count=2)
    app._arm()
    s = app.state
    assert s.screen == S.READY and s.is_batch and s.output_path == "" and not s.output_preexisted
    assert s.config["batch"] == str(folder) and s.config["input"] is None
    assert s.config["output_dir"] == str(tmp_path / "saida")


def ready_batch_app(tmp_path, folder, ran, monkeypatch, seen_errors):
    app, _, _ = make_home(tmp_path, ["ENTER", "ESC", "ESC", "ESC", "ESC", "ESC"],
                          run_batch=lambda *a: ran.append(1) or 0)
    app.state = S.UIState(config={"batch": str(folder), "input": None}, screen=S.READY, preset=3, is_batch=True)
    app._ready_at = 0.0
    orig_apply = S.apply

    def spy(s, ev):
        out = orig_apply(s, ev)
        if out.ready_error:
            seen_errors.append(out.ready_error)
        return out

    monkeypatch.setattr(S, "apply", spy)
    return app


def test_ready_blocks_emptied_folder(tmp_path, monkeypatch):
    folder = batch_folder(tmp_path, names=("a.mov",))
    (folder / "a.mov").unlink()
    ran, errors = [], []
    app = ready_batch_app(tmp_path, folder, ran, monkeypatch, errors)
    assert app.run() == 0
    assert ran == [] and errors and errors[0] == f"nenhum vídeo encontrado em: {folder}"


def test_ready_blocks_missing_folder(tmp_path, monkeypatch):
    ran, errors = [], []
    app = ready_batch_app(tmp_path, tmp_path / "sumiu", ran, monkeypatch, errors)
    assert app.run() == 0
    assert ran == [] and errors and errors[0] == f"pasta não encontrada: {tmp_path / 'sumiu'}"


@pytest.mark.timeout(30)
def test_batch_held_enter_after_arm_never_starts_queue(tmp_path):
    folder = batch_folder(tmp_path)
    ran = []
    clock = StillClock()
    seen = {"ready": None, "loops": 0}

    def sleep(_):
        seen["loops"] += 1
        if seen["loops"] > 2000:
            raise KeyboardInterrupt
        if app.state.screen in S.FINAL_SCREENS:
            app._queue.put(S.Key("ENTER"))
        elif app.state.screen == S.READY:
            if seen["ready"] is None:
                seen["ready"] = clock.t
            if clock.t - seen["ready"] > 6.0:
                raise KeyboardInterrupt
            clock.t += 0.03
            app._queue.put(S.Key("ENTER"))

    app = A.App(run_batch=lambda *a: ran.append(1) or 0, reader_factory=CharReader(["ENTER"]),
                live_factory=lambda c: FakeLive(), clock=clock, sleep=sleep, perf=lambda: (None, None, None),
                size=lambda: (120, 40), system=(), probe=lambda p: None)
    app.state = S.UIState(config={}, screen=S.PREVIEW, preset=3, source_count=2,
                          drafts=((3, {**F.new_draft(3), "batch": str(folder)}),))
    assert app.run() == 130
    assert ran == [] and app.state.screen == S.READY and app.state.is_batch


def test_arm_batch_quoted_output_dir_is_cleaned_and_form_keys_stripped(tmp_path):
    folder = batch_folder(tmp_path)
    saida = tmp_path / "Saída Final"
    app, _, _ = make_home(tmp_path, [])
    s = S.apply(app.state, S.Key("CHAR", "3"))
    s = replace(s, source=W.TextBuf(str(folder), len(str(folder))))
    s = S.apply(s, S.SourceChecked(str(folder), "VALID", None, 2))
    s = S.apply(S.apply(S.apply(s, S.Key("ENTER")), S.Key("SPACE")), S.Key("DOWN"))
    for name, ch in keys_for(f'"{saida}"'):
        s = S.apply(s, S.Key(name, ch))
    app.state = S.apply(s, S.Key("ENTER"))
    assert S.draft(app.state)[F.OUTDIR_ON] == "on" and S.draft(app.state)["batch"] == str(folder)
    app._arm()
    cfg = app.state.config
    assert app.state.screen == S.READY and app.state.field_error is None
    assert cfg["output_dir"] == str(saida)
    assert F.OUTDIR_ON not in cfg and F.SOURCE_KIND not in cfg


@pytest.mark.timeout(30)
def test_batch_runner_exception_before_queue_goes_to_error_screen(tmp_path):
    folder = batch_folder(tmp_path)
    con = recording()

    def run(ns_, q, control, on_tick):
        raise OSError("sem permissão")

    app = batch_app(folder, run, console=con)
    assert app.run() == 1
    assert app.state.screen == S.ERROR and "sem permissão" in screen_text(app.state)
    assert summary_lines(con) == ["✗ erro (código 1): OSError: sem permissão"]


def _jobs(folder):
    return tuple((p, os.path.splitext(p)[0] + "_o.mp4") for p in RE.find_video_files(str(folder)))


@pytest.mark.timeout(30)
@pytest.mark.parametrize("code, last, line", [
    (0, R.JobDone(1, "ok", None), "✓ fila: 2 ok · 0 pulados · 0 falhas (código 0)"),
    (1, R.JobDone(1, "falha", "boom"), "✗ fila: 1 ok · 0 pulados · 1 falha (código 1)"),
])
def test_batch_ctrl_c_on_report_keeps_queue_exit_code(tmp_path, code, last, line):
    folder = batch_folder(tmp_path)
    con = recording()
    evs = [R.JobStart(0), R.JobDone(0, "ok", None), R.JobStart(1), last]
    app = batch_app(folder, fake_batch(evs, code, []), console=con)

    def sleep(_):
        if app.state.screen == S.REPORT:
            raise KeyboardInterrupt
        if app.state.screen == S.READY:
            app._queue.put(S.Key("ENTER"))

    app._sleep = sleep
    assert app.run() == code
    assert app.state.screen == S.REPORT and summary_lines(con) == [line]


@pytest.mark.timeout(30)
@pytest.mark.parametrize("started, line", [
    (True, "⚠ fila interrompida: 0 ok · 0 pulados · 0 falhas · 1 interrompido (código 130)"),
    (False, "⚠ fila interrompida: 0 ok · 0 pulados · 0 falhas · 0 interrompidos (código 130)"),
])
def test_batch_ctrl_c_outside_job_prints_interrupted_summary(tmp_path, started, line):
    folder = batch_folder(tmp_path)
    con = recording()

    def run(ns_, q, control, on_tick):
        if started:
            q.put(R.QueueInit(_jobs(folder)))
            q.put(R.JobStart(0))
            on_tick()
        raise KeyboardInterrupt

    app = batch_app(folder, run, console=con)
    assert app.run() == 130
    assert app.state.screen == S.REPORT and app.state.exit_code == 130
    assert [j.status for j in app.state.queue] == (["interrompido", "aguardando"] if started else [])
    assert summary_lines(con) == [line]


@pytest.mark.timeout(30)
def test_batch_runner_exception_after_queue_init_fails_active_job(tmp_path):
    folder = batch_folder(tmp_path)
    con = recording()

    def run(ns_, q, control, on_tick):
        q.put(R.QueueInit(_jobs(folder)))
        q.put(R.JobStart(0))
        on_tick()
        raise OSError("sem permissão")

    app = batch_app(folder, run, console=con)
    assert app.run() == 1
    assert app.state.screen == S.REPORT
    assert [(j.status, j.reason) for j in app.state.queue] == [("falha", "OSError: sem permissão"),
                                                               ("aguardando", None)]
    assert summary_lines(con) == ["✗ fila: 0 ok · 0 pulados · 1 falha (código 1)"]


@pytest.mark.timeout(30)
def test_batch_runner_exception_after_cancel_returns_130(tmp_path):
    folder = batch_folder(tmp_path)
    con = recording()

    def run(ns_, q, control, on_tick):
        q.put(R.QueueInit(_jobs(folder)))
        q.put(R.JobStart(0))
        on_tick()
        assert control.request_cancel()
        raise RuntimeError("ffmpeg morto")

    app = batch_app(folder, run, console=con, terminate=lambda: True)
    assert app.run() == 130
    assert [j.status for j in app.state.queue] == ["interrompido", "aguardando"]
    assert summary_lines(con) == ["⚠ fila interrompida: 0 ok · 0 pulados · 0 falhas · 1 interrompido (código 130)"]


@pytest.mark.timeout(30)
def test_batch_cancel_in_blocked_stage_warns_in_log(tmp_path):
    folder = batch_folder(tmp_path)
    seen = []

    def run(ns_, q, control, on_tick):
        for ev in (R.QueueInit(_jobs(folder)), R.JobStart(0), R.JobDone(0, "ok", None), R.JobStart(1)):
            q.put(ev)
        on_tick()
        control.stage = (R.QC, None)
        for k in ("C", "RIGHT", "ENTER"):
            q.put(S.Key(k))
        on_tick()
        seen.append((control.cancelled, app.state.modal, app.state.log[-1]))
        for ev in (R.JobDone(1, "ok", None), R.QueueDone(0)):
            q.put(ev)
        on_tick()
        return 0

    app = batch_app(folder, run, terminate=lambda: True)
    assert app.run() == 0
    assert seen == [(False, None, S.LogRow("WARNING", S.CANCEL_UNAVAILABLE))]
    assert S.CANCEL_UNAVAILABLE == "cancelamento indisponível neste estágio — tente de novo em instantes"


def _scandir_down(path):
    raise OSError(59, "erro de rede inesperado")


def test_check_folder_oserror_is_not_found(tmp_path, monkeypatch):
    folder = batch_folder(tmp_path)
    app, _, _ = make_home(tmp_path, [])
    app.state = S.apply(app.state, S.Key("CHAR", "3"))
    app.state = replace(app.state, source=W.TextBuf(str(folder), len(str(folder))))
    monkeypatch.setattr(RE, "find_video_files", _scandir_down)
    app._check_source()
    assert (app.state.source_status, app.state.source_count) == ("NOT_FOUND", None)


@pytest.mark.timeout(30)
def test_ready_blocks_unreadable_folder(tmp_path, monkeypatch):
    folder = batch_folder(tmp_path)
    ran, errors = [], []
    app = ready_batch_app(tmp_path, folder, ran, monkeypatch, errors)
    monkeypatch.setattr(RE, "find_video_files", _scandir_down)
    assert app.run() == 0
    assert ran == [] and errors and str(folder) in errors[0] and "erro de rede inesperado" in errors[0]
