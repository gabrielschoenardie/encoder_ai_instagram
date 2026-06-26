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


def test_delivery_seal_unknown_renders():
    checks = [
        ("Loudness", "—", None),
        ("True Peak", "-1.5 dBTP", True),
    ]
    out = _render(C.delivery_seal(checks))
    assert "Loudness" in out
