"""Tests for the pure aspect-ratio classifier (ui.aspect)."""

from ui.aspect import classify_aspect, describe_aspect, orientation_of


def test_classify_known_ratios():
    assert classify_aspect(1080, 1920) == "9:16"
    assert classify_aspect(1920, 1080) == "16:9"
    assert classify_aspect(1920, 1440) == "4:3"
    assert classify_aspect(1440, 1920) == "3:4"
    assert classify_aspect(1000, 1000) == "1:1"


def test_classify_invalid_dims():
    assert classify_aspect(0, 1920) == "?"
    assert classify_aspect(1080, 0) == "?"
    assert classify_aspect(-10, 100) == "?"


def test_classify_weird_ratio_reduces():
    # 1000x300 → 10:3, not one of the known anchors
    assert classify_aspect(1000, 300) == "10:3"


def test_orientation_of():
    assert orientation_of(1080, 1920) == "portrait"
    assert orientation_of(1920, 1080) == "landscape"
    assert orientation_of(1000, 1000) == "square"
    assert orientation_of(0, 0) == "?"


def test_describe_aspect_basic():
    assert describe_aspect(1080, 1920) == "9:16 vertical"
    assert describe_aspect(1920, 1080) == "16:9 horizontal"
    assert describe_aspect(1000, 1000) == "1:1 quadrado"


def test_describe_aspect_iphone_note():
    # rotation in (90, -90, 270, -270) appends the auto-rotate note
    out = describe_aspect(1080, 1920, rotation=90)
    assert "9:16 vertical" in out
    assert "iPhone auto-rotate" in out
    # no note for non-rotated
    assert "iPhone" not in describe_aspect(1080, 1920, rotation=0)
