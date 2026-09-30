import io
import json
import os
import re
import subprocess

import pytest

import Reels_Encoder_v2_FINAL as RE
from ui.config import EncodeConfig
from ui.theme import get_console

GOLDEN_DIR = os.path.join(os.path.dirname(__file__), "golden")
UPDATE = os.environ.get("REELS_UPDATE_GOLDEN") == "1"
SCENARIOS = {
    "native_crf": {"cineon_pipeline": "off", "mode": "crf"},
    "native_2pass": {"cineon_pipeline": "off", "mode": "2pass"},
    "cineon_crf": {"cineon_pipeline": "on", "mode": "crf"},
    "cineon_2pass": {"cineon_pipeline": "on", "mode": "2pass"},
}


def _runs(binary):
    try:
        return subprocess.run([binary, "-hide_banner", "-version"],
                              capture_output=True, timeout=60).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _fixed_hardware():
    hw = RE.HardwareProfile()
    hw.cpu_name, hw.cpu_cores, hw.cpu_threads, hw.cpu_freq_mhz = "GOLDEN CPU", 4, 8, 3000
    hw.cpu_arch, hw.os_name, hw.os_version = "x86_64", "GoldenOS", "1"
    hw.ram_total_gb, hw.ram_available_gb, hw.ram_percent_used = 16.0, 8.0, 50.0
    hw.tier, hw.perf_score = "medium", 50
    hw.recommended_threads, hw.recommended_preset = 1, "veryfast"
    hw.recommended_lookahead, hw.recommended_filter_threads = 10, 1
    hw.recommended_decoder_threads = 1
    return hw


def _source(tmp_path):
    src = str(tmp_path / "src.mp4")
    proc = subprocess.run(
        [RE.FFMPEG, "-hide_banner", "-v", "error", "-y",
         "-f", "lavfi", "-i", "testsrc2=size=90x160:rate=30:duration=1",
         "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=1",
         "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
         "-c:a", "aac", "-shortest", src],
        capture_output=True, timeout=120)
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "ignore")[-800:]
    return src


def _norm_token(tok, tmp):
    s = str(tok).replace("\\", "/")
    for needle, label in ((str(RE.FFMPEG).replace("\\", "/"), "<FFMPEG>"),
                          (str(RE.FFPROBE).replace("\\", "/"), "<FFPROBE>"),
                          (tmp, "<TMP>"),
                          (os.path.dirname(os.path.abspath(RE.__file__)).replace("\\", "/"), "<REPO>")):
        s = s.replace(needle, label)
    return s


def _norm_argv(argv, tmp):
    out = [re.sub(r"creation_time=.*", "creation_time=<TIME>", _norm_token(t, tmp), flags=re.S)
           for t in argv]
    if out and out[-1] == RE.DEVNULL_FF:
        out[-1] = "<NULL>"
    return out


def _norm_line(line, tmp):
    s = _norm_token(line, tmp)
    s = re.sub(r"(\[\w+) @ (?:0x)?[0-9a-fA-F]+\]", r"\1 @ 0xH]", s)
    s = re.sub(r"0x[0-9a-fA-F]+", "0xH", s)
    s = re.sub("[⠀-⣿]", "", s)
    s = re.sub("[─-╿▀-▟]+", "<BAR>", s)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\d+(?:[.,]\d+)?", "N", s)
    return s.rstrip()


def run_classic(tmp_path, monkeypatch, scenario, reporter=None):
    if SCENARIOS[scenario]["cineon_pipeline"] == "on":
        pytest.importorskip("av")
        pytest.importorskip("colour")
    src = _source(tmp_path)
    out = str(tmp_path / f"{scenario}.mp4")
    calls = []
    real_popen, real_run = subprocess.Popen, subprocess.run

    def _popen(args, *a, **k):
        calls.append(list(args))
        return real_popen(args, *a, **k)

    def _run(args, *a, **k):
        if isinstance(args, (list, tuple)):
            calls.append(list(args))
        return real_run(args, *a, **k)

    buf = io.StringIO()
    cons = get_console(file=buf, width=120, force_terminal=False, color_system=None,
                       legacy_windows=False)
    monkeypatch.setattr(subprocess, "Popen", _popen)
    monkeypatch.setattr(subprocess, "run", _run)
    monkeypatch.setattr(RE, "console", cons)
    monkeypatch.setattr(RE, "detect_hardware", _fixed_hardware)
    ns = EncodeConfig(input=src, ebu_meter="off", report="off", enhance="off",
                      **SCENARIOS[scenario]).to_namespace()
    kwargs = {} if reporter is None else {"reporter": reporter}
    RE._encode_single_file(src, out, ns, **kwargs)
    tmp = str(tmp_path).replace("\\", "/")
    return {
        "argv": [_norm_argv(c, tmp) for c in calls],
        "console": [_norm_line(line, tmp) for line in buf.getvalue().splitlines()],
        "output": out,
    }


@pytest.fixture(autouse=True)
def _require_ffmpeg():
    if not (_runs(RE.FFMPEG) and _runs(RE.FFPROBE)):
        pytest.skip("ffmpeg/ffprobe indisponíveis")


@pytest.mark.timeout(300)
@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_classic_path_matches_golden(tmp_path, monkeypatch, scenario):
    got = run_classic(tmp_path, monkeypatch, scenario)
    got.pop("output")
    path = os.path.join(GOLDEN_DIR, f"classic_{scenario}.json")
    if UPDATE:
        os.makedirs(GOLDEN_DIR, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(got, fh, ensure_ascii=False, indent=1)
        pytest.skip("golden gravado")
    with open(path, encoding="utf-8") as fh:
        want = json.load(fh)
    assert got["argv"] == want["argv"]
    assert got["console"] == want["console"]
