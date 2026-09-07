import os

from ui import binaries as B


def _none(_n):
    return None


def _ext(name):
    return name + (".exe" if os.name == "nt" else "")


def test_bundled_wins_over_path(tmp_path):
    binp = tmp_path / "bin"
    binp.mkdir()
    (binp / _ext("ffmpeg")).write_text("x")
    got = B.resolve_binary("ffmpeg", which=lambda n: "/usr/bin/ffmpeg", proj_dir=str(tmp_path), env={})
    assert got == str(binp / _ext("ffmpeg"))


def test_path_used_when_no_bundle(tmp_path):
    got = B.resolve_binary("ffmpeg", which=lambda n: "/usr/bin/ffmpeg", proj_dir=str(tmp_path), env={})
    assert got == "/usr/bin/ffmpeg"


def test_bare_fallback_when_missing(tmp_path):
    got = B.resolve_binary("ffmpeg", which=_none, proj_dir=str(tmp_path), env={})
    assert os.path.basename(got).startswith("ffmpeg")


def test_find_missing_lists_absent(tmp_path):
    missing = B.find_missing_binaries(("ffmpeg", "ffprobe"), which=_none, proj_dir=str(tmp_path), env={})
    assert missing == ["ffmpeg", "ffprobe"]


def test_find_missing_empty_when_bundled(tmp_path):
    binp = tmp_path / "bin"
    binp.mkdir()
    for n in ("ffmpeg", "ffprobe"):
        (binp / _ext(n)).write_text("x")
    assert B.find_missing_binaries(("ffmpeg", "ffprobe"), which=_none, proj_dir=str(tmp_path), env={}) == []


def test_find_missing_empty_when_on_path(tmp_path):
    assert B.find_missing_binaries(("ffmpeg",), which=lambda n: "/usr/bin/" + n, proj_dir=str(tmp_path), env={}) == []


def test_ffplay_optional(tmp_path):
    assert "ffplay" not in B.find_missing_binaries(which=_none, proj_dir=str(tmp_path), env={})


def test_available(tmp_path):
    assert B.available("ffmpeg", which=lambda n: "/x/ffmpeg", proj_dir=str(tmp_path), env={}) is True
    assert B.available("ffmpeg", which=_none, proj_dir=str(tmp_path), env={}) is False


def test_env_wins_over_bundled(tmp_path):
    binp = tmp_path / "bin"
    binp.mkdir()
    (binp / _ext("ffmpeg")).write_text("x")
    pinned = tmp_path / "pinned-ffmpeg"
    pinned.write_text("x")
    got = B.resolve_binary(
        "ffmpeg", which=lambda n: "/usr/bin/ffmpeg", proj_dir=str(tmp_path), env={"REELS_FFMPEG": str(pinned)}
    )
    assert got == str(pinned)


def test_env_pointing_at_missing_file_is_ignored(tmp_path):
    binp = tmp_path / "bin"
    binp.mkdir()
    (binp / _ext("ffmpeg")).write_text("x")
    got = B.resolve_binary(
        "ffmpeg", which=_none, proj_dir=str(tmp_path), env={"REELS_FFMPEG": str(tmp_path / "nao-existe")}
    )
    assert got == str(binp / _ext("ffmpeg"))


def test_env_absent_preserves_old_order(tmp_path):
    binp = tmp_path / "bin"
    binp.mkdir()
    (binp / _ext("ffmpeg")).write_text("x")
    got = B.resolve_binary(
        "ffmpeg", which=lambda n: "/usr/bin/ffmpeg", proj_dir=str(tmp_path), env={"REELS_FFPROBE": "/x/ffprobe"}
    )
    assert got == str(binp / _ext("ffmpeg"))


def test_available_sees_env(tmp_path):
    pinned = tmp_path / "pinned-ffmpeg"
    pinned.write_text("x")
    assert B.available("ffmpeg", which=_none, proj_dir=str(tmp_path), env={"REELS_FFMPEG": str(pinned)}) is True


def test_find_missing_sees_env(tmp_path):
    pinned = tmp_path / "pinned-ffprobe"
    pinned.write_text("x")
    missing = B.find_missing_binaries(
        ("ffmpeg", "ffprobe"), which=_none, proj_dir=str(tmp_path), env={"REELS_FFPROBE": str(pinned)}
    )
    assert missing == ["ffmpeg"]
