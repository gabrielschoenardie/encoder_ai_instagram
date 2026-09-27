"""Entrada YUV->RGB do Cineon (BDF2) e recusa de fonte HDR (BDF14).

Sem FFmpeg: frames sintéticos do PyAV com `colorspace`/`color_range`
atribuídos (graváveis a partir do PyAV 17).
"""
import importlib

import numpy as np
import pytest

av = pytest.importorskip("av")

R = importlib.import_module("Reels_Encoder_v2_FINAL")

W = H = 16
RED = (255, 0, 0)
SKIN = (204, 153, 128)
GRAY = (128, 128, 128)


@pytest.fixture(autouse=True)
def _silence_console(monkeypatch):
    monkeypatch.setattr(R.console, "print", lambda *a, **k: None)


def _bt709_ycbcr(rgb, full_range):
    r, g, b = (c / 255.0 for c in rgb)
    kr, kb = 0.2126, 0.0722
    y = kr * r + (1 - kr - kb) * g + kb * b
    cb = (b - y) / (2 * (1 - kb))
    cr = (r - y) / (2 * (1 - kr))
    if full_range:
        vals = (255 * y, 128 + 255 * cb, 128 + 255 * cr)
    else:
        vals = (16 + 219 * y, 128 + 224 * cb, 128 + 224 * cr)
    return tuple(int(min(255, max(0, round(v)))) for v in vals)


def _frame(ycbcr, colorspace, color_range):
    y, cb, cr = ycbcr
    arr = np.empty((H * 3 // 2, W), np.uint8)
    arr[:H] = y
    arr[H:H + H // 4] = cb
    arr[H + H // 4:] = cr
    frame = av.VideoFrame.from_ndarray(arr, format="yuv420p")
    frame.colorspace = colorspace
    frame.color_range = color_range
    return frame


def _assert_rgb(frame, rgb):
    out = R._pyav_frame_to_rgb24(frame)
    assert out.shape == (H, W, 3)
    assert out.dtype == np.uint8
    center = out[H // 2, W // 2].astype(int)
    assert np.all(np.abs(center - np.array(rgb)) <= 2), (center.tolist(), rgb)


def test_red_bt709_tv_range():
    assert _bt709_ycbcr(RED, full_range=False) == (63, 102, 240)
    _assert_rgb(_frame((63, 102, 240), colorspace=1, color_range=1), RED)


def test_red_bt709_full_range():
    _assert_rgb(_frame(_bt709_ycbcr(RED, full_range=True), colorspace=1, color_range=2), RED)


def test_untagged_frame_is_treated_as_bt709():
    _assert_rgb(_frame((63, 102, 240), colorspace=2, color_range=0), RED)


@pytest.mark.parametrize("rgb", [SKIN, GRAY])
def test_skin_and_gray_bt709_tv_range(rgb):
    _assert_rgb(_frame(_bt709_ycbcr(rgb, full_range=False), colorspace=1, color_range=1), rgb)


def test_hdr_source_refused_before_any_video_io(monkeypatch, tmp_path):
    pytest.importorskip("colour")
    probe = R.VideoProbe(
        physical_width=1080, physical_height=1920, rotation=0,
        width=1080, height=1920, fps_rational="30/1", fps_int=30,
        duration=2.0, nb_frames=60, is_hdr=True, hdr_type="HDR10 (PQ)",
        color_primaries="bt2020", color_transfer="smpte2084",
        color_space="bt2020nc", color_range="tv", max_luminance=1000.0,
    )
    monkeypatch.setattr(R, "probe_video", lambda path: probe)

    def _forbidden(*args, **kwargs):
        raise AssertionError("I/O de vídeo antes da recusa de HDR")

    monkeypatch.setattr(av, "open", _forbidden)
    monkeypatch.setattr(R.subprocess, "Popen", _forbidden)

    with pytest.raises(RuntimeError, match="HDR10 \\(PQ\\)") as exc:
        R.run_ffmpeg_with_cineon(
            str(tmp_path / "in.mp4"), str(tmp_path / "out.mp4"), show_hardware=False
        )
    assert "--cineon-pipeline off" in str(exc.value)
