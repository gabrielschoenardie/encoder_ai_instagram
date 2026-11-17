"""R-06: MCTF não escreve no console da TUI (ffmpeg filho sem stdout herdado, barra Rich desligada)."""
import argparse
import os
import subprocess
import sys

import pytest

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import enhance_visualizer as V  # noqa: E402
import Reels_Encoder_v2_FINAL as RE  # noqa: E402


class _Cap:
    def isOpened(self):
        return True

    def get(self, prop):
        return {V.cv2.CAP_PROP_FPS: 30.0, V.cv2.CAP_PROP_FRAME_WIDTH: 16, V.cv2.CAP_PROP_FRAME_HEIGHT: 16}.get(prop, 0)

    def read(self):
        return False, None

    def release(self):
        pass


class _Proc:
    class stdin:
        @staticmethod
        def close():
            pass

    def wait(self):
        return 0


def test_mctf_ffmpeg_writers_do_not_inherit_stdout(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(V.cv2, "VideoCapture", lambda path: _Cap())
    monkeypatch.setattr(subprocess, "Popen", lambda args, **kw: calls.append(kw) or _Proc())
    out = V.generate_mctf_mask_video("in.mov", out_dir=str(tmp_path), show_progress=False)
    assert out["frames"] == 0 and len(calls) == 2
    for kw in calls:
        assert kw["stdout"] == subprocess.DEVNULL and kw["stderr"] == subprocess.DEVNULL
        assert kw["stdin"] == subprocess.PIPE


class _Stop(BaseException):
    pass


class _Reporter:
    def emit(self, ev):
        pass


@pytest.mark.parametrize("reporter, is_batch, want", [(_Reporter(), False, False), (None, False, True),
                                                      (None, True, False)])
def test_encode_single_file_mctf_progress_off_under_reporter(tmp_path, monkeypatch, reporter, is_batch, want):
    seen = []

    def fake_mctf(path, **kw):
        seen.append(kw)
        raise _Stop

    monkeypatch.setattr(RE, "ENHANCE_AVAILABLE", True)
    monkeypatch.setattr(V, "run_preflight", lambda path, samples=3: {"out_dir": str(tmp_path), "masks": {}})
    monkeypatch.setattr(V, "generate_mctf_mask_video", fake_mctf)
    args = argparse.Namespace(enhance="on", enhance_ai="on", mctf="on")
    with pytest.raises(_Stop):
        RE._encode_single_file(str(tmp_path / "in.mov"), str(tmp_path / "out.mp4"), args,
                               is_batch=is_batch, reporter=reporter)
    assert seen == [{"out_dir": "enhance_maps", "show_progress": want}]
