"""Render-smoke tests for ui.components / ui.prompts (no stdin, no engine).

Each renderable must build and render under a recording Console without error,
and produce non-empty output.
"""

from ui import components as C
from ui.config import EncodeConfig
from ui.prompts import render_choice_menu
from ui.theme import get_console


def _render(renderable) -> str:
    # Components reference named theme styles, so render on a themed console
    # (the real contract: the UI always uses get_console()).
    con = get_console(record=True, width=80)
    con.print(renderable)
    return con.export_text()


def test_banner_renders():
    assert _render(C.banner("REELS ENCODER", "Premiere")).strip()


def test_tab_bar_marks_active():
    out = _render(C.tab_bar(["Source", "Color", "Audio"], active=1))
    assert "Color" in out and "Source" in out


def test_program_panel_renders():
    out = _render(C.program_panel("in.mov", "out.mp4", ["4K HDR"]))
    assert "in.mov" in out and "out.mp4" in out


def test_properties_panel_renders():
    out = _render(C.properties_panel([("Resolution", "1080x1920"), ("LUT", "Hollywood")]))
    assert "Resolution" in out and "Hollywood" in out


def test_quality_chip_states():
    assert "LUT" in _render(C.quality_chip("LUT", True))
    assert "AI" in _render(C.quality_chip("AI", False))
    assert "X" in _render(C.quality_chip("X", None))


def test_log_panel_bounds_lines():
    lines = [f"line {i}" for i in range(20)]
    out = _render(C.log_panel(lines, max_lines=3))
    assert "line 19" in out
    assert "line 0" not in out


def test_log_panel_empty():
    assert _render(C.log_panel([])).strip()


def test_notification_levels():
    for lvl in ("info", "ok", "warn", "err"):
        assert _render(C.notification("msg", lvl)).strip()


def test_settings_preview_ffmpeg():
    cfg = EncodeConfig(input="clip.mov", lut="on", loudnorm="on")
    out = _render(C.settings_preview(cfg))
    assert "FFmpeg Native" in out
    assert "clip.mov" in out


def test_settings_preview_cineon():
    cfg = EncodeConfig(input="clip.mov", cineon_pipeline="on", exposure_offset=0.5, saturation=1.2)
    out = _render(C.settings_preview(cfg))
    assert "Cineon Film" in out


def test_settings_preview_elides_long_paths():
    # A deep absolute path must not clip the PREVIEW title and swallow the
    # output filename: the launcher shows source → output there.
    longin = ("C:/Users/someone/Videos/projects/2026/reels/raw/"
              "a_really_quite_long_source_clip_filename.mov")
    cfg = EncodeConfig(input=longin)
    out = _render(C.settings_preview(cfg))
    assert "→" in out
    # the output's extension survives instead of being clipped off
    assert ".mp4" in out
    # the deep directory is not crammed into the title
    assert "projects" not in out


def test_render_choice_menu():
    out = _render(render_choice_menu("Preset", ["Quick", "Film", "Batch"]))
    assert "Quick" in out and "Film" in out and "Batch" in out


def test_delivery_seal_ready():
    checks = [
        ("Loudness", "-14.0 LUFS", True),
        ("True Peak", "-1.5 dBTP", True),
        ("Codec", "aac", True),
        ("Sample Rate", "48000", True),
    ]
    out = _render(C.delivery_seal(checks))
    assert "MASTER QC" in out
    assert "Loudness" in out
    # the seal renders letter-spaced ("D E L I V E R Y")
    assert "DELIVERY" in out.replace(" ", "")


def test_delivery_seal_review():
    checks = [
        ("Loudness", "-9.0 LUFS", False),
        ("True Peak", "-1.5 dBTP", True),
        ("Codec", "aac", True),
        ("Sample Rate", "48000", True),
    ]
    out = _render(C.delivery_seal(checks))
    assert "MASTER QC" in out
    # the seal renders letter-spaced ("R E V I S A R")
    assert "REVISAR" in out.replace(" ", "")


def test_aspect_frame_contain_vs_cover():
    c = _render(C._aspect_frame("contain"))
    v = _render(C._aspect_frame("cover"))
    assert "9:16" in c and "9:16" in v
    assert "contain" in c
    assert "cover" in v
    assert c != v


def test_program_panel_shows_9_16_frame():
    out = _render(C.program_panel("in.mov", "out.mp4", ["4K HDR"], fit="cover"))
    assert "in.mov" in out and "out.mp4" in out
    assert "9:16" in out


def test_program_split_renders():
    out = _render(C.program_split("clip.mov", "clip_out.mp4",
                                  [("LUT", "Hollywood")], fit="contain"))
    assert "clip.mov" in out and "Hollywood" in out and "9:16" in out


def test_settings_preview_has_program_viewer():
    cfg = EncodeConfig(input="clip.mov", lut="on", loudnorm="on")
    out = _render(C.settings_preview(cfg))
    assert "FFmpeg Native" in out
    assert "9:16" in out


def test_program_panel_reflects_16_9_source():
    out = _render(C.program_panel("c.mov", "o.mp4", src_dims=(1920, 1080)))
    assert "16:9" in out
    assert "1920 x 1080" in out


def test_program_panel_reflects_9_16_source():
    out = _render(C.program_panel("c.mov", "o.mp4", src_dims=(1080, 1920)))
    assert "9:16" in out
    assert "1080 x 1920" in out


def test_settings_preview_reflects_16_9_source():
    cfg = EncodeConfig(input="clip.mov", lut="on", loudnorm="on")
    out = _render(C.settings_preview(cfg, src_dims=(1920, 1080)))
    assert "16:9" in out


def test_delivery_seal_unknown_renders():
    checks = [
        ("Loudness", "—", None),
        ("True Peak", "-1.5 dBTP", True),
    ]
    out = _render(C.delivery_seal(checks))
    assert "Loudness" in out


def test_gauge_bar_renders():
    out = _render(C.gauge_bar(45))
    assert out.strip() != ""


def test_gauge_bar_fill_scales_with_pct():
    low = _render(C.gauge_bar(10, width=12))
    high = _render(C.gauge_bar(90, width=12))
    assert high.count("█") > low.count("█")


def test_gauge_bar_clamps_out_of_range():
    # must not raise and must not exceed width
    assert _render(C.gauge_bar(150, width=10)).count("█") <= 10
    assert _render(C.gauge_bar(-20, width=10)).count("█") == 0
