from __future__ import annotations

import os

import pytest

import Reels_Encoder_v2_FINAL as RE
from ui.tui import app as A


def _exe(name: str) -> str:
    return name + ".exe" if os.name == "nt" else name


def _fake(folder, name: str):
    folder.mkdir(parents=True, exist_ok=True)
    p = folder / _exe(name)
    p.write_text("x")
    if os.name != "nt":
        p.chmod(0o755)
    return p


@pytest.fixture
def env(tmp_path, monkeypatch):
    root = tmp_path / "root"
    root.mkdir()
    path_dir = tmp_path / "pathdir"
    ffmpeg = _fake(path_dir, "ffmpeg")
    monkeypatch.setattr("ui.binaries._proj_dir", lambda: str(root))
    monkeypatch.setenv("PATH", str(path_dir))
    for var in ("REELS_FFPLAY", "REELS_FFMPEG", "REELS_FFPROBE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(RE, "FFMPEG", str(ffmpeg))
    return tmp_path, root, path_dir


def _ffplay_row() -> str:
    return dict(A.App._system_rows())["ffplay"]


def test_ffplay_only_in_bundled_bin(env):
    _, root, _ = env
    _fake(root / "bin", "ffplay")
    assert _ffplay_row() == "ok"


def test_ffplay_only_via_env(env, monkeypatch):
    tmp_path, _, _ = env
    p = _fake(tmp_path / "elsewhere", "ffplay")
    monkeypatch.setenv("REELS_FFPLAY", str(p))
    assert _ffplay_row() == "ok"


def test_ffplay_only_on_path(env, monkeypatch):
    tmp_path, _, path_dir = env
    other = tmp_path / "otherpath"
    _fake(other, "ffplay")
    monkeypatch.setenv("PATH", os.pathsep.join([str(path_dir), str(other)]))
    assert _ffplay_row() == "ok"


def test_ffplay_absent(env):
    row = _ffplay_row()
    assert row.startswith("⚠ ausente")
    assert "monitor EBU desligado" in row


@pytest.mark.parametrize("where", ["bin", "env", "path"])
def test_ffplay_path_with_spaces(env, monkeypatch, where):
    tmp_path, root, path_dir = env
    spaced = tmp_path / "pasta com espaco"
    if where == "bin":
        monkeypatch.setattr("ui.binaries._proj_dir", lambda: str(spaced))
        _fake(spaced / "bin", "ffplay")
    elif where == "env":
        monkeypatch.setenv("REELS_FFPLAY", str(_fake(spaced, "ffplay")))
    else:
        _fake(spaced, "ffplay")
        monkeypatch.setenv("PATH", os.pathsep.join([str(path_dir), str(spaced)]))
    assert _ffplay_row() == "ok"


def test_other_rows_and_order_unchanged(env):
    rows = A.App._system_rows()
    assert [k for k, _ in rows] == ["FFmpeg", "ffprobe", "ffplay", "hardware"]
    d = dict(rows)
    assert d["FFmpeg"] == os.path.basename(RE.FFMPEG)
    assert d["ffprobe"] == os.path.basename(RE.FFPROBE)
    assert d["hardware"] == "detectado no início do encode"
