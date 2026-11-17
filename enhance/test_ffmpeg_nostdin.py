"""P3HF1: todo FFmpeg do motor que não lê dados do stdin roda com `-nostdin` e
`stdin=DEVNULL`, para não consumir teclas do console destinadas à TUI.

O encode Cineon lê os frames do stdin (`-i -`, `stdin=PIPE`): ali o stdin já não
é o console e `-nostdin` não se aplica. Sem FFmpeg real: Popen/run são falsos.
"""
import importlib
import io
import subprocess
import types
from fractions import Fraction
from unittest import mock

import numpy as np
import pytest

import ebu_meter as E

R = importlib.import_module("Reels_Encoder_v2_FINAL")


def _probe(w=16, h=16, nb_frames=3):
    return R.VideoProbe(
        physical_width=w, physical_height=h, rotation=0,
        width=w, height=h, fps_rational="30/1", fps_int=30,
        duration=1.0, nb_frames=nb_frames, is_hdr=False, hdr_type="",
        color_primaries="bt709", color_transfer="bt709",
        color_space="bt709", color_range="tv", max_luminance=None,
    )


class _Reporter:
    def __init__(self):
        self.events = []

    def emit(self, event):
        self.events.append(event)


def _done_proc(stderr, running=False):
    proc = mock.MagicMock()
    proc.pid = 4242
    proc.returncode = 0
    proc.stdin = mock.MagicMock()
    proc.stderr = stderr
    proc.poll.return_value = None if running else 0
    proc.wait.return_value = 0
    proc.communicate.return_value = ("", "")
    return proc


@pytest.fixture
def spawns(monkeypatch):
    calls = []

    def _popen(cmd, **kwargs):
        calls.append((list(cmd), kwargs))
        if kwargs.get("stdin") is subprocess.PIPE:
            return _done_proc(io.BytesIO(b""), running=True)
        return _done_proc(io.StringIO(""))

    def _run(cmd, **kwargs):
        calls.append((list(cmd), kwargs))
        return subprocess.CompletedProcess(cmd, 0, "", "")

    real_tracked = R._run_ffmpeg_tracked
    monkeypatch.setattr(subprocess, "Popen", _popen)
    monkeypatch.setattr(subprocess, "run", _run)
    monkeypatch.setattr(R, "_run_ffmpeg_tracked", lambda cmd, **k: real_tracked(cmd, popen=_popen, **k))
    monkeypatch.setattr(R.console, "print", lambda *a, **k: None)
    monkeypatch.setattr(R, "probe_video", lambda path: _probe(1080, 1920, 30))
    monkeypatch.setattr(R, "probe_audio_channels", lambda path: 2)
    monkeypatch.setattr(R, "detect_hardware", lambda: R._calculate_recommendations(R.HardwareProfile()))
    try:
        yield calls
    finally:
        R._register_ffmpeg(None)


def _ffmpeg(calls):
    return [(c, k) for c, k in calls if c[0] == R.FFMPEG]


def _assert_nostdin(cmd, kwargs):
    assert cmd[1] == "-nostdin", cmd
    assert cmd.count("-nostdin") == 1
    assert kwargs.get("stdin") is subprocess.DEVNULL


@pytest.mark.parametrize("mode, encodes", [("crf", 1), ("2pass", 2)])
def test_native_encode_and_loudnorm_run_with_nostdin(spawns, tmp_path, mode, encodes):
    R.run_ffmpeg(str(tmp_path / "in.mp4"), str(tmp_path / "out.mp4"), mode=mode, lut_enabled=False,
                 loudnorm_enabled=True, show_hardware=False, reporter=_Reporter())
    ff = _ffmpeg(spawns)
    assert len([c for c, _ in ff if "libx264" in c]) == encodes
    assert any("loudnorm" in " ".join(c) for c, _ in ff)
    for cmd, kwargs in ff:
        _assert_nostdin(cmd, kwargs)


def test_derotate_remux_runs_with_nostdin(spawns, tmp_path):
    R._strip_residual_rotation(str(tmp_path / "out.mp4"))
    ff = _ffmpeg(spawns)
    assert len(ff) == 1 and "-display_rotation" in ff[0][0]
    _assert_nostdin(*ff[0])


def test_ebur128_measure_runs_with_nostdin(spawns):
    E.measure_loudness("clip.mp4")
    ff = [(c, k) for c, k in spawns if c[0] == E.FFMPEG]
    assert len(ff) == 1 and "ebur128=peak=true" in ff[0][0]
    _assert_nostdin(*ff[0])


def test_cineon_pipe_reads_stdin_and_colr_remux_runs_with_nostdin(spawns, tmp_path, monkeypatch):
    av = pytest.importorskip("av")
    import cineon_pipeline as cp

    monkeypatch.setattr(R, "probe_video", lambda path: _probe())

    def _container():
        arr = np.full((24, 16), 128, np.uint8)
        frame = av.VideoFrame.from_ndarray(arr, format="yuv420p")
        stream = types.SimpleNamespace(width=16, height=16, average_rate=Fraction(30),
                                       codec_context=types.SimpleNamespace(name="h264"))
        return types.SimpleNamespace(streams=types.SimpleNamespace(video=[stream]),
                                     decode=lambda video=0: iter([frame] * 3), close=lambda: None)

    class _FakeLut:
        lut_size = 2
        domain_min = (0.0, 0.0, 0.0)
        domain_max = (1.0, 1.0, 1.0)

        def __init__(self, path):
            self.path = path

    monkeypatch.setattr(cp, "_validate_cineon_constants", lambda: None)
    monkeypatch.setattr(cp, "LUT3D", _FakeLut)
    monkeypatch.setattr(cp, "process_frame_full_pipeline",
                        lambda rgb, lut, exposure_offset=0.0, saturation=1.0: np.zeros((16, 16, 3), np.uint8))
    monkeypatch.setattr(av, "open", lambda path: _container())
    lut = tmp_path / "fake.cube"
    lut.write_text("LUT_3D_SIZE 2\n")
    out = tmp_path / "out.mp4"
    out.write_bytes(b"mp4")

    R.run_ffmpeg_with_cineon(str(tmp_path / "in.mp4"), str(out), mode="crf", loudnorm_enabled=True,
                             target_fps="30", scale_mode="off", show_hardware=False,
                             cineon_lut_path=str(lut), enhance_enabled=False, reporter=_Reporter())

    ff = _ffmpeg(spawns)
    pipe = [(c, k) for c, k in ff if c[c.index("-i") + 1] == "-"]
    rest = [(c, k) for c, k in ff if c[c.index("-i") + 1] != "-"]
    assert len(pipe) == 1
    cmd, kwargs = pipe[0]
    assert "-nostdin" not in cmd and kwargs.get("stdin") is subprocess.PIPE
    assert any("+faststart+write_colr" in c and "copy" in c for c, _ in rest)
    assert any("loudnorm" in " ".join(c) for c, _ in rest)
    for cmd, kwargs in rest:
        _assert_nostdin(cmd, kwargs)
