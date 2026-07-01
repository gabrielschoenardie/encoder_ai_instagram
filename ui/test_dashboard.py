"""Tests for ui.dashboard (pure: no subprocess, no engine)."""

import collections

from ui.dashboard import EncodeDashboard, make_dashboard
from ui.theme import get_console


def _render(dash) -> str:
    con = get_console(record=True, width=90)
    con.print(dash.render())
    return con.export_text()


def test_duck_types_update_frame():
    dash = make_dashboard(100, fps=30)
    assert hasattr(dash, "update_frame") and hasattr(dash, "render")
    dash.update_frame(50)
    assert dash.current_frame == 50


def test_update_frame_ignores_garbage():
    dash = make_dashboard(100)
    dash.update_frame("not-a-number")
    assert dash.current_frame == 0


def test_progress_and_metrics_render():
    dash = make_dashboard(200, fps=30)
    dash.update_frame(100)
    out = _render(dash)
    assert "100/200" in out
    assert "TIMELINE" in out
    assert "PERFORMANCE" in out
    assert "50.0%" in out


def test_log_sink_shown():
    sink = collections.deque(maxlen=50)
    for i in range(10):
        sink.append(f"ffmpeg line {i}\n")
    dash = make_dashboard(100, log_sink=sink)
    out = _render(dash)
    assert "ffmpeg line 9" in out


def test_render_without_frames():
    # Fresh dashboard must render (0%) without error.
    assert "0.0%" in _render(make_dashboard(100))


def test_progress_bar_animates_and_shows_percent():
    dash = make_dashboard(200, fps=30)
    dash.update_frame(100)
    out = _render(dash)
    assert "50.0%" in out
    assert "█" in out  # filled blocks present


def test_perf_panel_renders_gauge_or_fallback():
    out = _render(make_dashboard(100))
    assert "PERFORMANCE" in out  # gauges when psutil present, fallback text otherwise


def test_dashboard_shows_job_identity():
    dash = make_dashboard(100, fps=30, source="in.mov", output="out.mp4",
                          src_dims=(1080, 1920))
    out = _render(dash)
    assert "in.mov" in out and "out.mp4" in out


def test_dashboard_without_job_identity_still_renders():
    out = _render(make_dashboard(100))
    assert "TIMELINE" in out and "PERFORMANCE" in out


def test_dashboard_shows_live_viewer():
    dash = make_dashboard(200, fps=30, source="in.mov", output="out.mp4",
                          src_dims=(1080, 1920), fit="contain")
    con = get_console(record=True, width=100)
    con.print(dash.render())
    out = con.export_text()
    assert "PROGRAM" in out and "9:16" in out
    assert "TIMELINE" in out and "PERFORMANCE" in out


def test_dashboard_no_srcdims_uses_two_col():
    # No src_dims → no viewer column, unchanged 2-col layout.
    out = _render(make_dashboard(100))
    assert "TIMELINE" in out and "PERFORMANCE" in out
    assert "PROGRAM" not in out
