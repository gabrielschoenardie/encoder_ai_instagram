import os
import queue
import threading

import pytest

import Reels_Encoder_v2_FINAL as RE
import render_queue
import reporter as R
from ui import tui_driver as D
from ui.config import EncodeConfig
from ui.tui_capture import ConsoleCapture


@pytest.fixture
def ns(tmp_path):
    src = tmp_path / "in.mp4"
    src.write_bytes(b"x")
    return EncodeConfig(input=str(src), ebu_meter="off", report="off").to_namespace()


def _out(ns):
    return D._single_output_path(ns)


def _drain(q):
    out = []
    while not q.empty():
        out.append(q.get_nowait())
    return out


def _ctl(calls=None):
    return R.CancelControl(terminate=lambda: (calls.append(1) if calls is not None else None) or True)


def _fake_encode(monkeypatch, body):
    def fake(inp, out, args, is_batch=False, reporter=None):
        body(inp, out, reporter)
    monkeypatch.setattr(RE, "_encode_single_file", fake)


def test_success_returns_0(ns, monkeypatch):
    def body(inp, out, rep):
        rep.emit(R.Stage(R.PASS, "1"))
        open(out, "wb").close()
        rep.emit(R.Done(out, 0.1))
    _fake_encode(monkeypatch, body)
    q = queue.Queue()
    assert D.run_single(ns, q, _ctl(), on_tick=lambda: None) == 0
    assert isinstance(_drain(q)[-1], R.Done)


def test_error_returns_1_with_traceback(ns, monkeypatch):
    def body(inp, out, rep):
        raise ValueError("falhou")
    _fake_encode(monkeypatch, body)
    q = queue.Queue()
    assert D.run_single(ns, q, _ctl(), on_tick=lambda: None) == 1
    err = next(e for e in _drain(q) if isinstance(e, R.Error))
    assert err.kind == "ValueError" and "falhou" in err.traceback


def test_validation_error_returns_2(ns, monkeypatch):
    monkeypatch.setattr(RE, "_validate_args_consistency", lambda a: "combinação inválida")
    q = queue.Queue()
    assert D.run_single(ns, q, _ctl(), on_tick=lambda: None) == 2
    assert _drain(q)[-1].kind == "validation"


def test_cancel_before_ffmpeg_stops_at_next_stage(ns, monkeypatch):
    ctl = _ctl()
    started = []

    def body(inp, out, rep):
        rep.emit(R.Stage(R.ANALYZING, "preflight"))
        assert ctl.request_cancel()
        rep.emit(R.Stage(R.PROBING))
        started.append("pass1")
    _fake_encode(monkeypatch, body)
    assert D.run_single(ns, queue.Queue(), ctl, on_tick=lambda: None) == 130
    assert started == []


def test_cancel_refused_during_mctf_and_qc(ns, monkeypatch):
    ctl = _ctl()
    answers = []

    def body(inp, out, rep):
        rep.emit(R.Stage(R.ANALYZING, "mctf_mask"))
        answers.append(ctl.request_cancel())
        rep.emit(R.Stage(R.QC))
        answers.append(ctl.request_cancel())
        open(out, "wb").close()
    _fake_encode(monkeypatch, body)
    assert D.run_single(ns, queue.Queue(), ctl, on_tick=lambda: None) == 0
    assert answers == [False, False]


def _ctrl_c_on_first_tick():
    fired = []

    def tick():
        if not fired:
            fired.append(1)
            raise KeyboardInterrupt
    return tick


def test_ctrl_c_during_qc_deletes_new_master(ns, monkeypatch):
    in_qc = threading.Event()
    release = threading.Event()

    def body(inp, out, rep):
        open(out, "wb").close()
        rep.emit(R.Stage(R.QC))
        in_qc.set()
        release.wait(5)

    _fake_encode(monkeypatch, body)
    terminated = []
    monkeypatch.setattr(RE, "terminate_active_ffmpeg", lambda *a, **k: terminated.append(1) or False)

    def tick():
        if in_qc.is_set() and not terminated:
            release.set()
            raise KeyboardInterrupt

    q = queue.Queue()
    assert D.run_single(ns, q, _ctl(), on_tick=tick) == 130
    assert not os.path.exists(_out(ns))
    ev = _drain(q)
    assert any(isinstance(e, R.Cancel) and e.phase == "cleaned" and e.partial_removed for e in ev)
    phases = [e.phase for e in ev if isinstance(e, R.Cancel)]
    assert phases.index("requested") < phases.index("terminated")


def test_ctrl_c_wait_keeps_ticking_and_ignores_second_ctrl_c(ns, monkeypatch):
    def body(inp, out, rep):
        open(out, "wb").close()
        threading.Event().wait(0.8)
    _fake_encode(monkeypatch, body)
    monkeypatch.setattr(RE, "terminate_active_ffmpeg", lambda *a, **k: False)
    ticks = []

    def tick():
        ticks.append(1)
        raise KeyboardInterrupt

    q = queue.Queue()
    assert D.run_single(ns, q, _ctl(), on_tick=tick) == 130
    assert len(ticks) >= 3
    assert not os.path.exists(_out(ns))
    ev = _drain(q)
    phases = [e.phase for e in ev if isinstance(e, R.Cancel)]
    assert phases[:2] == ["requested", "terminated"]
    assert any(isinstance(e, R.Cancel) and e.phase == "cleaned" and e.partial_removed for e in ev)


def _qc_paths(out):
    base = os.path.splitext(out)[0]
    return base + ".qc.html", base + ".qc.json"


def _write_master_and_certificate(out):
    for path in (out, *_qc_paths(out)):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("novo")


def test_ctrl_c_during_qc_removes_new_certificate_keeps_preexisting(ns, monkeypatch):
    html, json_ = _qc_paths(_out(ns))
    with open(html, "w", encoding="utf-8") as fh:
        fh.write("antigo")
    in_qc = threading.Event()

    def body(inp, out, rep):
        rep.emit(R.Stage(R.QC))
        _write_master_and_certificate(out)
        in_qc.set()
        release.wait(5)
    _fake_encode(monkeypatch, body)
    monkeypatch.setattr(RE, "terminate_active_ffmpeg", lambda *a, **k: False)
    release = threading.Event()

    def tick():
        if in_qc.is_set() and not release.is_set():
            release.set()
            raise KeyboardInterrupt

    assert D.run_single(ns, queue.Queue(), _ctl(), on_tick=tick) == 130
    assert not os.path.exists(_out(ns))
    assert not os.path.exists(json_)
    assert os.path.exists(html)


def test_batch_ctrl_c_during_qc_removes_new_certificate(batch_ns, monkeypatch):
    in_qc = threading.Event()

    def body(inp, out, rep):
        rep.emit(R.Stage(R.QC))
        _write_master_and_certificate(out)
        in_qc.set()
        release.wait(5)
    _fake_encode(monkeypatch, body)
    monkeypatch.setattr(RE, "terminate_active_ffmpeg", lambda *a, **k: False)
    release = threading.Event()

    def tick():
        if in_qc.is_set() and not release.is_set():
            release.set()
            raise KeyboardInterrupt

    _, jobs = D._batch_jobs(batch_ns)
    assert D.run_batch(batch_ns, queue.Queue(), _ctl(), on_tick=tick) == 130
    assert not any(os.path.exists(p) for p in (jobs[0].output_path, *_qc_paths(jobs[0].output_path)))


def test_ctrl_c_keeps_preexisting_output(ns, monkeypatch):
    out = _out(ns)
    with open(out, "wb") as fh:
        fh.write(b"old")
    release = threading.Event()

    def body(inp, o, rep):
        release.wait(5)
    _fake_encode(monkeypatch, body)
    monkeypatch.setattr(RE, "terminate_active_ffmpeg", lambda *a, **k: release.set() or False)
    assert D.run_single(ns, queue.Queue(), _ctl(), on_tick=_ctrl_c_on_first_tick()) == 130
    with open(out, "rb") as fh:
        assert fh.read() == b"old"


def test_cancel_after_done_keeps_master(ns, monkeypatch):
    ctl = _ctl()

    def body(inp, out, rep):
        open(out, "wb").close()
        rep.emit(R.Stage(R.DONE))
        assert ctl.request_cancel()
    _fake_encode(monkeypatch, body)
    assert D.run_single(ns, queue.Queue(), ctl, on_tick=lambda: None) == 0
    assert os.path.exists(_out(ns))


def test_worker_prints_reach_console_capture(ns, monkeypatch):
    def body(inp, out, rep):
        RE.console.print("✓ LUT carregada")
    _fake_encode(monkeypatch, body)
    q = queue.Queue()
    with ConsoleCapture(RE.console, q.put):
        assert D.run_single(ns, q, _ctl(), on_tick=lambda: None) == 0
    assert any(isinstance(e, R.Info) and e.text == "LUT carregada" for e in _drain(q))


def test_ctrl_c_unremovable_output_emits_yf1_warning(ns, monkeypatch):
    written = threading.Event()
    release = threading.Event()

    def body(inp, out, rep):
        open(out, "wb").close()
        written.set()
        release.wait(5)
    _fake_encode(monkeypatch, body)
    monkeypatch.setattr(RE, "terminate_active_ffmpeg", lambda *a, **k: release.set() or False)
    monkeypatch.setattr(render_queue, "discard_partial_output", lambda job: False)

    def tick():
        if written.is_set() and not release.is_set():
            raise KeyboardInterrupt

    q = queue.Queue()
    assert D.run_single(ns, q, _ctl(), on_tick=tick) == 130
    infos = [e.text for e in _drain(q) if isinstance(e, R.Info)]
    assert any("NÃO foi possível remover" in t for t in infos)
    assert any("NÃO passou pelo controle de qualidade" in t for t in infos)


def test_cancel_during_pass_generic_error_returns_130(ns, monkeypatch):
    ctl = _ctl()

    def body(inp, out, rep):
        rep.emit(R.Stage(R.PASS, "1"))
        assert ctl.request_cancel()
        raise RuntimeError("Encoding interrompido por erro no processamento")
    _fake_encode(monkeypatch, body)
    q = queue.Queue()
    assert D.run_single(ns, q, ctl, on_tick=lambda: None) == 130
    assert not any(isinstance(e, R.Error) for e in _drain(q))


def _call_main(monkeypatch, ns):
    monkeypatch.setattr("ui.preflight.missing_ffmpeg_binaries", lambda *a, **k: [])
    monkeypatch.setattr(RE, "parse_cli", lambda *a, **k: ns)
    try:
        RE.main()
    except SystemExit:
        pass


def test_single_output_path_matches_main(ns, monkeypatch):
    seen = {}
    monkeypatch.setattr(RE, "_encode_single_file",
                        lambda i, o, a, is_batch=False, reporter=None: seen.setdefault("out", o))
    _call_main(monkeypatch, ns)
    assert D._single_output_path(ns) == seen["out"]


@pytest.fixture
def batch_ns(tmp_path):
    folder = tmp_path / "lote"
    folder.mkdir()
    for n in ("a.mp4", "b.mp4"):
        (folder / n).write_bytes(b"x")
    return EncodeConfig(batch=str(folder), ebu_meter="off", report="off").to_namespace()


def test_batch_zero_videos_returns_0(tmp_path):
    folder = tmp_path / "vazio"
    folder.mkdir()
    ns = EncodeConfig(batch=str(folder), ebu_meter="off", report="off").to_namespace()
    q = queue.Queue()
    assert D.run_batch(ns, q, _ctl(), on_tick=lambda: None) == 0
    assert _drain(q)[-1].exit_code == 0


def test_batch_jobs_match_classic_main(batch_ns, monkeypatch):
    seen = []
    monkeypatch.setattr(RE, "_encode_single_file",
                        lambda i, o, a, is_batch=False, reporter=None: seen.append((i, o)))
    _call_main(monkeypatch, batch_ns)
    _, jobs = D._batch_jobs(batch_ns)
    assert [(j.input_path, j.output_path) for j in jobs] == seen


def test_batch_skip_fail_and_exit_1(batch_ns, monkeypatch):
    _, jobs = D._batch_jobs(batch_ns)
    open(jobs[0].output_path, "wb").close()

    def body(inp, out, rep):
        raise ValueError("x")
    _fake_encode(monkeypatch, body)
    q = queue.Queue()
    assert D.run_batch(batch_ns, q, _ctl(), on_tick=lambda: None) == 1
    ev = _drain(q)
    assert any(isinstance(e, R.JobSkip) and e.index == 0 for e in ev)
    assert any(isinstance(e, R.JobDone) and e.index == 1 and e.status == "falha" for e in ev)


def test_batch_all_ok_returns_0(batch_ns, monkeypatch):
    _fake_encode(monkeypatch, lambda inp, out, rep: open(out, "wb").close())
    assert D.run_batch(batch_ns, queue.Queue(), _ctl(), on_tick=lambda: None) == 0


def test_batch_ctrl_c_discards_current_even_if_complete(batch_ns, monkeypatch):
    release = threading.Event()

    def body(inp, out, rep):
        open(out, "wb").close()
        release.wait(5)
    _fake_encode(monkeypatch, body)
    monkeypatch.setattr(RE, "terminate_active_ffmpeg", lambda *a, **k: release.set() or False)
    _, jobs = D._batch_jobs(batch_ns)
    q = queue.Queue()
    assert D.run_batch(batch_ns, q, _ctl(), on_tick=_ctrl_c_on_first_tick()) == 130
    assert not os.path.exists(jobs[0].output_path)
    phases = [e.phase for e in _drain(q) if isinstance(e, R.Cancel)]
    assert phases.index("requested") < phases.index("terminated")


def test_batch_cancel_key_stops_queue_and_cleans(batch_ns, monkeypatch):
    ctl = _ctl()
    started = []

    def body(inp, out, rep):
        started.append(inp)
        open(out, "wb").close()
        rep.emit(R.Stage(R.PASS, "1"))
        assert ctl.request_cancel()
        raise RuntimeError("Encoding interrompido por erro no processamento")
    _fake_encode(monkeypatch, body)
    _, jobs = D._batch_jobs(batch_ns)
    q = queue.Queue()
    assert D.run_batch(batch_ns, q, ctl, on_tick=lambda: None) == 130
    ev = _drain(q)
    assert len(started) == 1
    assert not os.path.exists(jobs[0].output_path)
    assert any(isinstance(e, R.Cancel) and e.phase == "cleaned" for e in ev)
    assert ev[-1] == R.QueueDone(130, ts=ev[-1].ts)


def test_batch_ctrl_c_unremovable_output_uses_queue_wording(batch_ns, monkeypatch):
    written = threading.Event()
    release = threading.Event()

    def body(inp, out, rep):
        open(out, "wb").close()
        written.set()
        release.wait(5)
    _fake_encode(monkeypatch, body)
    monkeypatch.setattr(RE, "terminate_active_ffmpeg", lambda *a, **k: release.set() or False)
    monkeypatch.setattr(render_queue, "discard_partial_output", lambda job: False)

    def tick():
        if written.is_set() and not release.is_set():
            raise KeyboardInterrupt

    q = queue.Queue()
    assert D.run_batch(batch_ns, q, _ctl(), on_tick=tick) == 130
    infos = [e.text for e in _drain(q) if isinstance(e, R.Info)]
    assert any("NÃO foi possível remover" in t for t in infos)
    assert any("rodar a fila de novo" in t for t in infos)
    assert not any("rodar o encode de novo" in t for t in infos)
