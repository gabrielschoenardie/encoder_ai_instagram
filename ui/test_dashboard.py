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
