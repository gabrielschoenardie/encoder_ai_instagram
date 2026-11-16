"""Cancelamento no laço de frames do Cineon (P3FF3 / P3F-1b).

`CancelRequested` herda de `BaseException`: sem o `except _rep.CancelRequested`
de `_render_pass`, ele atravessaria o `except Exception` e sairia sem encerrar
o FFmpeg. Sem FFmpeg real e sem vídeo: `av.open`, `subprocess.Popen`, probe,
hardware e LUT são falsos; os frames são sintéticos 16x16.
"""
import importlib
import io
import types
from fractions import Fraction
from unittest import mock

import numpy as np
import pytest

av = pytest.importorskip("av")

import cineon_pipeline as cp  # noqa: E402
import reporter as rep  # noqa: E402

R = importlib.import_module("Reels_Encoder_v2_FINAL")

W = H = 16
N_FRAMES = 3
PARTIAL = b"partial-mp4-bytes"


def _probe():
    return R.VideoProbe(
        physical_width=W, physical_height=H, rotation=0,
        width=W, height=H, fps_rational="30/1", fps_int=30,
        duration=1.0, nb_frames=N_FRAMES, is_hdr=False, hdr_type="",
        color_primaries="bt709", color_transfer="bt709",
        color_space="bt709", color_range="tv", max_luminance=None,
    )


def _frame():
    arr = np.full((H * 3 // 2, W), 128, np.uint8)
    frame = av.VideoFrame.from_ndarray(arr, format="yuv420p")
    frame.colorspace = 1
    frame.color_range = 1
    return frame


def _container():
    stream = types.SimpleNamespace(
        width=W, height=H, average_rate=Fraction(30),
        codec_context=types.SimpleNamespace(name="h264"),
    )
    frames = [_frame() for _ in range(N_FRAMES)]
    return types.SimpleNamespace(
        streams=types.SimpleNamespace(video=[stream]),
        decode=lambda video=0: iter(frames),
        close=lambda: None,
    )


class _FakeLut:
    lut_size = 2
    domain_min = (0.0, 0.0, 0.0)
    domain_max = (1.0, 1.0, 1.0)

    def __init__(self, path):
        self.path = path


def _fake_proc(order):
    proc = mock.MagicMock()
    proc.pid = 4242
    proc.stdin = mock.MagicMock()
    proc.stdout = None
    proc.stderr = io.BytesIO(b"")
    proc.poll.return_value = None
    proc.terminate.side_effect = lambda: order.append("terminate")
    proc.wait.side_effect = lambda timeout=None: order.append("wait") or -15
    proc.kill.side_effect = lambda: order.append("kill")
    return proc


class _Reporter:
    def __init__(self, order, exc_factory, label):
        self.order = order
        self.exc_factory = exc_factory
        self.label = label
        self.events = []

    def emit(self, event):
        self.events.append(event)
        if isinstance(event, rep.Progress):
            self.order.append(self.label)
            raise self.exc_factory()


@pytest.fixture
def harness(monkeypatch, tmp_path):
    monkeypatch.setattr(R.console, "print", lambda *a, **k: None)
    monkeypatch.setattr(R, "probe_video", lambda path: _probe())
    monkeypatch.setattr(
        R, "detect_hardware", lambda: R._calculate_recommendations(R.HardwareProfile())
    )
    monkeypatch.setattr(cp, "_validate_cineon_constants", lambda: None)
    monkeypatch.setattr(cp, "LUT3D", _FakeLut)
    monkeypatch.setattr(
        cp, "process_frame_full_pipeline",
        lambda rgb, lut, exposure_offset=0.0, saturation=1.0: np.zeros((H, W, 3), np.uint8),
    )
    monkeypatch.setattr(av, "open", lambda path: _container())

    def _no_remux(*a, **k):
        raise AssertionError("remux executado após cancelamento/erro no laço")

    monkeypatch.setattr(R, "_run_ffmpeg_tracked", _no_remux)

    order = []
    proc = _fake_proc(order)
    popen_calls = []

    def _popen(cmd, **kwargs):
        popen_calls.append(list(cmd))
        return proc

    monkeypatch.setattr(R.subprocess, "Popen", _popen)

    lut = tmp_path / "fake.cube"
    lut.write_text("LUT_3D_SIZE 2\n")
    out = tmp_path / "out.mp4"
    out.write_bytes(PARTIAL)

    ns = types.SimpleNamespace(
        order=order, proc=proc, popen_calls=popen_calls,
        input=str(tmp_path / "in.mp4"), output=out,
        temp=tmp_path / "out_temp.mp4", lut=str(lut),
    )
    try:
        yield ns
    finally:
        R._register_ffmpeg(None)


def _run(h, reporter):
    R.run_ffmpeg_with_cineon(
        h.input, str(h.output), mode="crf", loudnorm_enabled=False,
        target_fps="30", scale_mode="off", show_hardware=False,
        cineon_lut_path=h.lut, enhance_enabled=False, reporter=reporter,
    )


def _assert_single_pipe_and_no_remux(h, reporter):
    assert len(h.popen_calls) == 1
    cmd = h.popen_calls[0]
    assert "rawvideo" in cmd and cmd[cmd.index("-i") + 1] == "-"
    assert h.proc.stdin.write.called
    assert h.proc.stdin.close.called
    assert h.output.read_bytes() == PARTIAL
    assert not h.temp.exists()
    assert not any(
        isinstance(e, rep.Stage) and e.name == rep.FINALIZING for e in reporter.events
    )


def test_cancel_in_frame_loop_terminates_ffmpeg_then_propagates(harness):
    reporter = _Reporter(harness.order, rep.CancelRequested, "cancel")

    with pytest.raises(rep.CancelRequested) as excinfo:
        _run(harness, reporter)

    assert type(excinfo.value) is rep.CancelRequested
    assert harness.order[:2] == ["cancel", "terminate"]
    harness.proc.terminate.assert_called_once_with()
    _assert_single_pipe_and_no_remux(harness, reporter)


def test_ordinary_error_in_frame_loop_still_becomes_runtime_error(harness):
    reporter = _Reporter(harness.order, lambda: ValueError("boom"), "error")

    with pytest.raises(RuntimeError, match="Encoding interrompido"):
        _run(harness, reporter)

    assert harness.order[:2] == ["error", "terminate"]
    harness.proc.terminate.assert_called_once_with()
    _assert_single_pipe_and_no_remux(harness, reporter)
