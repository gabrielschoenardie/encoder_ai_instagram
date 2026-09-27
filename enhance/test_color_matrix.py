"""Matriz RGB<->YUV das cadeias de saída (BDF1).

A carta de 5 patches é lida de volta como `yuv420p` cru, sem conversão na
leitura. Pula se o FFmpeg resolvido por `ui.binaries` não executar; os testes de
cadeia pulam também sem `zscale`.
"""
import importlib
import subprocess

import numpy as np
import pytest

from ui.binaries import FFMPEG

R = importlib.import_module("Reels_Encoder_v2_FINAL")

P = 64
PATCHES = (
    (255, 0, 0),
    (0, 255, 0),
    (0, 0, 255),
    (204, 153, 128),
    (128, 128, 128),
)
W, H = P * len(PATCHES), P


def _ffmpeg_output(*args):
    try:
        proc = subprocess.run(
            [FFMPEG, "-hide_banner", *args], capture_output=True, timeout=60
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout if proc.returncode == 0 else None


def _require_ffmpeg():
    if _ffmpeg_output("-version") is None:
        pytest.skip(f"FFmpeg não executa: {FFMPEG}")


def _require_zscale():
    _require_ffmpeg()
    filters = _ffmpeg_output("-filters") or b""
    if b" zscale " not in filters:
        pytest.skip("FFmpeg sem zscale")


@pytest.fixture(autouse=True)
def _silence_console(monkeypatch):
    monkeypatch.setattr(R.console, "print", lambda *a, **k: None)


def _chart_rgb24():
    img = np.zeros((H, W, 3), np.uint8)
    for i, rgb in enumerate(PATCHES):
        img[:, i * P:(i + 1) * P] = rgb
    return img.tobytes()


def _bt709_tv(rgb):
    r, g, b = (c / 255.0 for c in rgb)
    kr, kb = 0.2126, 0.0722
    y = kr * r + (1 - kr - kb) * g + kb * b
    cb = (b - y) / (2 * (1 - kb))
    cr = (r - y) / (2 * (1 - kr))
    return 16 + 219 * y, 128 + 224 * cb, 128 + 224 * cr


def _planes(raw):
    y = np.frombuffer(raw[:W * H], np.uint8).reshape(H, W).astype(float)
    u = np.frombuffer(raw[W * H:W * H * 5 // 4], np.uint8).reshape(H // 2, W // 2)
    v = np.frombuffer(raw[W * H * 5 // 4:W * H * 3 // 2], np.uint8).reshape(H // 2, W // 2)
    return y, u.astype(float), v.astype(float)


def _patch_means(raw):
    y, u, v = _planes(raw)
    out = []
    for i in range(len(PATCHES)):
        ys = slice(i * P + 16, (i + 1) * P - 16)
        cs = slice(i * P // 2 + 8, (i + 1) * P // 2 - 8)
        out.append((y[16:-16, ys].mean(), u[8:-8, cs].mean(), v[8:-8, cs].mean()))
    return out


def _run(args, stdin=None):
    proc = subprocess.run(
        [FFMPEG, "-hide_banner", "-v", "error", "-y", *args],
        input=stdin, capture_output=True, timeout=120,
    )
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "ignore")[-800:]
    return proc.stdout


_RGB_IN = ["-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", "30", "-i", "-"]
_YUV_OUT = ["-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "yuv420p", "-"]
_TAGS_709 = [
    "-color_primaries", "bt709", "-color_trc", "bt709",
    "-colorspace", "bt709", "-color_range", "tv",
]


def _bt709_source(tmp_path):
    src = str(tmp_path / "chart709.mkv")
    _run([*_RGB_IN, "-vf", R._CINEON_RGB_TO_YUV709_VF, *_TAGS_709, "-c:v", "ffv1", src],
         stdin=_chart_rgb24())
    return src


def test_cineon_output_vf_is_bt709():
    _require_ffmpeg()
    raw = _run([*_RGB_IN, "-vf", R._CINEON_RGB_TO_YUV709_VF, *_YUV_OUT], stdin=_chart_rgb24())
    for rgb, measured in zip(PATCHES, _patch_means(raw)):
        expected = _bt709_tv(rgb)
        for m, e in zip(measured, expected):
            assert abs(m - e) <= 1, (rgb, measured, expected)


def test_sdr_chain_is_bt709(tmp_path):
    _require_zscale()
    src = _bt709_source(tmp_path)
    source_raw = _run(["-i", src, *_YUV_OUT])
    vf = R.build_sdr_float_pipeline(None, None, lut_enabled=False, dither_enabled=False)
    out_raw = _run(["-i", src, "-vf", vf, *_YUV_OUT])
    for rgb, before, after in zip(PATCHES, _patch_means(source_raw), _patch_means(out_raw)):
        for b, a in zip(before, after):
            assert abs(a - b) <= 1, (rgb, before, after)


def test_hdr_chain_final_conversion_is_zscale(tmp_path):
    _require_zscale()
    src = _bt709_source(tmp_path)
    hdr = str(tmp_path / "chart_pq.mkv")
    _run([
        "-i", src, "-vf",
        "zscale=t=linear:npl=100,format=gbrpf32le,"
        "zscale=p=bt2020:t=smpte2084:m=bt2020nc:r=tv:npl=100,format=yuv420p10le",
        "-color_primaries", "bt2020", "-color_trc", "smpte2084",
        "-colorspace", "bt2020nc", "-color_range", "tv",
        "-c:v", "ffv1", hdr,
    ])
    vf = R.build_scene_referred_hdr_pipeline(
        scale_filter=None,
        target_resolution=None,
        tonemap_algorithm="mobius",
        dither_enabled=False,
        input_color=("bt2020", "smpte2084", "bt2020nc"),
    )
    anchor = "zscale=t=bt709:m=bt709:r=tv:p=bt709"
    assert vf.count(anchor) == 1
    pinned = vf.replace(anchor, anchor + ",format=yuv420p")
    as_is = _run(["-i", hdr, "-vf", vf, *_YUV_OUT])
    forced = _run(["-i", hdr, "-vf", pinned, *_YUV_OUT])
    assert len(as_is) == W * H * 3 // 2
    assert as_is == forced
