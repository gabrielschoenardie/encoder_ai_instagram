"""E2E do Cineon com FFmpeg real (BDF3, BDF4, BDF5, BDF1).

Fonte sintética: testsrc2 90x160 + sine 48 kHz, 1 s. Pula sem ffmpeg e ffprobe
executáveis.
"""
import importlib
import json
import os
import subprocess

import pytest

pytest.importorskip("av")
pytest.importorskip("colour")

from ui.binaries import FFMPEG, FFPROBE  # noqa: E402

R = importlib.import_module("Reels_Encoder_v2_FINAL")


def _runs(binary):
    try:
        return subprocess.run(
            [binary, "-hide_banner", "-version"], capture_output=True, timeout=60
        ).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


@pytest.fixture(autouse=True)
def _require_ffmpeg_and_silence(monkeypatch):
    if not (_runs(FFMPEG) and _runs(FFPROBE)):
        pytest.skip(f"ffmpeg/ffprobe não executam: {FFMPEG}, {FFPROBE}")
    monkeypatch.setattr(R.console, "print", lambda *a, **k: None)


@pytest.fixture
def popen_calls(monkeypatch):
    calls = []
    original = subprocess.Popen

    def _recording_popen(args, *a, **k):
        calls.append(list(args) if isinstance(args, (list, tuple)) else [args])
        return original(args, *a, **k)

    monkeypatch.setattr(subprocess, "Popen", _recording_popen)
    return calls


def _source(tmp_path, fps):
    src = str(tmp_path / f"src_{fps}fps.mp4")
    proc = subprocess.run(
        [
            FFMPEG, "-hide_banner", "-v", "error", "-y",
            "-f", "lavfi", "-i", f"testsrc2=size=90x160:rate={fps}:duration=1",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=1",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
            "-c:a", "aac", "-shortest", src,
        ],
        capture_output=True, timeout=120,
    )
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "ignore")[-800:]
    return src


def _encode(tmp_path, fps, mode):
    src = _source(tmp_path, fps)
    out = str(tmp_path / f"out_{fps}_{mode}.mp4")
    R.run_ffmpeg_with_cineon(
        src, out, mode=mode, target_fps="30", scale_mode="off",
        loudnorm_enabled=False, enhance_enabled=False, show_hardware=False,
    )
    return out


def _streams(path):
    out = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries",
         "stream=codec_type,nb_frames,duration", "-of", "json", path],
        capture_output=True, check=True, timeout=60,
    ).stdout
    return {s["codec_type"]: s for s in json.loads(out)["streams"]}


def _assert_av_in_sync(path, expected_frames):
    streams = _streams(path)
    video, audio = streams["video"], streams["audio"]
    assert int(video["nb_frames"]) == expected_frames
    assert abs(float(video["duration"]) - float(audio["duration"])) <= 1 / 30 + 1e-6


def _pipe_commands(calls):
    return [c for c in calls if "rawvideo" in c and "-i" in c and c[c.index("-i") + 1] == "-"]


def test_60fps_crf_is_30_frames_in_sync(tmp_path):
    out = _encode(tmp_path, 60, "crf")
    _assert_av_in_sync(out, 30)


def test_60fps_2pass_is_30_frames_in_sync_and_leaves_no_logs(tmp_path, monkeypatch):
    seen_logs = []
    original = R._analyze_pass1_log

    def _spy(logfile_base):
        seen_logs.append(os.path.exists(f"{logfile_base}-0.log"))
        return original(logfile_base)

    monkeypatch.setattr(R, "_analyze_pass1_log", _spy)
    out = _encode(tmp_path, 60, "2pass")
    assert seen_logs == [True]
    _assert_av_in_sync(out, 30)
    log_prefix = os.path.basename(out) + "_2pass"
    assert not [p.name for p in tmp_path.iterdir() if p.name.startswith(log_prefix)]


def test_24fps_crf_is_30_frames(tmp_path):
    out = _encode(tmp_path, 24, "crf")
    assert int(_streams(out)["video"]["nb_frames"]) == 30


@pytest.mark.parametrize("mode, n_pipes", [("crf", 1), ("2pass", 2)])
def test_every_pipe_command_converts_with_bt709_vf(tmp_path, popen_calls, mode, n_pipes):
    _encode(tmp_path, 60, mode)
    pipes = _pipe_commands(popen_calls)
    assert len(pipes) == n_pipes
    for cmd in pipes:
        assert "-vf" in cmd
        assert cmd[cmd.index("-vf") + 1] == R._CINEON_RGB_TO_YUV709_VF
