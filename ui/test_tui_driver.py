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


MASTER = b"MASTER-COMPLETO-" * 64


def _once(event):
    fired = []

    def tick():
        if event.is_set() and not fired:
            fired.append(1)
            raise KeyboardInterrupt
    return tick


def test_ctrl_c_during_qc_keeps_new_master(ns, monkeypatch):
    in_qc = threading.Event()
    release = threading.Event()

    def body(inp, out, rep):
        with open(out, "wb") as fh:
            fh.write(MASTER)
        rep.emit(R.Stage(R.QC))
        in_qc.set()
        release.wait(5)

    _fake_encode(monkeypatch, body)
    monkeypatch.setattr(RE, "terminate_active_ffmpeg", lambda *a, **k: release.set() or False)

    q = queue.Queue()
    assert D.run_single(ns, q, _ctl(), on_tick=_once(in_qc)) == 130
    with open(_out(ns), "rb") as fh:
        assert fh.read() == MASTER
    ev = _drain(q)
    infos = [e.text for e in ev if isinstance(e, R.Info)]
    assert "Master mantido — QC não concluído." in infos
    assert not any("NÃO foi possível remover" in t for t in infos)
    assert not any(isinstance(e, R.Cancel) and e.phase == "cleaned" and e.partial_removed for e in ev)
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


def _write_master_and_new_json(out):
    with open(out, "wb") as fh:
        fh.write(MASTER)
    with open(_qc_paths(out)[1], "w", encoding="utf-8") as fh:
        fh.write("novo")


def test_ctrl_c_during_qc_removes_new_certificate_keeps_preexisting(ns, monkeypatch):
    html, json_ = _qc_paths(_out(ns))
    with open(html, "w", encoding="utf-8") as fh:
        fh.write("antigo")
    in_qc = threading.Event()
    release = threading.Event()

    def body(inp, out, rep):
        rep.emit(R.Stage(R.QC))
        _write_master_and_new_json(out)
        in_qc.set()
        release.wait(5)
    _fake_encode(monkeypatch, body)
    monkeypatch.setattr(RE, "terminate_active_ffmpeg", lambda *a, **k: release.set() or False)

    assert D.run_single(ns, queue.Queue(), _ctl(), on_tick=_once(in_qc)) == 130
    with open(_out(ns), "rb") as fh:
        assert fh.read() == MASTER
    assert not os.path.exists(json_)
    with open(html, encoding="utf-8") as fh:
        assert fh.read() == "antigo"


def test_batch_ctrl_c_during_qc_removes_new_certificate(batch_ns, monkeypatch):
    _, jobs = D._batch_jobs(batch_ns)
    html, json_ = _qc_paths(jobs[0].output_path)
    with open(html, "w", encoding="utf-8") as fh:
        fh.write("antigo")
    in_qc = threading.Event()
    release = threading.Event()
    calls = []

    def body(inp, out, rep):
        calls.append(inp)
        rep.emit(R.Stage(R.PREPARING))
        rep.emit(R.Stage(R.QC))
        _write_master_and_new_json(out)
        in_qc.set()
        release.wait(5)
    _fake_encode(monkeypatch, body)
    monkeypatch.setattr(RE, "terminate_active_ffmpeg", lambda *a, **k: release.set() or False)

    q = queue.Queue()
    assert D.run_batch(batch_ns, q, _ctl(), on_tick=_once(in_qc)) == 130
    with open(jobs[0].output_path, "rb") as fh:
        assert fh.read() == MASTER
    assert not os.path.exists(json_)
    with open(html, encoding="utf-8") as fh:
        assert fh.read() == "antigo"
    ev = _drain(q)
    assert len(calls) == 1
    assert not any(isinstance(e, R.JobStart) and e.index == 1 for e in ev)
    assert ev[-1] == R.QueueDone(130, ts=ev[-1].ts)


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


def _absorbing_body(ctl, after):
    def body(inp, out, rep):
        rep.emit(R.Stage(R.PREPARING))
        rep.emit(R.Stage(R.PASS, "1"))
        assert ctl.request_cancel()
        try:
            rep.emit(R.Progress(1, 10, 1.0, 1.0, "x", 0.0))
        except Exception:
            pass
        after.append(1)
    return body


def test_cancel_not_absorbed_by_except_exception_single(ns, monkeypatch):
    ctl = _ctl()
    after = []
    _fake_encode(monkeypatch, _absorbing_body(ctl, after))
    q = queue.Queue()
    assert D.run_single(ns, q, ctl, on_tick=lambda: None) == 130
    assert after == []
    assert not any(isinstance(e, R.Error) for e in _drain(q))


def test_cancel_not_absorbed_by_except_exception_batch(batch_ns, monkeypatch):
    ctl = _ctl()
    after = []
    _fake_encode(monkeypatch, _absorbing_body(ctl, after))
    q = queue.Queue()
    assert D.run_batch(batch_ns, q, ctl, on_tick=lambda: None) == 130
    ev = _drain(q)
    assert after == []
    assert not any(isinstance(e, R.Error) for e in ev)
    done = [e for e in ev if isinstance(e, R.JobDone) and e.index == 0]
    assert len(done) == 1 and done[0].status != "processando"
    assert ev[-1] == R.QueueDone(130, ts=ev[-1].ts)


def _remux_body(started, release, finish):
    def body(inp, out, rep):
        rep.emit(R.Stage(R.PREPARING))
        rep.emit(R.Stage(R.PASS, "1"))
        with open(out, "wb") as fh:
            fh.write(MASTER)
        rep.emit(R.Stage(R.FINALIZING, "remux"))
        temp = out.replace(".mp4", "_temp.mp4")
        os.replace(out, temp)
        started.set()
        release.wait(5)
        finish(out, temp)
        rep.emit(R.Stage(R.QC))
        rep.emit(R.Stage(R.DONE))
    return body


def _restore_ok(out, temp):
    os.replace(temp, out)


def _restore_failed(out, temp):
    with open(out, "wb") as fh:
        fh.write(b"TRUNC")


def _remux_completed(out, temp):
    with open(out, "wb") as fh:
        fh.write(b"REMUXED")
    os.remove(temp)


REMUX_KEPT = "Master mantido — remux não confirmado (átomo colr) e QC não concluído."


def _run_remux_ctrl_c(ns, monkeypatch, finish):
    started = threading.Event()
    release = threading.Event()
    _fake_encode(monkeypatch, _remux_body(started, release, finish))
    monkeypatch.setattr(RE, "terminate_active_ffmpeg", lambda *a, **k: release.set() or False)
    q = queue.Queue()
    code = D.run_single(ns, q, _ctl(), on_tick=_once(started))
    return code, _drain(q)


def test_ctrl_c_in_remux_with_restore_keeps_master(ns, monkeypatch):
    code, ev = _run_remux_ctrl_c(ns, monkeypatch, _restore_ok)
    assert code == 130
    out = _out(ns)
    with open(out, "rb") as fh:
        assert fh.read() == MASTER
    assert not os.path.exists(D._temp_path(out))
    infos = [e.text for e in ev if isinstance(e, R.Info)]
    assert REMUX_KEPT in infos
    assert not any("NÃO foi possível remover" in t for t in infos)


def test_ctrl_c_in_remux_failed_restore_deletes_nothing(ns, monkeypatch):
    code, ev = _run_remux_ctrl_c(ns, monkeypatch, _restore_failed)
    assert code == 130
    out = _out(ns)
    temp = D._temp_path(out)
    with open(out, "rb") as fh:
        assert fh.read() == b"TRUNC"
    with open(temp, "rb") as fh:
        assert fh.read() == MASTER
    infos = [e.text for e in ev if isinstance(e, R.Info)]
    assert any(os.path.basename(temp) in t for t in infos)
    assert not any(t.startswith("Master mantido") for t in infos)


def test_ctrl_c_in_remux_that_completes_keeps_master(ns, monkeypatch):
    code, ev = _run_remux_ctrl_c(ns, monkeypatch, _remux_completed)
    assert code == 130
    out = _out(ns)
    with open(out, "rb") as fh:
        assert fh.read() == b"REMUXED"
    assert not os.path.exists(D._temp_path(out))
    assert REMUX_KEPT in [e.text for e in ev if isinstance(e, R.Info)]


def test_cancel_key_in_remux_with_restore_keeps_master(ns, monkeypatch):
    started = threading.Event()
    release = threading.Event()
    _fake_encode(monkeypatch, _remux_body(started, release, _restore_ok))
    ctl = R.CancelControl(terminate=lambda: release.set() or True)
    answers = []

    def tick():
        if started.is_set() and not answers:
            answers.append(ctl.request_cancel())

    q = queue.Queue()
    assert D.run_single(ns, q, ctl, on_tick=tick) == 130
    assert answers == [True]
    with open(_out(ns), "rb") as fh:
        assert fh.read() == MASTER
    ev = _drain(q)
    assert REMUX_KEPT in [e.text for e in ev if isinstance(e, R.Info)]
    assert not any(isinstance(e, R.Error) for e in ev)


def test_ctrl_c_at_done_keeps_master_and_reports(ns, monkeypatch):
    at_done = threading.Event()
    release = threading.Event()
    html, json_ = _qc_paths(_out(ns))

    def body(inp, out, rep):
        rep.emit(R.Stage(R.PREPARING))
        with open(out, "wb") as fh:
            fh.write(MASTER)
        rep.emit(R.Stage(R.QC))
        for path in (html, json_):
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("novo")
        rep.emit(R.Stage(R.DONE))
        at_done.set()
        release.wait(5)
    _fake_encode(monkeypatch, body)
    monkeypatch.setattr(RE, "terminate_active_ffmpeg", lambda *a, **k: release.set() or False)
    q = queue.Queue()
    assert D.run_single(ns, q, _ctl(), on_tick=_once(at_done)) == 130
    with open(_out(ns), "rb") as fh:
        assert fh.read() == MASTER
    for path in (html, json_):
        with open(path, encoding="utf-8") as fh:
            assert fh.read() == "novo"
    assert "Master mantido — QC concluído." in [e.text for e in _drain(q) if isinstance(e, R.Info)]


def test_worker_timeout_touches_no_file(ns, monkeypatch):
    monkeypatch.setattr(D, "WORKER_WAIT_S", 0.3)
    started = threading.Event()
    hold = threading.Event()

    def body(inp, out, rep):
        rep.emit(R.Stage(R.PASS, "1"))
        with open(out, "wb") as fh:
            fh.write(PARTIAL)
        started.set()
        hold.wait(30)
    _fake_encode(monkeypatch, body)
    monkeypatch.setattr(RE, "terminate_active_ffmpeg", lambda *a, **k: False)
    q = queue.Queue()
    try:
        assert D.run_single(ns, q, _ctl(), on_tick=_once(started)) == 130
        with open(_out(ns), "rb") as fh:
            assert fh.read() == PARTIAL
        ev = _drain(q)
        infos = [e.text for e in ev if isinstance(e, R.Info)]
        name = os.path.basename(_out(ns))
        assert (f"O encoder não encerrou em 0.3 s — nenhum arquivo foi alterado. {name} pode estar "
                "incompleto e NÃO passou pelo controle de qualidade.") in infos
        assert not any(isinstance(e, R.Cancel) and e.phase == "cleaned" for e in ev)
    finally:
        hold.set()


PARTIAL = b"PARCIAL-R02"


def _partial_then_fail(inp, out, rep):
    rep.emit(R.Stage(R.PREPARING))
    rep.emit(R.Stage(R.PASS, "1"))
    with open(out, "wb") as fh:
        fh.write(PARTIAL)
    raise ValueError("falhou no meio")


def test_failure_removes_partial_output_created_here(ns, monkeypatch):
    _fake_encode(monkeypatch, _partial_then_fail)
    q = queue.Queue()
    assert D.run_single(ns, q, _ctl(), on_tick=lambda: None) == 1
    assert not os.path.exists(_out(ns))
    ev = _drain(q)
    assert any(isinstance(e, R.Error) and e.kind == "ValueError" for e in ev)
    infos = [e.text for e in ev if isinstance(e, R.Info)]
    assert f"output parcial removido: {os.path.basename(_out(ns))}" in infos


def test_failure_keeps_preexisting_output(ns, monkeypatch):
    out = _out(ns)
    with open(out, "wb") as fh:
        fh.write(b"old")

    def body(inp, o, rep):
        rep.emit(R.Stage(R.PREPARING))
        raise ValueError("falhou")
    _fake_encode(monkeypatch, body)
    assert D.run_single(ns, queue.Queue(), _ctl(), on_tick=lambda: None) == 1
    with open(out, "rb") as fh:
        assert fh.read() == b"old"


def test_failure_unremovable_partial_emits_warnings(ns, monkeypatch):
    _fake_encode(monkeypatch, _partial_then_fail)
    monkeypatch.setattr(render_queue, "discard_partial_output", lambda job: False)
    q = queue.Queue()
    assert D.run_single(ns, q, _ctl(), on_tick=lambda: None) == 1
    infos = [e.text for e in _drain(q) if isinstance(e, R.Info)]
    assert any("NÃO foi possível remover" in t for t in infos)
    assert any("NÃO passou pelo controle de qualidade" in t for t in infos)
    with open(_out(ns), "rb") as fh:
        assert fh.read() == PARTIAL


def test_failure_after_encode_keeps_master(ns, monkeypatch):
    def body(inp, out, rep):
        rep.emit(R.Stage(R.PREPARING))
        with open(out, "wb") as fh:
            fh.write(b"MASTER")
        rep.emit(R.Stage(R.QC))
        raise ValueError("qc quebrou")
    _fake_encode(monkeypatch, body)
    q = queue.Queue()
    assert D.run_single(ns, q, _ctl(), on_tick=lambda: None) == 1
    with open(_out(ns), "rb") as fh:
        assert fh.read() == b"MASTER"
    infos = [e.text for e in _drain(q) if isinstance(e, R.Info)]
    name = os.path.basename(_out(ns))
    assert f"Falha após o encode — master mantido sem QC concluído: {name}" in infos


def test_failure_with_remux_temp_deletes_nothing(ns, monkeypatch):
    def body(inp, out, rep):
        rep.emit(R.Stage(R.FINALIZING, "remux"))
        with open(out, "wb") as fh:
            fh.write(b"TRUNCADO")
        with open(D._temp_path(out), "wb") as fh:
            fh.write(b"ORIGINAL")
        raise ValueError("remux quebrou")
    _fake_encode(monkeypatch, body)
    q = queue.Queue()
    assert D.run_single(ns, q, _ctl(), on_tick=lambda: None) == 1
    out = _out(ns)
    with open(out, "rb") as fh:
        assert fh.read() == b"TRUNCADO"
    with open(D._temp_path(out), "rb") as fh:
        assert fh.read() == b"ORIGINAL"
    infos = [e.text for e in _drain(q) if isinstance(e, R.Info)]
    assert any(os.path.basename(D._temp_path(out)) in t and "nada foi apagado" in t for t in infos)


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


def _batch_fail_first(fail):
    def body(inp, out, rep):
        rep.emit(R.Stage(R.PREPARING))
        rep.emit(R.Stage(R.PASS, "1"))
        if fail and os.path.basename(inp) == "a.mp4":
            with open(out, "wb") as fh:
                fh.write(PARTIAL)
            raise ValueError("falhou no meio")
        with open(out, "wb") as fh:
            fh.write(b"OK")
        rep.emit(R.Stage(R.DONE))
    return body


def test_batch_failure_removes_partial_and_rerun_retries_job(batch_ns, monkeypatch):
    _, jobs = D._batch_jobs(batch_ns)
    _fake_encode(monkeypatch, _batch_fail_first(fail=True))
    q = queue.Queue()
    assert D.run_batch(batch_ns, q, _ctl(), on_tick=lambda: None) == 1
    ev = _drain(q)
    assert not os.path.exists(jobs[0].output_path)
    assert any(isinstance(e, R.JobDone) and e.index == 0 and e.status == "falha" for e in ev)
    assert any(isinstance(e, R.JobDone) and e.index == 1 and e.status == "ok" for e in ev)
    with open(jobs[1].output_path, "rb") as fh:
        assert fh.read() == b"OK"

    _fake_encode(monkeypatch, _batch_fail_first(fail=False))
    q = queue.Queue()
    assert D.run_batch(batch_ns, q, _ctl(), on_tick=lambda: None) == 0
    ev = _drain(q)
    assert any(isinstance(e, R.JobStart) and e.index == 0 for e in ev)
    assert not any(isinstance(e, R.JobSkip) and e.index == 0 for e in ev)


def test_batch_stage_does_not_leak_between_jobs(batch_ns, monkeypatch):
    _, jobs = D._batch_jobs(batch_ns)

    def body(inp, out, rep):
        if os.path.basename(inp) == "a.mp4":
            rep.emit(R.Stage(R.PREPARING))
            with open(out, "wb") as fh:
                fh.write(b"OK")
            rep.emit(R.Stage(R.DONE))
            return
        with open(out, "wb") as fh:
            fh.write(PARTIAL)
        raise ValueError("falhou sem Stage")
    _fake_encode(monkeypatch, body)
    q = queue.Queue()
    assert D.run_batch(batch_ns, q, _ctl(), on_tick=lambda: None) == 1
    ev = _drain(q)
    assert any(isinstance(e, R.JobDone) and e.index == 0 and e.status == "ok" for e in ev)
    assert any(isinstance(e, R.JobDone) and e.index == 1 and e.status == "falha" for e in ev)
    assert os.path.exists(jobs[0].output_path)
    assert not os.path.exists(jobs[1].output_path)


def test_batch_failure_unremovable_partial_warns(batch_ns, monkeypatch):
    _, jobs = D._batch_jobs(batch_ns)
    _fake_encode(monkeypatch, _batch_fail_first(fail=True))
    monkeypatch.setattr(render_queue, "discard_partial_output", lambda job: False)
    q = queue.Queue()
    assert D.run_batch(batch_ns, q, _ctl(), on_tick=lambda: None) == 1
    infos = [e.text for e in _drain(q) if isinstance(e, R.Info)]
    assert any("NÃO foi possível remover" in t for t in infos)
    assert any("rodar a fila de novo" in t for t in infos)
    assert os.path.exists(jobs[0].output_path)


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
