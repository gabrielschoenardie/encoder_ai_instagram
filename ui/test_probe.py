"""Tests for the best-effort, silent source-dims probe (ui.probe)."""

from ui.probe import probe_source_dims


def test_probe_nonexistent_returns_none():
    # Must degrade gracefully (no raise) when the path does not exist or
    # ffprobe is unavailable.
    assert probe_source_dims("/nonexistent/file.mp4") is None


def test_probe_empty_path_returns_none():
    assert probe_source_dims("") is None
