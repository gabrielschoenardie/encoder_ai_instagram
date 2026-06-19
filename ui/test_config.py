"""Unit tests for ui.config.EncodeConfig (pure: no engine, no subprocess)."""

import argparse

import pytest

from ui.config import DEFAULT_CINEON_LUT, EncodeConfig


# The complete set of argparse dest names the engine reads off `args`.
ENGINE_ATTRS = {
    "input", "batch", "output_dir", "mode", "fps", "scale", "fit", "performance",
    "threads", "lut", "hdr", "tonemap", "loudnorm", "ebu_meter", "cineon_pipeline",
    "cineon_lut", "exposure_offset", "saturation", "enhance", "enhance_ai", "mctf",
    "dither", "show_hardware", "hardware_info", "ui",
}


def test_defaults_match_argparse_defaults():
    """EncodeConfig defaults must equal the argparse defaults in the engine."""
    cfg = EncodeConfig()
    ns = cfg.to_namespace()
    assert ns.mode == "crf"
    assert ns.lut == "on"
    assert ns.loudnorm == "on"
    assert ns.ebu_meter == "on"
    assert ns.hdr == "auto"
    assert ns.tonemap == "mobius"
    assert ns.fps == "30"
    assert ns.scale == "auto"
    assert ns.fit == "contain"
    assert ns.show_hardware == "on"
    assert ns.threads == 0
    assert ns.performance == "balanced"
    assert ns.cineon_pipeline == "off"
    assert ns.cineon_lut == DEFAULT_CINEON_LUT
    assert ns.exposure_offset == 0.0
    assert ns.saturation == 1.0
    assert ns.enhance == "off"
    assert ns.enhance_ai == "off"
    assert ns.mctf == "off"
    assert ns.dither == "auto"
    assert ns.hardware_info is False
    assert ns.ui is False


def test_namespace_has_every_engine_attribute():
    """to_namespace must expose every attribute the engine accesses."""
    ns = EncodeConfig().to_namespace()
    for attr in ENGINE_ATTRS:
        assert hasattr(ns, attr), f"Namespace missing engine attr: {attr}"


def test_round_trip_namespace():
    """from_namespace(to_namespace(x)) preserves all fields."""
    cfg = EncodeConfig(input="a.mp4", mode="2pass", cineon_pipeline="on", saturation=1.3)
    ns = cfg.to_namespace()
    back = EncodeConfig.from_namespace(ns)
    assert back == cfg


def test_from_namespace_ignores_unknown_attrs():
    ns = argparse.Namespace(input="x.mp4", mode="crf", some_future_flag=123)
    cfg = EncodeConfig.from_namespace(ns)
    assert cfg.input == "x.mp4"
    assert cfg.mode == "crf"


@pytest.mark.parametrize("field,bad", [
    ("mode", "lossless"),
    ("fps", "120"),
    ("tonemap", "aces"),
    ("dither", "maybe"),
    ("fit", "stretch"),
])
def test_invalid_choice_rejected(field, bad):
    with pytest.raises(ValueError):
        EncodeConfig(**{field: bad})


@pytest.mark.parametrize("field,bad", [
    ("exposure_offset", 3.0),
    ("exposure_offset", -2.5),
    ("saturation", -0.1),
    ("saturation", 2.1),
    ("threads", -1),
])
def test_numeric_range_rejected(field, bad):
    with pytest.raises(Exception):
        EncodeConfig(**{field: bad})


def test_output_path_matches_engine_naming():
    assert EncodeConfig(input="clip.mov").output_path() == "clip_Hollywood_CRF18.mp4"
    assert EncodeConfig(input="clip.mov", mode="2pass").output_path() == "clip_Hollywood_2Pass.mp4"
    assert EncodeConfig(input="clip.mov", cineon_pipeline="on").output_path() == "clip_Cineon_Film.mp4"
    assert EncodeConfig().output_path() is None


def test_presets():
    assert EncodeConfig.preset_quick_ffmpeg("a.mp4").cineon_pipeline == "off"
    assert EncodeConfig.preset_film_cineon("a.mp4").cineon_pipeline == "on"
    assert EncodeConfig.preset_batch("./clips").batch == "./clips"
