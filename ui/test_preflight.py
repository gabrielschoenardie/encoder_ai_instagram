from ui import preflight


def test_missing_all(tmp_path):
    assert set(preflight.missing_ffmpeg_binaries(which=lambda n: None, proj_dir=str(tmp_path))) == {"ffmpeg", "ffprobe"}


def test_none_missing_on_path(tmp_path):
    assert preflight.missing_ffmpeg_binaries(which=lambda n: "/usr/bin/" + n, proj_dir=str(tmp_path)) == []
