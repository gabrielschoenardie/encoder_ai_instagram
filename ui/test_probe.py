"""Tests for the best-effort, silent source-dims probe (ui.probe)."""

import json
import subprocess

import pytest

from Reels_Encoder_v2_FINAL import get_input_resolution
from ui.probe import probe_source_dims


def _payload(
    width=1920,
    height=1080,
    stream_rotate=None,
    display_matrix_rotation=None,
    format_rotate=None,
    streams=True,
):
    stream = {"width": width, "height": height}
    tags = {}
    if stream_rotate is not None:
        tags["rotate"] = stream_rotate
    if tags:
        stream["tags"] = tags

    if display_matrix_rotation is not None:
        stream["side_data_list"] = [
            {
                "side_data_type": "Display Matrix",
                "rotation": display_matrix_rotation,
            }
        ]

    data = {}
    if streams:
        data["streams"] = [stream]
    else:
        data["streams"] = []

    if format_rotate is not None:
        data["format"] = {"tags": {"rotate": format_rotate}}

    return json.dumps(data).encode()


def _fake_check_output_factory(payload):
    def _fake_check_output(cmd, stderr=None):
        return payload

    return _fake_check_output


ROTATION_MATRIX_CASES = [
    pytest.param({}, (1920, 1080), id="no_tag_no_side_data"),
    pytest.param(
        {"stream_rotate": "90"}, (1080, 1920), id="stream_rotate_90"
    ),
    pytest.param(
        {"stream_rotate": "180"}, (1920, 1080), id="stream_rotate_180_no_swap"
    ),
    pytest.param(
        {"stream_rotate": "270"}, (1080, 1920), id="stream_rotate_270"
    ),
    pytest.param(
        {"display_matrix_rotation": -90.000000},
        (1080, 1920),
        id="display_matrix_negative_90",
    ),
    pytest.param(
        {"stream_rotate": "90", "display_matrix_rotation": 0},
        (1080, 1920),
        id="tag_90_plus_display_matrix_0_does_not_erase_tag",
    ),
    pytest.param(
        {"stream_rotate": "180", "format_rotate": "90"},
        (1920, 1080),
        id="stream_rotate_wins_over_format_rotate",
    ),
    pytest.param(
        {"format_rotate": "90"},
        (1080, 1920),
        id="format_rotate_used_when_no_stream_rotation",
    ),
    pytest.param({"streams": False}, None, id="empty_streams_list"),
    pytest.param({"width": 0}, None, id="zero_width"),
]


@pytest.mark.parametrize("kwargs,expected", ROTATION_MATRIX_CASES)
def test_probe_rotation_matrix(monkeypatch, kwargs, expected):
    payload = _payload(**kwargs)
    monkeypatch.setattr(
        "ui.probe.subprocess.check_output", _fake_check_output_factory(payload)
    )
    assert probe_source_dims("irrelevant/path.mp4") == expected


def test_probe_argv_contract(monkeypatch):
    captured = {}

    def _fake_check_output(cmd, stderr=None):
        captured["cmd"] = cmd
        return _payload()

    monkeypatch.setattr("ui.probe.subprocess.check_output", _fake_check_output)

    probe_source_dims("some/input.mp4")

    cmd = captured["cmd"]
    assert (
        "stream=width,height:stream_tags=rotate:side_data:format_tags=rotate"
        in cmd
    )
    assert "some/input.mp4" in cmd
    assert "-select_streams" in cmd
    select_streams_index = cmd.index("-select_streams")
    assert cmd[select_streams_index + 1] == "v:0"


@pytest.mark.parametrize("kwargs,expected", ROTATION_MATRIX_CASES)
def test_probe_matches_engine_rotation_swap(monkeypatch, kwargs, expected):
    payload = _payload(**kwargs)

    monkeypatch.setattr(
        "ui.probe.subprocess.check_output", _fake_check_output_factory(payload)
    )
    monkeypatch.setattr(
        "Reels_Encoder_v2_FINAL.subprocess.check_output",
        _fake_check_output_factory(payload),
    )

    probe_dims = probe_source_dims("irrelevant/path.mp4")
    engine_dims = get_input_resolution("irrelevant/path.mp4")

    if expected is None:
        assert probe_dims is None
        assert engine_dims == (0, 0)
    else:
        assert probe_dims == engine_dims == expected


def test_probe_missing_binary_returns_none(monkeypatch):
    def _raise(cmd, stderr=None):
        raise FileNotFoundError("ffprobe not found")

    monkeypatch.setattr("ui.probe.subprocess.check_output", _raise)
    assert probe_source_dims("/nonexistent/file.mp4") is None


def test_probe_invalid_path_returns_none(monkeypatch):
    def _raise(cmd, stderr=None):
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr("ui.probe.subprocess.check_output", _raise)
    assert probe_source_dims("/nonexistent/file.mp4") is None


def test_probe_corrupted_output_returns_none(monkeypatch):
    def _fake_check_output(cmd, stderr=None):
        return b"not json"

    monkeypatch.setattr("ui.probe.subprocess.check_output", _fake_check_output)
    assert probe_source_dims("irrelevant/path.mp4") is None
