"""P3HF2: a máscara MCTF executa o FFmpeg resolvido por ui.binaries, não o literal "ffmpeg"."""
import os
import subprocess
import sys

import pytest

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import enhance_visualizer as V  # noqa: E402
import ui.binaries as B  # noqa: E402


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


def _fake_exe(directory):
    directory.mkdir(parents=True, exist_ok=True)
    p = directory / B._exe_name("ffmpeg")
    p.write_bytes(b"")
    p.chmod(0o755)
    return str(p)


@pytest.fixture
def env(tmp_path, monkeypatch):
    root = tmp_path / "proj"
    root.mkdir()
    empty = tmp_path / "empty_path"
    empty.mkdir()
    monkeypatch.setattr(B, "_proj_dir", lambda: str(root))
    monkeypatch.delenv("REELS_FFMPEG", raising=False)
    monkeypatch.setenv("PATH", str(empty))
    monkeypatch.chdir(tmp_path)
    return root


def _run(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(V.cv2, "VideoCapture", lambda path: _Cap())
    monkeypatch.setattr(subprocess, "Popen", lambda args, **kw: calls.append((args, kw)) or _Proc())
    out = V.generate_mctf_mask_video("in.mov", out_dir=str(tmp_path / "out"), show_progress=False)
    assert out["frames"] == 0 and len(calls) == 2
    return calls


def test_bundled_bin_only(env, tmp_path, monkeypatch):
    exe = _fake_exe(env / "bin")
    for args, _ in _run(tmp_path, monkeypatch):
        assert args[0] == exe


def test_env_wins_over_bundled(env, tmp_path, monkeypatch):
    _fake_exe(env / "bin")
    pinned = _fake_exe(tmp_path / "pinned")
    monkeypatch.setenv("REELS_FFMPEG", pinned)
    for args, _ in _run(tmp_path, monkeypatch):
        assert args[0] == pinned


def test_path_only(env, tmp_path, monkeypatch):
    on_path = tmp_path / "on_path"
    exe = _fake_exe(on_path)
    monkeypatch.setenv("PATH", str(on_path))
    for args, _ in _run(tmp_path, monkeypatch):
        assert os.path.normcase(args[0]) == os.path.normcase(exe)


def test_space_in_path_via_env(env, tmp_path, monkeypatch):
    pinned = _fake_exe(tmp_path / "pasta com espaço")
    monkeypatch.setenv("REELS_FFMPEG", pinned)
    for args, kw in _run(tmp_path, monkeypatch):
        assert args[0] == pinned and " " in args[0]
        assert args.count(pinned) == 1
        assert not kw.get("shell")


def test_space_in_path_via_bundled(tmp_path, monkeypatch):
    root = tmp_path / "pasta com espaço"
    root.mkdir()
    empty = tmp_path / "empty_path"
    empty.mkdir()
    monkeypatch.setattr(B, "_proj_dir", lambda: str(root))
    monkeypatch.delenv("REELS_FFMPEG", raising=False)
    monkeypatch.setenv("PATH", str(empty))
    monkeypatch.chdir(tmp_path)
    exe = _fake_exe(root / "bin")
    for args, kw in _run(tmp_path, monkeypatch):
        assert args[0] == exe and " " in args[0]
        assert not kw.get("shell")


def test_nothing_available_uses_resolver_fallback(env, tmp_path, monkeypatch):
    want = B._exe_name("ffmpeg") if os.name == "nt" else "ffmpeg"
    for args, _ in _run(tmp_path, monkeypatch):
        assert args[0] == want


@pytest.mark.parametrize("writer", [0, 1], ids=["deband", "sharpen"])
def test_remaining_args_and_kwargs_preserved(env, tmp_path, monkeypatch, writer):
    _fake_exe(env / "bin")
    args, kw = _run(tmp_path, monkeypatch)[writer]
    out_name = ["mctf_deband_mask.mp4", "mctf_sharpen_mask.mp4"][writer]
    out_path = os.path.abspath(os.path.join(str(tmp_path / "out"), out_name))
    assert args[1:] == ["-y", "-f", "rawvideo", "-pix_fmt", "gray", "-video_size", "16x16", "-r", "30.0",
                        "-i", "pipe:0", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "0",
                        "-preset", "ultrafast", out_path]
    assert kw == {"stdin": subprocess.PIPE, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}


def test_env_changed_after_import_is_respected(env, tmp_path, monkeypatch):
    first = _fake_exe(env / "bin")
    assert all(a[0] == first for a, _ in _run(tmp_path, monkeypatch))
    pinned = _fake_exe(tmp_path / "late")
    monkeypatch.setenv("REELS_FFMPEG", pinned)
    assert all(a[0] == pinned for a, _ in _run(tmp_path, monkeypatch))
